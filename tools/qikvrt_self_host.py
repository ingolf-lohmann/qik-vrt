#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Freeze and start the existing monitor/terminal carriers; no job executor."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
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
    parser.add_argument("operation", choices=("pack", "verify", "run"))
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-head")
    parser.add_argument("--expected-tree")
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--browser-assets-root", type=Path, help="explicit provisioned noVNC source tree; freeze a Firefox-capable variant")
    args = parser.parse_args()
    try:
        if args.operation == "pack":
            if not args.output or not args.expected_head or not args.expected_tree: raise ValueError("EXACT_EXPORT_INPUTS_REQUIRED")
            result = freeze(args.root, args.output, args.expected_head, args.expected_tree, args.browser_assets_root)
        elif args.operation == "verify":
            verify(args.root, args.manifest_sha256)
            result = {"state": "EXACT_PACKAGE_RUNTIME_VERIFIED", "effect_ack_done": False}
        else:
            if not args.config: raise ValueError("PRIVATE_START_CONFIGURATION_REQUIRED")
            return start(args.root.resolve(), args.manifest_sha256, args.config.absolute())
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"state": "HOLD", "cause": str(exc), "effect_ack_done": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
