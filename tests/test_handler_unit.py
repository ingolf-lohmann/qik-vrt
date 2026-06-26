#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Origin: QIK-VRT V38 remote format repair and dispatch attestation kit
# Rights-Holder: Ingolf Lohmann
# Project: QIK-VRT
# Source-Code-License: Apache-2.0
# Non-Source-Code-License: CC BY-NC 4.0 for non-code repository materials
# Notice: See RIGHTS.md / QIKVRT_LICENSE_AND_RIGHTS.md, LICENSE, NOTICE, and .q/lic/.
import base64, hashlib, json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "src"))
from qikvrt_api_handler import HandlerConfig, run_handler

ROOT = Path.cwd() / "unit_state"
if ROOT.exists():
    shutil.rmtree(ROOT)
ROOT.mkdir()
payload = b"unit payload"
sha = hashlib.sha256(payload).hexdigest()
b64 = base64.b64encode(payload).decode()
r1 = run_handler(HandlerConfig(ROOT, "ingest", "unit", b64, sha, True))
r2 = run_handler(HandlerConfig(ROOT, "ingest", "unit", b64, "0"*64, True))
r3 = run_handler(HandlerConfig(ROOT, "release_status", "status", "", "", True))
report = {
  "gate": "HANDLER_UNIT_GATE",
  "dry_run_ingest_pass": r1.get("status") == "PASS" and r1.get("commit",{}).get("git_invoked") is False,
  "bad_hash_blocked": r2.get("status") == "BLOCK",
  "release_status_not_confirmed": r3.get("remote_byte_exact_asset_hash") == "NOT_CONFIRMED",
}
report["pass"] = all(v for k,v in report.items() if k != "gate")
Path("audit").mkdir(exist_ok=True)
Path("audit/HANDLER_UNIT_TEST_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["pass"] else 1)
