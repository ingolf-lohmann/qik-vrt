#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Freeze and start the existing monitor/terminal carriers; no job executor."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import ipaddress
import json
import os
import platform
import re
import shutil
import signal
import socket
import stat
import struct
import time
import urllib.request
import urllib.parse
import subprocess
import sys
import tarfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFINITION = "runtime/self-host/PACKAGE.json"
BROWSER_COMMANDS = ("firefox-esr", "Xvfb", "x11vnc", "websockify", "xdpyinfo", "xwininfo")


def raw_json(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=30, stderr=subprocess.DEVNULL).strip()


def runtime(command):
    path = Path(shutil.which(command) or command).resolve(strict=True)
    version = subprocess.check_output([str(path), "--version"], timeout=5, stderr=subprocess.STDOUT,
                                      env={"PATH": os.environ.get("PATH", ""), "LANG": "C"}).decode().strip()
    return {"version": version, "executable_sha256": digest(path.read_bytes())}


def browser_executables():
    # Distribution-built tools use an exact executable binding, not a made-up
    # universal version. Actual package versions are retained by the image build.
    return {name: digest(Path(shutil.which(name) or name).resolve(strict=True).read_bytes())
            for name in BROWSER_COMMANDS}


def freeze(root, output, head, tree, browser_assets=None):
    """Export committed bytes only. Tar metadata is deterministic; no credentials."""
    if git(root, "rev-parse", "HEAD").decode() != head or git(root, "rev-parse", "HEAD^{tree}").decode() != tree:
        raise ValueError("EXACT_SOURCE_BINDING_MISMATCH")
    git(root, "diff", "--quiet", head, "--")
    definition = json.loads(git(root, "show", head + ":" + DEFINITION))
    node, python = runtime("node"), runtime(sys.executable)
    if not node["version"].startswith("v24.") or not python["version"].startswith("Python 3.12.") or sys.platform != "linux":
        raise ValueError("LINUX_NODE24_PYTHON312_REQUIRED")
    manifest = {"schema": "qikvrt-self-host-package/v1", "package_version": definition["version"],
                "source_repository": definition["source_repository"], "source_head": head, "source_tree": tree,
                "runtime": {"node": node, "python": python, "platform": platform.machine(), "system": "linux"},
                "files": {}, "effect_ack_done": False,
                "terminal_scope": "RECOVERED_HISTORICAL_TEMDD_DAEMON_AND_FIREFOX_NOVNC_SOURCES; SEALED_S1_ADAPTER",
                "native_terminal_daemon_included": definition.get("native_terminal_daemon_included", False)}
    if browser_assets is not None:
        manifest["browser_runtime"] = {"executables": browser_executables(), "files": [],
            "asset_origin": "OPERATOR_PROVISIONED_DEBIAN_NOVNC_SOURCE; EXACT_EXPORTED_BYTES",
            "firefox_version": subprocess.check_output([shutil.which("firefox-esr"), "--version"],
                timeout=10, stderr=subprocess.DEVNULL).decode().strip()}
        if not (browser_assets / "vnc.html").is_file() or not (browser_assets / "core/rfb.js").is_file():
            raise ValueError("COMPLETE_NOVNC_SOURCE_REQUIRED")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    try:
        for name in sorted(definition["files"]):
            if name.startswith("/") or ".." in Path(name).parts:
                raise ValueError("UNSAFE_PACKAGE_PATH")
            data = subprocess.check_output(["git", "-C", str(root), "cat-file", "blob", head + ":" + name], timeout=30)
            entry = git(root, "ls-tree", head, "--", name).decode().split()[0]
            if entry not in {"100644", "100755"}:
                raise ValueError("REGULAR_COMMITTED_FILES_REQUIRED")
            path = output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(0o755 if entry == "100755" else 0o644)
            manifest["files"][name] = {"bytes": len(data), "sha256": digest(data), "mode": entry}
        if browser_assets is not None:
            # Debian's noVNC tree contains distribution-managed JS links.
            # Freeze their resolved source bytes as regular files, with no key,
            # certificate, credential, VCS or executable payload admitted.
            suffixes = {".html", ".js", ".css", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico",
                        ".woff", ".woff2", ".ttf", ".eot", ".oga", ".ogg", ".wav", ".mp3", ".json", ".txt", ".map"}
            allowed = (browser_assets.resolve(), Path('/usr/share/javascript'), Path('/usr/share/nodejs'))
            def admitted(source):
                resolved = source.resolve(strict=True)
                if not any(resolved == root or root in resolved.parents for root in allowed):
                    raise ValueError("NOVNC_DISTRIBUTION_SOURCE_LINK_ESCAPED")
            sources = []
            for parent, directories, filenames in os.walk(browser_assets, followlinks=True):
                admitted(Path(parent))
                if len(Path(parent).relative_to(browser_assets).parts) > 16:
                    raise ValueError("NOVNC_SOURCE_LINK_CYCLE_OR_DEPTH")
                directories[:] = sorted(p for p in directories if not p.startswith('.'))
                sources.extend(Path(parent) / name for name in filenames)
                if len(sources) > 4096: raise ValueError("BOUNDED_NOVNC_FILESET_REQUIRED")
            for source in sorted(sources):
                relative = source.relative_to(browser_assets)
                if any(p.startswith(".") for p in relative.parts) or not source.is_file() or source.suffix not in suffixes:
                    continue
                admitted(source)
                data = source.read_bytes()
                if len(data) > 8 * 1024 * 1024: raise ValueError("BOUNDED_NOVNC_ASSET_REQUIRED")
                name = "runtime/self-host/novnc/" + relative.as_posix()
                dest = output / name; dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data); dest.chmod(0o644)
                manifest["files"][name] = {"bytes": len(data), "sha256": digest(data), "mode": "100644"}
                manifest["browser_runtime"]["files"].append(name)
            copyright_file = Path("/usr/share/doc/novnc/copyright")
            if not copyright_file.is_file(): raise ValueError("NOVNC_DISTRIBUTION_RIGHTS_REQUIRED")
            name = "runtime/self-host/novnc/DEBIAN_COPYRIGHT.txt"
            data = copyright_file.read_bytes(); (output / name).write_bytes(data); (output / name).chmod(0o644)
            manifest["files"][name] = {"bytes": len(data), "sha256": digest(data), "mode": "100644"}
            manifest["browser_runtime"]["files"].append(name)
            manifest["browser_runtime"]["files"].sort()
        data = raw_json(manifest)
        (output / "MANIFEST.json").write_bytes(data)
        (output / "MANIFEST.json").chmod(0o644)
        with tarfile.open(str(output) + ".tar", "w", format=tarfile.PAX_FORMAT) as archive:
            for path in sorted(p for p in output.rglob("*") if p.is_file()):
                info = archive.gettarinfo(str(path), path.relative_to(output).as_posix())
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ""
                with path.open("rb") as source:
                    archive.addfile(info, source)
        return {"state": "PACKAGE_FROZEN", "manifest_sha256": digest(data), "source_head": head,
                "source_tree": tree, "archive_sha256": digest(Path(str(output) + ".tar").read_bytes()),
                "effect_ack_done": False}
    except BaseException:
        shutil.rmtree(output)
        raise


