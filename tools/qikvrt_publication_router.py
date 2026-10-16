#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed publication router for QIK-VRT publication bundles."""
from __future__ import annotations
import argparse, hashlib, html, io, json, os, re, subprocess, sys
from pathlib import Path

AUTHORITY = "ingolf-lohmann/qik-vrt"
EDITORIAL_SCHEMA = "qikvrt_editorial_publication_request_v1"
EDITORIAL_QUEUE = "state/publication_requests"
PUBLIC_ORIGIN = "https://raumzeitterminal.de"
ROUTER_WORKFLOW = "qikvrt_publication_router.yml"


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def _committed(root, path, head, executor, publication):
    raw = publication.zenodo.read_regular_file(path, publication.zenodo.MAX_JSON_BYTES)
    relative = path.relative_to(root).as_posix()
    if executor._git(root, "rev-parse", "--verify", head + ":" + relative) != publication._git_blob_sha(raw):
        raise ValueError("editorial control differs from its committed bytes")
    return raw


def _manuscript_format(path, raw):
    """Structural/readability gate only; human content and visual review remain separate."""
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ".tex"}:
        text = raw.decode("utf-8")
        if not text.strip() or "\x00" in text:
            raise ValueError("empty or binary manuscript")
        return {"format": suffix[1:], "utf8_nonempty": True, "visual_review": "SEPARATE"}
    if suffix == ".pdf":
        # pypdf is already hash/version locked by the publication runtime.
        import importlib.metadata
        if importlib.metadata.version("pypdf") != "6.15.0":
            raise ValueError("locked PDF inspection runtime unavailable")
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 2000:
            raise ValueError("encrypted or invalid manuscript PDF")
        if not any((page.extract_text() or "").strip() for page in reader.pages):
            raise ValueError("manuscript PDF lacks machine-readable text")
        return {"format": "pdf", "pages": len(reader.pages), "extractable_text": True,
                "visual_review": "SEPARATE_CANDIDATE_REVIEW_REQUIRED"}
    raise ValueError("unsupported manuscript format")


def editorial_intake(root: Path, request_relative: str, *, committed_head=None):
    """Receive repository manuscripts without manufacturing proof or author consent."""
    root = root.resolve(strict=True)
    executor, publication, _ = _publication_dependencies()
    path = publication._safe_relative(root, request_relative, "editorial request", must_exist=True)
    relative = path.relative_to(root).as_posix()
    if path.parent != root / EDITORIAL_QUEUE or path.suffix != ".json":
        raise ValueError("editorial request must be in the reviewed intake queue")
    raw = (_committed(root, path, committed_head, executor, publication) if committed_head else
           publication.zenodo.read_regular_file(path, publication.zenodo.MAX_JSON_BYTES))
    request = json.loads(raw)
    keys = {"schema", "publication_id", "manifest_path", "manifest_sha256", "manuscript_paths", "website"}
    if (not isinstance(request, dict) or set(request) != keys or request["schema"] != EDITORIAL_SCHEMA
            or not isinstance(request["publication_id"], str)
            or re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,95}", request["publication_id"]) is None
            or re.fullmatch(r"[0-9a-f]{64}", str(request["manifest_sha256"])) is None):
        raise ValueError("invalid editorial request")
    site = request["website"]
    if (not isinstance(site, dict) or set(site) != {"origin", "path"}
            or site["origin"] != PUBLIC_ORIGIN
            or site["path"] != "/publications/" + request["publication_id"] + "/"):
        raise ValueError("editorial website must retain the exact delivery origin and publication path")
    manuscript_paths = request["manuscript_paths"]
    if (not isinstance(manuscript_paths, list) or not 1 <= len(manuscript_paths) <= 32
            or not all(isinstance(p, str) for p in manuscript_paths)
            or len(set(manuscript_paths)) != len(manuscript_paths)):
        raise ValueError("invalid manuscript selection")
    manifest_path = publication._safe_relative(root, request["manifest_path"], "editorial manifest", must_exist=True)
    manifest_raw = (_committed(root, manifest_path, committed_head, executor, publication) if committed_head else
                    publication.zenodo.read_regular_file(manifest_path, publication.zenodo.MAX_JSON_BYTES))
    if hashlib.sha256(manifest_raw).hexdigest() != request["manifest_sha256"]:
        raise ValueError("editorial manifest digest differs")
    value = json.loads(manifest_raw)
    if not isinstance(value, dict) or value.get("schema") != publication.SCHEMA_V2 or value.get("repository") != AUTHORITY:
        raise ValueError("editorial intake requires an Authority v2 candidate")
    by_path = {f["path"]: f for f in value.get("files", []) if isinstance(f, dict) and isinstance(f.get("path"), str)}
    formats = []
    for manuscript in manuscript_paths:
        if manuscript not in by_path:
            raise ValueError("manuscript is outside the exact upload fileset")
        item = publication._materialize_file(by_path[manuscript], root, "editorial manuscript")
        source = publication._safe_relative(root, manuscript, "editorial manuscript", must_exist=True)
        raw_source = publication.zenodo.read_regular_file(source, publication.zenodo.MAX_UPLOAD_BYTES)
        formats.append({**item, **_manuscript_format(source, raw_source)})
    result = {"schema": "qikvrt_editorial_intake_v1", "request_path": relative,
              "request_sha256": hashlib.sha256(raw).hexdigest(), "publication_id": request["publication_id"],
              "manifest_path": request["manifest_path"], "manifest_sha256": request["manifest_sha256"],
              "website": site, "manuscripts": formats, "state": "HOLD_PROOF_OR_INDIVIDUAL_AUTHOR_AUTHORIZATION",
              "external_effect_performed": False, "effect_ack_done": False}
    try:
        manifest = publication.load_manifest(manifest_path, root)
    except publication.zenodo.ZenodoError:
        return result  # Drafts can enter; neither proof nor consent is generated.
    proof = manifest["machine_proof"]
    if (proof["publication_id"] != request["publication_id"]
            or not set(manuscript_paths).issubset({f["path"] for f in proof["returned_candidate_files"]})):
        raise ValueError("editorial manuscript was not returned for this exact publication")
    # The active publisher policy supports its named natural-person principal.
    # Multi-author intake must not treat one person's grant as everybody's grant.
    if len(manifest["metadata"]["creators"]) != 1:
        result["state"] = "HOLD_INDIVIDUAL_COAUTHOR_APPROVAL_PROTOCOL"
        return result
    if committed_head:
        if publication._validate_repository_source_head(root, manifest_path, manifest) != committed_head:
            raise ValueError("editorial execution source differs")
    result.update(state="READY_EXACT_AUTHOR_AUTHORIZED", author=manifest["owner_authorization"]["principal"],
                  proof_publication_id=proof["publication_id"],
                  authorization_consumption_key=manifest["owner_authorization"]["consumption_key"]["value"])
    return result


