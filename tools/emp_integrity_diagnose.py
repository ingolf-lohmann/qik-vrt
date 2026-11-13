"""TEMDD diagnostic for deterministic repository integrity drift.

Read-only: compares generated metadata with committed metadata without
rewriting the manifest or asserting that regeneration is authorized.
"""
import difflib
import hashlib
import json
from pathlib import Path
from tools import qikvrt_integrity as integrity


def diagnose(root: Path) -> dict:
    expected_manifest, expected_index, expected_detached, _ = integrity.build_outputs(root)
    expected = {
        integrity.MANIFEST_NAME: expected_manifest,
        integrity.INDEX_NAME: expected_index,
        integrity.DETACHED_NAME: expected_detached,
    }
    differences = []
    for name, generated in expected.items():
        path = root / name
        stored = integrity._regular_file_bytes(root, name, max_bytes=integrity.MAX_INTEGRITY_METADATA_BYTES)
        if stored == generated:
            continue
        entry = {
            "path": name, "stored_sha256": hashlib.sha256(stored).hexdigest(),
            "generated_sha256": hashlib.sha256(generated).hexdigest(),
            "stored_bytes": len(stored), "generated_bytes": len(generated),
        }
        if name == integrity.MANIFEST_NAME:
            old = json.loads(stored)
            new = json.loads(generated)
            old_files = {x["path"]: x for x in old["files"]}
            new_files = {x["path"]: x for x in new["files"]}
            entry["added_paths"] = sorted(new_files.keys() - old_files.keys())
            entry["removed_paths"] = sorted(old_files.keys() - new_files.keys())
            entry["changed_paths"] = sorted(
                k for k in old_files.keys() & new_files.keys()
                if old_files[k] != new_files[k])
            entry["other_changed_keys"] = sorted(
                k for k in old.keys() | new.keys()
                if k != "files" and old.get(k) != new.get(k))
        differences.append(entry)
    return {"integrity_match": not differences, "differences": differences,
            "effect_ack_done": False, "manifest_modified": False}


if __name__ == "__main__":
    result = diagnose(integrity.ROOT)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["integrity_match"] else 2)
