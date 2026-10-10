#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Build a static offline shell and a byte-verified Git working-tree transfer.

No GitHub writes, executor, credential access or native approval mutation.
The transfer contains files and local-history metadata, never a .git directory.
"""
from __future__ import annotations
import argparse
import base64
import gzip
import hashlib
import json
import pathlib
import subprocess
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLIENT = ROOT / "docs/monitor/offline"
CHUNK = 1048576
ASSETS = ("index.html", "style.css", "manifest.webmanifest", "icon.svg", "client.js", "updates.js", "repository.js", "git-hash.js", "vendor/react-runtime.js", "vendor/REACT_LICENSE.txt")

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)

def tree_hash(files):
    root = {}
    for entry in files:
        node = root
        parts = entry["path"].split("/")
        for part in parts[:-1]:
            if part in node and not isinstance(node[part], dict):
                raise ValueError("FILE_DIRECTORY_CONFLICT")
            node = node.setdefault(part, {})
        node[parts[-1]] = (entry["mode"], entry["git_blob_sha1"])
    def visit(node):
        rows = []
        for name, value in node.items():
            directory = isinstance(value, dict)
            mode, sha = ("40000", visit(value)) if directory else value
            rows.append(((name + ("/" if directory else "")).encode(), (mode + " " + name + "\0").encode() + bytes.fromhex(sha)))
        body = b"".join(row for _, row in sorted(rows))
        return hashlib.sha1(b"tree " + str(len(body)).encode() + b"\0" + body).hexdigest()
    return visit(root)

def shell(client=CLIENT):
    hashes = {name: hashlib.sha256((client / name).read_bytes()).hexdigest() for name in ASSETS}
    template = (client / "service-worker.template.js").read_text()
    template_sha = hashlib.sha256(template.encode()).hexdigest()
    binding = {"assets": hashes, "worker_template_sha256": template_sha}
    shell_id = hashlib.sha256(canonical(binding).encode()).hexdigest()
    worker = template.replace("__SHELL_ID__", shell_id).replace("__ASSETS__", canonical(hashes)).replace("__WORKER_TEMPLATE_SHA256__", template_sha)
    (client / "service-worker.js").write_text(worker)
    return {"schema": "qikvrt-offline-shell/v1", "shell_sha256": shell_id, "assets": hashes}

def client_package(ref, output):
    """Export only committed static-client bytes; never private browser data."""
    output = pathlib.Path(output)
    if output.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    head = git("rev-parse", "--verify", ref + "^{commit}").decode().strip()
    tree = git("rev-parse", head + "^{tree}").decode().strip()
    files = {}
    for name in (*ASSETS, "service-worker.js", "static-server.mjs", "package.json", "README.md"):
        files[name] = git("show", head + ":docs/monitor/offline/" + name)
    binding = {"schema": "qikvrt-offline-client-source/v1", "repository": "ingolf-lohmann/qik-vrt", "source_head": head, "source_tree": tree,
               "files": {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in sorted(files.items())},
               "first_install_requires_https": True, "actual_iphone_devices_tested": False, "native_review": False, "main_effect": False}
    files["SOURCE.json"] = (canonical(binding) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return {"schema": "qikvrt-offline-client-receipt/v1", "source_head": head, "source_tree": tree, "archive_bytes": output.stat().st_size, "archive_sha256": file_hash(output), "files": len(files), "native_review": False, "main_effect": False}

def pack(ref, output, paths=()):
    output = pathlib.Path(output)
    if output.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    head = git("rev-parse", "--verify", ref + "^{commit}").decode().strip()
    tree = git("rev-parse", head + "^{tree}").decode().strip()
    created = git("show", "-s", "--format=%cI", head).decode().strip()
    inventory = []
    for line in git("ls-tree", "-rz", head).split(b"\0"):
        if not line:
            continue
        meta, path = line.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        path = path.decode("utf-8", "strict")
        if kind != "blob":
            raise ValueError("SUBMODULE_REQUIRES_EXPLICIT_EXPORT")
        if not paths or path in paths:
            inventory.append((path, mode, oid))
    if paths and set(paths) != {path for path, _, _ in inventory}:
        raise ValueError("SELECTED_SOURCE_PATH_MISSING")
    inventory.sort()
    known, files, total = set(), [], 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile() as staging:
        process = subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        try:
            for path, mode, oid in inventory:
                process.stdin.write((oid + "\n").encode()); process.stdin.flush()
                object_id, kind, length = process.stdout.readline().decode().split()
                if object_id != oid or kind != "blob":
                    raise ValueError("SOURCE_GIT_OBJECT_MISMATCH")
                length = int(length)
                blob = hashlib.sha1(b"blob " + str(length).encode() + b"\0")
                chunks, remaining = [], length
                while remaining:
                    size = min(remaining, CHUNK)
                    raw = process.stdout.read(size)
                    if len(raw) != size:
                        raise ValueError("TRUNCATED_GIT_OBJECT")
                    blob.update(raw)
                    sha = hashlib.sha256(raw).hexdigest()
                    chunks.append({"sha256": sha, "bytes": size})
                    if sha not in known:
                        known.add(sha)
                        staging.write((canonical({"type": "block", "sha256": sha, "data": base64.b64encode(raw).decode()}) + "\n").encode())
                    remaining -= size
                if process.stdout.read(1) != b"\n" or blob.hexdigest() != oid:
                    raise ValueError("SOURCE_GIT_BLOB_DIGEST_MISMATCH")
                files.append({"path": path, "mode": mode, "bytes": length, "git_blob_sha1": oid, "chunks": chunks})
                total += length
                if total > 2147483648:
                    raise ValueError("REPOSITORY_CAPACITY_LIMIT")
        finally:
            process.stdin.close()
            process.stdout.close()
            if process.wait() != 0:
                raise ValueError("GIT_SOURCE_EXPORT_FAILED")
        calculated_tree = tree_hash(files)
        if not paths and calculated_tree != tree:
            raise ValueError("COMPLETE_GIT_TREE_MISMATCH")
        snapshot = {"schema": "qikvrt-offline-snapshot/v1", "repository_id": "ingolf-lohmann/qik-vrt", "parents": [], "source": {"repository": "ingolf-lohmann/qik-vrt", "head": head, "tree": tree, "scope": "SELECTED_GIT_FILES" if paths else "COMPLETE_GIT_WORKING_TREE", "git_object_bytes_verified": True}, "created_at": created, "message": "Quellgebundene Offline-Arbeitskopie", "files": files, "git_tree_sha1": calculated_tree}
        raw = canonical(snapshot).encode()
        if len(raw) > 1499800:
            raise ValueError("SNAPSHOT_METADATA_CAPACITY_LIMIT")
        revision = hashlib.sha256(raw).hexdigest()
        header = {"schema": "qikvrt-offline-archive/v1", "repository_id": snapshot["repository_id"], "head": revision}
        with output.open("xb") as carrier:
            with gzip.GzipFile(filename="", mode="wb", fileobj=carrier, mtime=0) if output.name.endswith(".gz") else _plain(carrier) as destination:
                destination.write((canonical(header) + "\n").encode())
                staging.seek(0)
                while data := staging.read(CHUNK):
                    destination.write(data)
                destination.write((canonical({"type": "snapshot", "id": revision, "snapshot": snapshot}) + "\n").encode())
                destination.write((canonical({"type": "end", "head": revision, "blocks": len(known), "snapshots": 1}) + "\n").encode())
    return {"schema": "qikvrt-offline-export-receipt/v1", "source_head": head, "source_tree": tree, "working_tree": calculated_tree, "snapshot": revision, "files": len(files), "source_bytes": total, "archive_bytes": output.stat().st_size, "archive_sha256": file_hash(output), "scope": snapshot["source"]["scope"], "mobile_device_readback": False, "native_review": False, "effect_ack_done": False}

class _plain:
    def __init__(self, file): self.file = file
    def __enter__(self): return self.file
    def __exit__(self, *args): return False

def file_hash(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        while raw := f.read(CHUNK): h.update(raw)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("shell", "pack", "client"))
    parser.add_argument("--ref", default="HEAD")
    parser.add_argument("--output")
    parser.add_argument("--path", action="append", default=[])
    args = parser.parse_args()
    if args.command != "shell" and not args.output: parser.error(args.command + " requires --output")
    print(json.dumps(shell() if args.command == "shell" else client_package(args.ref, args.output) if args.command == "client" else pack(args.ref, args.output, args.path), indent=2, sort_keys=True))

if __name__ == "__main__": main()
