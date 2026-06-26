#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import argparse, base64, hashlib, json, sys, urllib.request, urllib.error
from pathlib import Path

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8766")
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--token", default="local-dev-token")
    ap.add_argument("--ref", default="main")
    ap.add_argument("--operation", choices=["ingest", "verify", "stage", "release_status"], default="ingest")
    ap.add_argument("--artifact-id", default="qikvrt_artifact")
    ap.add_argument("--payload-file")
    ap.add_argument("--expected-sha256")
    ap.add_argument("--dry-run", default="true", choices=["true", "false"])
    args = ap.parse_args()

    payload_b64 = ""
    expected = args.expected_sha256 or ""
    if args.payload_file:
        p = Path(args.payload_file)
        payload_b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        expected = expected or sha256_file(p)

    body = {"ref": args.ref, "inputs": {"operation": args.operation, "artifact_id": args.artifact_id, "payload_b64": payload_b64, "expected_sha256": expected, "dry_run": args.dry_run}}
    url = f"{args.base_url.rstrip('/')}/repos/{args.owner}/{args.repo}/actions/workflows/qikvrt_mesh_api.yml/dispatches"
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": f"Bearer {args.token}", "Accept": "application/vnd.github+json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")
            print(text)
            return 0 if 200 <= resp.status < 300 else 1
    except urllib.error.HTTPError as e:
        print(e.read().decode("utf-8"), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