def _rest(method, endpoint, data=None):
    """Bound REST-only wrapper; never reflect provider errors or credentials."""
    if (method not in {"GET", "POST"} or not endpoint.startswith("repos/" + AUTHORITY + "/")
            or any(c in endpoint for c in ("\r", "\n", "#"))):
        raise ValueError("editorial REST scope invalid")
    if method == "POST" and endpoint not in {
            "repos/" + AUTHORITY + "/git/refs",
            "repos/" + AUTHORITY + "/actions/workflows/" + ROUTER_WORKFLOW + "/dispatches"}:
        raise ValueError("editorial REST effect outside the existing router")
    if method == "POST" and endpoint.endswith("/git/refs") and (
            not isinstance(data, dict) or set(data) != {"ref", "sha"}
            or re.fullmatch(r"refs/tags/qikvrt-editorial-dispatch/[0-9a-f]{64}", str(data["ref"])) is None
            or re.fullmatch(r"[0-9a-f]{40}", str(data["sha"])) is None):
        raise ValueError("editorial reservation is not a create-only dispatch tag")
    args = ["gh", "api", "--hostname", "github.com", "--method", method, endpoint]
    if data is not None:
        args += ["--input", "-"]
    response = subprocess.run(args, input=None if data is None else json.dumps(data),
                              capture_output=True, text=True, timeout=60, check=False)
    if response.returncode:
        raise ValueError("editorial REST unavailable; reconcile before another effect")
    return json.loads(response.stdout) if response.stdout.strip() else None


def _pages(endpoint):
    rows = []
    for page in range(1, 101):
        value = _rest("GET", endpoint + ("&" if "?" in endpoint else "?") + f"per_page=100&page={page}")
        if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
            raise ValueError("incomplete editorial REST inventory")
        rows.extend(value)
        if len(value) < 100:
            return rows
    raise ValueError("editorial REST inventory exceeded its bound")


def _main_governance(root, head):
    """Reuse native Code Owner policy for the actual merged Main carrier."""
    from tools import qikvrt_required_review_gate as review
    prefix = "repos/" + AUTHORITY
    rules = _pages(prefix + "/rules/branches/main")
    if not review.native_code_owner_rule_is_enforced(rules):
        raise ValueError("CODE_OWNER_RULE_NOT_ENFORCED")
    pulls = _pages(prefix + "/commits/" + head + "/pulls")
    candidates = [p for p in pulls if p.get("merged_at") and p.get("merge_commit_sha") == head
                  and p.get("base", {}).get("repo", {}).get("full_name") == AUTHORITY
                  and p.get("base", {}).get("ref") == "main" and not p.get("draft")]
    for pr in candidates:
        owner = review.resolve_required_code_owner(AUTHORITY, pr_author=pr["user"]["login"])
        reviews = _pages(prefix + f"/pulls/{int(pr['number'])}/reviews")
        gate = review.evaluate_required_review(pr, rules, reviews, required_code_owner=owner)
        if gate["gate_state"] == "success":
            return gate
    raise ValueError("EXACT_MAIN_MERGE_REVIEW_NOT_VERIFIED")


