#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""One fixed Authority source reader and a fail-closed, credential-free resume point."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.qikvrt_r11_read_only_observation_dispatch_v2 import (
    MAX_RESPONSE, NoRedirect, RetryingGitHubAPI,
)
from tools.qikvrt_integrity import verify_recursive_git_tree

AUTHORITY = "Goldkelch/qik-vrt"
AUTHORITY_ID = 1271407206
OWNER_ID = 293941403
CONNECTION_INSTALLATION_ID = 147849532
MIRROR = "ingolf-lohmann/qik-vrt"
MIRROR_ID = 1273784147
QR_URL = "https://github.com/Goldkelch/qik-vrt/blob/main/AI"
RAW_URL = "https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/AI"
SHA = r"[0-9a-f]{40}"
WORKFLOW = ".github/workflows/qikvrt_mesh_authority_edge.yml"
RESUME_PATH = "evidence/receipts/authority-recovery-20261002/ACCEPTANCE.json"
CARRIER_ID = "qikvrt-mesh-authority-edge/authority_url_probe"
APP_ACTION = "actions/create-github-app-token@fee1f7d63c2ff003460e3d139729b119787bc349"
PUBLIC_PAGES = (
    "https://goldkelch.github.io/qik-vrt/",
    "https://goldkelch.github.io/qik-vrt/mesh/live/",
    "https://goldkelch.github.io/qik-vrt/mesh/live/version.json",
)
CREDENTIALS = (
    "QIKVRT_RULESET_ADMIN_TOKEN", "QIKVRT_GITHUB_ADMIN_TOKEN",
    "QIKVRT_MESH_TOKEN", "QIKVRT_AUTHORITY_APP_TOKEN", "GITHUB_TOKEN",
)
MAX_OBJECT_READS = 20000
MAX_REFS = 1000


class ProbeBlocked(ValueError):
    pass


class AuthorityURLAPI(RetryingGitHubAPI):
    @staticmethod
    def _validate_path(path):
        fixed = {
            f"/repos/{AUTHORITY}", f"/repositories/{AUTHORITY_ID}",
            "/installation/repositories?per_page=100",
            f"/repos/{AUTHORITY}/git/ref/heads/main",
            f"/repos/{AUTHORITY}/git/matching-refs/",
            f"/repos/{AUTHORITY}/pages", f"/repos/{AUTHORITY}/pages/builds/latest",
        }
        if path in fixed or re.fullmatch(
            rf"/repos/{AUTHORITY}/git/(commits|tags|blobs)/{SHA}", path
        ) or re.fullmatch(rf"/repos/{AUTHORITY}/git/trees/{SHA}\?recursive=1", path):
            return
        raise ValueError("GET path is outside the fixed Authority source carrier")


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(value):
    return isinstance(value, str) and re.fullmatch(SHA, value) is not None


def identity(value):
    return (isinstance(value, dict) and value.get("id") == AUTHORITY_ID
            and value.get("full_name") == AUTHORITY
            and isinstance(value.get("owner"), dict)
            and value["owner"].get("id") == OWNER_ID)


def credential(environment):
    """Unattested direct inputs and the Mirror token cannot shadow the App route."""
    present = {name: bool(environment.get(name)) for name in CREDENTIALS}
    if present["QIKVRT_AUTHORITY_APP_TOKEN"]:
        return environment["QIKVRT_AUTHORITY_APP_TOKEN"], "QIKVRT_AUTHORITY_APP_TOKEN", present
    return "", None, present


def app_binding(environment):
    installation = environment.get("QIKVRT_AUTHORITY_APP_INSTALLATION_ID", "")
    if (environment.get("QIKVRT_APP_TOKEN_ISSUANCE_OUTCOME") != "success"
            or not re.fullmatch(r"[1-9][0-9]{0,19}", installation)):
        return None
    permissions = {"contents": "read"}
    if environment.get("QIKVRT_AUTHORITY_OPERATION") == "authority_pages_readback":
        permissions["pages"] = "read"
    return {
        "kind": "EXISTING_APP_ACTION_OUTPUT", "action": APP_ACTION,
        "installation_id": int(installation), "repository": AUTHORITY,
        "repository_id": AUTHORITY_ID, "owner_id": OWNER_ID,
        "requested_permissions": permissions,
    }


