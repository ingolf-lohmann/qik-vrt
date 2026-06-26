#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Origin: QIK-VRT V38 remote format repair and dispatch attestation kit
# Rights-Holder: Ingolf Lohmann
# Project: QIK-VRT
# Source-Code-License: Apache-2.0
# Non-Source-Code-License: CC BY-NC 4.0 for non-code repository materials
# Notice: See RIGHTS.md / QIKVRT_LICENSE_AND_RIGHTS.md, LICENSE, NOTICE, and .q/lic/.
from __future__ import annotations
import base64, hashlib, json, os, shutil, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path.cwd()
STATE = ROOT / "e2e_state"
if STATE.exists():
    shutil.rmtree(STATE)
STATE.mkdir()
Path("audit").mkdir(exist_ok=True)

PORT = "8777"
TOKEN = "e2e-token"
env = os.environ.copy()
env.update({"PYTHONNOUSERSITE": "1", "QIKVRT_API_HOST": "127.0.0.1", "QIKVRT_API_PORT": PORT, "QIKVRT_API_TOKEN": TOKEN, "QIKVRT_REPO_ROOT": str(STATE)})

server = subprocess.Popen([sys.executable, "-S", "src/qikvrt_github_api_shim.py"], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def request(method, path, body=None, token=True):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + TOKEN
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try: parsed = json.loads(raw)
        except Exception: parsed = {"raw": raw}
        return e.code, parsed

try:
    health = None
    for _ in range(50):
        try:
            health = request("GET", "/health", token=False)
            if health[0] == 200:
                break
        except Exception:
            time.sleep(0.1)
    if not health or health[0] != 200:
        raise RuntimeError("server did not start")

    payload = b"QIKVRT TCP/IP E2E payload"
    sha = hashlib.sha256(payload).hexdigest()
    b64 = base64.b64encode(payload).decode("ascii")

    unauth = request("POST", "/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches", {"ref":"main","inputs":{"operation":"release_status","artifact_id":"status"}}, token=False)
    ingest = request("POST", "/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches", {"ref":"main","inputs":{"operation":"ingest","artifact_id":"e2e_payload","payload_b64":b64,"expected_sha256":sha,"dry_run":"false"}})
    verify = request("POST", "/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches", {"ref":"main","inputs":{"operation":"verify","artifact_id":"e2e_payload","expected_sha256":sha,"dry_run":"true"}})
    stage = request("POST", "/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches", {"ref":"main","inputs":{"operation":"stage","artifact_id":"status","dry_run":"true"}})
    rel = request("POST", "/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches", {"ref":"main","inputs":{"operation":"release_status","artifact_id":"status","dry_run":"true"}})
    bad = request("POST", "/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches", {"ref":"main","inputs":{"operation":"ingest","artifact_id":"bad_hash","payload_b64":b64,"expected_sha256":"0"*64,"dry_run":"true"}})
    repo_dispatch = request("POST", "/repos/owner/repo/dispatches", {"event_type":"qikvrt_mesh_api","client_payload":{"operation":"release_status","artifact_id":"status","dry_run":"true"}})

    audit_path = STATE / ".qikvrt" / "api" / "audit" / "events.jsonl"
    inbox_payload = STATE / ".qikvrt" / "api" / "inbox" / "e2e_payload.bin"
    audit_text = audit_path.read_text(encoding="utf-8") if audit_path.exists() else ""
    report = {
        "gate": "TCPIP_GITHUB_COMPATIBLE_API_E2E_GATE",
        "health": health,
        "unauthorized_status": unauth[0],
        "unauthorized_blocked": unauth[0] == 401,
        "ingest_status": ingest[0],
        "ingest_pass": ingest[0] == 202 and ingest[1]["handler_result"]["status"] == "PASS",
        "verify_status": verify[0],
        "verify_pass": verify[0] == 202 and verify[1]["handler_result"].get("sha256_match") is True,
        "stage_status": stage[0],
        "stage_pass": stage[0] == 202,
        "release_status": rel[0],
        "release_status_pass": rel[0] == 202 and rel[1]["handler_result"]["remote_byte_exact_asset_hash"] == "NOT_CONFIRMED",
        "bad_hash_status": bad[0],
        "bad_hash_blocked": bad[0] == 400 and bad[1]["handler_result"]["status"] == "BLOCK",
        "repository_dispatch_status": repo_dispatch[0],
        "repository_dispatch_pass": repo_dispatch[0] == 202,
        "payload_written": inbox_payload.exists() and inbox_payload.read_bytes() == payload,
        "audit_exists": audit_path.exists(),
        "audit_contains_ingest": '"event": "ingest"' in audit_text or '"event":"ingest"' in audit_text,
        "audit_contains_block": '"status": "BLOCK"' in audit_text or '"status":"BLOCK"' in audit_text,
    }
    report["pass"] = all([report["unauthorized_blocked"], report["ingest_pass"], report["verify_pass"], report["stage_pass"], report["release_status_pass"], report["bad_hash_blocked"], report["repository_dispatch_pass"], report["payload_written"], report["audit_exists"], report["audit_contains_ingest"], report["audit_contains_block"]])
    Path("audit/TCPIP_E2E_TEST_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["pass"] else 1)
finally:
    server.terminate()
    try: server.wait(timeout=3)
    except subprocess.TimeoutExpired: server.kill()
    out, err = server.communicate(timeout=3)
    Path("audit/TCPIP_SHIM_stdout.txt").write_text(out or "", encoding="utf-8")
    Path("audit/TCPIP_SHIM_stderr.txt").write_text(err or "", encoding="utf-8")
