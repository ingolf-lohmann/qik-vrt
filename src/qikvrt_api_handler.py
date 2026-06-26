#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SAFE_ID = re.compile(r"^[A-Za-z0-9_.=-]{1,128}$")
SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")

@dataclass
class HandlerConfig:
    root: Path
    operation: str
    artifact_id: str
    payload_b64: str
    expected_sha256: str
    dry_run: bool
    repository: str = "local/qik-vrt"
    run_id: str = "local-run"

def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def safe_id(raw: str) -> str:
    if not raw or not SAFE_ID.match(raw):
        raise ValueError("BLOCK unsafe or missing artifact_id")
    return raw

def require_sha(raw: str) -> str:
    if not raw or not SHA256_HEX.match(raw):
        raise ValueError("BLOCK expected_sha256 must be 64 hex chars")
    return raw.lower()

def dirs(root: Path) -> dict[str, Path]:
    state = root / ".qikvrt" / "api"
    d = {"state": state, "inbox": state / "inbox", "audit": state / "audit", "out": state / "out"}
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return d

def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def append_audit(root: Path, event: dict[str, Any]) -> None:
    d = dirs(root)
    event = dict(event)
    event.setdefault("time", utc_now())
    with (d["audit"] / "events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

def git_commit(root: Path, paths: list[str], message: str, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"status": "DRY_RUN", "git_invoked": False, "paths": paths, "message": message}
    if not (root / ".git").exists():
        return {"status": "LOCAL_WRITE_NO_GIT_REPO", "git_invoked": False, "paths": paths, "message": message}
    subprocess.run(["git", "config", "user.name", "qikvrt-api"], cwd=root, check=True, timeout=10)
    subprocess.run(["git", "config", "user.email", "actions@users.noreply.github.com"], cwd=root, check=True, timeout=10)
    subprocess.run(["git", "add", *paths], cwd=root, check=True, timeout=10)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root, timeout=10)
    if diff.returncode == 0:
        return {"status": "NO_CHANGES", "git_invoked": True, "paths": paths}
    subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, timeout=20)
    if os.environ.get("QIKVRT_SKIP_GIT_PUSH", "0") == "1":
        return {"status": "COMMIT_NO_PUSH", "git_invoked": True, "paths": paths, "message": message}
    subprocess.run(["git", "push"], cwd=root, check=True, timeout=30)
    return {"status": "PASS", "git_invoked": True, "paths": paths, "message": message}

def op_ingest(cfg: HandlerConfig) -> dict[str, Any]:
    artifact_id = safe_id(cfg.artifact_id)
    expected = require_sha(cfg.expected_sha256)
    try:
        payload = base64.b64decode(cfg.payload_b64.encode("utf-8"), validate=True)
    except Exception as e:
        raise ValueError("BLOCK invalid base64 payload") from e
    actual = sha256_bytes(payload)
    if actual != expected:
        raise ValueError(f"BLOCK sha256 mismatch actual={actual} expected={expected}")
    d = dirs(cfg.root)
    target = d["inbox"] / f"{artifact_id}.bin"
    sidecar = d["inbox"] / f"{artifact_id}.bin.sha256"
    meta = d["inbox"] / f"{artifact_id}.meta.json"
    if not cfg.dry_run:
        target.write_bytes(payload)
        sidecar.write_text(f"{actual}  {target.name}\n", encoding="utf-8")
        write_json(meta, {"artifact_id": artifact_id, "sha256": actual, "size": len(payload), "ingested_at": utc_now(), "status": "INGESTED", "repository": cfg.repository, "run_id": cfg.run_id})
    return {
        "operation": "ingest",
        "artifact_id": artifact_id,
        "sha256": actual,
        "size": len(payload),
        "write_status": "DRY_RUN" if cfg.dry_run else "WRITTEN",
        "commit": git_commit(cfg.root, [str(target.relative_to(cfg.root)), str(sidecar.relative_to(cfg.root)), str(meta.relative_to(cfg.root)), ".qikvrt/api/audit/events.jsonl"], f"QIKVRT API ingest {artifact_id}", cfg.dry_run),
        "status": "PASS",
    }

