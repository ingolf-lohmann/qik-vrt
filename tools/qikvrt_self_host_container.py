#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""OCI extension of the existing S1 launcher; no scheduler or Mesh controller.

Local Docker is used only for build witnesses. Production control uses the
existing host's mutually authenticated HTTPS Docker Engine REST API. There are
no DNS, registrar, credential-store, purchase or destructive cutover operations.
"""
from __future__ import annotations

import hashlib
import base64
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import stat
import subprocess
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
import zipfile
import io
import ipaddress

REPOSITORY = "ingolf-lohmann/qik-vrt"
IMAGE = "ghcr.io/ingolf-lohmann/qik-vrt-s1"
ORIGIN = "https://raumzeitterminal.de"
ENVIRONMENT = "qikvrt-production"
ARTIFACT_PART_BYTES = 256 * 1024 * 1024
ARTIFACT_MAX_BYTES = 4 * ARTIFACT_PART_BYTES


def _artifact_pin(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value),
            "EXACT_ARTIFACT_SHA256_REQUIRED")
    return value


def _artifact_open(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid(),
                "OWNER_REGULAR_ARTIFACT_REQUIRED")
        return os.fdopen(descriptor, "rb"), info
    except BaseException:
        os.close(descriptor)
        raise


def _artifact_sync(directory):
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def artifact_split(archive, output, expected_sha256, *, part_bytes=ARTIFACT_PART_BYTES):
    """Transport the original pinned bytes below the connector's ZIP limit.

    This never imports, executes, signs or admits the image. PARTS.json is the
    completion marker; a failed export removes only its new output directory.
    """
    expected_sha256 = _artifact_pin(expected_sha256)
    require(type(part_bytes) is int and 1 <= part_bytes <= ARTIFACT_PART_BYTES,
            "BOUNDED_ARTIFACT_PART_SIZE_REQUIRED")
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink(), "CREATE_ONLY_ARTIFACT_PARTS_REQUIRED")
    source, before = _artifact_open(archive)
    created = False
    try:
        with source:
            require(0 < before.st_size <= ARTIFACT_MAX_BYTES, "BOUNDED_ARTIFACT_ARCHIVE_REQUIRED")
            require((before.st_size + part_bytes - 1) // part_bytes <= 4,
                    "AT_MOST_FOUR_ARTIFACT_PARTS_REQUIRED")
            output.mkdir(mode=0o700)
            created = True
            total = hashlib.sha256()
            parts = []
            remaining = before.st_size
            while remaining:
                size = min(part_bytes, remaining)
                name = "artifact.part-%03d" % len(parts)
                part_hash = hashlib.sha256()
                with (output / name).open("xb") as destination:
                    outstanding = size
                    while outstanding:
                        raw = source.read(min(1024 * 1024, outstanding))
                        require(bool(raw), "ARTIFACT_CHANGED_DURING_SPLIT")
                        total.update(raw); part_hash.update(raw)
                        destination.write(raw); outstanding -= len(raw)
                    destination.flush(); os.fsync(destination.fileno())
                (output / name).chmod(0o600)
                parts.append({"index": len(parts), "name": name, "bytes": size,
                              "sha256": part_hash.hexdigest()})
                remaining -= size
            after = os.fstat(source.fileno())
            require(not source.read(1) and (before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                    (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "ARTIFACT_CHANGED_DURING_SPLIT")
            require(total.hexdigest() == expected_sha256, "ORIGINAL_ARTIFACT_SHA256_MISMATCH")
        manifest = {"schema": "qikvrt-container-artifact-parts/v1", "archive_bytes": before.st_size,
                    "archive_sha256": expected_sha256, "part_bytes": part_bytes, "parts": parts}
        raw = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
        with (output / "PARTS.json").open("xb") as destination:
            destination.write(raw); destination.flush(); os.fsync(destination.fileno())
        (output / "PARTS.json").chmod(0o600)
        _artifact_sync(output)
        _artifact_sync(output.parent)
        return {"state": "ORIGINAL_ARTIFACT_SPLIT_VERIFIED", "archive_bytes": before.st_size,
                "archive_sha256": expected_sha256, "parts_manifest_sha256": sha(raw),
                "part_count": len(parts), "part_bytes": part_bytes,
                "image_imported": False, "extension_activation_verified": False,
                "public_production_verified": False}
    except BaseException:
        if created:
            shutil.rmtree(output)
        raise


def artifact_join(parts_directory, output, manifest_sha256, archive_sha256):
    """Independently re-read every part; publish one create-only exact archive."""
    manifest_sha256, archive_sha256 = _artifact_pin(manifest_sha256), _artifact_pin(archive_sha256)
    directory = Path(parts_directory).absolute()
    require(not directory.is_symlink() and directory.is_dir(), "REGULAR_ARTIFACT_PART_DIRECTORY_REQUIRED")
    source, _ = _artifact_open(directory / "PARTS.json")
    with source:
        raw = source.read(32769)
    require(len(raw) <= 32768 and sha(raw) == manifest_sha256, "ARTIFACT_PART_MANIFEST_MISMATCH")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "DUPLICATE_ARTIFACT_MANIFEST_MEMBER")
            result[key] = value
        return result
    manifest = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(manifest, dict) and set(manifest) ==
            {"schema", "archive_bytes", "archive_sha256", "part_bytes", "parts"} and
            manifest["schema"] == "qikvrt-container-artifact-parts/v1", "EXACT_ARTIFACT_PART_MANIFEST_REQUIRED")
    size, part_bytes, parts = manifest["archive_bytes"], manifest["part_bytes"], manifest["parts"]
    require(type(size) is int and 0 < size <= ARTIFACT_MAX_BYTES and type(part_bytes) is int and
            1 <= part_bytes <= ARTIFACT_PART_BYTES and isinstance(parts, list) and
            1 <= len(parts) <= 4 and len(parts) == (size + part_bytes - 1) // part_bytes and
            manifest["archive_sha256"] == archive_sha256, "BOUNDED_EXACT_ARTIFACT_PARTS_REQUIRED")
    for index, part in enumerate(parts):
        require(isinstance(part, dict) and set(part) == {"index", "name", "bytes", "sha256"} and
                type(part["index"]) is int and part["index"] == index and
                part["name"] == "artifact.part-%03d" % index and type(part["bytes"]) is int and
                part["bytes"] == min(part_bytes, size - index * part_bytes), "EXACT_ORDERED_ARTIFACT_PART_REQUIRED")
        _artifact_pin(part["sha256"])
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink() and directory not in output.parents,
            "SEPARATE_CREATE_ONLY_ARTIFACT_REQUIRED")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".qikvrt-artifact-", dir=output.parent, delete=False) as destination:
            temporary = Path(destination.name)
            total = hashlib.sha256()
            for part in parts:
                source, before = _artifact_open(directory / part["name"])
                with source:
                    require(before.st_size == part["bytes"], "ARTIFACT_PART_SIZE_MISMATCH")
                    part_hash = hashlib.sha256()
                    remaining = part["bytes"]
                    while remaining:
                        raw = source.read(min(1024 * 1024, remaining))
                        require(bool(raw), "ARTIFACT_PART_CHANGED_DURING_READ")
                        part_hash.update(raw); total.update(raw); destination.write(raw)
                        remaining -= len(raw)
                    after = os.fstat(source.fileno())
                    require(not source.read(1) and (before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                            (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "ARTIFACT_PART_CHANGED_DURING_READ")
                    require(part_hash.hexdigest() == part["sha256"], "ARTIFACT_PART_SHA256_MISMATCH")
            require(total.hexdigest() == archive_sha256, "ORIGINAL_ARTIFACT_SHA256_MISMATCH")
            destination.flush(); os.fsync(destination.fileno())
        # link is atomic and refuses an existing destination, including a race.
        os.link(temporary, output, follow_symlinks=False)
        _artifact_sync(output.parent)
        check, observed = _artifact_open(output)
        with check:
            require(observed.st_size == size and hashlib.file_digest(check, "sha256").hexdigest() == archive_sha256,
                    "RESTORED_ARTIFACT_READBACK_MISMATCH")
        return {"state": "ORIGINAL_ARTIFACT_REASSEMBLED_VERIFIED", "archive_bytes": size,
                "archive_sha256": archive_sha256, "parts_manifest_sha256": manifest_sha256,
                "part_count": len(parts), "image_imported": False,
                "extension_activation_verified": False, "public_production_verified": False}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def write_receipt(path, result):
    # Receipts contain public source/image/operation identities, never config
    # bytes, auth headers, tokens, client certificates or daemon responses.
    result = {"schema": "qikvrt-s1-container-receipt/v1", **result,
              "effect_ack_done": False, "ordinary_release": False}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def command(*argv, input=None):
    return subprocess.check_output(list(argv), input=input, timeout=240,
                                   stderr=subprocess.PIPE)


def context(root, output):
    """Export tracked source and credential-free Git objects into a new context."""
    root, output = Path(root).resolve(), Path(output).absolute()
    require(not output.exists() and not (output == root or root in output.parents),
            "SEPARATE_CREATE_ONLY_BUILD_CONTEXT_REQUIRED")
    head = command("git", "-C", str(root), "rev-parse", "HEAD").decode().strip()
    tree = command("git", "-C", str(root), "rev-parse", "HEAD^{tree}").decode().strip()
    command("git", "-C", str(root), "diff", "--quiet", "HEAD", "--")
    epoch = int(command("git", "-C", str(root), "show", "-s", "--format=%ct", "HEAD"))
    output.mkdir(parents=True)
    rows = command("git", "-C", str(root), "ls-tree", "-r", "-z", "HEAD").split(b"\0")
    for row in rows:
        if not row:
            continue
        metadata, name = row.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split()
        path = name.decode()
        require(kind == "blob" and mode in ("100644", "100755") and
                not Path(path).is_absolute() and ".." not in Path(path).parts,
                "REGULAR_TRACKED_BUILD_INPUT_REQUIRED")
        raw = command("git", "-C", str(root), "cat-file", "blob", blob)
        require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == blob,
                "BUILD_SOURCE_BLOB_MISMATCH")
        dest = output / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        dest.chmod(0o755 if mode == "100755" else 0o644)
        os.utime(dest, (epoch, epoch))
    gitdir = Path(command("git", "-C", str(root), "rev-parse", "--absolute-git-dir").decode().strip())
    require(not (gitdir / "objects/info/alternates").exists(), "SELF_CONTAINED_GIT_OBJECTS_REQUIRED")
    (output / ".git").mkdir()
    shutil.copytree(gitdir / "objects", output / ".git/objects")
    (output / ".git/HEAD").write_text(head + "\n")
    (output / ".git/shallow").write_text(head + "\n")
    (output / ".git/config").write_text("[core]\nrepositoryformatversion=0\nbare=false\nfilemode=true\nautocrlf=false\n")
    (output / ".git/refs").mkdir()
    command("git", "-C", str(output), "read-tree", "HEAD")
    command("git", "-C", str(output), "diff", "--quiet", "HEAD", "--")
    return {"state": "SEALED_BUILD_CONTEXT", "source_head": head, "source_tree": tree,
            "source_date_epoch": epoch, "credential_material_included": False}


def oci(path, head, tree):
    """Check every referenced OCI blob, image platform and exact source labels."""
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
        require(all(m.isfile() or m.isdir() for m in members), "OCI_REGULAR_ENTRIES_REQUIRED")
        names = [m.name.removeprefix("./") for m in members if m.isfile()]
        require(len(names) == len(set(names)), "OCI_DUPLICATE_PATH")
        entries = {m.name.removeprefix("./"): m for m in members if m.isfile()}
        def read(name):
            require(name in entries and entries[name].size <= 2 * 1024**3, "OCI_BLOB_MISSING_OR_TOO_LARGE")
            return archive.extractfile(entries[name]).read()
        def blob(descriptor):
            digest = descriptor.get("digest", "")
            require(re.fullmatch(r"sha256:[a-f0-9]{64}", digest), "OCI_DIGEST_REQUIRED")
            raw = read("blobs/sha256/" + digest[7:])
            require(len(raw) == descriptor.get("size") and sha(raw) == digest[7:], "OCI_BLOB_INTEGRITY_MISMATCH")
            return raw
        require(json.loads(read("oci-layout"))["imageLayoutVersion"] == "1.0.0", "OCI_LAYOUT_REQUIRED")
        index = json.loads(read("index.json"))
        require(len(index.get("manifests", [])) == 1, "SINGLE_TESTED_LINUX_IMAGE_REQUIRED")
        descriptor = index["manifests"][0]
        manifest = json.loads(blob(descriptor))
        config = json.loads(blob(manifest["config"]))
        for layer in manifest["layers"]:
            blob(layer)
        require(config.get("os") == "linux" and config.get("architecture") == "amd64", "LINUX_AMD64_REQUIRED")
        labels = config["config"].get("Labels", {})
        require(labels.get("org.opencontainers.image.revision") == head and
                labels.get("de.qikvrt.source-tree") == tree, "OCI_SOURCE_BINDING_MISMATCH")
        require(config["config"].get("User") == "10001:10001", "UNPRIVILEGED_IMAGE_REQUIRED")
        return {"state": "OCI_BYTES_VERIFIED", "source_head": head, "source_tree": tree,
                "image_digest": descriptor["digest"], "config_digest": manifest["config"]["digest"],
                "layers": manifest["layers"], "diff_ids": config.get("rootfs", {}).get("diff_ids", []),
                "image_config_digest": manifest["config"]["digest"],
                "layer_digests": [layer["digest"] for layer in manifest["layers"]],
                "rootfs_diff_ids": config.get("rootfs", {}).get("diff_ids", []),
                "created": config.get("created"),
                "history_created": [item.get("created") for item in config.get("history", [])],
                "oci_archive_sha256": sha(Path(path).read_bytes())}


def carrier_download(expected, path):
    """Read original Actions artifact; never forward API auth to blob storage."""
    require(expected["repository"] == REPOSITORY and
            os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "CARRIER_AUTHORITY_REQUIRED")
    token = os.environ.get("GITHUB_TOKEN")
    require(bool(token), "ACTIONS_READ_BINDING_REQUIRED")
    base = "https://api.github.com/repos/" + REPOSITORY + "/actions/artifacts/" + str(expected["artifact_id"])
    metadata = json.loads(get(base, token))
    require(metadata.get("expired") is False and
            metadata.get("size_in_bytes") == expected["archive_bytes"] and
            metadata.get("digest") == "sha256:" + expected["archive_sha256"] and
            metadata.get("workflow_run", {}).get("id") == expected["run_id"] and
            metadata.get("workflow_run", {}).get("head_sha") == expected["source_head"],
            "ORIGINAL_CARRIER_ARTIFACT_BINDING_MISMATCH_OR_EXPIRED")
    class CaptureRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    request = urllib.request.Request(base + "/zip", headers={"Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        try:
            urllib.request.build_opener(CaptureRedirect()).open(request, timeout=30)
        except urllib.error.HTTPError as response:
            require(response.code == 302, "ORIGINAL_ACTIONS_ARCHIVE_REDIRECT_REQUIRED")
            location = response.headers.get("Location", "")
        else:
            raise ValueError("ORIGINAL_ACTIONS_ARCHIVE_REDIRECT_REQUIRED")
        target = urllib.parse.urlsplit(location)
        require(target.scheme == "https" and target.hostname and not target.username and
                target.hostname.endswith((".blob.core.windows.net", ".actions.githubusercontent.com",
                                          ".githubusercontent.com", ".s3.amazonaws.com")),
                "ORIGINAL_ACTIONS_BLOB_ORIGIN_REQUIRED")
        # Signed location stays in memory. No Authorization header on this GET.
        with urllib.request.build_opener(NoRedirect()).open(location, timeout=90) as response, Path(path).open("xb") as output:
            remaining = expected["archive_bytes"]
            while remaining:
                raw = response.read(min(1024**2, remaining))
                require(bool(raw), "CARRIER_ARCHIVE_TRUNCATED")
                output.write(raw); remaining -= len(raw)
            require(not response.read(1), "CARRIER_ARCHIVE_TOO_LARGE")
    except (OSError, urllib.error.URLError):
        raise ValueError("PINNED_CARRIER_FETCH_NOT_ADMITTED") from None


def carrier_import(expected, path, output):
    """Verify original ZIP, sealed source and every image blob; copy OCI bytes."""
    require(expected.get("schema") == "qikvrt-s1-frozen-container-carrier/v1" and
            expected.get("repository") == REPOSITORY, "FROZEN_CARRIER_CONTRACT_REQUIRED")
    path, output = Path(path), Path(output)
    require(not output.exists(), "CREATE_ONLY_CARRIER_OUTPUT_REQUIRED")
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    require(path.stat().st_size == expected["archive_bytes"] and
            digest == expected["archive_sha256"], "ORIGINAL_CARRIER_ZIP_INTEGRITY_MISMATCH")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and all("/" not in n and "\\" not in n for n in names),
                "REGULAR_UNIQUE_DELIVERY_FILES_REQUIRED")
        raw_delivery = archive.read("DELIVERY.json")
        require(sha(raw_delivery) == expected["delivery_sha256"], "CARRIER_DELIVERY_PIN_MISMATCH")
        delivery = json.loads(raw_delivery)
        require(delivery["schema"] == "qikvrt-firefox-runtime-delivery/v1" and
                delivery["source_head"] == expected["source_head"] and
                delivery["source_tree"] == expected["source_tree"] and
                delivery["runtime_image_id"] == expected["image_config_digest"] and
                delivery["manifest_sha256"] == expected["package_manifest_sha256"] and
                (delivery["os"], delivery["architecture"]) == ("linux", "amd64") and
                set(names) == set(delivery["files"]) | {"DELIVERY.json"}, "CARRIER_DELIVERY_SOURCE_MISMATCH")
        for name, pin in delivery["files"].items():
            with archive.open(name) as source:
                actual = hashlib.file_digest(source, "sha256").hexdigest()
            require(archive.getinfo(name).file_size == pin["bytes"] and actual == pin["sha256"],
                    "CARRIER_DELIVERY_FILE_INTEGRITY_MISMATCH")
        with tarfile.open(fileobj=io.BytesIO(archive.read("package.tar")), mode="r:") as package:
            entries = package.getmembers()
            require(all(e.isfile() and not Path(e.name).is_absolute() and ".." not in Path(e.name).parts
                        for e in entries) and len(entries) == len({e.name for e in entries}),
                    "REGULAR_SEALED_PACKAGE_REQUIRED")
            manifest_raw = package.extractfile("MANIFEST.json").read()
            require(sha(manifest_raw) == expected["package_manifest_sha256"], "CARRIER_PACKAGE_PIN_MISMATCH")
            manifest = json.loads(manifest_raw)
            require((manifest["source_head"], manifest["source_tree"], manifest["source_repository"]) ==
                    (expected["source_head"], expected["source_tree"], REPOSITORY) and
                    "browser_runtime" in manifest and
                    set(e.name for e in entries) == set(manifest["files"]) | {"MANIFEST.json"},
                    "CARRIER_SEALED_SOURCE_MISMATCH")
            for name, pin in manifest["files"].items():
                entry = package.getmember(name)
                raw = package.extractfile(entry).read()
                require(len(raw) == pin["bytes"] and sha(raw) == pin["sha256"] and
                        entry.mode == (0o755 if pin["mode"] == "100755" else 0o644),
                        "CARRIER_SEALED_FILE_INTEGRITY_MISMATCH")
        output.mkdir(parents=True)
        sizes, seen = {}, set()
        with archive.open("runtime-image.tar.gz") as compressed, tarfile.open(fileobj=compressed, mode="r|gz") as image:
            for entry in image:
                name = entry.name.removeprefix("./")
                require(name not in seen and (entry.isfile() or entry.isdir()) and
                        not Path(name).is_absolute() and ".." not in Path(name).parts and
                        entry.size <= 2 * 1024**3, "REGULAR_BOUNDED_CARRIER_IMAGE_REQUIRED")
                seen.add(name)
                if not entry.isfile():
                    continue
                require(name in ("index.json", "oci-layout", "manifest.json", "repositories") or
                        re.fullmatch(r"blobs/sha256/[a-f0-9]{64}", name), "CARRIER_IMAGE_PATH_REFUSED")
                if name in ("manifest.json", "repositories"):
                    continue
                dest = output / name; dest.parent.mkdir(parents=True, exist_ok=True)
                hasher = hashlib.sha256()
                with image.extractfile(entry) as source, dest.open("xb") as target:
                    while raw := source.read(1024**2):
                        hasher.update(raw); target.write(raw)
                sizes[name] = entry.size
                if name.startswith("blobs/"):
                    require(hasher.hexdigest() == name.rsplit("/", 1)[-1], "CARRIER_IMAGE_BLOB_MISMATCH")
        require(json.loads((output / "oci-layout").read_bytes())["imageLayoutVersion"] == "1.0.0",
                "CARRIER_OCI_LAYOUT_REQUIRED")
        index = json.loads((output / "index.json").read_bytes())
        require(len(index["manifests"]) == 1 and
                index["manifests"][0]["digest"] == expected["oci_manifest_digest"], "CARRIER_MANIFEST_PIN_MISMATCH")
        def descriptor(value):
            name = "blobs/sha256/" + value["digest"].removeprefix("sha256:")
            require(name in sizes and sizes[name] == value["size"], "CARRIER_DESCRIPTOR_BINDING_MISMATCH")
            return output / name
        image_manifest = json.loads(descriptor(index["manifests"][0]).read_bytes())
        config = json.loads(descriptor(image_manifest["config"]).read_bytes())
        require(image_manifest["config"]["digest"] == expected["image_config_digest"] and
                (config["os"], config["architecture"]) == ("linux", "amd64") and
                config["rootfs"]["diff_ids"] == [layer["digest"] for layer in image_manifest["layers"]],
                "CARRIER_CONFIG_OR_ORDERED_DIFFID_MISMATCH")
        for layer in image_manifest["layers"]:
            require(layer["mediaType"] == "application/vnd.oci.image.layer.v1.tar", "ORIGINAL_UNCOMPRESSED_CARRIER_LAYER_REQUIRED")
            descriptor(layer)
        return {"state": "ORIGINAL_FROZEN_CARRIER_VERIFIED", "scope": "DEPENDENCY_IMAGE_ONLY",
                "artifact_id": expected["artifact_id"], "run_id": expected["run_id"],
                "predecessor_source_head": expected["source_head"], "predecessor_source_tree": expected["source_tree"],
                "archive_bytes": expected["archive_bytes"], "archive_sha256": digest,
                "image_digest": expected["oci_manifest_digest"], "image_config_digest": expected["image_config_digest"],
                "ordered_layers": len(image_manifest["layers"]), "sealed_files_verified": len(manifest["files"]),
                "predecessor_acceptance_transferred": False, "public_production_verified": False}


def carrier_archive_config(expected, layer_digest):
    require(expected.get("schema") == "qikvrt-s1-frozen-container-carrier/v1" and
            expected.get("repository") == REPOSITORY and
            re.fullmatch(r"[a-f0-9]{64}", expected.get("archive_sha256", "")) and
            type(expected.get("archive_bytes")) is int and
            0 < expected["archive_bytes"] <= 2 * 1024**3,
            "FROZEN_CARRIER_ARCHIVE_CONTRACT_REQUIRED")
    return {"architecture": "amd64", "os": "linux", "created": "1970-01-01T00:00:00Z",
            "config": {"User": "10001:10001", "Labels": {
                "org.opencontainers.image.revision": expected["source_head"],
                "de.qikvrt.source-tree": expected["source_tree"],
                "de.qikvrt.original-archive-sha256": expected["archive_sha256"],
                "de.qikvrt.original-artifact-id": str(expected["artifact_id"])}},
            "rootfs": {"type": "layers", "diff_ids": [layer_digest]}}


def carrier_archive(expected, path, output):
    """Encapsulate the unchanged original ZIP using the existing OCI publisher."""
    path, output = Path(path), Path(output)
    carrier_archive_config(expected, "sha256:" + "0" * 64)
    require(not output.exists(), "CREATE_ONLY_CARRIER_ARCHIVE_REQUIRED")
    require(path.is_file() and not path.is_symlink() and
            path.stat().st_size == expected["archive_bytes"], "ORIGINAL_CARRIER_ZIP_INTEGRITY_MISMATCH")
    def encoded(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    def entry(name, size):
        item = tarfile.TarInfo(name); item.size = size; item.mode = 0o444
        return item
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        layer = Path(tmp) / "layer.tar"
        with path.open("rb") as source:
            require(hashlib.file_digest(source, "sha256").hexdigest() == expected["archive_sha256"],
                    "ORIGINAL_CARRIER_ZIP_INTEGRITY_MISMATCH")
            source.seek(0)
            with tarfile.open(layer, "w", format=tarfile.USTAR_FORMAT) as archive:
                archive.addfile(entry("original-delivery.zip", expected["archive_bytes"]), source)
        with layer.open("rb") as source:
            layer_digest = "sha256:" + hashlib.file_digest(source, "sha256").hexdigest()
        config = encoded(carrier_archive_config(expected, layer_digest))
        config_digest = "sha256:" + sha(config)
        manifest = encoded({"schemaVersion": 2, "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {"mediaType": "application/vnd.oci.image.config.v1+json",
                       "digest": config_digest, "size": len(config)},
            "layers": [{"mediaType": "application/vnd.oci.image.layer.v1.tar",
                        "digest": layer_digest, "size": layer.stat().st_size}]})
        manifest_digest = "sha256:" + sha(manifest)
        blobs = {"oci-layout": encoded({"imageLayoutVersion": "1.0.0"}),
                 "index.json": encoded({"schemaVersion": 2, "manifests": [{
                     "mediaType": "application/vnd.oci.image.manifest.v1+json",
                     "digest": manifest_digest, "size": len(manifest)}]}),
                 "blobs/sha256/" + config_digest[7:]: config,
                 "blobs/sha256/" + manifest_digest[7:]: manifest}
        with output.open("xb") as target, tarfile.open(fileobj=target, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, raw in sorted(blobs.items()):
                archive.addfile(entry(name, len(raw)), io.BytesIO(raw))
            with layer.open("rb") as source:
                archive.addfile(entry("blobs/sha256/" + layer_digest[7:], layer.stat().st_size), source)
    return carrier_archive_check(expected, output)


def carrier_archive_check(expected, path):
    """Independently read OCI transport and recover/hash the exact original ZIP."""
    carrier_archive_config(expected, "sha256:" + "0" * 64)
    with tarfile.open(path, "r:*") as archive:
        members = archive.getmembers()
        require(all(e.isfile() or e.isdir() for e in members), "ARCHIVE_OCI_REGULAR_ENTRIES_REQUIRED")
        entries = {e.name.removeprefix("./"): e for e in members if e.isfile()}
        require(len(entries) == sum(e.isfile() for e in members), "ARCHIVE_OCI_DUPLICATE_PATH")
        def small(name):
            require(name in entries and entries[name].size <= 1024**2, "ARCHIVE_OCI_METADATA_REQUIRED")
            return archive.extractfile(entries[name]).read()
        def descriptor(value):
            digest = value.get("digest", "")
            require(re.fullmatch(r"sha256:[a-f0-9]{64}", digest), "ARCHIVE_OCI_DIGEST_REQUIRED")
            name = "blobs/sha256/" + digest[7:]
            require(name in entries and entries[name].size == value.get("size") and
                    entries[name].size <= expected["archive_bytes"] + 1024**2,
                    "ARCHIVE_OCI_DESCRIPTOR_MISMATCH")
            with archive.extractfile(entries[name]) as source:
                require(hashlib.file_digest(source, "sha256").hexdigest() == digest[7:],
                        "ARCHIVE_OCI_BLOB_INTEGRITY_MISMATCH")
            return name
        require(json.loads(small("oci-layout")) == {"imageLayoutVersion": "1.0.0"}, "ARCHIVE_OCI_LAYOUT_REQUIRED")
        index = json.loads(small("index.json"))
        require(index.get("schemaVersion") == 2 and len(index.get("manifests", [])) == 1,
                "SINGLE_ORIGINAL_ARCHIVE_REQUIRED")
        manifest_descriptor = index["manifests"][0]
        manifest_name = descriptor(manifest_descriptor)
        manifest = json.loads(small(manifest_name))
        require(manifest.get("schemaVersion") == 2 and
                manifest.get("mediaType") == "application/vnd.oci.image.manifest.v1+json" and
                manifest_descriptor.get("mediaType") == manifest["mediaType"] and
                len(manifest.get("layers", [])) == 1, "ORIGINAL_ARCHIVE_IMAGE_REQUIRED")
        layer = manifest["layers"][0]
        require(layer.get("mediaType") == "application/vnd.oci.image.layer.v1.tar" and
                manifest["config"].get("mediaType") == "application/vnd.oci.image.config.v1+json",
                "ORIGINAL_ARCHIVE_MEDIA_TYPE_REQUIRED")
        config_name, layer_name = descriptor(manifest["config"]), descriptor(layer)
        require(set(entries) == {"oci-layout", "index.json", manifest_name, config_name, layer_name},
                "ORIGINAL_ARCHIVE_FILESET_REQUIRED")
        require(json.loads(small(config_name)) == carrier_archive_config(expected, layer["digest"]),
                "ORIGINAL_ARCHIVE_SOURCE_BINDING_MISMATCH")
        with archive.extractfile(entries[layer_name]) as source, tarfile.open(fileobj=source, mode="r|") as payload:
            item = payload.next()
            require(item is not None and item.isfile() and item.name == "original-delivery.zip" and
                    item.size == expected["archive_bytes"] and item.mode == 0o444 and
                    item.uid == item.gid == item.mtime == 0,
                    "SINGLE_PINNED_ORIGINAL_ZIP_REQUIRED")
            with payload.extractfile(item) as original:
                require(hashlib.file_digest(original, "sha256").hexdigest() == expected["archive_sha256"],
                        "ORIGINAL_CARRIER_ZIP_INTEGRITY_MISMATCH")
            require(payload.next() is None, "SINGLE_PINNED_ORIGINAL_ZIP_REQUIRED")
    return {"state": "ORIGINAL_ARCHIVE_OCI_BYTE_READBACK_VERIFIED",
            "scope": "ORIGINAL_ARCHIVE_BYTES_ONLY", "image_digest": manifest_descriptor["digest"],
            "archive_bytes": expected["archive_bytes"], "archive_sha256": expected["archive_sha256"],
            "artifact_id": expected["artifact_id"], "source_head": expected["source_head"],
            "source_tree": expected["source_tree"], "predecessor_acceptance_transferred": False,
            "public_production_verified": False, "durable_ci_source_activated": False}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("REDIRECT_FORBIDDEN")


def get(url, token=None):
    headers = {"Accept": "application/json", "User-Agent": "QIKVRT-S1-REST"}
    if token:
        require(url.startswith("https://api.github.com/"), "GITHUB_CREDENTIAL_ORIGIN_MISMATCH")
        headers["Authorization"] = "Bearer " + token
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(urllib.request.Request(url, headers=headers), timeout=20) as response:
        require(response.status == 200, "READBACK_HTTP_200_REQUIRED")
        raw = response.read(16 * 1024**2 + 1)
        require(len(raw) <= 16 * 1024**2, "BOUNDED_READBACK_REQUIRED")
        return raw


def pages(path, token):
    result = []
    for page in range(1, 101):
        values = json.loads(get("https://api.github.com/repos/" + REPOSITORY + path +
                                ("&" if "?" in path else "?") + "per_page=100&page=" + str(page), token))
        require(isinstance(values, list), "COMPLETE_GITHUB_COLLECTION_REQUIRED")
        result.extend(values)
        if len(values) < 100:
            return result
    raise ValueError("GITHUB_COLLECTION_BOUND_EXCEEDED")


def production_gate(head):
    """Fresh native governance; caller must already be on trusted main."""
    from tools.qikvrt_required_review_gate import evaluate_required_review, resolve_required_code_owner
    token = os.environ.get("GITHUB_TOKEN")
    require(token and os.environ.get("GITHUB_REPOSITORY") == REPOSITORY and
            os.environ.get("GITHUB_REF") == "refs/heads/main", "TRUSTED_MAIN_PRODUCTION_REQUIRED")
    base = "https://api.github.com/repos/" + REPOSITORY
    current = json.loads(get(base + "/branches/main", token))
    require(current["commit"]["sha"] == head and current.get("protected") is True,
            "PROTECTED_EXACT_MAIN_REQUIRED")
    environment = json.loads(get(base + "/environments/" + ENVIRONMENT, token))
    reviewers = [r for r in environment.get("protection_rules", [])
                 if r.get("type") == "required_reviewers" and r.get("reviewers") and r.get("prevent_self_review") is True]
    require(reviewers, "INDEPENDENT_PROTECTED_PRODUCTION_ENVIRONMENT_REQUIRED")
    rules = json.loads(get(base + "/rules/branches/main", token))
    require(any(r.get("type") == "required_status_checks" and
                {"test", "QIKVRT required code-owner review"} <=
                {c.get("context") for c in r.get("parameters", {}).get("required_status_checks", [])}
                for r in rules), "EXISTING_REQUIRED_CHECKS_NOT_ENFORCED")
    # Reuse the existing exact-head run folding. The owning CI is necessarily
    # still executing; its test/container jobs are mandatory `needs` gates.
    # Every other applicable current-head workflow must already be terminal.
    from tools.qikvrt_expected_head_promotion import collapse_latest_runs
    runs = []
    for page in range(1, 101):
        response = json.loads(get(base + "/actions/runs?head_sha=" + head +
                                  "&per_page=100&page=" + str(page), token))
        batch = response.get("workflow_runs")
        require(isinstance(batch, list), "EXACT_HEAD_WORKFLOW_INVENTORY_REQUIRED")
        runs.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise ValueError("EXACT_HEAD_WORKFLOW_INVENTORY_INCOMPLETE")
    require(any(str(r.get("id")) == os.environ.get("GITHUB_RUN_ID") and r.get("head_sha") == head
                for r in runs), "OWNING_EXACT_HEAD_CI_NOT_OBSERVED")
    for name, run in collapse_latest_runs(runs).items():
        if str(run.get("id")) == os.environ.get("GITHUB_RUN_ID"):
            continue
        require(run.get("head_sha") == head and run.get("status") == "completed" and
                run.get("conclusion") in ("success", "skipped"),
                "OTHER_APPLICABLE_EXACT_HEAD_WORKFLOW_NOT_GREEN")
    prs = pages("/commits/" + head + "/pulls", token)
    for pr in prs:
        if not pr.get("merged_at") or pr.get("base", {}).get("ref") != "main":
            continue
        live = json.loads(get(base + "/pulls/" + str(pr["number"]), token))
        if live.get("merge_commit_sha") != head and live.get("head", {}).get("sha") != head:
            continue
        reviews = pages("/pulls/" + str(pr["number"]) + "/reviews", token)
        reviewer = resolve_required_code_owner(REPOSITORY, pr_author=live["user"]["login"])
        decision = evaluate_required_review(live, rules, reviews, required_code_owner=reviewer)
        if decision["gate_state"] == "success":
            require(json.loads(get(base + "/branches/main", token))["commit"]["sha"] == head,
                    "MAIN_DRIFT_AFTER_ADMISSION")
            return {"state": "PRODUCTION_GOVERNANCE_ADMITTED", "source_head": head,
                    "review_id": decision["review_id"], "pr_number": pr["number"], "environment": ENVIRONMENT}
    raise ValueError("EXACT_MERGED_PR_OWNER_REVIEW_REQUIRED")


def binding(raw, pin, image):
    require(sha(raw) == pin, "INDEPENDENT_DEPLOYMENT_BINDING_PIN_REQUIRED")
    value = json.loads(raw)
    fields = {"schema", "repository", "origin", "docker_api", "daemon_id", "container_name",
              "state_volume", "config_directory", "config_sha256", "node_id", "manifest_sha256",
              "loopback_port", "source_head", "source_tree", "image_digest"}
    require(set(value) == fields and value["schema"] == "qikvrt-s1-linux-host-binding/v1" and
            value["repository"] == REPOSITORY and value["origin"] == ORIGIN,
            "EXACT_OWNER_HOST_BINDING_REQUIRED")
    url = urllib.parse.urlsplit(value["docker_api"])
    require(url.scheme == "https" and url.hostname and not url.username and not url.password and
            url.path in ("", "/") and not url.query and not url.fragment, "MUTUAL_TLS_REST_ORIGIN_REQUIRED")
    require(image == IMAGE + "@" + value["image_digest"] and
            re.fullmatch(r"sha256:[a-f0-9]{64}", value["image_digest"]), "EXACT_VERSIONED_IMAGE_REQUIRED")
    for key in ("source_head", "source_tree"):
        require(re.fullmatch(r"[a-f0-9]{40}", value[key]), "EXACT_SOURCE_REQUIRED")
    for key in ("config_sha256", "manifest_sha256"):
        require(re.fullmatch(r"[a-f0-9]{64}", value[key]), "EXACT_RUNTIME_PINS_REQUIRED")
    for key in ("container_name", "state_volume", "node_id", "daemon_id"):
        require(re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", value[key]), "BOUNDED_HOST_IDENTITY_REQUIRED")
    directory = Path(value["config_directory"])
    require(directory.is_absolute() and str(directory).startswith("/etc/qikvrt/") and
            ".." not in directory.parts, "EXISTING_PRIVATE_HOST_CONFIGURATION_REQUIRED")
    require(type(value["loopback_port"]) is int and 1024 <= value["loopback_port"] <= 65535,
            "LOOPBACK_ROUTING_PORT_REQUIRED")
    return value


class Engine:
    def __init__(self, origin, ca, cert, key):
        for path in (ca, cert, key):
            require(Path(path).is_file() and not Path(path).is_symlink() and
                    Path(path).stat().st_mode & 0o777 == 0o600, "OWNER_ONLY_MTLS_FILES_REQUIRED")
        self.context = ssl.create_default_context(cafile=str(ca))
        self.context.load_cert_chain(str(cert), str(key))
        self.origin = urllib.parse.urlsplit(origin)

    def call(self, method, path, value=None, *, binary=False):
        connection = http.client.HTTPSConnection(self.origin.hostname, self.origin.port or 443,
                                                 context=self.context, timeout=120)
        try:
            body = json.dumps(value).encode() if value is not None else None
            headers = {"Content-Type": "application/json"}
            if method == "POST" and path.startswith("/v1.45/images/create?"):
                # Only the admitted owner daemon receives a short-lived,
                # package-read credential through Docker's native pull API.
                token = os.environ.get("GITHUB_TOKEN")
                if token:
                    auth = {"username": os.environ["GITHUB_ACTOR"], "password": token, "serveraddress": "ghcr.io"}
                    headers["X-Registry-Auth"] = base64.b64encode(json.dumps(auth).encode()).decode()
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read(32 * 1024**2 + 1)
            require(len(raw) <= 32 * 1024**2, "BOUNDED_ENGINE_RESPONSE_REQUIRED")
            require(200 <= response.status < 300, "ENGINE_REST_HTTP_" + str(response.status))
            return json.loads(raw) if raw and not binary and not path.startswith("/v1.45/images/create?") else raw
        finally:
            connection.close()


def host_preflight(head, tree, output, environment=None):
    """Observe the existing protected host independently of image production.

    Reuse the exact production admission, binding and mTLS Engine. This is one
    GET /info only: no image pull, container creation/start, DNS or key change.
    Public metadata identifies the first boundary without exposing private
    connection values or treating the observation as deployment acceptance.
    """
    env = os.environ if environment is None else environment
    names = ("QIKVRT_HOST_BINDING", "QIKVRT_HOST_BINDING_SHA256",
             "QIKVRT_HOST_CA", "QIKVRT_HOST_CERT", "QIKVRT_HOST_KEY")
    receipt = {"schema": "qikvrt-s1-host-preflight/v1", "state": "HOLD",
               "subject": {"repository": REPOSITORY, "head": head, "tree": tree},
               "binding_present": {name: bool(env.get(name)) for name in names},
               "first_boundary": None, "authenticated_daemon_readback": False,
               "host_requests": 0, "deployment_performed": False,
               "public_production_verified": False, "effect_ack_done": False}
    safe_errors = {"TRUSTED_MAIN_PRODUCTION_REQUIRED", "PROTECTED_EXACT_MAIN_REQUIRED",
        "INDEPENDENT_PROTECTED_PRODUCTION_ENVIRONMENT_REQUIRED", "EXISTING_REQUIRED_CHECKS_NOT_ENFORCED",
        "EXACT_MERGED_PR_OWNER_REVIEW_REQUIRED", "OTHER_APPLICABLE_EXACT_HEAD_WORKFLOW_NOT_GREEN",
        "OWNING_EXACT_HEAD_CI_NOT_OBSERVED", "MAIN_DRIFT_AFTER_ADMISSION",
        "HOST_PREFLIGHT_EXACT_SOURCE_REQUIRED", "HOST_PREFLIGHT_BINDINGS_UNAVAILABLE",
        "INDEPENDENT_DEPLOYMENT_BINDING_PIN_REQUIRED", "EXACT_OWNER_HOST_BINDING_REQUIRED",
        "MUTUAL_TLS_REST_ORIGIN_REQUIRED", "EXACT_VERSIONED_IMAGE_REQUIRED", "EXACT_SOURCE_REQUIRED",
        "EXACT_RUNTIME_PINS_REQUIRED", "BOUNDED_HOST_IDENTITY_REQUIRED",
        "EXISTING_PRIVATE_HOST_CONFIGURATION_REQUIRED", "LOOPBACK_ROUTING_PORT_REQUIRED",
        "EXACT_ADMITTED_DAEMON_REQUIRED", "OWNER_ONLY_MTLS_FILES_REQUIRED"}
    try:
        require(re.fullmatch(r"[a-f0-9]{40}", head or "") and
                re.fullmatch(r"[a-f0-9]{40}", tree or "") and env.get("GITHUB_SHA") == head and
                env.get("GITHUB_REPOSITORY") == REPOSITORY and env.get("GITHUB_REF") == "refs/heads/main",
                "HOST_PREFLIGHT_EXACT_SOURCE_REQUIRED")
        require(all(receipt["binding_present"].values()), "HOST_PREFLIGHT_BINDINGS_UNAVAILABLE")
        raw = env["QIKVRT_HOST_BINDING"].encode("utf-8")
        value = json.loads(raw)
        image = IMAGE + "@" + value["image_digest"]
        value = binding(raw, env["QIKVRT_HOST_BINDING_SHA256"], image)
        require(value["source_head"] == head and value["source_tree"] == tree,
                "HOST_PREFLIGHT_EXACT_SOURCE_REQUIRED")
        production_gate(head)  # Preserve every original protected-host guard.
        with tempfile.TemporaryDirectory(prefix="qikvrt-host-preflight-") as temporary:
            private = Path(temporary)
            paths = []
            for name in ("QIKVRT_HOST_CA", "QIKVRT_HOST_CERT", "QIKVRT_HOST_KEY"):
                path = private / name
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w") as stream:
                    stream.write(env[name])
                paths.append(path)
            engine = Engine(value["docker_api"], *paths)
            receipt["host_requests"] = 1
            info = engine.call("GET", "/v1.45/info")
            require(isinstance(info, dict) and info.get("OSType") == "linux" and
                    info.get("ID") == value["daemon_id"], "EXACT_ADMITTED_DAEMON_REQUIRED")
            receipt.update(state="AUTHENTICATED_EXISTING_DAEMON_OBSERVED",
                           authenticated_daemon_readback=True,
                           binding_sha256=sha(raw), daemon_readback_sha256=sha(json.dumps(info, sort_keys=True).encode()))
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException) as error:
        code = str(error)
        receipt["first_boundary"] = code if code in safe_errors else "HOST_PREFLIGHT_VALIDATION_OR_TRANSPORT_FAILED"
    return write_receipt(output, receipt)


def container_request(value, image):
    """One admitted specification for initial creation and unchanged recovery."""
    return {"Image": image, "User": "10001:10001",
        "Cmd": ["--config", "/run/qikvrt/config.json", "--manifest-sha256", value["manifest_sha256"]],
        "Labels": {"de.qikvrt.repository": REPOSITORY,
                   "de.qikvrt.binding-sha256": sha(json.dumps(value, sort_keys=True).encode())},
        "ExposedPorts": {"8080/tcp": {}},
        "HostConfig": {"ReadonlyRootfs": True, "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"], "Init": True,
            "RestartPolicy": {"Name": "unless-stopped"}, "ShmSize": 256 * 1024**2,
            "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=768m,mode=1777"},
            "PortBindings": {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(value["loopback_port"])}]},
            "Mounts": [{"Type": "volume", "Source": value["state_volume"], "Target": "/var/lib/qikvrt/node"},
                       {"Type": "bind", "Source": value["config_directory"], "Target": "/run/qikvrt", "ReadOnly": True}]}}


def existing_container(live, identifier, value, request):
    """Read-only admission of the same container; never inspect profile bytes."""
    config, host = live.get("Config", {}), live.get("HostConfig", {})
    require(live.get("Id") == identifier and
            all(config.get(key) == request[key] for key in ("Image", "User", "Cmd")) and
            all(config.get("Labels", {}).get(key) == pin for key, pin in request["Labels"].items()),
            "EXISTING_NODE_REPLACEMENT_REQUIRES_S1_MIGRATION")
    require(all(host.get(key) == expected for key, expected in request["HostConfig"].items()
                if key not in ("Mounts", "RestartPolicy")) and
            host.get("RestartPolicy", {}).get("Name") == "unless-stopped" and
            not host.get("Privileged") and host.get("NetworkMode", "default") in ("default", "bridge"),
            "EXISTING_CONTAINER_SECURITY_ROUTING_OR_RESTART_DRIFT")
    mounts = live.get("Mounts", [])
    require(len(mounts) == 2 and
            sum(m.get("Type") == "volume" and m.get("Name") == value["state_volume"] and
                m.get("Destination") == "/var/lib/qikvrt/node" and m.get("RW") is True for m in mounts) == 1 and
            sum(m.get("Type") == "bind" and m.get("Source") == value["config_directory"] and
                m.get("Destination") == "/run/qikvrt" and m.get("RW") is False for m in mounts) == 1,
            "EXISTING_PRIVATE_VOLUME_OR_CONFIGURATION_MOUNT_DRIFT")
    state = live.get("State", {})
    require(not any(state.get(key) for key in ("Paused", "Dead", "Restarting")) and
            ((state.get("Running") is True and state.get("Status") == "running") or
             (state.get("Running") is False and state.get("Status") in ("created", "exited"))),
            "EXISTING_CONTAINER_NOT_RESUMABLE")


def deploy(value, image, engine):
    """Create-only initial delivery, or resume the exact existing container."""
    info = engine.call("GET", "/v1.45/info")
    require(info.get("OSType") == "linux" and info.get("ID") == value["daemon_id"], "AUTHENTICATED_LINUX_HOST_MISMATCH")
    volume = engine.call("GET", "/v1.45/volumes/" + value["state_volume"])
    require(volume.get("Driver") == "local" and volume.get("Scope") == "local" and
            volume.get("Labels", {}).get("de.qikvrt.repository") == REPOSITORY and
            not volume.get("Options"), "EXISTING_PERSISTENT_OWNER_VOLUME_REQUIRED")
    existing = engine.call("GET", "/v1.45/containers/json?all=true&filters=" +
                           urllib.parse.quote(json.dumps({"name": ["^/" + value["container_name"] + "$"]})))
    require(len(existing) <= 1, "SINGLE_EXISTING_NODE_REQUIRED")
    request = container_request(value, image)
    if existing:
        identifier = existing[0]["Id"]
        require(re.fullmatch(r"[a-f0-9]{64}", identifier), "ENGINE_CONTAINER_ID_REQUIRED")
        live = engine.call("GET", "/v1.45/containers/" + identifier + "/json")
        require(live.get("Config", {}).get("Image") == image and
                live["Config"].get("Labels", {}).get("de.qikvrt.binding-sha256") == sha(json.dumps(value, sort_keys=True).encode()),
                "EXISTING_NODE_REPLACEMENT_REQUIRES_S1_MIGRATION")
        existing_container(live, identifier, value, request)
    else:
        engine.call("POST", "/v1.45/images/create?fromImage=" + urllib.parse.quote(image, safe=""))
    observed = engine.call("GET", "/v1.45/images/" + urllib.parse.quote(image, safe="") + "/json")
    require(image in observed.get("RepoDigests", []), "REMOTE_IMAGE_DIGEST_MISMATCH")
    labels = observed.get("Config", {}).get("Labels", {})
    require(labels.get("org.opencontainers.image.revision") == value["source_head"] and
            labels.get("de.qikvrt.source-tree") == value["source_tree"], "REMOTE_SOURCE_BINDING_MISMATCH")
    if not existing:
        try:
            created = engine.call("POST", "/v1.45/containers/create?name=" + value["container_name"], request)
            identifier = created["Id"]
        except Exception:
            # An ambiguous create is read back once. It is never issued again.
            found = engine.call("GET", "/v1.45/containers/json?all=true&filters=" +
                                urllib.parse.quote(json.dumps({"name": ["^/" + value["container_name"] + "$"]})))
            require(len(found) == 1, "AMBIGUOUS_CREATE_REQUIRES_READBACK")
            identifier = found[0]["Id"]
            check = engine.call("GET", "/v1.45/containers/" + identifier + "/json")
            require(check.get("Config", {}).get("Labels") == request["Labels"] and
                    check.get("Config", {}).get("Image") == image, "AMBIGUOUS_CREATE_SUBJECT_MISMATCH")
    require(re.fullmatch(r"[a-f0-9]{64}", identifier), "ENGINE_CONTAINER_ID_REQUIRED")
    config_archive = engine.call("GET", "/v1.45/containers/" + identifier +
                                 "/archive?path=/run/qikvrt/config.json", binary=True)
    import io
    with tarfile.open(fileobj=io.BytesIO(config_archive), mode="r:*") as exported:
        files = [m for m in exported.getmembers() if m.isfile()]
        require(len(files) == 1 and files[0].uid == 10001 and files[0].gid == 10001 and
                files[0].mode == 0o600 and files[0].size < 65536, "PRIVATE_HOST_CONFIG_OWNERSHIP_REQUIRED")
        config_raw = exported.extractfile(files[0]).read()
    require(sha(config_raw) == value["config_sha256"], "HOST_CONFIG_DIGEST_MISMATCH")
    config = json.loads(config_raw)
    require(all(config.get(key) == value[key] for key in ("source_head", "source_tree", "node_id")) and
            config.get("source_repository") == REPOSITORY and config.get("host") == "0.0.0.0" and
            config.get("port") == 8080 and config.get("state_dir") == "/var/lib/qikvrt/node" and
            config.get("adapter") == "none" and config.get("terminal_profile") == "firefox",
            "HOST_NATIVE_CONFIGURATION_MISMATCH")
    package_archive = engine.call("GET", "/v1.45/containers/" + identifier +
                                  "/archive?path=/opt/qikvrt/MANIFEST.json", binary=True)
    with tarfile.open(fileobj=io.BytesIO(package_archive), mode="r:*") as exported:
        files = [m for m in exported.getmembers() if m.isfile()]
        require(len(files) == 1 and sha(exported.extractfile(files[0]).read()) == value["manifest_sha256"],
                "HOST_IMAGE_MANIFEST_PIN_MISMATCH")
    if existing:
        # Reobserve immediately before the sole effect. A concurrent start is
        # NOOP; changed storage/security is HOLD, never an update or recreation.
        live = engine.call("GET", "/v1.45/containers/" + identifier + "/json")
        existing_container(live, identifier, value, request)
        if live["State"]["Running"] is True:
            return {"state": "EXACT_EXISTING_CONTAINER_NOOP", "container_id": identifier, **value}
    try:
        engine.call("POST", "/v1.45/containers/" + identifier + "/start")
    except Exception:
        pass  # Only the authoritative GET below can establish start success.
    live = engine.call("GET", "/v1.45/containers/" + identifier + "/json")
    require(live.get("State", {}).get("Running") is True, "CONTAINER_START_NOT_OBSERVED")
    if existing:
        existing_container(live, identifier, value, request)
    for attempt in range(60):
        live = engine.call("GET", "/v1.45/containers/" + identifier + "/json")
        if existing:
            existing_container(live, identifier, value, request)
        state = live.get("State", {})
        require(state.get("Running") is True, "DEPLOYED_CONTAINER_EXITED")
        if state.get("Health", {}).get("Status") == "healthy":
            break
        require(state.get("Health", {}).get("Status") != "unhealthy", "DEPLOYED_CONTAINER_UNHEALTHY")
        time.sleep(1)
    else:
        raise ValueError("DEPLOYED_CONTAINER_HEALTH_NOT_OBSERVED")
    result = "EXACT_EXISTING_CONTAINER_RESUMED_PENDING_PUBLIC_ACCEPTANCE" if existing else "CONTAINER_STARTED_PENDING_PUBLIC_ACCEPTANCE"
    return {"state": result, "container_id": identifier, **value}


def public_readback(value, package):
    require(value["origin"] == ORIGIN, "EXACT_PRODUCT_ORIGIN_REQUIRED")
    observed = {}
    # Reuse the original observation GET before validating fresh durable state.
    for path in ("/api/activity", "/health", "/api/runtime", "/api/terminal", "/AI/"):
        raw = get(ORIGIN + path)
        observed[path] = {"status": 200, "sha256": sha(raw), "bytes": len(raw)}
        if path == "/api/runtime":
            runtime = json.loads(raw)
            require(all(runtime.get(key) == value[key] for key in
                        ("source_head", "source_tree", "manifest_sha256", "config_sha256", "node_id")),
                    "PUBLIC_RUNTIME_BINDING_MISMATCH")
        if path == "/api/terminal":
            terminal = json.loads(raw)
            require(terminal.get("state") == "NATIVE_TEMDD_READY" and
                    terminal.get("manifest_sha256") == value["manifest_sha256"], "PUBLIC_NATIVE_TERMINAL_NOT_READY")
    original = command("node", str(Path(package) / "tools/qikvrt_mesh_monitor_readback.mjs"),
                       "--self-host", str(package), ORIGIN, value["manifest_sha256"],
                       value["config_sha256"], value["node_id"], "none")
    return {"state": "EXACT_PUBLIC_CONTAINER_DELIVERY_VERIFIED", "source_head": value["source_head"],
            "source_tree": value["source_tree"], "image_digest": value["image_digest"],
            "origin": ORIGIN, "tls_hostname_validation": True, "http_readbacks": observed,
            "original_independent_readback_sha256": sha(original), "physical_iphone_verified": False,
            "native_multi_node_acceptance": False}


def smoke_origin(inspected, network):
    """Use the running fixture's isolated bridge address, never a public route."""
    require(inspected.get("State", {}).get("Running") is True, "SMOKE_CONTAINER_EXITED")
    require(inspected.get("HostConfig", {}).get("NetworkMode") == network,
            "EXACT_INTERNAL_FIXTURE_NETWORK_REQUIRED")
    address = inspected.get("NetworkSettings", {}).get("Networks", {}).get(network, {}).get("IPAddress", "")
    try:
        value = ipaddress.IPv4Address(address)
    except ipaddress.AddressValueError:
        raise ValueError("INTERNAL_FIXTURE_IPV4_REQUIRED") from None
    require(any(value in ipaddress.IPv4Network(block) for block in
                ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")),
            "PRIVATE_INTERNAL_FIXTURE_ADDRESS_REQUIRED")
    return "http://" + str(value) + ":8080"



def firefox_image_admission(image, output):
    """Actual final-image minimum, signed Standard payload and restart gate."""
    output=Path(output).absolute();output.mkdir(parents=True,exist_ok=True)
    evidence=output/'firefox-extension';evidence.mkdir(mode=0o777);evidence.chmod(0o777)
    xpi='/usr/lib/firefox/distribution/extensions/qikvrt-ai-terminal@goldkelch.local.xpi'
    command('docker','run','--rm','--init','--network','none','--user','10001:10001','--read-only',
        '--env','HOME=/tmp','--cap-drop','ALL','--security-opt','no-new-privileges:true','--shm-size','256m',
        '--tmpfs','/tmp:rw,nosuid,size=768m,mode=1777',
        '--mount','type=bind,source='+str(evidence)+',target=/evidence',
        '--entrypoint','python3',image,'-B','/opt/qikvrt/tools/qikvrt_self_host.py',
        'firefox-extension-check','--extension-xpi',xpi,'--firefox-package','firefox','--output','/evidence')
    from tools import qikvrt_self_host as host
    result=json.loads((evidence/'extension-installation.json').read_bytes())
    require(result.get('strict_min_version')=='158.0' and host.firefox_release_minimum_satisfied(result.get('firefox_version_output','')),
        'FINAL_IMAGE_FIREFOX_BELOW_OWNER_MINIMUM')
    phases=result.get('profiles',{}).get('default_signing_policy',[])
    require(result.get('state')=='EXTENSION_ACTIVATION_AND_RESTART_VERIFIED' and
        result.get('signed_production_package_verified') is True and
        result.get('extension_activation_verified') is True and len(phases)==2 and
        all(host.firefox_production_extension_accepted(phase) for phase in phases),
        'FINAL_IMAGE_MOZILLA_SIGNED_ACTIVATION_REQUIRED')
    raw=command('docker','run','--rm','--network','none','--entrypoint','cat',image,xpi)
    require(sha(raw)==result.get('xpi_sha256'),'FINAL_IMAGE_SIGNED_XPI_READBACK_MISMATCH')
    return result

def smoke(image, output):
    """Real unprivileged container, independent S1 readback and durable restart."""
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=True)
    firefox_image_admission(image, output)
    name = "qikvrt-s1-smoke-" + uuid.uuid4().hex[:16]
    config_volume, state_volume, network = name + "-config", name + "-state", name + "-net"
    manifest = json.loads(command("docker", "run", "--rm", "--network", "none", "--entrypoint", "cat", image,
                                  "/opt/qikvrt/MANIFEST.json"))
    pin = sha(command("docker", "run", "--rm", "--network", "none", "--entrypoint", "cat", image,
                      "/opt/qikvrt/MANIFEST.json"))
    config = {"schema": "qikvrt-self-host-config/v1", "node_id": "ci:s1-container", "adapter": "none",
              "source_head": manifest["source_head"], "source_tree": manifest["source_tree"],
              "source_repository": REPOSITORY, "state_dir": "/var/lib/qikvrt/node", "host": "0.0.0.0",
              "port": 8080, "terminal_port": 8771, "terminal_profile": "firefox", "subject_pr": 523,
              "terminal_token_file": "/run/qikvrt/terminal.token", "browser_password_file": "/run/qikvrt/browser.password",
              "novnc_port": 6080, "vnc_port": 5900, "display": ":99"}
    config_raw = json.dumps(config, sort_keys=True).encode()
    setup = ("import os,pathlib,secrets; p=pathlib.Path('/conf'); "
             "(p/'config.json').write_bytes(" + repr(config_raw) + "); "
             "(p/'terminal.token').write_text(secrets.token_hex(32)); "
             "(p/'browser.password').write_text(secrets.token_hex(4)); "
             "[(os.chown(str(f),10001,10001),f.chmod(0o600)) for f in p.iterdir()]; "
             "os.chown('/state',10001,10001); os.chmod('/state',0o700)")
    try:
        command("docker", "volume", "create", config_volume)
        command("docker", "volume", "create", state_volume)
        command("docker", "network", "create", "--internal", network)
        command("docker", "run", "--rm", "--network", "none", "--user", "0:0", "--entrypoint", "python3",
                "--mount", "type=volume,source=" + config_volume + ",target=/conf",
                "--mount", "type=volume,source=" + state_volume + ",target=/state", image, "-c", setup)
        command("docker", "run", "-d", "--name", name, "--init", "--network", network,
                "--user", "10001:10001", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                "--shm-size", "256m", "--tmpfs", "/tmp:rw,noexec,nosuid,size=768m,mode=1777",
                "--mount", "type=volume,source=" + config_volume + ",target=/run/qikvrt,readonly",
                "--mount", "type=volume,source=" + state_volume + ",target=/var/lib/qikvrt/node",
                image, "--config", "/run/qikvrt/config.json", "--manifest-sha256", pin)
        inspected = json.loads(command("docker", "inspect", name))[0]
        write_receipt(output / "smoke-fixture-network.json", {
            "state":"ISOLATED_FIXTURE_NETWORK_OBSERVED", "running":inspected.get("State", {}).get("Running"),
            "network_mode":inspected.get("HostConfig", {}).get("NetworkMode"),
            "ports":inspected.get("NetworkSettings", {}).get("Ports"),
            "networks":{key:{"IPAddress":value.get("IPAddress")} for key,value in
                        inspected.get("NetworkSettings", {}).get("Networks", {}).items()},
            "scope":"DISPOSABLE_CI_FIXTURE_ONLY", "public_production_verified":False})
        origin = smoke_origin(inspected, network)
        def ready():
            for attempt in range(60):
                state = json.loads(command("docker", "inspect", name))[0]["State"]
                require(state.get("Running"), "SMOKE_CONTAINER_EXITED")
                try:
                    terminal = json.loads(get(origin + "/api/terminal"))
                    if terminal.get("state") == "NATIVE_TEMDD_READY":
                        return terminal
                except (OSError, ValueError):
                    pass
                time.sleep(1)
            raise ValueError("SMOKE_READINESS_TIMEOUT")
        before = ready()
        observation = get(origin + "/api/activity")
        observed = json.loads(observation)
        require(observed.get("replication", {}).get("source_head") == manifest["source_head"] and
                observed.get("replication", {}).get("source_tree") == manifest["source_tree"],
                "INITIAL_OBSERVATION_SOURCE_BINDING_REQUIRED")
        (output / "smoke-initial-observation.json").write_bytes(observation)
        package = output / "public-package"
        command("docker", "cp", name + ":/opt/qikvrt", str(package))
        def readback(phase):
            try:
                original = command("node", str(package / "tools/qikvrt_mesh_monitor_readback.mjs"), "--self-host",
                                   str(package), origin, pin, sha(config_raw), config["node_id"], "none")
            except subprocess.CalledProcessError as error:
                # This disposable fixture contains synthetic configuration only.
                (output / ("smoke-readback-" + phase + ".stdout")).write_bytes((error.output or b"")[-30000:])
                (output / ("smoke-readback-" + phase + ".stderr")).write_bytes((error.stderr or b"")[-30000:])
                raise
            (output / ("smoke-readback-" + phase + ".stdout")).write_bytes(original[-30000:])
            return original
        first = readback("before-restart")
        require(b'data-qikvrt-source="node"' in get(origin + "/AI/"), "ACTUAL_TERMINAL_ENTRY_REQUIRED")
        command("docker", "restart", name)
        after = ready()
        second = readback("after-restart")
        require(before["ledger_id"] == after["ledger_id"], "DURABLE_LEDGER_ID_RESTART_MISMATCH")
        return {"state": "CONTAINER_SMOKE_AND_RESTART_VERIFIED", "source_head": manifest["source_head"],
                "source_tree": manifest["source_tree"], "manifest_sha256": pin, "image": image,
                "before_readback_sha256": sha(first), "after_readback_sha256": sha(second),
                "ledger_identity_preserved": True, "existing_native_event_restart_tests_required": True,
                "public_production_verified": False}
    except Exception:
        # Synthetic CI fixture only; no production logs/state are captured.
        logs = subprocess.run(["docker", "logs", name], capture_output=True, timeout=30)
        (output / "smoke-fixture-failure.log").write_bytes((logs.stdout + logs.stderr)[-30000:])
        raise
    finally:
        # Delete only this invocation's disposable fixture resources.
        for argv in (("docker", "rm", "-f", name), ("docker", "network", "rm", network),
                     ("docker", "volume", "rm", config_volume, state_volume)):
            subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)


