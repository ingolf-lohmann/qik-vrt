#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Frozen Git source -> standard ZIP -> native QIKVRTC / Linux SFX.

Reuses the existing QIKVRTC wire/signature, C90 compiler and original S1
runtime sources. No credentials, network, source execution or node admission.
The complete source-tree scope is explicit; Git history is not silently implied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import struct
import subprocess
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
META = ".QIKVRT_ARCHIVE/"
LIMIT = 2**31 - 1
SFX_FOOTER = struct.Struct(">8sQQ32s")
SOURCES = ("src/sha256.c", "src/codec_native.c", "src/finite_machine.c", "tools/qikvrt_archive_native.c")


def zip_entry(name, *, mode=0o100644, compression=zipfile.ZIP_DEFLATED):
    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = mode << 16
    info.compress_type = compression
    return info


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compile_native(output, *, compiler="cc", sanitize=False):
    output = Path(output)
    source_hashes = {p: file_digest(ROOT / p) for p in SOURCES}
    header_hashes = {str(p.relative_to(ROOT)): file_digest(p)
                     for p in sorted((ROOT / "include/qikvrt").glob("*.h"))}
    flags = ["-std=c90", "-pedantic-errors", "-Wall", "-Wextra", "-Werror"]
    flags += (["-O1", "-g", "-fsanitize=undefined", "-fno-sanitize-recover=all"]
              if sanitize else ["-O2"])
    command = [compiler, *flags, "-I", str(ROOT / "include"),
               *(str(ROOT / p) for p in SOURCES), "-lz", "-o", str(output)]
    subprocess.run(command, check=True, capture_output=True, timeout=120)
    if any(file_digest(ROOT / p) != h for p, h in {**source_hashes, **header_hashes}.items()):
        raise ValueError("NATIVE_SOURCE_CHANGED_DURING_BUILD")
    zlib_path = Path(subprocess.check_output([compiler, "-print-file-name=libz.so"], text=True).strip()).resolve()
    return {"compiler": subprocess.check_output([compiler, "--version"], text=True).splitlines()[0],
            "command": command, "binary_sha256": file_digest(output),
            "version": subprocess.check_output([str(output), "--version"], text=True).strip(),
            "sources_sha256": source_hashes, "headers_sha256": header_hashes,
            "zlib_shared_library": {"path": str(zlib_path), "sha256": file_digest(zlib_path)}}


def binary_increment_program():
    # State zero scans ones to the right; the first zero becomes one, then HALT.
    return b"QIKTM01\0" + struct.pack(">H", 1) + struct.pack(">HBBHBB", 65535, 1, 1, 0, 1, 2)


