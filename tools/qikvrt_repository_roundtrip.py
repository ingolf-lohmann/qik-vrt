#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Repository-wide byte-exact reflexive codec over a pinned Git tree.

A record carries raw file bytes, path bytes and Git mode. No checkout filters,
text transcoding, or lossy normalization. No Git objects are mutated.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import pathlib
import re
import subprocess
import sys

MAX_BLOB = 64 * 1024 * 1024


class RoundtripError(RuntimeError):
    pass


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE)


def records(root, commit):
    if not re.fullmatch("[0-9a-f]{40}", commit):
        raise RoundtripError("exact 40-character commit required")
    tree = git(root, "rev-parse", commit + "^{tree}").decode().strip()
    listing = git(root, "ls-tree", "-r", "-z", "--full-tree", commit)
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        mode, kind, oid = meta.split(b" ")
        if kind != b"blob" or mode not in (b"100644", b"100755", b"120000"):
            raise RoundtripError("unsupported tree entry")
        raw = git(root, "cat-file", "blob", oid.decode())
        if len(raw) > MAX_BLOB:
            raise RoundtripError("blob size limit")
        yield {"mode": mode.decode(), "path_b64": base64.b64encode(path).decode(),
               "oid": oid.decode(), "data_b64": base64.b64encode(raw).decode()}
    return tree


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def roundtrip(root, commit, output):
    tree = git(root, "rev-parse", commit + "^{tree}").decode().strip()
    count = 0
    byte_count = 0
    digest = hashlib.sha256()
    with open(output, "wb") as target:
        header = canonical({"schema": "qikvrt_git_tree_roundtrip_v1",
                            "commit": commit, "tree": tree}) + b"\n"
        target.write(header)
        digest.update(header)
        for item in records(root, commit):
            serialized = canonical(item)
            restored = json.loads(serialized)
            raw = base64.b64decode(restored["data_b64"], validate=True)
            path = base64.b64decode(restored["path_b64"], validate=True)
            # Git blob identity is computed on original bytes, not decoded text.
            git_oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if git_oid != item["oid"] or base64.b64encode(path).decode() != item["path_b64"]:
                raise RoundtripError("blob/path roundtrip mismatch")
            line = serialized + b"\n"
            target.write(line)
            digest.update(line)
            count += 1
            byte_count += len(raw)
    # Independent replay from serialized bytes, not original in-memory objects.
    replay_digest = hashlib.sha256()
    replay_count = 0
    with open(output, "rb") as source:
        header = source.readline()
        if json.loads(header) != {"schema": "qikvrt_git_tree_roundtrip_v1",
                                  "commit": commit, "tree": tree}:
            raise RoundtripError("header readback mismatch")
        replay_digest.update(header)
        for line in source:
            item = json.loads(line)
            if canonical(item) + b"\n" != line:
                raise RoundtripError("noncanonical replay")
            raw = base64.b64decode(item["data_b64"], validate=True)
            if hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != item["oid"]:
                raise RoundtripError("replay blob mismatch")
            base64.b64decode(item["path_b64"], validate=True)
            if item["mode"] not in ("100644", "100755", "120000"):
                raise RoundtripError("replay mode mismatch")
            replay_digest.update(line)
            replay_count += 1
    if replay_digest.digest() != digest.digest() or replay_count != count:
        raise RoundtripError("replay mismatch")
    return {"commit": commit, "tree": tree, "files": count, "payload_bytes": byte_count,
            "serialized_sha256": digest.hexdigest(), "roundtrip": "PASS",
            "effect_ack_done": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    print(json.dumps(roundtrip(args.root, args.commit, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