def dispatch_editorial_queue(root: Path):
    """A reviewed Main push supplies exact inputs to the existing manual-effect lane."""
    root = root.resolve(strict=True)
    executor, publication, _ = _publication_dependencies()
    head = executor._git(root, "rev-parse", "--verify", "HEAD^{commit}")
    tree = executor._git(root, "rev-parse", "--verify", "HEAD^{tree}")
    if (os.environ.get("GITHUB_EVENT_NAME") != "push" or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_REPOSITORY") != AUTHORITY or os.environ.get("GITHUB_SHA") != head
            or executor.load_repository_roles(root)["AUTHORITY"] != AUTHORITY):
        raise ValueError("automatic editorial admission requires the exact Authority Main push")
    paths = sorted((root / EDITORIAL_QUEUE).glob("*.json"))
    if len(paths) > 100:
        raise ValueError("editorial queue exceeded its bound")
    result = {"schema": "qikvrt_editorial_dispatch_v1", "head": head, "tree": tree,
              "requests": [], "effect_ack_done": False}
    for path in paths:
        receipt = editorial_intake(root, path.relative_to(root).as_posix(), committed_head=head)
        result["requests"].append(receipt)
        if receipt["state"] != "READY_EXACT_AUTHOR_AUTHORIZED":
            continue
        # Durable create-only reservation prevents concurrent or ambiguous redispatch.
        # It is distinct from the publisher's existing single-use authorization lock.
        key = receipt["authorization_consumption_key"]
        ref = "refs/tags/qikvrt-editorial-dispatch/" + key
        status, present = publication._github_api_request("GET", publication._github_ref_path(ref),
                        os.environ.get("GH_TOKEN", ""), accept=(200, 404))
        if status == 200:
            if (present.get("ref") != ref or present.get("object", {}).get("type") != "commit"
                    or re.fullmatch(r"[0-9a-f]{40}", str(present.get("object", {}).get("sha"))) is None):
                raise ValueError("existing editorial dispatch reservation identity differs")
            receipt["state"] = "NOOP_EXISTING_DISPATCH_RESERVATION_RECONCILE_ORIGINAL_RUN"
            continue
        _main_governance(root, head)
        live = executor.read_authority_main(root)
        if (live["repository"], live["main_head"], live["main_tree"]) != (AUTHORITY, head, tree):
            raise ValueError("editorial Authority Main drifted")
        publication._validate_origin_repository(root, AUTHORITY)
        # No blind retry of this create-only mutation or the following dispatch.
        _rest("POST", "repos/" + AUTHORITY + "/git/refs", {"ref": ref, "sha": head})
        observed = _rest("GET", "repos/" + AUTHORITY + "/git/ref/" + ref.removeprefix("refs/"))
        if not isinstance(observed, dict) or observed.get("ref") != ref or observed.get("object", {}).get("sha") != head:
            raise ValueError("editorial dispatch reservation readback differs")
        inputs = {"operation": "publish", "manifest_path": receipt["manifest_path"],
                  "manifest_sha256": receipt["manifest_sha256"], "expected_main_head": head,
                  "expected_main_tree": tree, "execute": "true", "editorial_request_path": receipt["request_path"]}
        _rest("POST", "repos/" + AUTHORITY + "/actions/workflows/" + ROUTER_WORKFLOW + "/dispatches",
              {"ref": "main", "inputs": inputs})
        receipt.update(state="DISPATCH_ACK_REQUIRES_NATIVE_RUN_READBACK", reservation_ref=ref,
                       dispatch_inputs=inputs, external_effect_performed=True)
    return result


def _web_name(item):
    suffix = Path(item["name"]).suffix.lower()
    suffix = suffix if suffix in {".pdf", ".txt", ".md", ".json", ".tex", ".zip"} else ".bin"
    return item["sha256"] + suffix


def _web_metadata(receipt, manifest, public, outputs):
    record = {"schema": "qikvrt_public_editorial_record_v1", "publication_id": receipt["publication_id"],
              "doi": public["doi"], "record_id": public["record_id"], "record_url": public["record_url"],
              "title": manifest["metadata"]["title"], "creators": manifest["metadata"]["creators"],
              "manifest_sha256": receipt["manifest_sha256"], "files": outputs,
              "zenodo_public_bytes_verified": True, "website_delivery_verified": False}
    links = "".join('<li><a href="' + html.escape(f["path"], quote=True) + '">' + html.escape(f["name"]) + '</a></li>' for f in outputs)
    page = ('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>' + html.escape(record["title"]) + '</title><main><h1>' + html.escape(record["title"]) + '</h1>'
            '<p>DOI: ' + html.escape(record["doi"]) + '</p><p><a href="' + html.escape(record["record_url"], quote=True)
            + '">' + html.escape(record["record_url"]) + '</a></p><ul>' + links
            + '</ul><p>Der veröffentlichte Nachweis gilt für die angegebenen Dateien und ihren deklarierten Geltungsbereich.</p></main></html>\n')
    return {"publication.json": _json_bytes(record), "index.html": page.encode("utf-8")}


