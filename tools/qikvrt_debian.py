#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Split the original sealed S1 export into Debian packages; no new executor."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = "runtime/self-host/DEBIAN_PACKAGES.json"
AR_MAGIC = b"!<arch>\n"
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
PACKAGES = ("qikvrt-eap", "qikvrt-terminal", "qikvrt-web", "qikvrt-runtime", "qikvrt-server")
DESCRIPTIONS = {
    "qikvrt-eap": "QIK-VRT Effect Acknowledgement Protocol and original C90 sources",
    "qikvrt-terminal": "QIK-VRT Universal Terminal and Transputer sources",
    "qikvrt-web": "QIK-VRT sealed React monitor and terminal web assets",
    "qikvrt-runtime": "QIK-VRT original S1 runtime and admission tools",
    "qikvrt-server": "QIK-VRT server installation through the existing S1 admission path",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def original(root=ROOT):
    spec = importlib.util.spec_from_file_location("qikvrt_distribution_original", root / "tools/qikvrt_self_host.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_directory(path):
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("ABSOLUTE_NON_SYMLINK_DIRECTORY_REQUIRED")
    return path


def owner(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\n" in name or "\x00" in name:
        raise ValueError("UNSAFE_DISTRIBUTION_PATH")
    if path.name == "qikvrt_effect_ack_http_terminal.py":
        return "qikvrt-terminal"
    if path.name.startswith("qikvrt_effect_ack") or name in {"src/effect_ack_core.c", "include/qikvrt/effect_ack.h"}:
        return "qikvrt-eap"
    if (path.name == "qikvrt_temdd_event_ledger.py"
            or name.startswith(("deploy/universal-terminal/", "evidence/self_host/original-recovered/"))):
        return "qikvrt-terminal"
    if name.startswith(("docs/monitor/", "docs/terminal/", "docs/assets/", "browser/", "runtime/self-host/original-firefox/")):
        return "qikvrt-web"
    return "qikvrt-runtime"


def tar_gzip(entries):
    """Deterministic regular files and parent directories; no host metadata."""
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as compressed:
        # dpkg accepts GNU long-name records, but rejects POSIX PAX 'x' records.
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
            directories = set()
            for name in entries:
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError("UNSAFE_DEB_PATH")
                directories.update(str(p) for p in path.parents if str(p) != ".")
            for name in sorted(directories):
                info = tarfile.TarInfo("./" + name)
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                archive.addfile(info)
            for name, (raw, mode) in sorted(entries.items()):
                info = tarfile.TarInfo("./" + name)
                info.size, info.mode = len(raw), mode
                archive.addfile(info, io.BytesIO(raw))
    return buffer.getvalue()


def deb_archive(control, data):
    """Debian 2.0 ar container, independently read by dpkg in acceptance tests."""
    result = bytearray(b"!<arch>\n")
    for name, raw in (("debian-binary", b"2.0\n"), ("control.tar.gz", tar_gzip(control)), ("data.tar.gz", tar_gzip(data))):
        result.extend((f"{name + '/':<16}{0:<12}{0:<6}{0:<6}{'100644':<8}{len(raw):<10}`\n").encode())
        result.extend(raw)
        if len(raw) % 2:
            result.extend(b"\n")
    return bytes(result)


def dependencies(name, version):
    exact = lambda package: f"{package} (= {version})"
    return {
        "qikvrt-eap": ["python3.12"],
        "qikvrt-terminal": [exact("qikvrt-eap")],
        "qikvrt-web": [exact("qikvrt-terminal"), "nodejs (>= 24)", "nodejs (<< 25)"],
        "qikvrt-runtime": [exact(p) for p in PACKAGES[:3]],
        "qikvrt-server": [exact("qikvrt-runtime"), "systemd (>= 252)", "ca-certificates"],
    }[name]


def build(package, pin, output, revision="1"):
    package, output = safe_directory(package), safe_directory(output)
    if not re.fullmatch(r"[1-9][0-9]*", revision):
        raise ValueError("NUMERIC_DEBIAN_REVISION_REQUIRED")
    host = original()
    manifest = host.verify(package, pin, check_runtime=False)
    layout = json.loads((package / LAYOUT).read_bytes())
    if (layout.get("schema") != "qikvrt-debian-package-layout/v2"
            or layout.get("packages") != list(PACKAGES)
            or layout.get("service_auto_start") is not False
            or layout.get("credentials_included") is not False):
        raise ValueError("DEBIAN_PACKAGE_LAYOUT_SCHEMA_MISMATCH")
    # This initial distribution follows the original native TEMDD-first scope.
    # Firefox/noVNC requires its separately signed extension and browser admission.
    if manifest.get("browser_runtime"):
        raise ValueError("NATIVE_TEMDD_DISTRIBUTION_REQUIRED")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", manifest["package_version"]):
        raise ValueError("NUMERIC_S1_VERSION_REQUIRED")
    if not (package / "tools/qikvrt_debian.py").is_file():
        raise ValueError("PACKAGED_DISTRIBUTION_ADAPTER_REQUIRED")
    if output.exists() or output == package or output in package.parents or package in output.parents:
        raise ValueError("CREATE_ONLY_SEPARATE_OUTPUT_REQUIRED")
    version = manifest["package_version"] + "-" + revision + "+g" + manifest["source_head"][:12]
    release = manifest["source_head"] + "-" + pin[:16]
    prefix = f"usr/lib/qikvrt/distribution/{release}"
    source = prefix + "/source"
    payloads = {p: {} for p in PACKAGES}
    ownership = {}
    for name, entry in manifest["files"].items():
        p = owner(name)
        ownership[name] = p
        payloads[p][source + "/" + name] = ((package / name).read_bytes(), 0o755 if entry["mode"] == "100755" else 0o644)
    payloads["qikvrt-runtime"][source + "/MANIFEST.json"] = ((package / "MANIFEST.json").read_bytes(), 0o644)
    payloads["qikvrt-runtime"][prefix + "/SOURCE.sha256"] = ((pin + "\n").encode(), 0o644)
    installed = "/var/lib/qikvrt/distribution"
    # DPKG_ROOT permits real lifecycle acceptance in an isolated dpkg root.
    # Production apt leaves it empty. No dependency downloads or service effects.
    invocation = (f'python3.12 -B "${{DPKG_ROOT:-}}/{source}/tools/qikvrt_debian.py" '
                  f'configure --root "${{DPKG_ROOT:-}}/{source}" --manifest-sha256 {pin} '
                  f'--output "${{DPKG_ROOT:-}}{installed}"')
    postinst = '#!/bin/sh\nset -eu\ncase "${1:-}" in\n configure) ' + invocation + ' ;;\nesac\n'
    # A user/CI can obtain the exact installed candidate; its original supervisor
    # command remains the only activation path, with independent host/config pins.
    cli = ('#!/bin/sh\nset -eu\ncase "${1:-}" in\n configure) shift; exec ' + invocation
           + ' "$@" ;;\n *) echo "Use qikvrt-server configure; activate only through the original pinned S1 supervisor." >&2; exit 64 ;;\nesac\n')
    payloads["qikvrt-server"]["usr/sbin/qikvrt-server"] = (cli.encode(), 0o755)
    receipt = {"schema": "qikvrt-debian-bundle/v2", "source_head": manifest["source_head"],
               "source_tree": manifest["source_tree"], "source_manifest_sha256": pin, "version": version,
               "source_prefix": "/" + source, "ownership": ownership, "packages": [],
               "architecture": "all", "profile": "temdd", "host_admission_verified": False,
               "effect_ack_done": False, "apt_repository_published": False,
               "state": "DEBIAN_PACKAGES_BUILT_NOT_INSTALLED", "service_auto_started": False}
    output.mkdir(mode=0o755, parents=True)
    try:
        rights = (package / "LICENSE").read_bytes()
        notices = [p for p in manifest["files"] if p.startswith("LICENSES/")
                   or PurePosixPath(p).name in {"LICENSE-CODE-APACHE-2.0.txt", "REACT_LICENSE.txt", "SQLJS_LICENSE.txt"}]
        for name in PACKAGES:
            data = payloads[name]
            data[f"usr/share/doc/{name}/copyright"] = (rights, 0o644)
            for notice in notices:
                data[f"usr/share/doc/{name}/licenses/{notice}"] = ((package / notice).read_bytes(), 0o644)
            data[f"usr/share/doc/{name}/distribution.json"] = (wire({k: v for k, v in receipt.items() if k not in {"packages", "ownership"}}), 0o644)
            # md5sums is a dpkg compatibility index, never the trust authority.
            sums = "".join(hashlib.md5(raw, usedforsecurity=False).hexdigest() + "  " + path + "\n" for path, (raw, _) in sorted(data.items()))
            control = (f"Package: {name}\nVersion: {version}\nArchitecture: all\nSection: non-free/net\nPriority: optional\n"
                       "Maintainer: Ingolf Lohmann <ingolf.lohmann@web.de>\n"
                       f"Depends: {', '.join(dependencies(name, version))}\n"
                       f"Installed-Size: {(sum(len(v[0]) for v in data.values()) + 1023) // 1024}\n"
                       f"Description: {DESCRIPTIONS[name]}\n"
                       " Source-bound installation; productive host admission remains separately required.\n")
            scripts = {"control": (control.encode(), 0o644), "md5sums": (sums.encode(), 0o644)}
            if name == "qikvrt-server":
                scripts["postinst"] = (postinst.encode(), 0o755)
            raw = deb_archive(scripts, data)
            filename = f"{name}_{version}_all.deb"
            (output / filename).write_bytes(raw)
            receipt["packages"].append({"name": name, "filename": filename, "bytes": len(raw),
                                        "sha256": digest(raw), "depends": dependencies(name, version)})
        (output / "DEBIAN_BUNDLE.json").write_bytes(wire(receipt))
        sums = "".join(digest(p.read_bytes()) + "  " + p.name + "\n" for p in sorted(output.iterdir()))
        (output / "SHA256SUMS.txt").write_text(sums)
        return {**receipt, "bundle_sha256": digest(wire(receipt))}
    except BaseException:
        shutil.rmtree(output)
        raise


# Independent archive readers retained from the prior Debian adapter.
def safe_relative(name: str) -> bool:
    path = Path(name)
    return bool(name) and not name.startswith("/") and ".." not in path.parts and not any(
        part in ("", ".") for part in path.parts
    )

def parse_ar(raw: bytes) -> dict[str, bytes]:
    if not raw.startswith(AR_MAGIC) or len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError("DEBIAN_AR_ARCHIVE_REQUIRED")
    position, members = len(AR_MAGIC), {}
    while position < len(raw):
        if position + 60 > len(raw):
            raise ValueError("TRUNCATED_AR_HEADER")
        header = raw[position:position + 60]
        if header[58:] != b"`\n":
            raise ValueError("INVALID_AR_HEADER")
        name = header[:16].decode("ascii").strip().rstrip("/")
        try:
            size = int(header[48:58].decode("ascii").strip())
        except ValueError as exc:
            raise ValueError("INVALID_AR_MEMBER_SIZE") from exc
        if size < 0:
            raise ValueError("INVALID_AR_MEMBER_SIZE")
        position += 60
        body = raw[position:position + size]
        if len(body) != size or name in members:
            raise ValueError("TRUNCATED_OR_DUPLICATE_AR_MEMBER")
        if size % 2 and raw[position + size:position + size + 1] != b"\n":
            raise ValueError("INVALID_AR_MEMBER_PADDING")
        members[name] = body
        position += size + size % 2
    if position != len(raw) or set(members) != {"debian-binary", "control.tar.gz", "data.tar.gz"} or members["debian-binary"] != b"2.0\n":
        raise ValueError("EXACT_DEBIAN_MEMBER_SET_REQUIRED")
    return members

def tar_files(raw: bytes) -> dict[str, tuple[bytes, int]]:
    result = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            for member in archive.getmembers():
                name = member.name[2:] if member.name.startswith("./") else member.name
                if member.isdir():
                    continue
                if not member.isfile() or not safe_relative(name) or member.size > MAX_ARCHIVE_BYTES:
                    raise ValueError("REGULAR_SAFE_DEBIAN_MEMBER_REQUIRED")
                source = archive.extractfile(member)
                body = source.read() if source else b""
                if len(body) != member.size or name in result:
                    raise ValueError("DEBIAN_MEMBER_READBACK_MISMATCH")
                result[name] = (body, stat.S_IMODE(member.mode))
    except (tarfile.TarError, OSError) as exc:
        raise ValueError("INVALID_DEBIAN_TAR_MEMBER") from exc
    return result

def verify(bundle, expected):
    """Read original archive bytes independently; never execute package scripts."""
    bundle = safe_directory(bundle)
    raw = (bundle / "DEBIAN_BUNDLE.json").read_bytes()
    if not re.fullmatch(r"[a-f0-9]{64}", expected or "") or digest(raw) != expected:
        raise ValueError("DEBIAN_BUNDLE_PIN_MISMATCH")
    receipt = json.loads(raw)
    if (receipt.get("schema") != "qikvrt-debian-bundle/v2"
            or receipt.get("state") != "DEBIAN_PACKAGES_BUILT_NOT_INSTALLED"
            or receipt.get("host_admission_verified") is not False
            or receipt.get("service_auto_started") is not False
            or receipt.get("effect_ack_done") is not False
            or [item.get("name") for item in receipt.get("packages", [])] != list(PACKAGES)):
        raise ValueError("DEBIAN_BUNDLE_SCHEMA_MISMATCH")
    expected_files = {"DEBIAN_BUNDLE.json", "SHA256SUMS.txt"} | {p["filename"] for p in receipt["packages"]}
    if ({p.name for p in bundle.iterdir()} != expected_files
            or any(not p.is_file() or p.is_symlink() for p in bundle.iterdir())):
        raise ValueError("DEBIAN_BUNDLE_INVENTORY_MISMATCH")
    source_prefix = receipt["source_prefix"].lstrip("/") + "/"
    sources, manifest_raw = {}, None
    for item in receipt["packages"]:
        filename = item["filename"]
        if PurePosixPath(filename).name != filename:
            raise ValueError("UNSAFE_DEBIAN_ARCHIVE_NAME")
        raw = (bundle / filename).read_bytes()
        if len(raw) != item["bytes"] or digest(raw) != item["sha256"]:
            raise ValueError("DEBIAN_PACKAGE_DIGEST_MISMATCH")
        members = parse_ar(raw)
        controls = tar_files(members["control.tar.gz"])
        if set(controls) != ({"control", "md5sums", "postinst"} if item["name"] == "qikvrt-server" else {"control", "md5sums"}):
            raise ValueError("DEBIAN_CONTROL_INVENTORY_MISMATCH")
        fields = {}
        for line in controls["control"][0].decode().splitlines():
            if line.startswith(" "):
                continue
            key, value = line.split(": ", 1)
            if key in fields:
                raise ValueError("DUPLICATE_DEBIAN_CONTROL_FIELD")
            fields[key] = value
        if (fields.get("Package") != item["name"] or fields.get("Version") != receipt["version"]
                or fields.get("Architecture") != "all"
                or fields.get("Depends") != ", ".join(dependencies(item["name"], receipt["version"]))):
            raise ValueError("DEBIAN_CONTROL_BINDING_MISMATCH")
        for name, entry in tar_files(members["data.tar.gz"]).items():
            if not name.startswith(source_prefix):
                continue
            relative = name[len(source_prefix):]
            if relative == "MANIFEST.json":
                if manifest_raw is not None or item["name"] != "qikvrt-runtime":
                    raise ValueError("DEBIAN_SOURCE_MANIFEST_OVERLAP")
                manifest_raw = entry[0]
            else:
                if relative in sources or receipt["ownership"].get(relative) != item["name"]:
                    raise ValueError("DEBIAN_SOURCE_PARTITION_MISMATCH")
                sources[relative] = entry
    if manifest_raw is None or digest(manifest_raw) != receipt["source_manifest_sha256"]:
        raise ValueError("DEBIAN_SOURCE_MANIFEST_PIN_MISMATCH")
    manifest = json.loads(manifest_raw)
    if (set(sources) != set(manifest["files"]) or set(sources) != set(receipt["ownership"])
            or manifest["source_head"] != receipt["source_head"] or manifest["source_tree"] != receipt["source_tree"]):
        raise ValueError("DEBIAN_SOURCE_INVENTORY_MISMATCH")
    for name, (body, mode) in sources.items():
        entry = manifest["files"][name]
        if (len(body) != entry["bytes"] or digest(body) != entry["sha256"]
                or mode != (0o755 if entry["mode"] == "100755" else 0o644)):
            raise ValueError("DEBIAN_SOURCE_READBACK_MISMATCH")
    index = "".join(digest(p.read_bytes()) + "  " + p.name + "\n"
                    for p in sorted(bundle.iterdir()) if p.name != "SHA256SUMS.txt")
    if (bundle / "SHA256SUMS.txt").read_text() != index:
        raise ValueError("DEBIAN_BUNDLE_CHECKSUM_INDEX_MISMATCH")
    return {"state": "DEBIAN_PACKAGES_INDEPENDENTLY_VERIFIED_NOT_INSTALLED",
            "bundle_sha256": expected, "verified_source_files": len(sources),
            "source_head": receipt["source_head"], "source_tree": receipt["source_tree"], "effect_ack_done": False}


def configure(package, pin, output):
    """Derive a new S1 seal for the observed host; never modify the source seal.

    Runtime binding is a local rebuild, not runtime/host admission. Original
    supervisor admission still requires the independently pinned derived seal.
    No existing config, token, database, active release or unit is changed.
    """
    package, output = safe_directory(package), safe_directory(output)
    # Use this adapter's trusted original verifier, not code imported from the
    # unverified --root supplied by a caller.
    host = original()
    manifest = host.verify(package, pin, check_runtime=False)
    if manifest.get("browser_runtime"):
        raise ValueError("NATIVE_TEMDD_DISTRIBUTION_REQUIRED")
    runtime = {"node": host.runtime("node"), "python": host.runtime(sys.executable),
               "platform": platform.machine(), "system": sys.platform}
    if (runtime["system"] != "linux" or not runtime["node"]["version"].startswith("v24.")
            or not runtime["python"]["version"].startswith("Python 3.12.")):
        raise ValueError("LINUX_NODE24_PYTHON312_REQUIRED")
    derived = {**manifest, "runtime": runtime, "distribution_source_manifest_sha256": pin}
    raw = wire(derived)
    new_pin = digest(raw)
    output.mkdir(mode=0o755, parents=True, exist_ok=True)
    target = output / new_pin
    safe_directory(target)
    result = {"schema": "qikvrt-linux-installed-candidate/v1", "source_head": manifest["source_head"],
              "source_tree": manifest["source_tree"], "source_manifest_sha256": pin,
              "package_path": str(target), "manifest_sha256": new_pin,
              "admission_tool_sha256": digest((package / "tools/qikvrt_self_host.py").read_bytes()),
              "state": "INSTALLED_CANDIDATE_NOT_HOST_ADMITTED", "service_started": False,
              "host_admission_verified": False, "effect_ack_done": False}
    if target.exists():
        safe_directory(target)
        host.verify(target, new_pin)
        return result
    # Create-only content addressed output, serialized by the same kernel lock
    # family as the original S1 adapter. No mutable 'current' or active pointer.
    import fcntl
    lock = output / ".configure.lock"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if target.exists():
            safe_directory(target)
            host.verify(target, new_pin)
            return result
        with tempfile.TemporaryDirectory(prefix=".candidate-", dir=output) as staging:
            candidate = Path(staging) / "package"
            candidate.mkdir(mode=0o755)
            for name in manifest["files"]:
                dest = candidate / name
                dest.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                shutil.copyfile(package / name, dest)
                dest.chmod(0o755 if manifest["files"][name]["mode"] == "100755" else 0o644)
            (candidate / "MANIFEST.json").write_bytes(raw)
            (candidate / "MANIFEST.json").chmod(0o644)
            host.verify(candidate, new_pin)
            # Publication under the content digest is atomic under dpkg/the lock.
            os.rename(candidate, target)
        directory_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        host.verify(target, new_pin)
        return result
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("build", "verify", "configure"))
    parser.add_argument("--root", type=Path, required=True, help="original sealed S1 package")
    parser.add_argument("--manifest-sha256", help="independently obtained original S1 seal")
    parser.add_argument("--bundle-sha256", help="independently obtained DEBIAN_BUNDLE.json pin")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--revision", default="1", help="positive Debian packaging revision")
    args = parser.parse_args()
    try:
        if args.operation == "verify":
            result = verify(args.root, args.bundle_sha256)
        else:
            if args.output is None:
                raise ValueError("EXPLICIT_OUTPUT_REQUIRED")
            result = (build(args.root, args.manifest_sha256, args.output, args.revision) if args.operation == "build"
                      else configure(args.root, args.manifest_sha256, args.output))
        print(json.dumps(result, sort_keys=True))
    except (ValueError, OSError, KeyError) as exc:
        print("LINUX_PACKAGES_HOLD: " + str(exc), file=sys.stderr)
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
