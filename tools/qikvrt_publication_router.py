#!/usr/bin/env python3
"""Fail-closed publication router for QIK-VRT publication bundles."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys
from pathlib import Path

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
                     expected_tree: str, *, execute: bool = False) -> dict:
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
    ns = ap.parse_args()
    if ns.zenodo_operation:
        if ns.bundle is not None:
            ap.error("bundle routing and requested Zenodo execution are separate")
        try:
            result = requested_zenodo(Path.cwd(), ns.zenodo_operation, ns.manifest,
                                     ns.manifest_sha256, ns.expected_head,
                                     ns.expected_tree, execute=ns.execute)
        except Exception as exc:
            # Do not reflect provider responses, request input or credentials.
            print("BLOCK REQUESTED_ZENODO " + type(exc).__name__, file=sys.stderr)
            return 2
    else:
        if ns.bundle is None or ns.execute or any((ns.manifest, ns.manifest_sha256,
                                                  ns.expected_head, ns.expected_tree)):
            ap.error("select bundle routing or an explicit exact Zenodo request")
        result = route_bundle(ns.bundle)
    print(json.dumps(result,ensure_ascii=False,sort_keys=True) if ns.json else "\n".join(f"{k}={v}" for k,v in result.items()))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