def execute(args):
    operation = args.operation.removeprefix("container-")
    if operation == "artifact-split":
        result = artifact_split(args.carrier_archive, args.output, args.transport_sha256)
    elif operation == "artifact-join":
        result = artifact_join(args.root, args.output, args.manifest_sha256, args.transport_sha256)
    elif operation == "context":
        result = context(args.root, args.output)
    elif operation == "carrier":
        expected = json.loads((args.root / "runtime/self-host/CONTAINER_CARRIER.json").read_bytes())
        with tempfile.TemporaryDirectory() as temporary:
            archive = args.carrier_archive or Path(temporary) / "original-delivery.zip"
            if not args.carrier_archive:
                carrier_download(expected, archive)
            result = carrier_import(expected, archive, args.output)
            if getattr(args, "carrier_oci_archive", None):
                result["original_archive_oci"] = carrier_archive(expected, archive, args.carrier_oci_archive)
    elif operation == "carrier-archive-check":
        expected = json.loads((args.root / "runtime/self-host/CONTAINER_CARRIER.json").read_bytes())
        result = carrier_archive_check(expected, args.oci_archive)
    elif operation == "oci-check":
        result = oci(args.oci_archive, args.expected_head, args.expected_tree)
        if args.second_oci_archive:
            second = oci(args.second_oci_archive, args.expected_head, args.expected_tree)
            result["independent_rebuild_digest_equal"] = result["image_digest"] == second["image_digest"]
            result["independent_rebuild"] = second
            if not result["independent_rebuild_digest_equal"]:
                result["state"] = "HOLD_INDEPENDENT_OCI_REBUILD_DIGEST_MISMATCH"
                result["cause"] = "INDEPENDENT_OCI_REBUILD_DIGEST_MISMATCH"
                first = dict(result)
                result["first_build"], result["second_build"] = first, second
                result["differing_fields"] = sorted(key for key in second if first.get(key) != second[key])
                result["public_production_verified"] = False
                write_receipt(args.receipt, result)
                raise ValueError("INDEPENDENT_OCI_REBUILD_DIGEST_MISMATCH")
    elif operation == "smoke":
        result = smoke(args.image, args.output)
    elif operation == "production-gate":
        result = production_gate(args.expected_head)
    elif operation == "host-preflight":
        return host_preflight(args.expected_head, args.expected_tree, args.receipt)
    elif operation == "deploy":
        value = binding(args.production_binding.read_bytes(), args.binding_sha256, args.image)
        production_gate(value["source_head"])
        result = deploy(value, args.image, Engine(value["docker_api"], args.ca_file, args.cert_file, args.key_file))
    elif operation == "readback":
        result = public_readback(json.loads(args.production_binding.read_bytes()), args.root)
    else:
        raise ValueError("UNKNOWN_CONTAINER_OPERATION")
    return write_receipt(args.receipt, result)

