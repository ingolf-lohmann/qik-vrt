#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Deterministic native Debian carriers for an already verified S1 export.

This module creates package-manager artifacts only.  It never installs,
configures, starts or admits a service and never reads host credentials.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import shutil
import stat
import tarfile
from pathlib import Path


LAYOUT = "runtime/self-host/DEBIAN_PACKAGES.json"
AR_MAGIC = b"!<arch>\n"
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def raw_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def safe_relative(name: str) -> bool:
    path = Path(name)
    return bool(name) and not name.startswith("/") and ".." not in path.parts and not any(
        part in ("", ".") for part in path.parts
    )


def architecture(manifest: dict) -> str:
    machine = manifest.get("runtime", {}).get("platform")
    mapping = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
    if machine not in mapping:
        raise ValueError("SUPPORTED_DEBIAN_ARCHITECTURE_REQUIRED")
    return mapping[machine]


def validate_layout(package: Path, manifest: dict) -> tuple[dict, dict[str, set[str]]]:
    path = package / LAYOUT
    if path.is_symlink() or not path.is_file():
        raise ValueError("DEBIAN_PACKAGE_LAYOUT_REQUIRED")
    layout = json.loads(path.read_bytes())
    if (layout.get("schema") != "qikvrt-debian-package-layout/v1"
            or layout.get("activation") != "EXPLICIT_EXISTING_HOST_ADMISSION_REQUIRED"
            or layout.get("service_auto_start") is not False
            or layout.get("credentials_included") is not False):
        raise ValueError("DEBIAN_PACKAGE_LAYOUT_SCHEMA_MISMATCH")
    specs = layout.get("packages")
    if not isinstance(specs, list) or [item.get("name") for item in specs] != ["qikvrt-eap", "qikvrt"]:
        raise ValueError("EXACT_DEBIAN_PACKAGE_SET_REQUIRED")
    source_files = set(manifest["files"])
    selections: dict[str, set[str]] = {}
    claimed: set[str] = set()
    for item in specs:
        if (set(item) != {"name", "description", "architecture", "depends", "source_files"}
                or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]{1,63}", item["name"])
                or item["architecture"] not in {"all", "native"}
                or not isinstance(item["depends"], list)
                or any(not isinstance(value, str) or "\n" in value for value in item["depends"])
                or not isinstance(item["description"], str) or "\n" in item["description"]):
            raise ValueError("DEBIAN_PACKAGE_SPEC_INVALID")
        selected = set(item["source_files"])
        if item["name"] == "qikvrt":
            if selected:
                raise ValueError("QIKVRT_REMAINDER_SELECTION_REQUIRED")
            selected = source_files - claimed
        elif not selected or not selected <= source_files:
            raise ValueError("DEBIAN_SOURCE_PARTITION_INVALID")
        if claimed & selected:
            raise ValueError("DEBIAN_SOURCE_PARTITION_OVERLAP")
        claimed |= selected
        selections[item["name"]] = selected
    if claimed != source_files:
        raise ValueError("DEBIAN_SOURCE_PARTITION_INCOMPLETE")
    return layout, selections


def control_bytes(spec: dict, version: str, arch: str) -> bytes:
    dependencies = [value.replace("${version}", version) for value in spec["depends"]]
    fields = [
        "Package: " + spec["name"],
        "Version: " + version,
        "Section: admin",
        "Priority: optional",
        "Architecture: " + (arch if spec["architecture"] == "native" else "all"),
        "Maintainer: QIK-VRT Owner <noreply@qik-vrt.invalid>",
    ]
    if dependencies:
        fields.append("Depends: " + ", ".join(dependencies))
    fields.extend(("Description: " + spec["description"], ""))
    raw = "\n".join(fields).encode("utf-8")
    if any(len(line) > 998 for line in raw.splitlines()):
        raise ValueError("DEBIAN_CONTROL_LINE_TOO_LONG")
    return raw


def add_directory(archive: tarfile.TarFile, name: str) -> None:
    info = tarfile.TarInfo("./" + name.rstrip("/") + "/")
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    info.uid = info.gid = info.mtime = 0
    info.uname = info.gname = ""
    archive.addfile(info)