def valid_binding(binding, pages=False):
    return (isinstance(binding, dict)
            and binding.get("kind") == "EXISTING_APP_ACTION_OUTPUT"
            and binding.get("action") == APP_ACTION
            and type(binding.get("installation_id")) is int
            and binding["installation_id"] > 0
            and binding.get("repository") == AUTHORITY
            and binding.get("repository_id") == AUTHORITY_ID
            and binding.get("owner_id") == OWNER_ID
            and binding.get("requested_permissions") ==
            ({"contents": "read", "pages": "read"} if pages else {"contents": "read"}))


def load_resume(root=ROOT):
    path = root / RESUME_PATH
    if path.is_symlink() or not path.is_file():
        raise ValueError("regular resume receipt is required")
    resume = json.loads(path.read_bytes())["source_closure_resume"]
    if (resume.get("schema") != "qikvrt_authority_source_closure_resume_v1"
            or resume.get("carrier_id") != CARRIER_ID
            or resume.get("target") != {
                "repository": AUTHORITY, "repository_id": AUTHORITY_ID,
                "owner_id": OWNER_ID, "ref": "refs/heads/main",
            }
            or resume.get("carrier", {}).get("workflow_path") != WORKFLOW
            or resume.get("carrier", {}).get("operation") != "authority_url_probe"
            or resume.get("credential_route", {}).get("action") != APP_ACTION
            or resume.get("credential_route", {}).get("requested_permissions") != {"contents": "read"}
            or resume.get("credential_route", {}).get("fallback") != "NONE"
            or resume.get("predecessor_evidence_transfer") is not False):
        raise ValueError("Authority resume contract drift")
    return resume


