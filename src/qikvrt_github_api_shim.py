#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qikvrt_api_handler import HandlerConfig, run_handler

DISPATCH_RE = re.compile(r"^/repos/([^/]+)/([^/]+)/actions/workflows/qikvrt_mesh_api\.yml/dispatches$")
REPO_DISPATCH_RE = re.compile(r"^/repos/([^/]+)/([^/]+)/dispatches$")

class QikvrtGitHubApiShim(BaseHTTPRequestHandler):
    server_version = "QIKVRTGitHubApiShim/1.0"

    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length", "0") or "0")
        if n > 1024 * 1024:
            raise ValueError("request too large")
        raw = self.rfile.read(n)
        return {} if not raw else json.loads(raw.decode("utf-8"))

    def _authorized(self) -> bool:
        token = os.environ.get("QIKVRT_API_TOKEN", "local-dev-token")
        if not token:
            return True
        return self.headers.get("Authorization", "") == f"Bearer {token}"

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "PASS", "service": "QIKVRT GitHub-Compatible REST API Shim", "tcpip": True, "github_compatible_dispatch": True})
            return
        self._send_json(404, {"status": "BLOCK", "reason": "not found"})

    def do_POST(self):
        if not self._authorized():
            self._send_json(401, {"status": "BLOCK", "reason": "unauthorized"})
            return
        parsed = urlparse(self.path)
        m = DISPATCH_RE.match(parsed.path)
        mr = REPO_DISPATCH_RE.match(parsed.path)
        if not (m or mr):
            self._send_json(404, {"status": "BLOCK", "reason": "unknown endpoint"})
            return
        try:
            body = self._read_json()
            if m:
                owner, repo = m.group(1), m.group(2)
                inputs = body.get("inputs", {})
            else:
                owner, repo = mr.group(1), mr.group(2)
                inputs = body.get("client_payload", {}) if isinstance(body.get("client_payload", {}), dict) else {}
            cfg = HandlerConfig(
                root=Path(os.environ.get("QIKVRT_REPO_ROOT", os.getcwd())),
                operation=str(inputs.get("operation", "")),
                artifact_id=str(inputs.get("artifact_id", "")),
                payload_b64=str(inputs.get("payload_b64", "")),
                expected_sha256=str(inputs.get("expected_sha256", "")),
                dry_run=str(inputs.get("dry_run", "true")).lower() != "false",
                repository=f"{owner}/{repo}",
                run_id="local-tcpip-shim",
            )
            result = run_handler(cfg)
            status = 202 if result.get("status") in ("PASS", "NOT_FOUND") else 400
            self._send_json(status, {"status": "ACCEPTED" if status == 202 else "BLOCK", "handler_result": result})
        except Exception as e:
            self._send_json(400, {"status": "BLOCK", "reason": str(e)})

    def log_message(self, fmt, *args):
        if os.environ.get("QIKVRT_API_LOG", "0") == "1":
            super().log_message(fmt, *args)

def main() -> int:
    host = os.environ.get("QIKVRT_API_HOST", "127.0.0.1")
    port = int(os.environ.get("QIKVRT_API_PORT", "8766"))
    if host != "127.0.0.1" and os.environ.get("QIKVRT_ALLOW_NON_LOOPBACK") != "1":
        print("BLOCK non-loopback requires QIKVRT_ALLOW_NON_LOOPBACK=1", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((host, port), QikvrtGitHubApiShim)
    print(json.dumps({"status": "PASS", "listening": f"{host}:{port}"}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