def complete_editorial(root: Path, request_relative: str, stage_relative: str):
    """Anonymous independent Zenodo verification, DOI capture and safe website projection."""
    executor, publication, _ = _publication_dependencies()
    from tools import qikvrt_verify_zenodo_public_manifest as verifier
    receipt = editorial_intake(root, request_relative)
    if receipt["state"] != "READY_EXACT_AUTHOR_AUTHORIZED":
        raise ValueError("editorial completion requires the exact author-authorized candidate")
    manifest_path = root / receipt["manifest_path"]
    manifest = publication.load_manifest(manifest_path, root)
    public = verifier.verify_generic(manifest_path, root)
    stage = publication._safe_relative(root, stage_relative, "editorial delivery stage", must_exist=False)
    if (not stage.relative_to(root).as_posix().startswith(".qikvrt/evidence/publication-request/")
            or stage.exists()):
        raise ValueError("editorial stage must be a new private workflow output directory")
    site_path = receipt["website"]["path"].strip("/")
    target = stage / site_path
    target.mkdir(parents=True)
    outputs = []
    for item in manifest["files"]:
        # Upload basenames may be any safe Zenodo name; use opaque generated web
        # names so scripts, HTML or path aliases never become executable site assets.
        name = _web_name(item)
        raw = publication.zenodo.read_regular_file(root / item["path"], publication.zenodo.MAX_UPLOAD_BYTES)
        if len(raw) != item["size"] or hashlib.sha256(raw).hexdigest() != item["sha256"]:
            raise ValueError("website upload source changed after public verification")
        (target / name).write_bytes(raw)
        outputs.append({"name": item["name"], "path": name, "size": len(raw), "sha256": item["sha256"]})
    for name, raw in _web_metadata(receipt, manifest, public, outputs).items():
        (target / name).write_bytes(raw)
    assets = [{"path": p.relative_to(stage).as_posix(), "size": p.stat().st_size,
               "sha256": sha256(p)} for p in sorted(target.iterdir())]
    result = {"schema": "qikvrt_editorial_completion_v1", "request": receipt,
              "public_zenodo_verification": public, "doi": public["doi"],
              "website_stage": stage.relative_to(root).as_posix(), "website_assets": assets,
              "state": "ZENODO_PUBLIC_BYTE_VERIFIED_WEBSITE_STAGED", "effect_ack_done": False,
              "remaining": ["REVIEWED_AUTHORITY_EVIDENCE_PERSISTENCE", "EXISTING_WEBSITE_DEPLOYMENT", "EXACT_HOST_BYTE_READBACK"]}
    (stage.parent / "completion.json").write_bytes(_json_bytes(result))
    return result


def _validated_editorial_completion(root: Path, completion_relative: str, *, persisted=False):
    _, publication, _ = _publication_dependencies()
    path = publication._safe_relative(root, completion_relative, "editorial completion", must_exist=True)
    value, _ = publication.zenodo._load_json_file(path)
    if value.get("schema") != "qikvrt_editorial_completion_v1":
        raise ValueError("invalid editorial completion")
    intake = editorial_intake(root, value["request"]["request_path"])
    if intake != value["request"] or value["public_zenodo_verification"].get("manifest_sha256") != intake["manifest_sha256"]:
        raise ValueError("editorial delivery subject differs")
    if persisted:
        canonical = "evidence/publications/" + intake["publication_id"] + "/" + intake["manifest_sha256"] + "/EDITORIAL_COMPLETION.json"
        if path.relative_to(root).as_posix() != canonical:
            raise ValueError("persisted editorial receipt is outside its canonical path")
        value["website_stage"] = "docs"
    manifest = publication.load_manifest(root / intake["manifest_path"], root)
    prefix = intake["website"]["path"].lstrip("/")
    outputs = [{"name": f["name"], "path": _web_name(f), "size": f["size"], "sha256": f["sha256"]}
               for f in manifest["files"]]
    metadata = _web_metadata(intake, manifest, value["public_zenodo_verification"], outputs)
    expected = {prefix + f["path"]: (f["size"], f["sha256"]) for f in outputs}
    expected.update({prefix + n: (len(raw), hashlib.sha256(raw).hexdigest()) for n, raw in metadata.items()})
    assets = value.get("website_assets")
    if (not isinstance(assets, list) or len(assets) != len(expected)
            or {a.get("path") for a in assets if isinstance(a, dict)} != set(expected)):
        raise ValueError("website asset inventory differs from the exact projection")
    for asset in assets:
        if (asset.get("size"), asset.get("sha256")) != expected[asset["path"]]:
            raise ValueError("website asset identity differs")
        staged = publication._safe_relative(root, value["website_stage"] + "/" + asset["path"], "staged website asset", must_exist=True)
        raw = publication.zenodo.read_regular_file(staged, publication.zenodo.MAX_UPLOAD_BYTES)
        if (len(raw), hashlib.sha256(raw).hexdigest()) != expected[asset["path"]]:
            raise ValueError("staged website bytes differ from the approved publication projection")
    return value, intake, manifest, expected