def tar_gzip(files: dict[str, tuple[bytes, int]]) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0, compresslevel=9) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
            directories: set[str] = set()
            for name in sorted(files):
                if not safe_relative(name):
                    raise ValueError("UNSAFE_DEBIAN_DATA_PATH")
                parent = Path(name).parent
                while parent != Path("."):
                    directories.add(parent.as_posix())
                    parent = parent.parent
            for name in sorted(directories, key=lambda value: (value.count("/"), value)):
                add_directory(archive, name)
            for name, (raw, mode) in sorted(files.items()):
                info = tarfile.TarInfo("./" + name)
                info.size = len(raw)
                info.mode = mode
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                archive.addfile(info, io.BytesIO(raw))
    return output.getvalue()


def ar_member(name: str, raw: bytes) -> bytes:
    if not re.fullmatch(r"[a-z0-9.-]{1,15}", name):
        raise ValueError("BOUNDED_AR_MEMBER_NAME_REQUIRED")
    header = (f"{name + '/':<16}{0:<12}{0:<6}{0:<6}{0o100644:<8o}{len(raw):<10}`\n").encode("ascii")
    return header + raw + (b"\n" if len(raw) % 2 else b"")


def make_deb(control: bytes, data: dict[str, tuple[bytes, int]]) -> bytes:
    return (AR_MAGIC + ar_member("debian-binary", b"2.0\n")
            + ar_member("control.tar.gz", tar_gzip({"control": (control, 0o644)}))
            + ar_member("data.tar.gz", tar_gzip(data)))


def source_data(package: Path, manifest: dict, names: set[str], version: str) -> dict[str, tuple[bytes, int]]:
    prefix = f"usr/lib/qikvrt/{version}/"
    result: dict[str, tuple[bytes, int]] = {}
    for name in sorted(names):
        entry = manifest["files"][name]
        result[prefix + name] = ((package / name).read_bytes(), 0o755 if entry["mode"] == "100755" else 0o644)
    return result