def op_verify(cfg: HandlerConfig) -> dict[str, Any]:
    artifact_id = safe_id(cfg.artifact_id)
    expected = require_sha(cfg.expected_sha256)
    target = dirs(cfg.root)["inbox"] / f"{artifact_id}.bin"
    if not target.exists():
        return {"operation": "verify", "artifact_id": artifact_id, "status": "NOT_FOUND", "sha256_match": False}
    actual = sha256_bytes(target.read_bytes())
    return {"operation": "verify", "artifact_id": artifact_id, "actual_sha256": actual, "expected_sha256": expected, "sha256_match": actual == expected, "status": "PASS" if actual == expected else "BLOCK"}

def op_stage(cfg: HandlerConfig) -> dict[str, Any]:
    d = dirs(cfg.root)
    entries = [{"path": str(p.relative_to(cfg.root)), "size": p.stat().st_size, "sha256": sha256_bytes(p.read_bytes())} for p in sorted(d["inbox"].glob("*.bin"))]
    stage_manifest = d["out"] / "stage_manifest.json"
    if not cfg.dry_run:
        write_json(stage_manifest, {"generated_at": utc_now(), "entries": entries, "count": len(entries), "status": "PASS"})
    return {"operation": "stage", "count": len(entries), "stage_manifest": str(stage_manifest.relative_to(cfg.root)), "write_status": "DRY_RUN" if cfg.dry_run else "WRITTEN", "status": "PASS"}

def op_release_status(cfg: HandlerConfig) -> dict[str, Any]:
    return {"operation": "release_status", "repository": cfg.repository, "run_id": cfg.run_id, "github_rest_api_entrypoint": "workflow_dispatch/repository_dispatch", "remote_visibility": "ACTIONS_RUN_VISIBLE_IF_GITHUB_CONFIRMS", "remote_byte_exact_asset_hash": "NOT_CONFIRMED", "status": "PASS"}

def run_handler(cfg: HandlerConfig) -> dict[str, Any]:
    try:
        if cfg.operation == "ingest":
            result = op_ingest(cfg)
        elif cfg.operation == "verify":
            result = op_verify(cfg)
        elif cfg.operation == "stage":
            result = op_stage(cfg)
        elif cfg.operation == "release_status":
            result = op_release_status(cfg)
        else:
            raise ValueError("BLOCK unknown operation")
        append_audit(cfg.root, {"event": cfg.operation, "artifact_id": cfg.artifact_id, "dry_run": cfg.dry_run, "result": result})
        write_json(dirs(cfg.root)["audit"] / "last_result.json", result)
        return result
    except Exception as e:
        result = {"status": "BLOCK", "reason": str(e), "operation": cfg.operation, "artifact_id": cfg.artifact_id}
        append_audit(cfg.root, {"event": cfg.operation or "UNKNOWN", "status": "BLOCK", "reason": str(e), "artifact_id": cfg.artifact_id})
        write_json(dirs(cfg.root)["audit"] / "last_result.json", result)
        return result

def config_from_env(root: Path | None = None) -> HandlerConfig:
    return HandlerConfig(
        root=root or Path.cwd(),
        operation=os.environ.get("QIKVRT_OPERATION", "").strip(),
        artifact_id=os.environ.get("QIKVRT_ARTIFACT_ID", "").strip() or "status",
        payload_b64=os.environ.get("QIKVRT_PAYLOAD_B64", ""),
        expected_sha256=os.environ.get("QIKVRT_EXPECTED_SHA256", ""),
        dry_run=os.environ.get("QIKVRT_DRY_RUN", "true").lower() != "false",
        repository=os.environ.get("GITHUB_REPOSITORY", "local/qik-vrt"),
        run_id=os.environ.get("GITHUB_RUN_ID", "local-run"),
    )

def main() -> int:
    result = run_handler(config_from_env())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in ("PASS", "NOT_FOUND") else 1

if __name__ == "__main__":
    raise SystemExit(main())