def persist_editorial(root: Path, completion_relative: str, *, api=None):
    """Persist receipts and the docs projection through a create-only draft PR.

    Reuse the existing REST materializer transport, publication index and
    integrity generator. The self-heal controller's repair-only allowlist is
    deliberately not widened to grant publication authority.
    """
    import base64
    from tools import qikvrt_self_heal_pr_materializer as materializer
    from tools import qikvrt_publication_overview as overview
    from tools import qikvrt_integrity as integrity
    from tools import qikvrt_verify_zenodo_public_manifest as verifier
    root = root.resolve(strict=True)
    value, intake, manifest, _ = _validated_editorial_completion(root, completion_relative)
    executor, publication, _ = _publication_dependencies()
    base = executor._git(root, "rev-parse", "--verify", "HEAD^{commit}")
    if (os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch" or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_REPOSITORY") != AUTHORITY or os.environ.get("GITHUB_SHA") != base
            or publication._validate_repository_source_head(root, root / intake["manifest_path"], manifest) != base):
        raise ValueError("publication evidence persistence requires its exact Main execution")
    public = verifier.verify_generic(root / intake["manifest_path"], root)
    if public != value["public_zenodo_verification"]:
        raise ValueError("public publication identity changed before persistence")
    initially_staged = set(executor._git(root, "diff", "--cached", "--name-only").splitlines())
    prefix = "evidence/publications/" + intake["publication_id"] + "/" + intake["manifest_sha256"] + "/"
    generated = {prefix + "PUBLIC_ZENODO_READBACK.json": _json_bytes(public),
                 prefix + "EDITORIAL_COMPLETION.json": _json_bytes(value)}
    for asset in value["website_assets"]:
        generated["docs/" + asset["path"]] = (root / value["website_stage"] / asset["path"]).read_bytes()
    readme = "docs" + intake["website"]["path"] + "README.md"
    if not (root / readme).exists():
        generated[readme] = ("# " + manifest["metadata"]["title"] + "\n\nPublication ID: `" + intake["publication_id"]
            + "`\nPublication Index State: `zenodo_public_byte_verified_website_delivery_pending`\n\nDOI: " + public["doi"]
            + "\n\n" + public["record_url"] + "\n\nZenodo-Dateien unabhängig bytegenau geprüft; Website-Auslieferung benötigt eigenen HTTPS-Readback.\n").encode()
    for relative, raw in generated.items():
        path = publication._safe_relative(root, relative, "publication persistence output", must_exist=False)
        if path.exists() and path.read_bytes() != raw:
            raise ValueError("publication persistence would overwrite differing repository bytes")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    paths = set(generated) | {manifest["evidence_path"].relative_to(root).as_posix()}
    paths.update(overview.execute(root, materialize=True)["changed_paths"])
    paths.update(p.as_posix() for p in (overview.MACHINE_INDEX, overview.HUMAN_INDEX) if (root / p).is_file())
    if not initially_staged.issubset(paths | integrity.INTEGRITY_PATHS):
        raise ValueError("unrelated staged changes block publication persistence")
    gate = integrity.generate(root)
    if not gate.ok:
        raise ValueError("publication persistence integrity generation failed")
    paths.update(integrity.INTEGRITY_PATHS)
    executor._git(root, "add", "--", *sorted(paths))
    changed = set(executor._git(root, "diff", "--cached", "--name-only").splitlines())
    if not changed or not changed.issubset(paths) or executor._git(root, "diff", "--cached", "--diff-filter=D", "--name-only"):
        raise ValueError("publication persistence changed paths differ")
    tree = executor._git(root, "write-tree")
    branch = "publication/" + intake["publication_id"] + "-" + intake["manifest_sha256"][:16]
    client = api or materializer.GitHubAPI()
    repo = "repos/" + AUTHORITY
    def branch_head():
        try:
            observed = client("GET", repo + "/git/ref/heads/" + branch)
            if observed.get("ref") != "refs/heads/" + branch or observed.get("object", {}).get("type") != "commit":
                raise ValueError("publication branch readback differs")
            return observed["object"]["sha"]
        except materializer.ApiFailure as exc:
            if exc.status == 404: return None
            raise
    def verify_commit(head):
        commit = client("GET", repo + "/git/commits/" + head)
        if (commit.get("sha") != head or commit.get("tree", {}).get("sha") != tree
                or [p.get("sha") for p in commit.get("parents", [])] != [base]):
            raise ValueError("publication evidence commit readback differs")
    head = branch_head()
    existing_branch = head is not None
    if head is None:
        entries = []
        uploads = {"docs" + intake["website"]["path"] + _web_name(f): f["git_blob_sha"] for f in manifest["files"]}
        for path in sorted(changed):
            raw = publication.zenodo.read_regular_file(root / path, publication.zenodo.MAX_UPLOAD_BYTES)
            blob = publication._git_blob_sha(raw)
            if uploads.get(path) != blob:
                created = client("POST", repo + "/git/blobs", {"encoding": "base64", "content": base64.b64encode(raw).decode()})
                if created.get("sha") != blob: raise ValueError("publication blob readback differs")
            entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob})
        base_tree = executor._git(root, "rev-parse", "--verify", "HEAD^{tree}")
        made = client("POST", repo + "/git/trees", {"base_tree": base_tree, "tree": entries})
        if made.get("sha") != tree: raise ValueError("publication tree readback differs")
        commit = client("POST", repo + "/git/commits", {"tree": tree, "parents": [base],
                        "message": "publication: persist exact public receipt and reviewed website projection " + intake["publication_id"]})
        head = commit["sha"]
        verify_commit(head)
        try:
            client("POST", repo + "/git/refs", {"ref": "refs/heads/" + branch, "sha": head})
        except materializer.Block:
            if branch_head() != head: raise
        if branch_head() != head: raise ValueError("publication ref readback differs")
    verify_commit(head)
    prs = client("GET", repo + "/pulls?state=all&per_page=100&head=" + AUTHORITY.split("/")[0] + ":" + branch)
    if not isinstance(prs, list) or len(prs) > 1:
        raise ValueError("publication review carrier inventory differs")
    if not prs and existing_branch:
        return {"schema": "qikvrt_editorial_persistence_v1", "state": "HOLD_EXISTING_EVIDENCE_BRANCH_RECONCILE_PR",
                "repository": AUTHORITY, "branch": branch, "head": head, "tree": tree,
                "doi": public["doi"], "effect_ack_done": False, "automatic_repost": False}
    if not prs:
        try:
            client("POST", repo + "/pulls", {"base": "main", "head": branch, "draft": True,
                   "title": "Publication receipt and website: " + intake["publication_id"],
                   "body": "Exact author-authorized Zenodo publication and independent public byte readback. DOI: " + public["doi"]
                           + "\n\nGenerated docs/index/integrity projection requires native checks and independent review. No automatic Main merge or website-delivery claim."})
        except materializer.Block:
            pass  # Read the ambiguous effect once; never repeat its POST.
        prs = client("GET", repo + "/pulls?state=all&per_page=100&head=" + AUTHORITY.split("/")[0] + ":" + branch)
    if (not isinstance(prs, list) or len(prs) != 1 or prs[0].get("head", {}).get("sha") != head
            or prs[0].get("base", {}).get("ref") != "main"):
        raise ValueError("publication review carrier readback unavailable; reconcile without repost")
    return {"schema": "qikvrt_editorial_persistence_v1", "state": "EVIDENCE_AND_WEBSITE_REVIEW_CARRIER_PERSISTED",
            "repository": AUTHORITY, "branch": branch, "head": head, "tree": tree,
            "pull_request": prs[0]["number"], "pr_state": prs[0].get("state"), "doi": public["doi"],
            "source_execution_head": base, "main_merge_verified": False, "website_delivery_verified": False,
            "effect_ack_done": False}


