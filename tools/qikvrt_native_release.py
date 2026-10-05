#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Build and rebuild the retained C90 kernel; reuse the S1 and Zenodo publishers.

Source export and build evidence are separate. No install, remote effect,
credential, live state, automatic approval or publication occurs here.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = "runtime/native/PACKAGE.json"
STRICT = ["-std=c90", "-pedantic-errors", "-Wall", "-Wextra", "-Werror", "-O2"]


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(argv, **kwargs):
    return subprocess.run(list(map(str, argv)), capture_output=True, check=True,
                          timeout=120, **kwargs).stdout


def safe(name):
    path = PurePosixPath(name)
    if (path.is_absolute() or path.as_posix() != name or "\\" in name
            or any(p in (".", "..") for p in path.parts) or not path.parts):
        raise ValueError("UNSAFE_PACKAGE_PATH")
    return name


def relative_files(package):
    files = {}
    for p in package.rglob("*"):
        if p.is_symlink():
            raise ValueError("PACKAGE_SYMLINK")
        if p.is_file():
            files[p.relative_to(package).as_posix()] = p
    return files


def verify(package, pin):
    if package.is_symlink() or not re.fullmatch(r"[0-9a-f]{64}", pin or ""):
        raise ValueError("INDEPENDENT_MANIFEST_PIN_REQUIRED")
    raw = (package / "MANIFEST.json").read_bytes()
    if sha(raw) != pin:
        raise ValueError("MANIFEST_PIN_MISMATCH")
    value = json.loads(raw)
    if (value.get("schema") != "qikvrt-native-package/v1"
            or value.get("effect_ack_done") is not False):
        raise ValueError("PACKAGE_SCHEMA")
    files = relative_files(package)
    if set(files) != set(value["files"]) | {"MANIFEST.json"}:
        raise ValueError("PACKAGE_INVENTORY")
    for name, entry in value["files"].items():
        safe(name)
        data = files[name].read_bytes()
        if len(data) != entry["bytes"] or sha(data) != entry["sha256"]:
            raise ValueError("PACKAGE_BYTES: " + name)
    return value


def sql_function(package, pin):
    value = verify(package, pin)
    if value["target"]["system"] != sys.platform or value["target"]["machine"] != platform.machine():
        raise ValueError("HOST_ABI_MISMATCH")
    library = ctypes.CDLL(str((package / value["shared_library"]).resolve()))
    kernel = library.qikvrt_evaluate_bytes
    kernel.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel.restype = None

    def evaluate(raw):
        if type(raw) is not bytes or len(raw) != 14:
            raise ValueError("EXACT_14_BYTE_INPUT_REQUIRED")
        output = ctypes.create_string_buffer(6)
        kernel(ctypes.create_string_buffer(raw, 14), output)
        return output.raw

    return evaluate


def selftest(output, binary, shared, source, compiler):
    logs = {}
    for name, test_sources in (
        ("core", [*json.loads((source / DEFINITION).read_bytes())["native_sources"], "next/core/tests/test_core.c"]),
        ("effect-ack", ["src/effect_ack_core.c", "tests/test_effect_ack_core.c"]),
        ("temdd", ["src/temdd_core.c", "tests/test_temdd_core.c"]),
    ):
        path = output / "bin" / ("test-" + name + (".exe" if sys.platform == "win32" else ""))
        run([compiler, *STRICT, "-I" + str(source / "include"), "-I" + str(source / "next/core/include"),
             *[source / p for p in test_sources], "-o", path])
        logs[name] = run([path]).decode()
    vector = bytes.fromhex("0000000700000003060201010100")
    expected = b"000000040201\n"
    if run([binary, "evaluate", vector.hex()]).replace(b"\r\n", b"\n") != expected:
        raise ValueError("NATIVE_CLI_READBACK")
    with tempfile.TemporaryDirectory() as temp:
        body = bytes(range(256)) * 32
        payload = Path(temp) / "payload.bin"
        payload.write_bytes(body)
        identities = [sha(p) for p in (b"source", b"destination", b"exact-subject")]
        frames = run([binary, "send", *identities, "2", payload])
        if run([binary, "receive", *identities], input=frames) != body:
            raise ValueError("BINARY_TRANSPORT_READBACK")
        bad = subprocess.run([str(binary), "receive", *identities], input=frames[:-1],
                             capture_output=True, timeout=10)
        if bad.returncode == 0:
            raise ValueError("TRUNCATED_TRANSPORT_ADMITTED")
    # Windows keeps a ctypes-loaded DLL mapped until process exit. Execute the
    # ABI/SQL witness in its own process so package cleanup can remove the DLL.
    run([sys.executable, "-I", "-B", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); from tools.qikvrt_native_release import selftest_shared; selftest_shared(sys.argv[2])",
         source, shared.resolve()])
    logs["adapters"] = "CLI, shared octet ABI, SQLite BLOB UDF, 8192-byte transport, truncation and invalid input controls executed"
    return logs


