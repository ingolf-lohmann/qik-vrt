# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Pinned, offline CPU inference behind the existing Personal REST adapter.

This owns a model subprocess, not a Mesh executor. No downloads, tool execution,
cloud fallback, automatic retry, promotion or autonomous authority are provided.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

try:
    from .qikvrt_personal_assistant import CapabilityBlock, MAX_BYTES, canonical
except ImportError:
    from qikvrt_personal_assistant import CapabilityBlock, MAX_BYTES, canonical

LOCK = Path(__file__).resolve().parents[1] / "runtime/models/smollm3-3b-q4-k-m.lock.json"
MODEL_ID = "qikvrt-smollm3-3b-q4-k-m"
PARAMETERS = {"temperature": 0, "seed": 1, "max_tokens": 512, "stream": False}


def verified_fd(directory: Path, artifact: dict) -> int:
    """Hash the same regular inode passed to the child, rather than reopen a path."""
    name = artifact["file"]
    if not isinstance(name, str) or name != Path(name).name or name in {".", ".."}:
        raise CapabilityBlock("LOCAL_MODEL_ARTIFACT_NAME_INVALID")
    path = directory / name
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise CapabilityBlock("LOCAL_MODEL_SYMLINK_REFUSED")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_mode & 0o022:
            raise CapabilityBlock("LOCAL_MODEL_ARTIFACT_PERMISSIONS_INVALID")
        if before.st_size != artifact["bytes"]:
            raise CapabilityBlock("LOCAL_MODEL_ARTIFACT_SIZE_MISMATCH")
        digest = hashlib.sha256()
        while raw := os.read(fd, 1024 * 1024):
            digest.update(raw)
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise CapabilityBlock("LOCAL_MODEL_ARTIFACT_CHANGED_DURING_VERIFICATION")
        if digest.hexdigest() != artifact["sha256"]:
            raise CapabilityBlock("LOCAL_MODEL_ARTIFACT_SHA256_MISMATCH")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except BaseException:
        os.close(fd)
        raise


class NoLocalRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CapabilityBlock("LOCAL_MODEL_REDIRECT_REFUSED")