def public_get(url):
    if url not in {QR_URL, RAW_URL, *PUBLIC_PAGES}:
        raise ValueError("public read escaped the two fixed entrypoints")
    request = urllib.request.Request(url, method="GET", headers={
        "User-Agent": "qikvrt-authority-url-probe/2", "Cache-Control": "no-cache",
    })
    try:
        response = urllib.request.build_opener(NoRedirect()).open(request, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError("public body exceeds its byte bound")
        return int(response.status), raw


def probe(token, source, executor, *, binding=None, transport=None, public_reader=public_get,
          object_budget=MAX_OBJECT_READS, pages=False):
    report = {
        "schema": "qikvrt_authority_url_probe_v2", "observed_at": utc(),
        "carrier_id": CARRIER_ID, "resume_pointer": RESUME_PATH + "#/source_closure_resume",
        "executor": executor, "target": {
            "repository": AUTHORITY, "repository_id": AUTHORITY_ID,
            "owner_id": OWNER_ID, "ref": "refs/heads/main", "qr_url": QR_URL,
        },
        "credential_source": source, "credential_binding": binding,
        "observations": [], "first_blocker": None, "state": "CONTINUE",
        "source_read_verified": False, "git_object_closure_verified": False,
        "latest_complete_authority_closure_verified": False,
        "public_url_effect_verified": False, "effect_ack_done": False,
        "mutation_count": 0, "predecessor_evidence_transfer": False,
    }
    if pages:
        report.update(authority_pages_state="HOLD_AUTHORITY_PAGES_READ_UNAVAILABLE",
                      authority_reads={}, publication_mutated=False,
                      deployed_candidate_head_tree_verified=False,
                      persistent_signed_installation_verified=False,
                      authenticated_runtime_readback=False,
                      personal_release_effect_ack_done=False)

    def blocked(reason):
        report.update(state="BLOCK", first_blocker=reason)
        return report

    if not token:
        return blocked("AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED")
    if source != "QIKVRT_AUTHORITY_APP_TOKEN" or not valid_binding(binding, pages):
        return blocked("AUTHORITY_INSTALLATION_BINDING_NOT_VERIFIED")
    if type(object_budget) is not int or not 0 < object_budget <= MAX_OBJECT_READS:
        return blocked("INVALID_OBJECT_READ_BUDGET")
    api = AuthorityURLAPI(token, transport=transport)
    object_reads = 0

    def get(label, path, *, object_read=False):
        nonlocal object_reads
        if object_read:
            if object_reads >= object_budget:
                raise ProbeBlocked("AUTHORITY_SOURCE_OBJECT_READ_BUDGET_REACHED")
            object_reads += 1
        # Every status is accepted exactly once; no retry, fallback or redirect.
        status, headers, raw = api.raw_get(path, tuple(range(100, 600)))
        if not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE:
            raise ProbeBlocked("AUTHORITY_RESPONSE_BYTE_BOUND_EXCEEDED")
        if token.encode() in raw:
            raise ValueError("response contains credential material; refusing persistence")
        report["observations"].append({
            "label": label, "path": path, "method": "GET", "status": status,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "observed_at": utc(),
        })
        if status != 200:
            raise ProbeBlocked("AUTHORITY_READ_REJECTED_CAUSE_UNDETERMINED")
        link = str(headers.get("link", headers.get("Link", "")))
        if 'rel="next"' in link:
            raise ProbeBlocked("AUTHORITY_COLLECTION_PAGINATION_UNCLOSED")
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError):
            raise ProbeBlocked("AUTHORITY_RESPONSE_JSON_INVALID") from None

    def refs():
        values = get("authority_refs", f"/repos/{AUTHORITY}/git/matching-refs/")
        if not isinstance(values, list) or not values or len(values) > MAX_REFS:
            raise ProbeBlocked("AUTHORITY_COMPLETE_REFS_NOT_VERIFIED")
        if (not all(isinstance(v, dict) and isinstance(v.get("ref"), str)
                    and v["ref"].startswith("refs/") and isinstance(v.get("object"), dict)
                    and v["object"].get("type") in {"commit", "tag"}
                    and sha(v["object"].get("sha")) for v in values)
                or len({v["ref"] for v in values}) != len(values)):
            raise ProbeBlocked("AUTHORITY_REF_BINDING_INVALID")
        return sorted([{"ref": v["ref"], "type": v["object"]["type"],
                        "sha": v["object"]["sha"]} for v in values], key=lambda v: v["ref"])

    try:
        installed = get("installation_target", "/installation/repositories?per_page=100")
        repositories = installed.get("repositories") if isinstance(installed, dict) else None
        if (not isinstance(repositories, list) or installed.get("total_count") != 1
                or len(repositories) != 1 or not identity(repositories[0])):
            return blocked("AUTHORITY_INSTALLATION_TARGET_SCOPE_MISMATCH")
        report["installation_target_verified"] = True
        for label, path in (("authority_by_name", f"/repos/{AUTHORITY}"),
                            ("authority_by_id", f"/repositories/{AUTHORITY_ID}")):
            if not identity(get(label, path)):
                return blocked("AUTHORITY_IDENTITY_MISMATCH")
        main_ref = get("authority_main_ref", f"/repos/{AUTHORITY}/git/ref/heads/main")
        if (not isinstance(main_ref, dict) or main_ref.get("ref") != "refs/heads/main"
                or main_ref.get("object", {}).get("type") != "commit"
                or not sha(main_ref.get("object", {}).get("sha"))):
            return blocked("AUTHORITY_MAIN_SUBJECT_NOT_VERIFIED")
        head = main_ref["object"]["sha"]
        if pages:
            value = get("authority_pages_source_commit",
                        f"/repos/{AUTHORITY}/git/commits/{head}", object_read=True)
            tree = value.get("tree", {}).get("sha") if isinstance(value, dict) else None
            if not isinstance(value, dict) or value.get("sha") != head or not sha(tree):
                return blocked("AUTHORITY_MAIN_SUBJECT_NOT_VERIFIED")
            inventory = get("authority_pages_source_inventory",
                            f"/repos/{AUTHORITY}/git/trees/{tree}?recursive=1", object_read=True)
            try:
                verified_tree = verify_recursive_git_tree(inventory, tree)
            except (ValueError, TypeError, KeyError):
                return blocked("AUTHORITY_TREE_CLOSURE_NOT_VERIFIED")
            report["authority_subject"] = {"head": head, "tree": tree}
            report["authority_reads"] = {"source_commit": {"head": head, "tree": tree},
                                        "source_inventory": verified_tree}
            # Preserve the existing Pages observer's separate read scope.
            # It shares this carrier and never claims source recovery closure.
            for suffix in ("pages", "pages/builds/latest"):
                path = f"/repos/{AUTHORITY}/" + suffix
                status, headers, raw = api.raw_get(path, tuple(range(100, 600)))
                if len(raw) > MAX_RESPONSE or token.encode() in raw:
                    raise ValueError("Pages response failed safe persistence validation")
                report["authority_reads"][suffix] = {
                    "status": status, "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            report["public_readbacks"] = []
            for url in PUBLIC_PAGES:
                status, raw = public_reader(url)
                if len(raw) > MAX_RESPONSE or token.encode() in raw:
                    raise ValueError("public Pages response failed safe persistence validation")
                report["public_readbacks"].append({
                    "url": url, "status": status, "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(), "authentication": "anonymous",
                })
            if get("authority_pages_main_reobservation",
                   f"/repos/{AUTHORITY}/git/ref/heads/main") != main_ref:
                return blocked("AUTHORITY_REFS_CHANGED_DURING_PROBE")
            if report["authority_reads"]["pages"]["status"] == 200:
                report.update(state="OBSERVED_AUTHORITY_PAGES",
                              authority_pages_state="OBSERVED_AUTHORITY_PAGES")
            else:
                report.update(state="HOLD", first_blocker="AUTHORITY_PAGES_READ_UNAVAILABLE")
            return report
        initial_refs = refs()
        if {"ref": "refs/heads/main", "type": "commit", "sha": head} not in initial_refs:
            return blocked("AUTHORITY_MAIN_REF_INVENTORY_MISMATCH")
        report["refs"] = initial_refs
        queue = [(v["type"], v["sha"]) for v in initial_refs]
        seen = set()
        trees = {}
        blob_proofs = {}
        ai_blob = None
        ai_digest = None
        while queue:
            kind, oid = queue.pop()
            if (kind, oid) in seen:
                continue
            seen.add((kind, oid))
            value = get("authority_" + kind, f"/repos/{AUTHORITY}/git/{kind}s/{oid}",
                        object_read=True)
            if not isinstance(value, dict) or value.get("sha") != oid:
                raise ProbeBlocked("AUTHORITY_REFERENCED_OBJECT_BINDING_MISMATCH")
            if kind == "tag":
                target = value.get("object", {})
                if target.get("type") not in {"commit", "tag"} or not sha(target.get("sha")):
                    raise ProbeBlocked("AUTHORITY_TAG_TARGET_NOT_VERIFIED")
                queue.append((target["type"], target["sha"]))
                continue
            tree = value.get("tree", {}).get("sha")
            parents = value.get("parents")
            if (not sha(tree) or not isinstance(parents, list)
                    or not all(isinstance(v, dict) and sha(v.get("sha")) for v in parents)):
                raise ProbeBlocked("AUTHORITY_COMMIT_TREE_PARENT_BINDING_INVALID")
            queue.extend(("commit", v["sha"]) for v in parents)
            if tree not in trees:
                inventory = get("authority_tree", f"/repos/{AUTHORITY}/git/trees/{tree}?recursive=1",
                                object_read=True)
                try:
                    trees[tree] = verify_recursive_git_tree(inventory, tree)
                except (ValueError, TypeError, KeyError):
                    raise ProbeBlocked("AUTHORITY_TREE_CLOSURE_NOT_VERIFIED") from None
                for entry in inventory["tree"]:
                    if entry["type"] != "blob":
                        continue
                    blob = entry["sha"]
                    if oid == head and entry["path"] == "AI":
                        ai_blob = blob
                    if blob not in blob_proofs:
                        data = get("authority_blob", f"/repos/{AUTHORITY}/git/blobs/{blob}",
                                   object_read=True)
                        if (not isinstance(data, dict) or data.get("sha") != blob
                                or data.get("encoding") != "base64"
                                or not isinstance(data.get("content"), str)):
                            raise ProbeBlocked("AUTHORITY_BLOB_ENCODING_INVALID")
                        try:
                            payload = base64.b64decode(data["content"].replace("\n", ""), validate=True)
                        except (ValueError, TypeError):
                            raise ProbeBlocked("AUTHORITY_BLOB_ENCODING_INVALID") from None
                        calculated = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()
                        if data.get("size") != len(payload) or calculated != blob:
                            raise ProbeBlocked("AUTHORITY_BLOB_CONTENT_MISMATCH")
                        if token.encode() in payload:
                            raise ValueError("blob contains credential material; refusing persistence")
                        if payload.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                            raise ProbeBlocked("AUTHORITY_LFS_PAYLOAD_CLOSURE_UNVERIFIED")
                        blob_proofs[blob] = {"bytes": len(payload),
                                            "sha256": hashlib.sha256(payload).hexdigest()}
                # A reused tree must still bind the selected main AI.
            if oid == head:
                if ai_blob is None:
                    # The main tree may have been reached through another ref first.
                    inventory = get("authority_main_tree", f"/repos/{AUTHORITY}/git/trees/{tree}?recursive=1",
                                    object_read=True)
                    verify_recursive_git_tree(inventory, tree)
                    ai_blob = next((v["sha"] for v in inventory["tree"]
                                    if v["path"] == "AI" and v["type"] == "blob"), None)
                if ai_blob not in blob_proofs:
                    raise ProbeBlocked("EXACT_AUTHORITY_AI_NOT_READABLE")
                ai_digest = blob_proofs[ai_blob]["sha256"]
                report["authority_subject"] = {
                    "head": head, "tree": tree, "AI_blob": ai_blob,
                    "AI_bytes": blob_proofs[ai_blob]["bytes"], "AI_sha256": ai_digest,
                }
        final_ref = get("authority_main_reobservation", f"/repos/{AUTHORITY}/git/ref/heads/main")
        if final_ref != main_ref or refs() != initial_refs:
            return blocked("AUTHORITY_REFS_CHANGED_DURING_PROBE")
        report.update(source_read_verified=True, git_object_closure_verified=True,
                      state="GIT_SOURCE_CLOSURE_VERIFIED", trees=trees,
                      blob_proofs=blob_proofs, verified_object_reads=object_reads,
                      source_closure_scope="LISTED_REFS_AND_REACHABLE_GIT_HISTORY_REGULAR_BLOBS")
        # Platform metadata, runtime state and actual role effects remain separate.
        report["remaining_acceptance"] = [
            "COMPARE_RETAINED_SOURCE_AND_FRESH_MIRROR",
            "BIND_ROLE_LOCAL_RECOVERY_RUNTIME_STATE_AND_PLATFORM_GOVERNANCE",
            "PROTECTED_EXACT_HEAD_REVIEW_AND_ROLE_EPOCH_FENCING",
        ]
        public = []
        for url in (QR_URL, RAW_URL):
            status, body = public_reader(url)
            if not isinstance(body, bytes) or len(body) > MAX_RESPONSE or token.encode() in body:
                raise ValueError("public body failed safe persistence validation")
            public.append({"url": url, "method": "GET", "authentication": "anonymous",
                           "status": status, "bytes": len(body),
                           "sha256": hashlib.sha256(body).hexdigest(), "observed_at": utc()})
        report["public_readbacks"] = public
        if (get("authority_final_main", f"/repos/{AUTHORITY}/git/ref/heads/main") != main_ref
                or refs() != initial_refs):
            report.update(source_read_verified=False, git_object_closure_verified=False)
            return blocked("AUTHORITY_REFS_CHANGED_DURING_PUBLIC_READBACK")
        if (public[0]["status"] == 200 and public[1]["status"] == 200
                and public[1]["sha256"] == ai_digest):
            report["public_url_effect_verified"] = True
        else:
            report["public_url_first_blocker"] = "PUBLIC_QR_URL_EFFECT_NOT_VERIFIED"
        return report
    except ProbeBlocked as error:
        return blocked(str(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    load_resume()
    expected = os.environ.get("GITHUB_SHA", "")
    if (os.environ.get("GITHUB_REPOSITORY") != MIRROR or not sha(expected)
            or os.environ.get("QIKVRT_PROBE_TARGET", AUTHORITY) != AUTHORITY):
        raise SystemExit("BLOCK: native fixed-target Mirror event binding is missing")

    def git(*parts):
        return subprocess.check_output(["git", "-C", str(ROOT), *parts], text=True).strip()

    if git("rev-parse", "HEAD") != expected:
        raise SystemExit("BLOCK: checkout does not match the native event head")
    if args.preflight:
        print("QIKVRT_AUTHORITY_PROBE_PREFLIGHT=VERIFIED")
        return 0
    if not args.output:
        parser.error("--output is required for readback")
    executor = {
        "repository": MIRROR, "head": expected, "tree": git("rev-parse", "HEAD^{tree}"),
        "run_id": os.environ.get("GITHUB_RUN_ID"), "attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "ref": os.environ.get("GITHUB_REF"), "actor": os.environ.get("GITHUB_ACTOR"),
        "event": os.environ.get("GITHUB_EVENT_NAME"), "workflow_path": WORKFLOW,
        "workflow_sha256": hashlib.sha256((ROOT / WORKFLOW).read_bytes()).hexdigest(),
        "resume_receipt_sha256": hashlib.sha256((ROOT / RESUME_PATH).read_bytes()).hexdigest(),
    }
    token, source, present = credential(os.environ)
    try:
        report = probe(token, source, executor, binding=app_binding(os.environ),
                       pages=os.environ.get("QIKVRT_AUTHORITY_OPERATION") == "authority_pages_readback")
    except (ValueError, TypeError, KeyError, OSError, SystemExit):
        report = {
            "schema": "qikvrt_authority_url_probe_v2", "carrier_id": CARRIER_ID,
            "resume_pointer": RESUME_PATH + "#/source_closure_resume", "executor": executor,
            "observed_at": utc(), "state": "BLOCK",
            "first_blocker": "PROBE_TRANSPORT_OR_RESPONSE_VALIDATION_FAILED",
            "credential_source": source, "mutation_count": 0, "effect_ack_done": False,
            "source_read_verified": False, "git_object_closure_verified": False,
            "latest_complete_authority_closure_verified": False,
            "predecessor_evidence_transfer": False,
        }
    try:
        delivered = json.loads(os.environ.get("QIKVRT_CREDENTIAL_PRESENCE", "{}"))
        present.update({k: v for k, v in delivered.items() if k in CREDENTIALS and type(v) is bool})
    except (ValueError, AttributeError):
        pass
    report["credential_names_present"] = present
    report["app_token_issuance_outcome"] = os.environ.get("QIKVRT_APP_TOKEN_ISSUANCE_OUTCOME", "skipped")
    if (report.get("first_blocker") == "AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED"
            and os.environ.get("QIKVRT_APP_INPUTS_PRESENT") == "true"
            and report["app_token_issuance_outcome"] != "success"):
        report["first_blocker"] = "AUTHORITY_APP_TOKEN_ISSUANCE_NOT_VERIFIED"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("QIKVRT_AUTHORITY_SOURCE_READBACK=" + json.dumps({
        key: report.get(key) for key in
        ("state", "first_blocker", "carrier_id", "resume_pointer", "git_object_closure_verified")
    }, sort_keys=True))
    return 0 if (report.get("git_object_closure_verified")
                 or report.get("authority_pages_state") == "OBSERVED_AUTHORITY_PAGES") else 2


if __name__ == "__main__":
    raise SystemExit(main())
