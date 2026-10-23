#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Restore pinned local model artifacts from ordered private backup chunks.

No network, provider credentials, runtime launch, overwrite or executor effects.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.qikvrt_local_llm import LOCK, verified_fd


def restore(source: Path, target: Path, parts: list, expected: dict):
    if target.exists() or target.is_symlink():
        raise ValueError("RESTORE_TARGET_ALREADY_EXISTS")
    if any(p.is_symlink() for p in [target.parent, *target.parent.parents]):
        raise ValueError("RESTORE_DIRECTORY_SYMLINK_REFUSED")
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if target.parent.stat().st_mode & 0o077:
        raise ValueError("RESTORE_DIRECTORY_REQUIRES_MODE_0700")
    descriptor, temporary = tempfile.mkstemp(prefix=".qikvrt-restore-", dir=target.parent)
    digest = hashlib.sha256(); size = 0
    try:
        with os.fdopen(descriptor, "wb") as output:
            for part in parts:
                fd = verified_fd(source, part)
                try:
                    while raw := os.read(fd, 1024 * 1024):
                        output.write(raw); digest.update(raw); size += len(raw)
                finally:
                    os.close(fd)
            output.flush(); os.fsync(output.fileno())
        if size != expected["bytes"] or digest.hexdigest() != expected["sha256"]:
            raise ValueError("RESTORED_WHOLE_ARTIFACT_MISMATCH")
        # Atomic no-overwrite publication, including a concurrent target creator.
        os.link(temporary, target)
        directory_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
        return {"file": target.name, "bytes": size, "sha256": digest.hexdigest()}
    finally:
        os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text())
    parts = json.loads((ROOT / "runtime/models/smollm3-3b-q4-k-m.parts.json").read_text())
    if any(parts.get(k) != lock["model"][k] for k in ("file", "bytes", "sha256")):
        raise ValueError("BACKUP_MANIFEST_MODEL_BINDING_MISMATCH")
    results = [restore(args.parts_dir, args.model_dir / lock["model"]["file"], parts["parts"], lock["model"])]
    results.append(restore(args.parts_dir, args.model_dir / lock["runtime"]["file"], [lock["runtime"]], lock["runtime"]))
    print(json.dumps({"state": "LOCAL_ARTIFACT_BYTES_RESTORED_AND_VERIFIED", "artifacts": results,
                      "runtime_started": False, "effect_ack_done": False}, sort_keys=True))


if __name__ == "__main__": main()