def verify(package, expected):
    raw = (package / "MANIFEST.json").read_bytes()
    if not re.fullmatch(r"[a-f0-9]{64}", expected or "") or digest(raw) != expected:
        raise ValueError("PACKAGE_MANIFEST_PIN_MISMATCH")
    value = json.loads(raw)
    if value.get("schema") != "qikvrt-self-host-package/v1" or value.get("effect_ack_done") is not False:
        raise ValueError("PACKAGE_SCHEMA_MISMATCH")
    for key in ("source_head", "source_tree"):
        if not re.fullmatch(r"[a-f0-9]{40}", value.get(key, "")):
            raise ValueError("EXACT_SOURCE_BINDING_REQUIRED")
    actual = {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file() or p.is_symlink()}
    if actual != set(value["files"]) | {"MANIFEST.json"}:
        raise ValueError("PACKAGE_INVENTORY_MISMATCH")
    for name, entry in value["files"].items():
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("UNSAFE_PACKAGE_PATH")
        path = package / name
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("PACKAGE_SYMLINK_FORBIDDEN")
        raw = path.read_bytes()
        if (entry["bytes"] != len(raw) or entry["sha256"] != digest(raw)
                or stat.S_IMODE(path.stat().st_mode) != (0o755 if entry["mode"] == "100755" else 0o644)):
            raise ValueError("PACKAGE_ARTIFACT_MISMATCH")
    definition = json.loads((package / DEFINITION).read_bytes())
    browser = value.get("browser_runtime")
    if browser is not None and (not isinstance(browser, dict)
            or set(browser.get('executables', {})) != set(BROWSER_COMMANDS)
            or not isinstance(browser.get('files'), list)
            or len(browser['files']) != len(set(browser['files']))
            or not {'runtime/self-host/novnc/vnc.html', 'runtime/self-host/novnc/core/rfb.js',
                    'runtime/self-host/novnc/DEBIAN_COPYRIGHT.txt'} <= set(browser['files'])):
        raise ValueError("BROWSER_RUNTIME_SCHEMA_MISMATCH")
    extra = set(browser["files"]) if browser is not None else set()
    if any(not p.startswith("runtime/self-host/novnc/") for p in extra):
        raise ValueError("NOVNC_SOURCE_CONFINEMENT_REQUIRED")
    if set(value["files"]) != set(definition["files"]) | extra or definition["version"] != value["package_version"]:
        raise ValueError("PACKAGE_DEFINITION_MISMATCH")
    if browser is not None and browser["executables"] != browser_executables():
        raise ValueError("BROWSER_EXECUTABLE_BINDING_MISMATCH")
    if value["runtime"] != {"node": runtime("node"), "python": runtime(sys.executable),
                            "platform": platform.machine(), "system": sys.platform}:
        raise ValueError("RUNTIME_EXECUTABLE_BINDING_MISMATCH")
    return value


def private_path(path, directory=False):
    if not path.is_absolute() or ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("PRIVATE_PATH_MUST_BE_ABSOLUTE_AND_NOT_SYMLINKED")
    info = path.lstat()
    if (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))):
        raise ValueError("OWNER_ONLY_PRIVATE_PATH_REQUIRED")


