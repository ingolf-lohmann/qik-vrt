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
import subprocess
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
import zipfile
import io

REPOSITORY = "ingolf-lohmann/qik-vrt"
IMAGE = "ghcr.io/ingolf-lohmann/qik-vrt-s1"
ORIGIN = "https://raumzeitterminal.de"
ENVIRONMENT = "qikvrt-production"


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
    from tools.qikvrt_required_review_gate import evaluate_required_review
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
        decision = evaluate_required_review(live, rules, reviews, required_code_owner="Goldkelch")
        if decision["gate_state"] == "success":
            require(json.loads(get(base + "/branches/main", token))["commit"]["sha"] == head,
                    "MAIN_DRIFT_AFTER_ADMISSION")
            return {"state": "PRODUCTION_GOVERNANCE_ADMITTED", "source_head": head,
                    "review_id": decision["review_id"], "pr_number": pr["number"], "environment": ENVIRONMENT}
    raise ValueError("EXACT_MERGED_PR_INDEPENDENT_REVIEW_REQUIRED")


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


def deploy(value, image, engine):
    """Create-only initial delivery, or exact unchanged readback. Never cut over."""
    info = engine.call("GET", "/v1.45/info")
    require(info.get("OSType") == "linux" and info.get("ID") == value["daemon_id"], "AUTHENTICATED_LINUX_HOST_MISMATCH")
    volume = engine.call("GET", "/v1.45/volumes/" + value["state_volume"])
    require(volume.get("Driver") == "local" and volume.get("Scope") == "local" and
            volume.get("Labels", {}).get("de.qikvrt.repository") == REPOSITORY and
            not volume.get("Options"), "EXISTING_PERSISTENT_OWNER_VOLUME_REQUIRED")
    existing = engine.call("GET", "/v1.45/containers/json?all=true&filters=" +
                           urllib.parse.quote(json.dumps({"name": ["^/" + value["container_name"] + "$"]})))
    require(len(existing) <= 1, "SINGLE_EXISTING_NODE_REQUIRED")
    if existing:
        live = engine.call("GET", "/v1.45/containers/" + existing[0]["Id"] + "/json")
        require(live.get("Config", {}).get("Image") == image and live.get("State", {}).get("Running") is True and
                live["Config"].get("Labels", {}).get("de.qikvrt.binding-sha256") == sha(json.dumps(value, sort_keys=True).encode()),
                "EXISTING_NODE_REPLACEMENT_REQUIRES_S1_MIGRATION")
        return {"state": "EXACT_EXISTING_CONTAINER_NOOP", "container_id": live["Id"], **value}
    engine.call("POST", "/v1.45/images/create?fromImage=" + urllib.parse.quote(image, safe=""))
    observed = engine.call("GET", "/v1.45/images/" + urllib.parse.quote(image, safe="") + "/json")
    require(image in observed.get("RepoDigests", []), "REMOTE_IMAGE_DIGEST_MISMATCH")
    labels = observed.get("Config", {}).get("Labels", {})
    require(labels.get("org.opencontainers.image.revision") == value["source_head"] and
            labels.get("de.qikvrt.source-tree") == value["source_tree"], "REMOTE_SOURCE_BINDING_MISMATCH")
    request = {"Image": image, "User": "10001:10001",
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
    try:
        engine.call("POST", "/v1.45/containers/" + identifier + "/start")
    except Exception:
        pass  # Only the authoritative GET below can establish start success.
    live = engine.call("GET", "/v1.45/containers/" + identifier + "/json")
    require(live.get("State", {}).get("Running") is True, "CONTAINER_START_NOT_OBSERVED")
    for attempt in range(60):
        state = engine.call("GET", "/v1.45/containers/" + identifier + "/json").get("State", {})
        require(state.get("Running") is True, "DEPLOYED_CONTAINER_EXITED")
        if state.get("Health", {}).get("Status") == "healthy":
            break
        require(state.get("Health", {}).get("Status") != "unhealthy", "DEPLOYED_CONTAINER_UNHEALTHY")
        time.sleep(1)
    else:
        raise ValueError("DEPLOYED_CONTAINER_HEALTH_NOT_OBSERVED")
    return {"state": "CONTAINER_STARTED_PENDING_PUBLIC_ACCEPTANCE", "container_id": identifier, **value}


def public_readback(value, package):
    require(value["origin"] == ORIGIN, "EXACT_PRODUCT_ORIGIN_REQUIRED")
    observed = {}
    for path in ("/health", "/api/runtime", "/api/terminal", "/AI/"):
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


def smoke(image, output):
    """Real unprivileged container, independent S1 readback and durable restart."""
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=True)
    name = "qikvrt-s1-smoke-" + uuid.uuid4().hex[:16]
    config_volume, state_volume, network = name + "-config", name + "-state", name + "-net"
    manifest = json.loads(command("docker", "run", "--rm", "--network", "none", "--entrypoint", "cat", image,
                                  "/opt/qikvrt/MANIFEST.json"))
    pin = sha(command("docker", "run", "--rm", "--network", "none", "--entrypoint", "cat", image,
                      "/opt/qikvrt/MANIFEST.json"))
    config = {"schema": "qikvrt-self-host-config/v1", "node_id": "ci:s1-container", "adapter": "none",
              "source_head": manifest["source_head"], "source_tree": manifest["source_tree"],
              "source_repository": REPOSITORY, "state_dir": "/var/lib/qikvrt/node", "host": "0.0.0.0",
              "port": 8080, "terminal_port": 8771, "terminal_profile": "firefox", "subject_pr": 457,
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
                "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                "--shm-size", "256m", "--tmpfs", "/tmp:rw,noexec,nosuid,size=768m,mode=1777",
                "--mount", "type=volume,source=" + config_volume + ",target=/run/qikvrt,readonly",
                "--mount", "type=volume,source=" + state_volume + ",target=/var/lib/qikvrt/node",
                "-p", "127.0.0.1::8080", image, "--config", "/run/qikvrt/config.json", "--manifest-sha256", pin)
        inspected = json.loads(command("docker", "inspect", name))[0]
        port = inspected["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"]
        origin = "http://127.0.0.1:" + port
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
        package = output / "public-package"
        command("docker", "cp", name + ":/opt/qikvrt", str(package))
        def readback():
            return command("node", str(package / "tools/qikvrt_mesh_monitor_readback.mjs"), "--self-host",
                           str(package), origin, pin, sha(config_raw), config["node_id"], "none")
        first = readback()
        require(b'data-qikvrt-source="node"' in get(origin + "/AI/"), "ACTUAL_TERMINAL_ENTRY_REQUIRED")
        command("docker", "restart", name)
        after = ready()
        second = readback()
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
    if operation == "context":
        result = context(args.root, args.output)
    elif operation == "carrier":
        expected = json.loads((args.root / "runtime/self-host/CONTAINER_CARRIER.json").read_bytes())
        with tempfile.TemporaryDirectory() as temporary:
            archive = args.carrier_archive or Path(temporary) / "original-delivery.zip"
            if not args.carrier_archive:
                carrier_download(expected, archive)
            result = carrier_import(expected, archive, args.output)
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
    elif operation == "deploy":
        value = binding(args.production_binding.read_bytes(), args.binding_sha256, args.image)
        production_gate(value["source_head"])
        result = deploy(value, args.image, Engine(value["docker_api"], args.ca_file, args.cert_file, args.key_file))
    elif operation == "readback":
        result = public_readback(json.loads(args.production_binding.read_bytes()), args.root)
    else:
        raise ValueError("UNKNOWN_CONTAINER_OPERATION")
    return write_receipt(args.receipt, result)