def terminal_readback(program_sha256, result):
    """Use the ORIGINAL terminal's authenticated local-input profile, once.

    This observes the bounded computation result. It neither executes a
    caller-supplied host command nor impersonates a productive native ledger.
    """
    import datetime
    from http.server import ThreadingHTTPServer
    import secrets
    import sys
    import threading
    import urllib.error
    import urllib.request
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src import qikvrt_effect_ack_http_terminal as terminal
    previous = terminal.STATE
    terminal.STATE = terminal.State()
    server = ThreadingHTTPServer(("127.0.0.1", 0), terminal.Handler)
    token = secrets.token_urlsafe(32)
    server.terminal_auth_token = token
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(path, body=None, field=None, authenticated=True):
        headers = {"Authorization": "Bearer " + token} if authenticated else {}
        if field:
            headers["Effect-Ack-Request"] = field
        data = None if body is None else terminal.canonical_json(body)
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"http://127.0.0.1:{server.server_port}" + path,
                                     data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    try:
        unauthorized, _ = request("/.well-known/effect-ack", authenticated=False)
        discovery, _ = request("/.well-known/effect-ack")
        text = json.dumps({"program_sha256": program_sha256, "result": result}, sort_keys=True)
        body = {"schema": "qikvrt_terminal_input_v1", "text": text,
                "submitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "audio": None, "video": None}
        input_hash = hashlib.sha256(terminal.canonical_json(body)).hexdigest()
        code, prepared = request("/terminal/prepare", body, "v=1, mode=prepare")
        if code != 200 or prepared.get("ordinary_release") is not False:
            raise ValueError("ORIGINAL_TERMINAL_PREPARE_FAILED")
        field = ("v=1, mode=commit, token=" + terminal.sf_bytes(prepared["commit_token"].encode())
                 + ", hash=" + terminal.sf_bytes(bytes.fromhex(prepared["record_hash"])))
        wrong, _ = request("/terminal/commit", dict(body, text="altered"), field)
        commit_status, committed = request("/terminal/commit", body, field)
        replay_status, _ = request("/terminal/commit", body, field)
        state_status, observed = request("/terminal/state")
        event = observed.get("last_event") or {}
        if (unauthorized != 401 or discovery != 200 or wrong != 409
                or commit_status != 200 or replay_status != 409 or state_status != 200
                or observed.get("events") != 1 or event.get("text") != text
                or event.get("input_hash") != input_hash or event.get("external_effect") != "NONE"
                or committed.get("post_effect") != event):
            raise ValueError("ORIGINAL_TERMINAL_INDEPENDENT_READBACK_FAILED")
        return {"scope": "ORIGINAL_AUTHENTICATED_LOOPBACK_TERMINAL_INPUT_ONLY",
                "unauthenticated_status": unauthorized, "discovery_status": discovery,
                "changed_input_status": wrong, "commit_status": commit_status,
                "replay_status": replay_status, "readback_status": state_status,
                "input_sha256": input_hash, "event": event,
                "productive_native_mesh_admission": False}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        terminal.STATE = previous


def snapshot_zip(repository, commit, output):
    """Archive every tracked blob, modes and symlink bytes, using one batch reader."""
    repository, output = Path(repository), Path(output)
    git = ["git", "-C", str(repository)]
    commit = subprocess.check_output(git + ["rev-parse", "--verify", commit + "^{commit}"], text=True).strip()
    tree = subprocess.check_output(git + ["rev-parse", commit + "^{tree}"], text=True).strip()
    commit_data = subprocess.check_output(git + ["cat-file", "commit", commit])
    if (hashlib.sha1(b"commit " + str(len(commit_data)).encode() + b"\0" + commit_data).hexdigest() != commit
            or not commit_data.startswith(b"tree " + tree.encode() + b"\n")):
        raise ValueError("GIT_COMMIT_IDENTITY_MISMATCH")
    records = subprocess.check_output(git + ["ls-tree", "-rtz", "--full-tree", tree]).split(b"\0")
    entries, trees = [], {tree}
    for row in filter(None, records):
        metadata, raw_name = row.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        if kind == "tree" and mode == "040000":
            trees.add(oid)
            continue
        name = raw_name.decode("utf-8", "strict")
        path = PurePosixPath(name)
        if (kind != "blob" or mode not in {"100644", "100755", "120000"}
                or path.is_absolute() or str(path) != name
                or ".." in path.parts or "\\" in name or name.startswith(META)):
            raise ValueError("UNSUPPORTED_OR_UNSAFE_SOURCE_PATH: " + name)
        entries.append((name, mode, oid))
    entries.sort()
    batch = subprocess.Popen(git + ["cat-file", "--batch"], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    manifest = {"schema": "qikvrt-native-source-archive/v1", "repository": "ingolf-lohmann/qik-vrt",
                "commit": commit, "tree": tree, "scope": "COMPLETE_TRACKED_SOURCE_TREE_NOT_GIT_HISTORY",
                "signature_sha256": file_digest(ROOT / "canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin"),
                "files": []}
    try:
        # Authenticate every traversed tree object, not only Git's displayed OID.
        for oid in sorted(trees):
            batch.stdin.write(oid.encode() + b"\n")
            batch.stdin.flush()
            header = batch.stdout.readline().decode("ascii").split()
            if len(header) != 3 or header[:2] != [oid, "tree"]:
                raise ValueError("GIT_TREE_UNAVAILABLE")
            size = int(header[2])
            if not 0 <= size <= LIMIT:
                raise ValueError("GIT_TREE_SIZE_LIMIT")
            digest = hashlib.sha1(b"tree " + str(size).encode() + b"\0")
            remaining = size
            while remaining:
                block = batch.stdout.read(min(remaining, 1024 * 1024))
                if not block:
                    raise ValueError("GIT_TREE_TRUNCATED")
                digest.update(block)
                remaining -= len(block)
            if batch.stdout.read(1) != b"\n" or digest.hexdigest() != oid:
                raise ValueError("GIT_TREE_IDENTITY_MISMATCH")
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for name, mode, oid in entries:
                batch.stdin.write(oid.encode() + b"\n")
                batch.stdin.flush()
                header = batch.stdout.readline().decode("ascii").split()
                if len(header) != 3 or header[:2] != [oid, "blob"]:
                    raise ValueError("GIT_BLOB_UNAVAILABLE: " + name)
                count = int(header[2])
                if not 0 <= count <= LIMIT:
                    raise ValueError("SOURCE_SIZE_LIMIT")
                info = zip_entry(name, mode=int(mode, 8))
                info.file_size = count
                digest, remaining = hashlib.sha256(), count
                git_digest = hashlib.sha1(b"blob " + str(count).encode() + b"\0")
                with z.open(info, "w") as sink:
                    while remaining:
                        block = batch.stdout.read(min(remaining, 1024 * 1024))
                        if not block:
                            raise ValueError("GIT_BLOB_TRUNCATED")
                        digest.update(block)
                        git_digest.update(block)
                        sink.write(block)
                        remaining -= len(block)
                if batch.stdout.read(1) != b"\n" or git_digest.hexdigest() != oid:
                    raise ValueError("GIT_BATCH_FRAMING")
                manifest["files"].append({"path": name, "mode": mode, "git_blob": oid,
                                          "bytes": count, "sha256": digest.hexdigest()})
            z.writestr(zip_entry(META + "manifest.json"), json.dumps(manifest, ensure_ascii=False,
                                                        sort_keys=True, indent=2).encode() + b"\n")
            z.writestr(zip_entry(META + "standpoint.bin"), (ROOT / "canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin").read_bytes())
        batch.stdin.close()
        if batch.wait(timeout=30) != 0:
            raise ValueError("GIT_BATCH_FAILED")
    finally:
        if batch.poll() is None:
            batch.kill()
            batch.wait()
        for stream in (batch.stdin, batch.stdout, batch.stderr):
            if stream and not stream.closed:
                stream.close()
    if output.stat().st_size > LIMIT:
        raise ValueError("NATIVE_ARCHIVE_SIZE_LIMIT")
    return manifest


def verify_snapshot(archive, expected):
    with zipfile.ZipFile(archive) as z:
        expected_names = [e["path"] for e in expected["files"]] + [META + "manifest.json", META + "standpoint.bin"]
        if z.namelist() != expected_names or len(set(z.namelist())) != len(expected_names):
            raise ValueError("ARCHIVE_INVENTORY_MISMATCH")
        if json.loads(z.read(META + "manifest.json")) != expected:
            raise ValueError("ARCHIVE_MANIFEST_MISMATCH")
        signature = z.read(META + "standpoint.bin")
        if len(signature) != 400 or hashlib.sha256(signature).hexdigest() != expected["signature_sha256"]:
            raise ValueError("ARCHIVE_SIGNATURE_MISMATCH")
        for entry in expected["files"]:
            info = z.getinfo(entry["path"])
            digest, count = hashlib.sha256(), 0
            git_digest = hashlib.sha1(b"blob " + str(entry["bytes"]).encode() + b"\0")
            with z.open(info) as f:
                for block in iter(lambda: f.read(1024 * 1024), b""):
                    digest.update(block)
                    git_digest.update(block)
                    count += len(block)
            if (count != entry["bytes"] or digest.hexdigest() != entry["sha256"]
                    or git_digest.hexdigest() != entry["git_blob"]
                    or (info.external_attr >> 16) != int(entry["mode"], 8)):
                raise ValueError("ARCHIVE_FILE_MISMATCH: " + entry["path"])
    return len(expected["files"])


def self_extractor(binary, source_zip, output):
    """Real ELF prefix + standard stored ZIP entry + bounded comment locator.

    Inner repository.zip remains byte-exact, and independent ZIP readers can
    access it without executing the ELF. No zero-byte prefix is prepended to ELF.
    """
    binary, source_zip, output = map(Path, (binary, source_zip, output))
    if binary.read_bytes()[:4] != b"\x7fELF":
        raise ValueError("TESTED_SFX_PROFILE_REQUIRES_ELF")
    shutil.copyfile(binary, output)
    with zipfile.ZipFile(output, "a") as z:
        size = source_zip.stat().st_size
        info = zip_entry("repository.zip", compression=zipfile.ZIP_STORED)
        info.file_size = size
        with source_zip.open("rb") as source, z.open(info, "w") as sink:
            shutil.copyfileobj(source, sink, 1024 * 1024)
        info = z.getinfo("repository.zip")
        offset = info.header_offset + 30 + len(info.filename.encode("utf-8")) + len(info.extra)
        if not 22 <= size <= LIMIT or offset > LIMIT:
            raise ValueError("SFX_NATIVE_SIZE_LIMIT")
        z.writestr(zip_entry("QIKVRT_RUNTIME/binary_increment.tm"), binary_increment_program())
        z.comment = SFX_FOOTER.pack(b"QIKSFX1\0", offset, size, bytes.fromhex(file_digest(source_zip)))
    output.chmod(0o700)
    return {"profile": "LINUX_ELF_POSIX_DYNAMIC_LIBZ", "payload_offset": offset,
            "payload_bytes": size, "payload_sha256": file_digest(source_zip),
            "sfx_sha256": file_digest(output), "sfx_bytes": output.stat().st_size}


def prove(repository, commit, output):
    driver_hash = file_digest(__file__)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    binary, archive = output / "qikvrt-archive", output / "repository.zip"
    build = compile_native(binary)
    manifest = snapshot_zip(repository, commit, archive)
    verify_snapshot(archive, manifest)
    wire, restored = output / "repository.qikvrt", output / "restored.zip"
    trials = []
    for operation, arguments in [("encode", ["encode", "balanced", str(archive), str(wire)]),
                                 ("decode", ["decode", str(wire), str(restored)])]:
        start = time.perf_counter_ns()
        subprocess.run([str(binary), *arguments], check=True, capture_output=True, timeout=900)
        trials.append({"operation": operation, "wall_ns": time.perf_counter_ns() - start})
    if file_digest(archive) != file_digest(restored):
        raise ValueError("NATIVE_COMPLETE_ARCHIVE_ROUNDTRIP_FAILED")
    verify_snapshot(restored, manifest)
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src import qikvrt_codec as reference
    python_restored = output / "python-reference-restored.zip"
    with wire.open("rb") as source, python_restored.open("wb") as target:
        reference.decode_stream(source, target, max_output_bytes=LIMIT)
    if file_digest(python_restored) != file_digest(archive):
        raise ValueError("FULL_ARCHIVE_PYTHON_REFERENCE_MISMATCH")
    sfx = output / "qikvrt-repository.run"
    sfx_info = self_extractor(binary, archive, sfx)
    self_output = output / "self-extracted.zip"
    subprocess.run([str(sfx), "extract", str(self_output)], check=True, capture_output=True, timeout=900)
    if file_digest(self_output) != file_digest(archive):
        raise ValueError("NATIVE_SELF_EXTRACTION_FAILED")
    program = output / "binary_increment.tm"
    program_readback = subprocess.check_output(["unzip", "-p", str(sfx), "QIKVRT_RUNTIME/binary_increment.tm"], timeout=30)
    if program_readback != binary_increment_program():
        raise ValueError("STORED_PROGRAM_READBACK_FAILED")
    program.write_bytes(program_readback)
    execution = subprocess.run([str(sfx), "machine", str(program), "1110", "100", "100"],
                               capture_output=True, check=True, timeout=10)
    machine_result = json.loads(execution.stdout)
    if machine_result != {"schema": "qikvrt-binary-machine-result/v1", "state": 65535,
                          "steps": 4, "head": 3, "cells": 4, "tape": "1111"}:
        raise ValueError("NATIVE_STORED_PROGRAM_RESULT_MISMATCH")
    readbacks = []
    for path in (archive, sfx, self_output):
        result = subprocess.run(["unzip", "-t", str(path)], capture_output=True, timeout=900)
        if result.returncode != 0:
            raise ValueError("INDEPENDENT_ZIP_READER_FAILED: " + path.name)
        readbacks.append({"file": path.name, "exit": result.returncode,
                          "output_sha256": hashlib.sha256(result.stdout + result.stderr).hexdigest()})
    if file_digest(__file__) != driver_hash:
        raise ValueError("EVIDENCE_DRIVER_CHANGED_DURING_PROOF")
    result = {"schema": "qikvrt-native-archive-evidence/v1", "driver_sha256": driver_hash,
              "reference_sha256": file_digest(ROOT / "src/qikvrt_codec.py"),
              "source": {k: manifest[k] for k in ("repository", "commit", "tree", "scope")},
              "source_files": len(manifest["files"]), "source_bytes": sum(e["bytes"] for e in manifest["files"]),
              "build": build, "host": {"system": platform.system(), "machine": platform.machine()},
              "archive_bytes": archive.stat().st_size, "archive_sha256": file_digest(archive),
              "wire_bytes": wire.stat().st_size, "wire_sha256": file_digest(wire),
              "restored_sha256": file_digest(restored), "self_extracted_sha256": file_digest(self_output),
              "python_reference_restored_sha256": file_digest(python_restored),
              "sfx": sfx_info, "trials": trials, "independent_zip_readbacks": readbacks,
              "stored_program": {"sha256": file_digest(program), "input": "1110", "result": machine_result,
                                 "output_sha256": hashlib.sha256(execution.stdout).hexdigest(),
                                 "scope": "BOUNDED_BINARY_TURING_TABLE_REFERENCE_NOT_MESH_ADMISSION"},
              "terminal": terminal_readback(file_digest(program), machine_result),
              "scope_status": {"complete_selected_source_archive_roundtrip": "VERIFIED", "linux_native_sfx": "VERIFIED",
                               "standard_zip_interoperability": "VERIFIED_WITH_INFOZIP_AND_PYTHON",
                               "winzip_application": "NOT_EXECUTED", "other_native_platforms": "OPEN",
                               "productive_mesh_transputer_terminal": "OPEN"},
              "effect_ack_done": False}
    (output / "EVIDENCE.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=ROOT)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prove(args.repository, args.commit, args.output)
    print(json.dumps({"source_files": result["source_files"], "archive_sha256": result["archive_sha256"],
                      "evidence": str(args.output / "EVIDENCE.json")}))


if __name__ == "__main__":
    main()
