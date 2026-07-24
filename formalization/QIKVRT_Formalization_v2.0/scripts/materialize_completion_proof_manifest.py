#!/usr/bin/env python3
"""Materialize proof-object coverage for every completed manuscript binding."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath

import materialize_completion as completion

ROOT = completion.PROJECT_ROOT
MANIFEST = ROOT / "proofs" / "PROOF_OBJECT_MANIFEST.json"
STATUS = "KERNEL_CHECK_REQUIRED_ON_EVERY_DISTINCT_INPUT_SET"


def compiled_object(source_path: str) -> str:
    source = PurePosixPath(source_path)
    return str(PurePosixPath(".lake/build/lib/lean").joinpath(source.with_suffix(".olean")))


def materialized() -> dict:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    existing = {
        item["claimId"]: item
        for item in value.get("objects", [])
        if isinstance(item, dict) and isinstance(item.get("claimId"), str)
    }
    for claim_id, binding in completion.ALL_FORMAL_BINDINGS.items():
        existing[claim_id] = {
            "claimId": claim_id,
            "statementConstant": binding["statementConstant"],
            "proofConstant": binding["proofConstant"],
            "registryConstant": binding["registryConstant"],
            "sourcePath": binding["sourcePath"],
            "registrySourcePath": binding["registrySourcePath"],
            "compiledObject": compiled_object(binding["sourcePath"]),
            "status": STATUS,
        }
    value["objects"] = [existing[key] for key in sorted(existing)]
    return value


def serialize(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = serialize(materialized())
    if args.check:
        if not args.manifest.is_file() or args.manifest.read_text(encoding="utf-8") != expected:
            raise SystemExit(f"stale completion proof-object manifest: {args.manifest}")
        print(
            f"PASS completion proof-object manifest current: "
            f"{len(completion.ALL_FORMAL_BINDINGS) + 1} manuscript proof bindings"
        )
        return 0
    args.manifest.write_text(expected, encoding="utf-8")
    print(
        f"PASS wrote completion proof-object manifest: "
        f"{len(completion.ALL_FORMAL_BINDINGS) + 1} manuscript proof bindings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