class LocalModelTransport:
    """Linux x86_64 bundle; bounded child lifetime and authenticated loopback only."""
    def __init__(self, directory):
        self.process = None
        self.private = None
        self.log = None
        self.credential = secrets.token_urlsafe(48)
        self.opener = build_opener(ProxyHandler({}), NoLocalRedirect())
        if sys.platform != "linux" or os.uname().machine != "x86_64" or not directory:
            raise CapabilityBlock("PINNED_LOCAL_MODEL_LINUX_X86_64_BUNDLE_REQUIRED")
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        if lock.get("schema") != "qikvrt-local-llm-lock-v1" or lock.get("model_id") != MODEL_ID:
            raise CapabilityBlock("LOCAL_MODEL_LOCK_INVALID")
        self.binding = {"provider": "LOCAL_OFFLINE_CPU_LLAMA_CPP", "model": MODEL_ID,
                        "artifacts": {k: {a: lock[k][a] for a in ("file", "bytes", "sha256")}
                                      for k in ("model", "runtime")},
                        "parameters": PARAMETERS.copy(), "context_tokens": 4096, "threads": 2,
                        "tools": [], "normal_retention": "FULL_PRIVATE_LOCAL_TRANSCRIPT_NO_EXTERNAL_PROVIDER"}
        model_fd = archive_fd = None
        try:
            root = Path(directory).expanduser().absolute()
            if any(p.is_symlink() for p in [root, *root.parents]):
                raise CapabilityBlock("LOCAL_MODEL_SYMLINK_REFUSED")
            model_fd = verified_fd(root, lock["model"])
            archive_fd = verified_fd(root, lock["runtime"])
            self.private = tempfile.TemporaryDirectory(prefix="qikvrt-local-model-")
            private = Path(self.private.name)
            with os.fdopen(os.dup(archive_fd), "rb") as source, tarfile.open(fileobj=source, mode="r:gz") as archive:
                archive.extractall(private, filter="data")
            executable = private / lock["runtime"]["executable"]
            if not executable.is_file() or executable.is_symlink():
                raise CapabilityBlock("PINNED_LOCAL_MODEL_EXECUTABLE_MISSING")
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            self.base = "http://127.0.0.1:" + str(port)
            # Only this verified child receives the random key. No environment
            # inheritance, credential file, argv secret, shell, proxy or LD_PRELOAD.
            env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(private),
                   "LD_LIBRARY_PATH": str(executable.parent), "LLAMA_API_KEY": self.credential}
            self.log = (private / "server.log").open("wb")
            os.chmod(private / "server.log", 0o600)
            self.process = subprocess.Popen([
                str(executable), "--model", "/proc/self/fd/" + str(model_fd),
                "--alias", MODEL_ID, "--host", "127.0.0.1", "--port", str(port),
                "--offline", "--no-webui", "--ctx-size", "4096", "--parallel", "1",
                "--threads", "2", "--threads-batch", "2", "--n-predict", "512",
                "--reasoning-budget", "0", "--chat-template-kwargs", '{"enable_thinking":false}'
            ], stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT,
                env=env, pass_fds=(model_fd,), start_new_session=True)
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if not self.alive():
                    raise CapabilityBlock("LOCAL_MODEL_PROCESS_EXITED_DURING_STARTUP")
                try:
                    models, _ = self._request("/v1/models")
                    if MODEL_ID not in [m.get("id") for m in models.get("data", []) if isinstance(m, dict)]:
                        raise CapabilityBlock("LOCAL_MODEL_IDENTITY_MISMATCH")
                    return
                except CapabilityBlock as exc:
                    if str(exc) not in {"LOCAL_MODEL_HTTP_503_NO_RETRY", "LOCAL_MODEL_RESULT_UNRESOLVED_NO_RETRY"}:
                        raise
                    # Read-only startup readiness, never retry a generation.
                    time.sleep(0.1)
            raise CapabilityBlock("LOCAL_MODEL_STARTUP_TIMEOUT")
        except BaseException:
            self.close()
            raise
        finally:
            for fd in (model_fd, archive_fd):
                if fd is not None:
                    os.close(fd)

    def alive(self):
        return self.process is not None and self.process.poll() is None

    def close(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.log:
            self.log.close()
        if self.private:
            self.private.cleanup()

    def _request(self, path, payload=None):
        if path not in {"/v1/models", "/v1/chat/completions"}:
            raise CapabilityBlock("LOCAL_MODEL_OPERATION_REFUSED")
        raw = canonical(payload) if payload is not None else None
        if raw and (len(raw) > MAX_BYTES or self.credential.encode() in raw):
            raise CapabilityBlock("LOCAL_MODEL_REQUEST_TOO_LARGE_OR_CONTAINS_SECRET")
        request = Request(self.base + path, data=raw,
                          headers={"Authorization": "Bearer " + self.credential, "Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=120) as response:
                data = response.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise CapabilityBlock("LOCAL_MODEL_RESPONSE_TOO_LARGE")
                value = json.loads(data)
                if not isinstance(value, dict):
                    raise CapabilityBlock("LOCAL_MODEL_RESPONSE_NOT_OBJECT")
                return value, {"evidence_class": "LOCAL_CPU_MODEL_HTTP_RESPONSE",
                               "http_status": response.status, "response_sha256": hashlib.sha256(data).hexdigest()}
        except HTTPError as exc:
            raise CapabilityBlock("LOCAL_MODEL_HTTP_" + str(exc.code) + "_NO_RETRY") from None
        except (URLError, OSError, ValueError, http.client.HTTPException) as exc:
            if isinstance(exc, CapabilityBlock):
                raise
            raise CapabilityBlock("LOCAL_MODEL_RESULT_UNRESOLVED_NO_RETRY") from None

    def post(self, path, payload):
        if not self.alive():
            raise CapabilityBlock("LOCAL_MODEL_PROCESS_NOT_RUNNING_NO_RETRY")
        if (path != "/responses" or set(payload) != {"model", "messages", *PARAMETERS} or
                payload.get("model") != MODEL_ID or any(payload.get(k) != v for k, v in PARAMETERS.items())):
            raise CapabilityBlock("LOCAL_MODEL_REQUEST_OUTSIDE_BOUND_CONTRACT")
        value, receipt = self._request("/v1/chat/completions", payload)
        choices = value.get("choices")
        if (value.get("model") != MODEL_ID or not isinstance(choices, list) or len(choices) != 1 or
                not isinstance(choices[0], dict) or choices[0].get("finish_reason") != "stop"):
            raise CapabilityBlock("LOCAL_MODEL_RESULT_INCOMPLETE_OR_MODEL_MISMATCH")
        message = choices[0].get("message")
        if not isinstance(message, dict) or message.get("tool_calls") or not isinstance(message.get("content"), str):
            raise CapabilityBlock("LOCAL_MODEL_TEXT_ONLY_RESPONSE_REQUIRED")
        return {"id": value.get("id"), "model": MODEL_ID, "status": "completed",
                "output": [{"type": "message", "role": "assistant", "content": [
                    {"type": "output_text", "text": message["content"]}]}], "usage": value.get("usage")}, receipt
