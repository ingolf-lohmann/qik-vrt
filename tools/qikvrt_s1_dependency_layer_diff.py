#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Bounded, data-only TEMDD comparison of two already-validated OCI layer archives.

Does not extract to disk, import an image, run a command or authenticate an EAP
effect. It discloses only changed paths, metadata and SHA-256s, never file bytes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path

PIN = re.compile(r"sha256:[0-9a-f]{64}\Z")
MAX_MEMBERS = 250_000
MAX_EXPANDED_BYTES = 3 * 1024 ** 3


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def layer_records(oci_archive: Path, layer_digest: str) -> dict:
    if not isinstance(layer_digest, str) or PIN.fullmatch(layer_digest) is None:
        raise ValueError("EXACT_LAYER_DIGEST_REQUIRED")
    rows = {}
    decompressed_bytes = 0
    with tarfile.open(oci_archive, mode="r:*") as outer:
        name = "blobs/sha256/" + layer_digest[7:]
        matches = [item for item in outer.getmembers() if item.name.lstrip("./") == name]
        if len(matches) != 1 or not matches[0].isfile():
            raise ValueError("EXACT_REGULAR_LAYER_REQUIRED")
        stream = outer.extractfile(matches[0])
        if stream is None:
            raise ValueError("LAYER_STREAM_MISSING")
        with stream, tarfile.open(fileobj=stream, mode="r|gz") as layer:
            for item in layer:
                if len(rows) >= MAX_MEMBERS or len(item.name) > 2048:
                    raise ValueError("LAYER_INVENTORY_BOUND_EXCEEDED")
                if item.name in rows:
                    raise ValueError("DUPLICATE_LAYER_PATH")
                record = {
                    "type": item.type.decode("latin-1") if isinstance(item.type, bytes) else str(item.type),
                    "bytes": item.size, "mode": item.mode,
                    "uid": item.uid, "gid": item.gid, "mtime": item.mtime,
                    "linkname": item.linkname, "pax": item.pax_headers,
                }
                if item.isfile():
                    content = layer.extractfile(item)
                    if content is None:
                        raise ValueError("LAYER_MEMBER_UNREADABLE")
                    digest = hashlib.sha256()
                    with content:
                        for chunk in iter(lambda: content.read(1024 * 1024), b""):
                            decompressed_bytes += len(chunk)
                            if decompressed_bytes > MAX_EXPANDED_BYTES:
                                raise ValueError("LAYER_DECOMPRESSED_BOUND_EXCEEDED")
                            digest.update(chunk)
                    record["sha256"] = digest.hexdigest()
                rows[item.name] = record
    return rows


def compare_oci(first: Path, second: Path, receipt: dict) -> dict:
    if receipt.get("cause") != "INDEPENDENT_OCI_REBUILD_DIGEST_MISMATCH" or receipt.get("effect_ack_done") is not False:
        raise ValueError("EXACT_FAILED_COMPARISON_REQUIRED")
    a, b = receipt.get("first_build"), receipt.get("second_build")
    if not isinstance(a, dict) or not isinstance(b, dict):
        raise ValueError("TWO_VALIDATED_BUILD_RECEIPTS_REQUIRED")
    if a.get("source_head") != b.get("source_head") or a.get("source_tree") != b.get("source_tree"):
        raise ValueError("SOURCE_BINDING_MISMATCH")
    for path, row in ((first, a), (second, b)):
        if not path.is_file() or path.is_symlink() or _digest(path) != row.get("oci_archive_sha256"):
            raise ValueError("OCI_ARCHIVE_SHA256_READBACK_MISMATCH")
    before, after = a.get("diff_ids"), b.get("diff_ids")
    layers_before, layers_after = a.get("layer_digests"), b.get("layer_digests")
    if not all(isinstance(v, list) and len(v) == len(before) for v in (before, after, layers_before, layers_after)):
        raise ValueError("ALIGNED_LAYERS_REQUIRED")
    mismatches = []
    for index, (old, new) in enumerate(zip(before, after)):
        if old == new:
            continue
        prev = layer_records(first, layers_before[index])
        curr = layer_records(second, layers_after[index])
        changed = [path for path in sorted(prev.keys() | curr.keys()) if prev.get(path) != curr.get(path)]
        mismatches.append({
            "layer_index": index, "first_diff_id": old, "second_diff_id": new,
            "first_members": len(prev), "second_members": len(curr),
            "changed_path_count": len(changed), "changed_paths_bounded": [
                {"path": name, "first": prev.get(name), "second": curr.get(name)}
                for name in changed[:75]
            ],
            "sample_truncated": len(changed) > 75,
            "cause_class": "FILE_OR_METADATA_DELTA" if changed else "OPAQUE_LAYER_BYTES_DRIFT",
        })
    if not mismatches:
        raise ValueError("NO_DIFF_IDS_TO_DIAGNOSE")
    return {
        "schema": "qikvrt_s1_oci_temdd_layer_diff_v1",
        "state": "CAUSE_ISOLATED_NO_ADMISSION",
        "source_head": a["source_head"], "source_tree": a["source_tree"],
        "first_image_digest": a["image_digest"], "second_image_digest": b["image_digest"],
        "differences": mismatches,
        "candidate_admitted": False, "effect_ack_done": False,
        "release_admission": "BLOCKED",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--first", type=Path, required=True)
    p.add_argument("--second", type=Path, required=True)
    p.add_argument("--oci-receipt", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("CREATE_ONLY_DIAGNOSIS_REQUIRED")
    result = compare_oci(args.first, args.second, json.loads(args.oci_receipt.read_bytes()))
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"state": result["state"], "layers": [
        {"index": x["layer_index"], "changed_paths": x["changed_path_count"], "class": x["cause_class"]}
        for x in result["differences"]], "effect_ack_done": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