def own_host_observation(volume):
    """Observe this Linux host/mount, without reading credentials or using a provider."""
    machine = Path("/etc/machine-id").read_bytes()
    if not re.fullmatch(rb"[a-f0-9]{32}\n?", machine) or machine.strip() == b"0" * 32:
        raise ValueError("OWN_HOST_MACHINE_ID_UNAVAILABLE")
    def unescape(value):
        return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), value)
    mounts = []
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        left, right = line.split(" - ", 1)
        fields, fs = left.split(), right.split()
        point = Path(unescape(fields[4]))
        if volume == point or point in volume.parents:
            mounts.append({"mount_point": str(point), "mount_root": unescape(fields[3]),
                "device_major_minor": fields[2], "filesystem": fs[0], "mount_source": unescape(fs[1])})
    if not mounts: raise ValueError("OWN_HOST_MOUNT_UNAVAILABLE")
    mount = max(mounts, key=lambda m: len(Path(m["mount_point"]).parts))
    if mount["filesystem"] in {"overlay", "tmpfs", "ramfs", "devtmpfs", "squashfs", "proc", "sysfs"}:
        raise ValueError("PERSISTENT_HOST_MOUNT_REQUIRED")
    return {"machine_id_sha256": digest(machine), "mount": mount}


def admission_plan(package, pin, config_path=None, admission_path=None, admission_pin=None):
    """Bind the existing launcher to pinned host declarations; never deploy or assert acceptance.

    An independently obtained admission pin binds the operator's declaration.
    Local identity/mount comparisons do not validate the external authorization,
    storage guarantees, control-plane capability, HTTPS route or review governance.
    """
    manifest = verify(package, pin)
    if config_path is None or admission_path is None:
        raise ValueError("HOLD_OWN_HOST_IDENTITY_STORAGE_ROUTING_UNAVAILABLE")
    private_path(config_path); private_path(admission_path)
    config_raw, admission_raw = config_path.read_bytes(), admission_path.read_bytes()
    if not re.fullmatch(r"[a-f0-9]{64}", admission_pin or "") or digest(admission_raw) != admission_pin:
        raise ValueError("HOST_ADMISSION_PIN_MISMATCH")
    config, admission = json.loads(config_raw), json.loads(admission_raw)
    fields = {"schema", "source_head", "source_tree", "manifest_sha256", "config_sha256", "node_id",
              "machine_id_sha256", "mount", "public_origin", "execution_operation", "supervisor_id",
              "authorization_evidence_sha256", "persistence_evidence_sha256", "https_routing_evidence_sha256"}
    if (set(admission) != fields or admission["schema"] != "qikvrt-own-host-admission/v1"
            or config.get("schema") != "qikvrt-self-host-config/v1"
            or config.get("adapter") != "none" or config.get("terminal_profile") not in {"temdd", "firefox"}
            or config.get("source_repository") != manifest["source_repository"]
            or type(config.get("subject_pr")) is not int or config["subject_pr"] < 1
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", config.get("node_id", ""))
            or "CHANGE_ME" in config["node_id"]
            or admission["manifest_sha256"] != pin or admission["config_sha256"] != digest(config_raw)
            or admission["node_id"] != config["node_id"]
            or any(admission[k] != manifest[k] or config.get(k) != manifest[k] for k in ("source_head", "source_tree"))):
        raise ValueError("HOST_ADMISSION_SUBJECT_MISMATCH")
    for field in ("authorization_evidence_sha256", "persistence_evidence_sha256", "https_routing_evidence_sha256"):
        if not re.fullmatch(r"[a-f0-9]{64}", admission.get(field) or ""):
            raise ValueError("HOST_ADMISSION_EVIDENCE_BINDINGS_REQUIRED")
    if any(not isinstance(admission.get(k), str) or not admission[k].strip()
            or len(admission[k]) > 256 or any(c in admission[k] for c in "\r\n\x00")
            for k in ("execution_operation", "supervisor_id")):
        raise ValueError("EXISTING_HOST_EXECUTION_AND_SUPERVISOR_REQUIRED")
    origin = admission.get("public_origin")
    if not isinstance(origin, str): raise ValueError("AUTHORIZED_PUBLIC_HTTPS_ORIGIN_REQUIRED")
    url = urllib.parse.urlsplit(origin)
    hostname = url.hostname or ""
    if (url.scheme != "https" or url.username or url.password or url.path or url.query or url.fragment
            or url.port not in {None, 443} or not hostname or hostname == "localhost"
            or hostname.endswith((".localhost", ".local", ".invalid", ".test", ".railway.app", ".vercel.app"))):
        raise ValueError("AUTHORIZED_PUBLIC_HTTPS_ORIGIN_REQUIRED")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
        tld = r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?"
        if len(hostname) > 253 or not re.fullmatch(r"(?:" + label + r"\.)+" + tld, hostname):
            raise ValueError("AUTHORIZED_PUBLIC_HTTPS_ORIGIN_REQUIRED")
    else:
        if not address.is_global: raise ValueError("AUTHORIZED_PUBLIC_HTTPS_ORIGIN_REQUIRED")
    volume = Path(config["state_dir"]); private_path(volume, directory=True)
    observed = own_host_observation(volume)
    if admission["machine_id_sha256"] != observed["machine_id_sha256"] or admission["mount"] != observed["mount"]:
        raise ValueError("OWN_HOST_IDENTITY_OR_MOUNT_MISMATCH")
    common = ["--root", str(package), "--manifest-sha256", pin]
    launcher = [str(Path(sys.executable).resolve()), "-B", str(package / "tools/qikvrt_self_host.py")]
    return {"schema": "qikvrt-own-host-launcher-binding/v1", "state": "HOST_LAUNCHER_BOUND_PENDING_EXTERNAL_ACCEPTANCE",
        "source_head": manifest["source_head"], "source_tree": manifest["source_tree"], "manifest_sha256": pin,
        "config_sha256": digest(config_raw), "node_id": config["node_id"], "admission_sha256": admission_pin,
        "admission_tool_sha256": digest(Path(__file__).read_bytes()),
        "local_identity_and_mount_match": True, "verify_argv": launcher + ["verify", *common],
        "run_argv": launcher + ["run", *common, "--config", str(config_path)],
        "readback_argv": [str(Path(shutil.which("node")).resolve()), str(package / "tools/qikvrt_mesh_monitor_readback.mjs"),
            "--self-host", str(package), origin, pin, digest(config_raw), config["node_id"], "none"],
        "execution_performed": False, "host_admission_verified": False, "public_readback_verified": False,
        "restart_verified": False, "review_governance_satisfied": False, "effect_ack_done": False,
        "remaining": ["validate independent host/control-plane, persistence and HTTPS authorization evidence",
            "use existing supervisor and exact verify/run argv on the admitted host",
            "fresh independent public readback, actual supervisor restart and byte-exact durable data readback",
            "separate current native review governance"]}