def verify_editorial_delivery(root: Path, completion_relative: str, *, persisted=False):
    """One anonymous exact-host observation; never follow a redirect or retry a failure."""
    import urllib.request
    _, publication, _ = _publication_dependencies()
    value, intake, _, expected = _validated_editorial_completion(root, completion_relative, persisted=persisted)
    result = {"schema": "qikvrt_editorial_public_delivery_v1", "doi": value["doi"], "origin": PUBLIC_ORIGIN,
              "state": "HOLD_PUBLIC_WEBSITE_READBACK", "files": [], "effect_ack_done": False}
    opener = urllib.request.build_opener(publication._NoCredentialRedirect())
    for asset in value["website_assets"]:
        relative = asset["path"]
        # Resolve against staged regular bytes; do not trust a supplied hash or URL.
        staged = publication._safe_relative(root, value["website_stage"] + "/" + relative, "staged website asset", must_exist=True)
        raw = publication.zenodo.read_regular_file(staged, publication.zenodo.MAX_UPLOAD_BYTES)
        if (len(raw), hashlib.sha256(raw).hexdigest()) != expected[relative]:
            raise ValueError("staged website bytes differ from the approved publication projection")
        if not relative.startswith(intake["website"]["path"].lstrip("/")) or any(c in relative for c in ("?", "#", "%", "\\")):
            raise ValueError("website asset path differs")
        url = PUBLIC_ORIGIN + "/" + relative
        try:
            with opener.open(urllib.request.Request(url, method="GET", headers={"User-Agent": "qikvrt-editorial-readback/1"}), timeout=30) as response:
                observed = response.read(len(raw) + 1)
                ok = response.status == 200 and response.geturl() == url and observed == raw
        except (OSError, ValueError):
            ok = False
        result["files"].append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "byte_exact_public_readback": ok})
        if not ok:
            return result
    if not result["files"]:
        raise ValueError("empty website readback cannot pass")
    result["state"] = "PUBLIC_WEBSITE_BYTES_VERIFIED_AUTHORITY_PERSISTENCE_SEPARATE"
    return result


def verify_after_existing_deployment(root: Path, run_id: str):
    """Use the existing deployment's native completion, never a timer or success inference."""
    if not re.fullmatch(r"[1-9][0-9]{0,19}", str(run_id)):
        raise ValueError("invalid deployment execution identity")
    executor, _, _ = _publication_dependencies()
    head = executor._git(root, "rev-parse", "--verify", "HEAD^{commit}")
    run = _rest("GET", "repos/" + AUTHORITY + "/actions/runs/" + str(run_id))
    if (not isinstance(run, dict) or run.get("head_sha") != head or run.get("head_branch") != "main"
            or run.get("repository", {}).get("full_name") != AUTHORITY
            or run.get("head_repository", {}).get("full_name") != AUTHORITY
            or run.get("event") not in {"push", "workflow_dispatch"}
            or run.get("path") != ".github/workflows/qikvrt_effect_ack_http_terminal.yml"
            or run.get("status") != "completed" or run.get("conclusion") != "success"):
        raise ValueError("existing deployment execution does not bind this Main subject")
    jobs = _rest("GET", "repos/" + AUTHORITY + "/actions/runs/" + str(run_id) + "/jobs?per_page=100")
    if not isinstance(jobs, dict) or jobs.get("total_count", 101) > 100 or not isinstance(jobs.get("jobs"), list):
        raise ValueError("existing deployment job inventory incomplete")
    required = {"deploy-existing-linux-host", "independent-product-http-readback"}
    executed = {j.get("name") for j in jobs["jobs"] if j.get("status") == "completed" and j.get("conclusion") == "success"}
    result = {"schema": "qikvrt_editorial_post_deployment_v1", "head": head,
              "deployment_run_id": str(run_id), "state": "NOOP_EXISTING_DEPLOYMENT_NOT_EXECUTED", "publications": [],
              "effect_ack_done": False}
    if not required.issubset(executed):
        return result
    paths = executor._git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", "evidence/publications").splitlines()
    for path in paths:
        if path.endswith("/EDITORIAL_COMPLETION.json"):
            result["publications"].append(verify_editorial_delivery(root, path, persisted=True))
    result["state"] = ("HOLD_PUBLICATION_ASSET_READBACK" if any(p["state"].startswith("HOLD") for p in result["publications"])
                       else "PUBLICATION_ASSET_READBACK_OBSERVED" if result["publications"] else "NOOP_NO_PERSISTED_EDITORIAL_PUBLICATIONS")
    return result

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _publication_dependencies():
    # Reuse the existing production implementations and their complete v2 gates.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import qikvrt_workflow_executor as executor
    import qikvrt_zenodo_publish as publication
    import qikvrt_zenodo_metadata_edit as metadata_edit
    return executor, publication, metadata_edit