def selftest_shared(shared):
    shared = Path(shared)
    vector = bytes.fromhex("0000000700000003060201010100")
    lib = ctypes.CDLL(str(shared.resolve()))
    kernel = lib.qikvrt_evaluate_bytes
    kernel.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel.restype = None

    def eval_blob(raw):
        if type(raw) is not bytes or len(raw) != 14:
            raise ValueError("EXACT_14_BYTE_INPUT_REQUIRED")
        out = ctypes.create_string_buffer(6)
        kernel(ctypes.create_string_buffer(raw, 14), out)
        return out.raw

    with sqlite3.connect(":memory:") as db:
        db.create_function("qikvrt_evaluate", 1, eval_blob, deterministic=True)
        if db.execute("select hex(qikvrt_evaluate(?))", (vector,)).fetchone()[0] != "000000040201":
            raise ValueError("SQL_NATIVE_READBACK")
        for invalid in (b"", b"x" * 13, b"x" * 15, "wrong-type", None):
            try:
                db.execute("select qikvrt_evaluate(?)", (invalid,)).fetchone()
            except sqlite3.OperationalError:
                pass
            else:
                raise ValueError("INVALID_SQL_INPUT_ADMITTED")
    for index in (10, 11, 12, 13):
        changed = bytearray(vector)
        changed[index] = 0 if index != 13 else 1
        if eval_blob(bytes(changed)) != bytes.fromhex("000000000100"):
            raise ValueError("KERNEL_GUARD_REGRESSION")