def supervisor_plan(package, pin, config_path, admission_path, admission_pin, tool_pin):
    """Materialize an existing systemd supervisor binding, never install a service."""
    tool = Path(__file__).resolve()
    if not re.fullmatch(r"[a-f0-9]{64}", tool_pin or "") or digest(tool.read_bytes()) != tool_pin:
        raise ValueError("ADMISSION_TOOL_PIN_MISMATCH")
    plan = admission_plan(package, pin, config_path, admission_path, admission_pin)
    admission = json.loads(admission_path.read_bytes())
    match = re.fullmatch(r"systemd:([A-Za-z0-9][A-Za-z0-9_.-]{0,90}\.service)", admission["supervisor_id"])
    if not match: raise ValueError("EXISTING_SYSTEMD_SERVICE_BINDING_REQUIRED")
    config = json.loads(config_path.read_bytes())
    # The main process's HOLD exit must not create an unattended restart loop.
    # Keep the same mount namespace: a private bind-remount would change the
    # mount descriptor that admit just compared with the operator declaration.
    def quoted(value, argv=False):
        if any(c in value for c in "\n\r\x00") or any(ord(c) < 32 for c in value):
            raise ValueError("UNSAFE_SYSTEMD_ARGUMENT")
        value = value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
        if argv: value = value.replace("$", "$$")
        return '"' + value + '"'
    point = admission["mount"]["mount_point"]
    if point == "/": mount_unit = "-.mount"
    else:
        escaped = ""
        for byte in point.strip("/").encode():
            char = chr(byte)
            escaped += "-" if char == "/" else char if char.isascii() and (char.isalnum() or char in "_:.") else "\\x%02x" % byte
        if escaped.startswith("."): escaped = "\\x2e" + escaped[1:]
        mount_unit = escaped + ".mount"
    command = [str(Path(sys.executable).resolve()), "-B", str(tool), "run-admitted",
        "--root", str(package), "--manifest-sha256", pin, "--config", str(config_path),
        "--admission", str(admission_path), "--admission-sha256", admission_pin,
        "--admission-tool-sha256", tool_pin]
    path = ":".join(dict.fromkeys([str(Path(shutil.which("node")).resolve().parent),
        str(Path(sys.executable).resolve().parent), "/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin", "/sbin", "/bin"]))
    unit = ("# Generated by the exact reviewed QIKVRT launcher; contains no token bytes.\n"
        "[Unit]\nDescription=QIKVRT pinned own-host node\n"
        "Wants=network-online.target\nAfter=network-online.target " + mount_unit + "\n"
        "BindsTo=" + mount_unit + "\nRequiresMountsFor=" + quoted(config["state_dir"]) + "\n"
        "StartLimitIntervalSec=300\nStartLimitBurst=5\n\n[Service]\nType=exec\n"
        "User=" + str(os.geteuid()) + "\nGroup=" + str(os.getegid()) + "\nUMask=0077\n"
        "Environment=" + quoted("PATH=" + path) + "\nNoNewPrivileges=yes\n"
        "ExecStart=" + " ".join(quoted(arg, argv=True) for arg in command) + "\n"
        "KillMode=control-group\nTimeoutStopSec=20\nSendSIGKILL=yes\n"
        "Restart=always\nRestartSec=3\nRestartPreventExitStatus=78\n\n"
        "[Install]\nWantedBy=multi-user.target " + mount_unit + "\n")
    path_name = match[1][:-8] + ".path"
    def path_value(p):
        # PathChanged is one raw absolute path, unlike ExecStart's argv parser.
        # Quotes would become literal path bytes. Refuse ambiguous unit syntax.
        value = str(p)
        if not re.fullmatch(r"/[A-Za-z0-9_./:$%+\-]+", value):
            raise ValueError("UNREPRESENTABLE_SYSTEMD_PATH")
        return value.replace("%", "%%")
    path_unit = ("# Retry only on a filesystem event; never repin or recreate state.\n"
        "[Unit]\nDescription=QIKVRT exact admission restoration events\n\n[Path]\n"
        + "".join("PathChanged=" + path_value(p) + "\n" for p in
            (config_path, admission_path, package / "MANIFEST.json", tool, Path("/etc/machine-id")))
        + "Unit=" + match[1] + "\nTriggerLimitIntervalSec=300\nTriggerLimitBurst=5\n\n"
        "[Install]\nWantedBy=multi-user.target\n")
    return {**plan, "schema": "qikvrt-own-host-supervisor-binding/v1",
        "state": "SYSTEMD_BINDING_PREPARED_NOT_INSTALLED", "unit_name": match[1], "unit_text": unit,
        "unit_sha256": digest(unit.encode()), "guard_argv": command,
        "path_unit_name": path_name, "path_unit_text": path_unit,
        "path_unit_sha256": digest(path_unit.encode()),
        "automatic_recovery": {"trigger": "PROCESS_EXIT_OR_BOOT", "supervisor": "EXISTING_SYSTEMD",
            "maximum_starts_per_300_seconds": 5, "hold_exit_status": 78,
            "every_start_rechecks_identity_mount_config_package": True,
            "cgroup_orphan_cleanup": True, "state_recreation_or_rebinding": False,
            "exact_admission_restoration_retry": "SYSTEMD_PATH_CHANGED_EVENT",
            "http_health_polling": False, "new_head_auto_deployment": False},
        "supervisor_installed": False, "live_recovery_verified": False}