def build(package: Path, manifest_pin: str, output: Path, verify_package) -> dict:
    package, output = package.resolve(), output.absolute()
    manifest = verify_package(package, manifest_pin)
    layout, selections = validate_layout(package, manifest)
    version = manifest["package_version"]
    arch = architecture(manifest)
    if (output.exists() or output.is_symlink() or not output.is_absolute()
            or any(parent.is_symlink() for parent in output.parents)):
        raise ValueError("ABSOLUTE_CREATE_ONLY_DEBIAN_OUTPUT_REQUIRED")
    output.mkdir(mode=0o700, parents=True)
    packages = []
    try:
        for spec in layout["packages"]:
            name = spec["name"]
            data = source_data(package, manifest, selections[name], version)
            if name == "qikvrt":
                data[f"usr/lib/qikvrt/{version}/MANIFEST.json"] = ((package / "MANIFEST.json").read_bytes(), 0o644)
                launcher = ("#!/bin/sh\nexec python3 -B /usr/lib/qikvrt/" + version
                            + "/tools/qikvrt_self_host.py \"$@\"\n").encode()
                data["usr/bin/qikvrt-self-host"] = (launcher, 0o755)
            raw = make_deb(control_bytes(spec, version, arch), data)
            filename = f"{name}_{version}_{arch if spec['architecture'] == 'native' else 'all'}.deb"
            path = output / filename
            with path.open("xb") as destination:
                os.chmod(destination.name, 0o600)
                destination.write(raw)
                destination.flush()
                os.fsync(destination.fileno())
            packages.append({"name": name, "file": filename, "sha256": digest(raw), "bytes": len(raw),
                             "architecture": arch if spec["architecture"] == "native" else "all",
                             "source_files": sorted(selections[name])})
        receipt = {"schema": "qikvrt-debian-bundle/v1", "state": "DEBIAN_PACKAGES_BUILT_NOT_INSTALLED",
                   "source_repository": manifest["source_repository"], "source_head": manifest["source_head"],
                   "source_tree": manifest["source_tree"], "source_manifest_sha256": manifest_pin,
                   "package_version": version, "packages": packages, "source_partition_complete": True,
                   "service_auto_started": False, "host_admission_verified": False,
                   "credentials_included": False, "effect_ack_done": False}
        receipt_raw = raw_json(receipt)
        receipt_path = output / "DEBIAN_BUNDLE.json"
        with receipt_path.open("xb") as destination:
            os.chmod(destination.name, 0o600)
            destination.write(receipt_raw)
            destination.flush()
            os.fsync(destination.fileno())
        fd = os.open(output, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return {**receipt, "bundle_sha256": digest(receipt_raw), "output_directory": str(output)}
    except BaseException:
        shutil.rmtree(output)
        raise


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
        position += 60
        body = raw[position:position + size]
        if len(body) != size or name in members:
            raise ValueError("TRUNCATED_OR_DUPLICATE_AR_MEMBER")
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


def parse_control(raw: bytes) -> dict[str, str]:
    try:
        lines = raw.decode("utf-8").splitlines()
        fields = dict(line.split(": ", 1) for line in lines if line)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("INVALID_DEBIAN_CONTROL") from exc
    required = {"Package", "Version", "Section", "Priority", "Architecture", "Maintainer", "Description"}
    if not required <= set(fields):
        raise ValueError("INCOMPLETE_DEBIAN_CONTROL")
    return fields


def verify(bundle: Path, expected: str) -> dict:
    bundle = bundle.resolve()
    receipt_raw = (bundle / "DEBIAN_BUNDLE.json").read_bytes()
    if not re.fullmatch(r"[a-f0-9]{64}", expected or "") or digest(receipt_raw) != expected:
        raise ValueError("DEBIAN_BUNDLE_PIN_MISMATCH")
    receipt = json.loads(receipt_raw)
    if (receipt.get("schema") != "qikvrt-debian-bundle/v1"
            or receipt.get("state") != "DEBIAN_PACKAGES_BUILT_NOT_INSTALLED"
            or receipt.get("service_auto_started") is not False
            or receipt.get("host_admission_verified") is not False
            or receipt.get("effect_ack_done") is not False):
        raise ValueError("DEBIAN_BUNDLE_SCHEMA_MISMATCH")
    actual = {path.name for path in bundle.iterdir() if path.is_file() or path.is_symlink()}
    expected_files = {"DEBIAN_BUNDLE.json"} | {item["file"] for item in receipt["packages"]}
    if actual != expected_files or any(path.is_symlink() for path in bundle.iterdir()):
        raise ValueError("DEBIAN_BUNDLE_INVENTORY_MISMATCH")
    all_sources, package_names = set(), []
    for item in receipt["packages"]:
        raw = (bundle / item["file"]).read_bytes()
        if len(raw) != item["bytes"] or digest(raw) != item["sha256"]:
            raise ValueError("DEBIAN_PACKAGE_DIGEST_MISMATCH")
        members = parse_ar(raw)
        controls = tar_files(members["control.tar.gz"])
        if set(controls) != {"control"}:
            raise ValueError("DEBIAN_CONTROL_INVENTORY_MISMATCH")
        fields = parse_control(controls["control"][0])
        if (fields["Package"] != item["name"] or fields["Version"] != receipt["package_version"]
                or fields["Architecture"] != item["architecture"]):
            raise ValueError("DEBIAN_CONTROL_BINDING_MISMATCH")
        data = tar_files(members["data.tar.gz"])
        prefix = f"usr/lib/qikvrt/{receipt['package_version']}/"
        projected = {name[len(prefix):] for name in data if name.startswith(prefix) and name != prefix + "MANIFEST.json"}
        if projected != set(item["source_files"]):
            raise ValueError("DEBIAN_SOURCE_PROJECTION_MISMATCH")
        if all_sources & projected:
            raise ValueError("DEBIAN_SOURCE_PARTITION_OVERLAP")
        all_sources |= projected
        package_names.append(item["name"])
    if package_names != ["qikvrt-eap", "qikvrt"] or not receipt.get("source_partition_complete"):
        raise ValueError("EXACT_DEBIAN_PACKAGE_SET_REQUIRED")
    return {**receipt, "state": "DEBIAN_PACKAGES_INDEPENDENTLY_VERIFIED_NOT_INSTALLED",
            "bundle_sha256": expected, "verified_source_files": len(all_sources), "effect_ack_done": False}