def build(root, output, head=None, tree=None, rebuild_pin=None, compiler=None):
    compiler = compiler or os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc")
    if not compiler:
        raise ValueError("DECLARED_C90_COMPILER_REQUIRED")
    compiler_path = Path(shutil.which(compiler) or compiler).resolve(strict=True)
    if rebuild_pin is None:
        observed_head = run(["git", "-C", root, "rev-parse", "HEAD"]).decode().strip()
        observed_tree = run(["git", "-C", root, "rev-parse", "HEAD^{tree}"]).decode().strip()
        if observed_head != head or observed_tree != tree:
            raise ValueError("EXACT_SOURCE_MISMATCH")
        run(["git", "-C", root, "diff", "--quiet", head, "--"])
        definition = json.loads(run(["git", "-C", root, "show", head + ":" + DEFINITION]))
        data = {safe(name): run(["git", "-C", root, "show", head + ":" + name]) for name in definition["files"]}
        origin = {"repository": definition["source_repository"], "head": head, "tree": tree}
    else:
        previous = verify(root, rebuild_pin)
        origin = {**previous["source"], "rebuilt_from_manifest_sha256": rebuild_pin}
        definition = json.loads((root / "source" / DEFINITION).read_bytes())
        if {"source/" + n for n in definition["files"]} != {n for n in previous["files"] if n.startswith("source/")}:
            raise ValueError("SOURCE_INVENTORY")
        data = {safe(n): (root / "source" / n).read_bytes() for n in definition["files"]}
    if sys.platform not in ("linux", "darwin", "win32"):
        raise ValueError("UNREGISTERED_HOST_TARGET")
    output.mkdir(parents=True, exist_ok=False)
    source = output / "source"
    for name, raw in data.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    (output / "bin").mkdir()
    common = [*STRICT, "-I" + str(source / "include"), "-I" + str(source / "next/core/include")]
    sources = [source / p for p in definition["native_sources"]]
    binary = output / "bin" / ("qikvrt-c90.exe" if sys.platform == "win32" else "qikvrt-c90")
    shared = output / "bin" / {"linux": "libqikvrt.so", "darwin": "libqikvrt.dylib", "win32": "qikvrt.dll"}[sys.platform]
    shared_flags = ["-dynamiclib", "-fPIC"] if sys.platform == "darwin" else ["-shared"]
    shared_flags += ["-Wl,--export-all-symbols"] if sys.platform == "win32" else ([] if sys.platform == "darwin" else ["-fPIC"])
    commands = [[compiler_path, *common, *sources, source / "next/core/adapters/stdio.c", "-o", binary],
                [compiler_path, *common, *shared_flags, *sources, "-o", shared]]
    for command in commands:
        run(command)
    logs = selftest(output, binary, shared, source, compiler_path)
    receipt = {"schema": "qikvrt-native-execution/v1", "source": origin,
               "target": {"system": sys.platform, "machine": platform.machine(), "os_version": platform.platform()},
               "compiler": {"version": run([compiler_path, "--version"]).decode(),
                            "executable_sha256": sha(compiler_path.read_bytes())},
               "commands": [[str(a).replace(str(output), "<package>") for a in c] for c in commands],
               "logs": logs, "binary_sha256": sha(binary.read_bytes()), "shared_sha256": sha(shared.read_bytes()),
               "sqlite_version": sqlite3.sqlite_version, "python_version": platform.python_version(),
               "scope": "EXECUTED_NATIVE_C90_AND_SQL_ADAPTERS; NOT_FULL_NODE_OR_PUBLICATION_ACCEPTANCE",
               "predecessor_evidence_transfer": False, "effect_ack_done": False}
    (output / "EXECUTION.json").write_bytes(canonical(receipt))
    manifest = {"schema": "qikvrt-native-package/v1", "version": definition["version"], "source": origin,
                "target": receipt["target"], "cli": binary.relative_to(output).as_posix(),
                "shared_library": shared.relative_to(output).as_posix(), "files": {},
                "providers_required": [], "third_party_runtime_bundled": False, "effect_ack_done": False}
    for name, path in sorted(relative_files(output).items()):
        raw = path.read_bytes()
        manifest["files"][name] = {"bytes": len(raw), "sha256": sha(raw)}
    raw = canonical(manifest)
    (output / "MANIFEST.json").write_bytes(raw)
    pin = sha(raw)
    verify(output, pin)
    archive = Path(str(output) + ".zip")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for name, path in sorted(relative_files(output).items()):
            info = zipfile.ZipInfo(name, (2026, 10, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = ((0o100755 if name.startswith("bin/") else 0o100644) << 16)
            z.writestr(info, path.read_bytes())
    return {"state": "BUILT_AND_EXECUTED", "source": origin, "target": receipt["target"],
            "manifest_sha256": pin, "archive_sha256": sha(archive.read_bytes()), "effect_ack_done": False}


def unpack(archive, output):
    """Extract an artifact without accepting symlinks, duplicates or path escape."""
    with zipfile.ZipFile(archive) as z:
        names = set()
        for entry in z.infolist():
            name = entry.filename.rstrip("/")
            safe(name)
            if name in names or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("UNSAFE_ARCHIVE_MEMBER")
            names.add(name)
            if entry.file_size > 512 * 1024 * 1024:
                raise ValueError("ARCHIVE_MEMBER_SIZE")
        z.extractall(output)
        if os.name != "nt":
            for entry in z.infolist():
                if not entry.is_dir() and entry.external_attr >> 16 & 0o111:
                    (output / entry.filename).chmod(0o755)


def catalog(artifacts, output, head, tree):
    """Freeze tested variants for the existing Zenodo-v2 publication controls."""
    if not re.fullmatch(r"[0-9a-f]{40}", head or "") or not re.fullmatch(r"[0-9a-f]{40}", tree or ""):
        raise ValueError("EXACT_SOURCE_REQUIRED")
    rows = []
    sources = []
    for receipt_path in sorted(artifacts.rglob("NATIVE_BUILD.json")):
        receipt = json.loads(receipt_path.read_bytes())
        if receipt["source"]["head"] != head or receipt["source"]["tree"] != tree:
            raise ValueError("VARIANT_SOURCE_MISMATCH")
        archive = receipt_path.parent / "qikvrt-native.zip"
        if sha(archive.read_bytes()) != receipt["archive_sha256"]:
            raise ValueError("VARIANT_ARCHIVE_MISMATCH")
        with tempfile.TemporaryDirectory() as temp:
            unpack(archive, Path(temp))
            manifest = verify(Path(temp), receipt["manifest_sha256"])
            execution = json.loads((Path(temp) / "EXECUTION.json").read_bytes())
            if (execution["source"] != receipt["source"] or execution["target"] != receipt["target"]
                    or execution["binary_sha256"] != manifest["files"][manifest["cli"]]["sha256"]
                    or execution["shared_sha256"] != manifest["files"][manifest["shared_library"]]["sha256"]):
                raise ValueError("VARIANT_EXECUTION_BINDING")
        target = receipt["target"]["system"] + "-" + receipt["target"]["machine"]
        name = "qikvrt-native-" + target + ".zip"
        rows.append({"target": target, "file": name, "archive_sha256": receipt["archive_sha256"],
                     "manifest_sha256": receipt["manifest_sha256"], "binary_sha256": execution["binary_sha256"],
                     "execution_scope": execution["scope"]})
        sources.append((archive, name))
    for path in sorted(artifacts.rglob("MANIFEST.json")):
        manifest = json.loads(path.read_bytes())
        if manifest.get("schema") not in ("qikvrt-smalltalk-package/v1", "qikvrt-m68000-package/v1"):
            continue
        if manifest["source_head"] != head or manifest["source_tree"] != tree:
            raise ValueError("BACKEND_SOURCE_MISMATCH")
        if manifest.get("effect_ack_done") is not False:
            raise ValueError("BACKEND_EFFECT_CLAIM")
        if set(relative_files(path.parent)) != set(manifest["files"]) | {"MANIFEST.json"}:
            raise ValueError("BACKEND_INVENTORY_MISMATCH")
        for name, item in manifest["files"].items():
            raw = (path.parent / safe(name)).read_bytes()
            if sha(raw) != item["sha256"] or len(raw) != item["bytes"]:
                raise ValueError("BACKEND_BYTES_MISMATCH")
        target = "smalltalk-pharo13-linux" if "smalltalk" in manifest["schema"] else "mc68000-d0-linux-abi-witness"
        rows.append({"target":target, "manifest_sha256":sha(path.read_bytes()), "execution_scope":target})
    if not rows or len({row["target"] for row in rows}) != len(rows):
        raise ValueError("EMPTY_OR_DUPLICATE_VARIANTS")
    output.mkdir(parents=True, exist_ok=False)
    for archive, name in sources:
        shutil.copyfile(archive, output / name)
    # Retain the backend images, VM bootstrap archives and S1 tar unchanged.
    for path in sorted(artifacts.rglob("*")):
        if path.is_symlink():
            raise ValueError("ARTIFACT_SYMLINK")
        if not path.is_file() or path.name in ("qikvrt-native.zip", "qikvrt-native-rebuilt.zip"):
            continue
        relative = path.relative_to(artifacts).as_posix()
        destination = output / "readbacks" / safe(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    for name in ("LICENSE", "LICENSES/PolyForm-Noncommercial-1.0.0.txt", "LICENSES/CC-BY-NC-ND-4.0.txt", "runtime/native/README.md"):
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    index = {"schema":"qikvrt-runtime-publication-candidate/v1", "source_head":head, "source_tree":tree,
             "variants":rows, "ci_run_id":os.environ.get("GITHUB_RUN_ID"), "state":"FROZEN_CANDIDATE",
             "zenodo_state":"PENDING_EXISTING_V2_CONTROLS_AUTHENTICATION_AND_PUBLIC_BYTE_READBACK",
             "publisher":"tools/qikvrt_zenodo_publish.py", "node_propagation":"PER_NODE_IMPORT_AND_FRESH_READBACK_REQUIRED",
             "historical_evidence_transfer":False, "effect_ack_done":False,
             "files":{name:{"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for name,p in sorted(relative_files(output).items())}}
    (output / "RELEASE_INDEX.json").write_bytes(canonical(index))
    return {"state":"FROZEN_CANDIDATE", "variant_count":len(rows),
            "release_index_sha256":sha((output / "RELEASE_INDEX.json").read_bytes()), "zenodo_published":False, "effect_ack_done":False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("build", "rebuild", "verify", "sql", "catalog"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--package", type=Path)
    parser.add_argument("--expected-head")
    parser.add_argument("--expected-tree")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--cc")
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    try:
        if args.operation == "catalog":
            if args.artifacts is None or args.output is None:
                parser.error("catalog requires --artifacts and new --output")
            result = catalog(args.artifacts, args.output, args.expected_head, args.expected_tree)
        elif args.operation in ("build", "rebuild"):
            if args.output is None or (args.operation == "rebuild" and args.package is None):
                parser.error("new --output and --package for rebuild required")
            if args.operation == "rebuild" and not args.manifest_sha256:
                parser.error("rebuild requires independent --manifest-sha256")
            result = build(args.root if args.operation == "build" else args.package, args.output,
                           args.expected_head, args.expected_tree,
                           args.manifest_sha256 if args.operation == "rebuild" else None, args.cc)
        elif args.package is None:
            parser.error("--package required")
        elif args.operation == "verify":
            value = verify(args.package, args.manifest_sha256)
            result = {"state": "BYTES_VERIFIED", "source": value["source"], "effect_ack_done": False}
        else:
            function = sql_function(args.package, args.manifest_sha256)
            with sqlite3.connect(":memory:") as db:
                db.create_function("qikvrt_evaluate", 1, function, deterministic=True)
                result = {"sql_readback": db.execute("select hex(qikvrt_evaluate(X'0000000700000003060201010100'))").fetchone()[0],
                          "effect_ack_done": False}
        print(canonical(result).decode(), end="")
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print("HOLD: " + str(error), file=sys.stderr)
        return 78


if __name__ == "__main__":
    raise SystemExit(main())