def materialize_supervisor(plan, output):
    if not output.is_absolute() or any(p.is_symlink() for p in (output, *output.parents)) or ".." in output.parts:
        raise ValueError("ABSOLUTE_CREATE_ONLY_SUPERVISOR_OUTPUT_REQUIRED")
    output.mkdir(mode=0o700, exist_ok=False)
    try:
        for name, raw in ((plan["unit_name"], plan["unit_text"].encode()),
                          (plan["path_unit_name"], plan["path_unit_text"].encode()),
                          ("BINDING.json", raw_json({k: v for k, v in plan.items() if k not in {"unit_text", "path_unit_text"}}))):
            with (output / name).open("xb") as dest:
                os.chmod(dest.name, 0o600)
                dest.write(raw); dest.flush(); os.fsync(dest.fileno())
        fd = os.open(output, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    except BaseException:
        shutil.rmtree(output); raise
    return {k: v for k, v in plan.items() if k not in {"unit_text", "path_unit_text"}} | {"output_directory": str(output)}


def systemd_invocation(unit):
    """Match the current process to the existing host manager, not an env self-report."""
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise ValueError("ACTIVE_HOST_SYSTEMD_REQUIRED")
    command = '/usr/bin/systemctl'
    version = subprocess.check_output([command, '--version'], timeout=5).decode()
    match = re.match(r'systemd ([0-9]+)\b', version)
    if not match or int(match[1]) < 252: raise ValueError("SYSTEMD_252_OR_NEWER_REQUIRED")
    raw = subprocess.check_output([command, 'show', unit, '--property=MainPID,InvocationID'], timeout=5).decode()
    observed = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
    invocation = os.environ.get('INVOCATION_ID', '')
    if (not re.fullmatch(r'[a-f0-9]{32}', invocation) or observed.get('InvocationID') != invocation
            or observed.get('MainPID') != str(os.getpid())):
        raise ValueError("EXISTING_SYSTEMD_INVOCATION_BINDING_MISMATCH")
    return invocation


def run_admitted(package, pin, config_path, admission_path, admission_pin, tool_pin):
    # The reviewed guard can also launch an unchanged historical export. A
    # separate process executes that export's verifier before exec'ing its run.
    # exec preserves the systemd MainPID and cgroup; no second supervisor.
    plan = supervisor_plan(package, pin, config_path, admission_path, admission_pin, tool_pin)
    result = subprocess.run(plan["verify_argv"], capture_output=True, timeout=60)
    if result.returncode != 0 or json.loads(result.stdout).get("state") != "EXACT_PACKAGE_RUNTIME_VERIFIED":
        raise ValueError("INDEPENDENT_PACKAGE_VERIFY_FAILED")
    config = json.loads(config_path.read_bytes())
    binding = Path(config["state_dir"]) / "binding.json"
    if binding.exists() or binding.is_symlink():
        private_path(binding)
        expected = {"schema": "qikvrt-self-host-volume/v1", "node_id": plan["node_id"],
            "manifest_sha256": pin, "config_sha256": plan["config_sha256"],
            "source_head": plan["source_head"], "source_tree": plan["source_tree"]}
        if json.loads(binding.read_bytes()) != expected:
            raise ValueError("PERSISTENT_VOLUME_BINDING_MISMATCH")
    # Reobserve immediately before the effect; stale plan metadata is not an
    # authorization or a replacement for admission after a crash.
    supervisor_plan(package, pin, config_path, admission_path, admission_pin, tool_pin)
    invocation = systemd_invocation(plan['unit_name'])
    print(json.dumps({"state": "HOST_GUARD_VERIFIED_STARTING_EXISTING_LAUNCHER",
        "source_head": plan["source_head"], "source_tree": plan["source_tree"],
        "manifest_sha256": pin, "config_sha256": plan["config_sha256"],
        "admission_sha256": admission_pin, "admission_tool_sha256": tool_pin,
        "systemd_invocation_id": invocation, "existing_supervisor_pid_binding_match": True,
        "public_readback_verified": False, "effect_ack_done": False}, sort_keys=True), flush=True)
    os.execv(plan["run_argv"][0], plan["run_argv"])


def packaged_subject(package, pin, repository, pr, head, tree):
    """Verify an independently pinned export, without Git or a remote provider."""
    manifest = verify(package, pin)
    if (repository != manifest["source_repository"] or type(pr) is not int or pr < 1
            or head != manifest["source_head"] or tree != manifest["source_tree"]):
        raise ValueError("EXACT_PACKAGED_SUBJECT_MISMATCH")
    return {"repository": repository, "pr": pr, "head": head, "tree": tree}


def load_source(package, name):
    spec = importlib.util.spec_from_file_location(name, package / "src" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def native_carrier(package, pin, config, config_path, binding, token):
    """Reuse the recovered ledger/HTTP/Unix implementation; adapt only its source binding.

    The original Runtime requires Git. This new S1 adapter binds the sealed
    package/config/volume instead. Original source bytes remain unmodified.
    """
    native = load_source(package, "qikvrt_temdd_event_ledger")

    class SealedRuntime(native.Runtime):
        def __init__(self):
            self.root = package
            self.repository, self.pr = config["source_repository"], config["subject_pr"]
            self.subject = packaged_subject(package, pin, self.repository, self.pr,
                                            config["source_head"], config["source_tree"])
            self.ledger = native.Ledger(config["state_dir"], self.subject)
            self.subscribers = threading.BoundedSemaphore(32)

        def ensure_subject(self):
            try:
                packaged_subject(package, pin, self.repository, self.pr,
                                 self.subject["head"], self.subject["tree"])
                private_path(config_path)
                if digest(config_path.read_bytes()) != binding["config_sha256"]:
                    raise native.Hold("EXACT_CONFIGURATION_CHANGED")
                volume_binding = Path(config["state_dir"]) / "binding.json"
                private_path(volume_binding)
                if json.loads(volume_binding.read_bytes()) != binding:
                    raise native.Hold("PERSISTENT_VOLUME_BINDING_MISMATCH")
                if self.ledger.stopped:
                    raise native.Hold(self.ledger.reason)
            except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
                self.ledger.stop(str(exc))
                raise native.Hold(str(exc)) from exc
            return self.subject

    runtime_instance = SealedRuntime()
    ingress = server = None
    try:
        original_handler = native.make_handler(runtime_instance)

        class ReadOnlyHTTP(original_handler):
            def do_POST(self):
                self._hold("NATIVE_UNIX_INGRESS_REQUIRED", 405)

        ingress = native.make_ingress(runtime_instance)
        # Defense in depth for the existing mode-0600 owner-only ingress.
        def same_owner(request, _address):
            _, uid, _ = struct.unpack("3i", request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            return uid == os.geteuid()
        ingress.verify_request = same_owner
        server = ThreadingHTTPServer(("127.0.0.1", config["terminal_port"]), ReadOnlyHTTP)
        server.terminal_auth_token = token
        server.runtime_binding = binding
        return runtime_instance, ingress, server
    except BaseException:
        if server is not None: server.server_close()
        if ingress is not None: ingress.server_close()
        runtime_instance.ledger.close()
        raise


def novnc_readback(package, port):
    # A loopback startup read must never inherit a provider/proxy route.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:' + str(port) + '/vnc.html', timeout=2) as response:
        return response.status == 200 and response.read() == (package / 'runtime/self-host/novnc/vnc.html').read_bytes()


def browser_carrier(package, manifest, config, volume):
    """New portable start adapter of the recovered Firefox/Xvfb/VNC recipe.

    No downloader, provider, unsigned-addon exception or public listener.
    Browser profiles remain private; the existing host owns HTTPS admission.
    """
    if "browser_runtime" not in manifest: raise ValueError("BROWSER_PACKAGE_REQUIRED")
    password = Path(config["browser_password_file"]); private_path(password)
    secret = password.read_bytes().rstrip(b"\n")
    if len(secret) != 8 or any(c < 33 or c > 126 for c in secret):
        raise ValueError("EIGHT_ASCII_BYTE_PRIVATE_VNC_PASSWORD_REQUIRED")
    directory = volume / "browser"
    directory.mkdir(mode=0o700, exist_ok=True); private_path(directory, directory=True)
    for name in ("profile", "home", "cache", "logs"):
        (directory / name).mkdir(mode=0o700, exist_ok=True); private_path(directory / name, directory=True)
    env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "DISPLAY": config["display"],
        "HOME": str(directory / "home"), "XDG_CACHE_HOME": str(directory / "cache"),
        "XDG_CONFIG_HOME": str(directory / "home")}
    processes, logs = [], []
    def spawn(name, argv):
        path = directory / "logs" / (name + ".log")
        if path.exists() or path.is_symlink(): private_path(path)
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        log = os.fdopen(fd, "wb"); logs.append(log)
        p = subprocess.Popen(argv, env=env, cwd=directory, stdout=log, stderr=log)
        processes.append(p); return p
    def ready(check, edge):
        until = time.monotonic() + 20
        while time.monotonic() < until:
            if any(p.poll() is not None for p in processes): raise ValueError("BROWSER_CHILD_EXITED")
            try:
                if check(): return
            except (OSError, ValueError, subprocess.SubprocessError): pass
            time.sleep(.05)  # bounded startup probe, no runtime polling
        raise ValueError("BROWSER_STARTUP_READBACK_TIMEOUT:" + edge)
    try:
        spawn("xvfb", [shutil.which("Xvfb"), config["display"], "-screen", "0", "1440x900x24", "-nolisten", "tcp"])
        ready(lambda: subprocess.run([shutil.which("xdpyinfo"), "-display", config["display"]],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2).returncode == 0, 'X11_DISPLAY')
        spawn("vnc", [shutil.which("x11vnc"), "-display", config["display"], "-forever", "-shared", "-localhost",
            "-no6", "-rfbportv6", "0", "-rfbport", str(config["vnc_port"]), "-passwdfile", str(password)])
        spawn("novnc", [shutil.which("websockify"), "--web=" + str(package / "runtime/self-host/novnc"),
            "127.0.0.1:" + str(config["novnc_port"]), "127.0.0.1:" + str(config["vnc_port"])])
        spawn("firefox", [shutil.which("firefox-esr"), "--no-remote", "--profile", str(directory / "profile"),
            "http://127.0.0.1:" + str(config["terminal_port"]) + "/AI"])
        def browser_window():
            raw = subprocess.check_output([shutil.which("xwininfo"), "-display", config["display"], "-root", "-tree"],
                env=env, timeout=2).decode()
            title = re.search(r'<title>([^<]+)</title>', (package / 'docs/terminal/temdd/index.html').read_text())[1]
            return '"Navigator" "firefox' in raw and '"' + title in raw
        ready(browser_window, 'FIREFOX_NATIVE_DOCUMENT')
        ready(lambda: novnc_readback(package, config['novnc_port']), 'NOVNC_HTTP')
        return processes, logs
    except BaseException:
        stop_children(processes, logs)
        raise


def stop_children(processes, logs=()):
    for p in processes:
        if p.poll() is None: p.terminate()
    for p in processes:
        try: p.wait(timeout=5)
        except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=2)
    for log in logs: log.close()


def start(package, pin, config_path):
    manifest = verify(package, pin)
    private_path(config_path)
    raw = config_path.read_bytes()
    config = json.loads(raw)
    fields = {"schema", "node_id", "source_head", "source_tree", "adapter", "state_dir", "host", "port", "terminal_port", "terminal_token_file", "github_webhook_secret_file", "terminal_profile", "subject_pr", "source_repository", "browser_password_file", "novnc_port", "vnc_port", "display"}
    if (set(config) - fields or config.get("schema") != "qikvrt-self-host-config/v1"
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", config.get("node_id", ""))
            or config.get("adapter") not in {"none", "github"} or config.get("host") not in {"127.0.0.1", "0.0.0.0"}
            or any(type(config.get(k)) is not int or not 1 <= config[k] <= 65535 for k in ("port", "terminal_port"))
            or config["port"] == config["terminal_port"]
            or any(config.get(k) != manifest[k] for k in ("source_head", "source_tree"))):
        raise ValueError("START_CONFIGURATION_BINDING_MISMATCH")
    profile = config.get("terminal_profile", "reference")
    if profile not in {"reference", "temdd", "firefox"}:
        raise ValueError("UNKNOWN_TERMINAL_PROFILE")
    if profile != "reference" and (type(config.get("subject_pr")) is not int or config["subject_pr"] < 1
            or config.get("source_repository") != manifest["source_repository"]
            or manifest.get("native_terminal_daemon_included") is not True):
        raise ValueError("EXACT_NATIVE_TERMINAL_SUBJECT_REQUIRED")
    if profile == "firefox" and ("browser_runtime" not in manifest
            or not re.fullmatch(r":[1-9][0-9]{0,3}", config.get("display", ""))
            or any(type(config.get(k)) is not int or not 1 <= config[k] <= 65535 for k in ("novnc_port", "vnc_port"))
            or len({config[k] for k in ("port", "terminal_port", "novnc_port", "vnc_port")}) != 4
            or not config.get("browser_password_file")):
        raise ValueError("EXACT_BROWSER_CONFIGURATION_REQUIRED")
    if config["adapter"] == "github":
        try:
            if runtime("gh")["version"].splitlines()[0].split()[:3] != ["gh", "version", "2.96.0"]:
                raise ValueError("GITHUB_ADAPTER_REQUIRES_LOCKED_GH")
        except OSError as exc:
            raise ValueError("GITHUB_ADAPTER_REQUIRES_LOCKED_GH") from exc
        if not config.get("github_webhook_secret_file"):
            raise ValueError("PRIVATE_GITHUB_WEBHOOK_SECRET_REQUIRED")
        secret = Path(config["github_webhook_secret_file"])
        private_path(secret)
        if not 32 <= len(secret.read_bytes().strip()) <= 256:
            raise ValueError("BOUNDED_PRIVATE_GITHUB_WEBHOOK_SECRET_REQUIRED")
    if config["adapter"] == "none" and config.get("github_webhook_secret_file"):
        raise ValueError("GITHUB_SECRET_WITHOUT_GITHUB_ADAPTER")
    token_file = Path(config["terminal_token_file"])
    private_path(token_file)
    token = token_file.read_text().strip()
    if len(token) < 32 or len(token) > 256 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError("BOUNDED_TERMINAL_SECRET_REQUIRED")
    volume = Path(config["state_dir"])
    private_path(volume, directory=True)
    if volume == package or package in volume.parents or volume in package.parents:
        raise ValueError("STATE_VOLUME_MUST_BE_SEPARATE_FROM_PACKAGE")
    for name in ("monitor", "temdd", "receipts"):
        (volume / name).mkdir(mode=0o700, exist_ok=True)
        private_path(volume / name, directory=True)
    lock_fd = os.open(volume / "node.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, "w") as lock:
        private_path(volume / "node.lock")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        binding = {"schema": "qikvrt-self-host-volume/v1", "node_id": config["node_id"], "manifest_sha256": pin,
                   "config_sha256": digest(raw), "source_head": manifest["source_head"], "source_tree": manifest["source_tree"]}
        bound_path = volume / "binding.json"
        if bound_path.exists() or bound_path.is_symlink():
            private_path(bound_path)
            if json.loads(bound_path.read_bytes()) != binding:
                raise ValueError("PERSISTENT_VOLUME_BINDING_MISMATCH")
        else:
            with bound_path.open("xb") as dest:
                os.chmod(bound_path, 0o600)
                dest.write(raw_json(binding)); dest.flush(); os.fsync(dest.fileno())
            fd = os.open(volume, os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
        for file in (volume / "monitor").iterdir():
            private_path(file)
        terminal = load_source(package, "qikvrt_effect_ack_http_terminal")
        native_runtime = ingress = None
        if profile == "reference":
            server = ThreadingHTTPServer(("127.0.0.1", config["terminal_port"]), terminal.Handler)
        else:
            native_runtime, ingress, server = native_carrier(package, pin, config, config_path, binding, token)
        server.terminal_auth_token = token
        server.runtime_binding = binding
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        ingress_thread = None
        if ingress is not None:
            ingress_thread = threading.Thread(target=ingress.serve_forever, daemon=True)
            ingress_thread.start()
        env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "QIKVRT_NODE_CONFIG": str(config_path),
               "QIKVRT_NODE_PACKAGE": str(package), "QIKVRT_NODE_MANIFEST_SHA256": pin,
               "QIKVRT_NODE_CONFIG_SHA256": digest(raw)}
        process = None
        browser_processes, browser_logs = [], []
        def stop(_signum, _frame):
            if process is not None and process.poll() is None:
                process.terminate()
        old_handlers = {s: signal.signal(s, stop) for s in (signal.SIGINT, signal.SIGTERM)}
        try:
            if profile == "firefox":
                browser_processes, browser_logs = browser_carrier(package, manifest, config, volume)
            # flock belongs to the shared open-file description. Keep it in
            # the monitor too, so an isolated launcher SIGKILL cannot admit a
            # second writer while the original monitor is still running.
            process = subprocess.Popen([shutil.which("node"), str(package / "docs/monitor/self-host.mjs")],
                                       cwd=package, env=env, pass_fds=(lock.fileno(),))
            if browser_processes:
                # Linux pidfds wait for actual child exits without timed polls.
                import select
                fds = [os.pidfd_open(p.pid) for p in [process, *browser_processes]]
                try:
                    select.select(fds, [], [])
                    if any(p.poll() is not None for p in browser_processes):
                        raise ValueError("BROWSER_CHILD_EXITED_AFTER_READINESS")
                    return process.wait()
                finally:
                    for fd in fds: os.close(fd)
            return process.wait()
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
            server.shutdown(); server.server_close(); thread.join(timeout=2)
            stop_children(browser_processes, browser_logs)
            if ingress is not None:
                native_runtime.ledger.stop()
                ingress.shutdown(); ingress.server_close(); ingress_thread.join(timeout=6)
                native_runtime.ledger.close()
            for s, handler in old_handlers.items(): signal.signal(s, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("pack", "verify", "run", "admit", "supervisor", "run-admitted"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-head")
    parser.add_argument("--expected-tree")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--admission", type=Path, help="private operator host declaration; no secrets")
    parser.add_argument("--admission-sha256", help="independently obtained host declaration pin")
    parser.add_argument("--admission-tool-sha256", help="independently reviewed guard pin; required for supervisor operations")
    parser.add_argument("--browser-assets-root", type=Path, help="explicit provisioned noVNC source tree; freeze a Firefox-capable variant")
    args = parser.parse_args()
    try:
        if args.operation == "pack":
            if not args.output or not args.expected_head or not args.expected_tree: raise ValueError("EXACT_EXPORT_INPUTS_REQUIRED")
            result = freeze(args.root, args.output, args.expected_head, args.expected_tree, args.browser_assets_root)
        elif args.operation == "verify":
            verify(args.root, args.manifest_sha256)
            result = {"state": "EXACT_PACKAGE_RUNTIME_VERIFIED", "effect_ack_done": False}
        elif args.operation == "admit":
            result = admission_plan(args.root.resolve(), args.manifest_sha256, args.config,
                                    args.admission, args.admission_sha256)
        elif args.operation == "supervisor":
            if not args.output: raise ValueError("CREATE_ONLY_SUPERVISOR_OUTPUT_REQUIRED")
            plan = supervisor_plan(args.root.resolve(), args.manifest_sha256, args.config,
                                   args.admission, args.admission_sha256, args.admission_tool_sha256)
            result = materialize_supervisor(plan, args.output)
        elif args.operation == "run-admitted":
            run_admitted(args.root.resolve(), args.manifest_sha256, args.config,
                         args.admission, args.admission_sha256, args.admission_tool_sha256)
            raise ValueError("ORIGINAL_LAUNCHER_EXEC_REQUIRED")
        else:
            if not args.config: raise ValueError("PRIVATE_START_CONFIGURATION_REQUIRED")
            return start(args.root.resolve(), args.manifest_sha256, args.config.absolute())
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"state": "HOLD", "cause": str(exc), "effect_ack_done": False}, sort_keys=True))
        return 78 if args.operation == "run-admitted" else 2


if __name__ == "__main__":
    raise SystemExit(main())