def requested_zenodo(root: Path, operation: str, manifest_relative: str,
                     manifest_sha256: str, expected_head: str,
                     expected_tree: str, *, execute: bool = False,
                     editorial_relative: str | None = None) -> dict:
    """Admit only an explicit exact-Main request; never auto-route a bundle."""
    if operation not in {"publish", "metadata-edit"}:
        raise ValueError("unsupported requested Zenodo operation")
    for value, size in ((manifest_sha256, 64), (expected_head, 40), (expected_tree, 40)):
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{%d}" % size, value) is None:
            raise ValueError("exact request identity is required")
    repository = "ingolf-lohmann/qik-vrt"
    if (os.environ.get("GITHUB_REPOSITORY") != repository
            or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_SHA") != expected_head):
        raise ValueError("requested publication requires the exact Authority Main event")
    root = root.resolve(strict=True)
    executor, publication, metadata_edit = _publication_dependencies()
    if publication.PRODUCTION_REPOSITORY != repository:
        raise ValueError("publisher Authority binding differs")
    if executor.load_repository_roles(root)["AUTHORITY"] != repository:
        raise ValueError("canonical Authority binding differs")
    if (executor._git(root, "rev-parse", "--verify", "HEAD^{commit}") != expected_head
            or executor._git(root, "rev-parse", "--verify", "HEAD^{tree}") != expected_tree):
        raise ValueError("checked-out exact subject differs")
    path = publication._safe_relative(root, manifest_relative, "requested manifest", must_exist=True)
    raw = publication.zenodo.read_regular_file(path, publication.zenodo.MAX_JSON_BYTES)
    if hashlib.sha256(raw).hexdigest() != manifest_sha256:
        raise ValueError("requested manifest SHA-256 differs")
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    relative = path.relative_to(root).as_posix()
    if executor._git(root, "rev-parse", "--verify", expected_head + ":" + relative) != blob:
        raise ValueError("requested manifest is not the exact committed blob")
    implementation = publication if operation == "publish" else metadata_edit
    manifest = implementation.load_manifest(path, root)
    if manifest["repository"] != repository:
        raise ValueError("manifest Authority binding differs")
    if operation == "publish":
        if manifest["schema"] != publication.SCHEMA_V2:
            raise ValueError("legacy manifests cannot admit a production publication")
        execution_head = publication._validate_repository_source_head(root, path, manifest)
    else:
        execution_head = metadata_edit._validate_repository_heads(root, path, manifest)
    publication._validate_origin_repository(root, repository)
    if execution_head != expected_head:
        raise ValueError("manifest execution subject differs")
    if editorial_relative:
        if operation != "publish":
            raise ValueError("editorial intake cannot authorize a metadata edit")
        intake = editorial_intake(root, editorial_relative, committed_head=expected_head)
        if (intake["state"] != "READY_EXACT_AUTHOR_AUTHORIZED"
                or intake["manifest_path"] != relative or intake["manifest_sha256"] != manifest_sha256):
            raise ValueError("editorial request differs from the exact publication request")
    # A fresh independent REST read is required even after local validation.
    live = executor.read_authority_main(root)
    if (live["repository"], live["main_head"], live["main_tree"]) != (
            repository, expected_head, expected_tree):
        raise ValueError("live Authority Main drifted")
    result = {
        "schema": "qikvrt_requested_zenodo_route_v1",
        "repository": repository, "head": expected_head, "tree": expected_tree,
        "operation": operation, "manifest_path": relative,
        "manifest_sha256": manifest_sha256, "manifest_blob_sha1": blob,
        "evidence_path": manifest["evidence_path"].relative_to(root).as_posix(),
        "state": "PREFLIGHT_VERIFIED_EFFECT_NOT_EXECUTED",
        "external_effect_performed": False, "effect_ack_done": False,
        "native_governance_verification": "SEPARATE_REQUIRED_GATE",
        "credential_configuration": "NOT_INFERRED_FROM_SOURCE_OR_PREFLIGHT",
    }
    if execute:
        if editorial_relative:
            _main_governance(root, expected_head)
        effect = publication.publish if operation == "publish" else metadata_edit.edit_published_metadata
        evidence = effect(path, root)
        result["state"] = "PUBLISHER_RETURNED_REQUIRES_INDEPENDENT_READBACK_AND_PERSISTENCE"
        result["external_effect_performed"] = None
        result["publisher_invoked"] = True
        result["publisher_evidence_phase"] = evidence.get("phase")
    return result


def route_bundle(root: Path) -> dict:
    manifest = json.loads((root / "PUBLICATION_ROUTING.json").read_text(encoding="utf-8"))
    required = {"schema","bundle_id","title","author","repository_scope","artifacts","routes","automation","release_claims"}
    if set(manifest) != required:
        raise SystemExit("BLOCK: routing manifest shape mismatch")
    if manifest["schema"] != "qikvrt_publication_routing_manifest_v1":
        raise SystemExit("BLOCK: unsupported routing schema")
    for item in manifest["artifacts"]:
        path = root / item["path"]
        if not path.is_file():
            raise SystemExit(f"BLOCK: missing artifact {item['path']}")
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise SystemExit(f"BLOCK: artifact digest mismatch {item['path']}")
    routes = manifest["routes"]
    if routes["repository"]["disposition"] != "CANDIDATE_REQUIRED":
        raise SystemExit("BLOCK: repository route must remain candidate-gated")
    if routes["zenodo"]["effect_gate"] != "EXPLICIT_HASH_BOUND_PUBLICATION_REQUEST_REQUIRED":
        raise SystemExit("BLOCK: Zenodo route is not explicitly gated")
    if routes["ietf"]["protocol_change_required"] is not False:
        raise SystemExit("BLOCK: unexpected IETF protocol change")
    if any(manifest["release_claims"].values()):
        raise SystemExit("BLOCK: completion claim inflation")
    result = {
      "schema":"qikvrt_publication_routing_result_v1",
      "bundle_id":manifest["bundle_id"],
      "repository":"CANDIDATE",
      "zenodo":"STAGED_REQUIRES_EXPLICIT_REQUEST",
      "ietf":"NO_SUBMISSION_SCOPE_NOTE_ONLY",
      "external_effect_performed":False
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle", type=Path, nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--zenodo-operation", choices=("publish", "metadata-edit"))
    ap.add_argument("--manifest")
    ap.add_argument("--manifest-sha256")
    ap.add_argument("--expected-head")
    ap.add_argument("--expected-tree")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--editorial-binding")
    editorial = ap.add_mutually_exclusive_group()
    editorial.add_argument("--editorial-request")
    editorial.add_argument("--dispatch-editorial-queue", action="store_true")
    editorial.add_argument("--complete-editorial")
    editorial.add_argument("--persist-editorial")
    editorial.add_argument("--verify-editorial-delivery")
    editorial.add_argument("--verify-after-existing-deployment")
    ap.add_argument("--stage", default=".qikvrt/evidence/publication-request/site")
    ns = ap.parse_args()
    if any((ns.editorial_request, ns.dispatch_editorial_queue, ns.complete_editorial, ns.persist_editorial, ns.verify_editorial_delivery, ns.verify_after_existing_deployment)):
        if ns.bundle is not None or ns.zenodo_operation or ns.execute or ns.editorial_binding or any((ns.manifest, ns.manifest_sha256, ns.expected_head, ns.expected_tree)):
            ap.error("editorial operations and direct Zenodo effects are separate")
        try:
            root = Path.cwd().resolve(strict=True)
            if ns.editorial_request:
                result = editorial_intake(root, ns.editorial_request)
            elif ns.dispatch_editorial_queue:
                result = dispatch_editorial_queue(root)
            elif ns.complete_editorial:
                result = complete_editorial(root, ns.complete_editorial, ns.stage)
            elif ns.persist_editorial:
                result = persist_editorial(root, ns.persist_editorial)
            elif ns.verify_after_existing_deployment:
                result = verify_after_existing_deployment(root, ns.verify_after_existing_deployment)
            else:
                result = verify_editorial_delivery(root, ns.verify_editorial_delivery)
        except (Exception, SystemExit) as exc:
            print("BLOCK EDITORIAL " + type(exc).__name__, file=sys.stderr)
            return 2
    elif ns.zenodo_operation:
        if ns.bundle is not None:
            ap.error("bundle routing and requested Zenodo execution are separate")
        try:
            result = requested_zenodo(Path.cwd(), ns.zenodo_operation, ns.manifest,
                                     ns.manifest_sha256, ns.expected_head,
                                     ns.expected_tree, execute=ns.execute,
                                     editorial_relative=ns.editorial_binding)
        except Exception as exc:
            # Do not reflect provider responses, request input or credentials.
            print("BLOCK REQUESTED_ZENODO " + type(exc).__name__, file=sys.stderr)
            return 2
    else:
        if ns.bundle is None or ns.execute or ns.editorial_binding or any((ns.manifest, ns.manifest_sha256,
                                                  ns.expected_head, ns.expected_tree)):
            ap.error("select bundle routing or an explicit exact Zenodo request")
        result = route_bundle(ns.bundle)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True) if ns.json else "\n".join(f"{k}={v}" for k,v in result.items()))
    return 2 if (ns.verify_editorial_delivery or ns.verify_after_existing_deployment) and result.get("state", "").startswith("HOLD") else 0

if __name__ == "__main__":
    raise SystemExit(main())
