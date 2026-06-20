#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Initial launcher acceptance gate."""
from __future__ import annotations
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "state"
ACCEPTANCE_FILE = STATE_DIR / "launcher_acceptance_record.json"
LOG_FILE = ROOT / "logs" / "qikvrt_last_run.jsonl"
EFFECTFUL_EVENTS = {
    "command_start",
    "runtime_missing",
    "dependency_resolution_start",
    "target_process_result",
    "download_start",
    "repair_start",
    "release_start",
    "master_gate_start",
}

def json_safe_path(path):
    """Return JSON-safe path."""
    return pathlib.Path(path).as_posix()

def append_event(event, **fields):
    """Append JSONL event."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **fields}
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload

def load_acceptance():
    """Load persisted acceptance record."""
    if not ACCEPTANCE_FILE.is_file():
        return None
    try:
        data = json.loads(ACCEPTANCE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    required = ["accepted", "product_owner_acceptance", "accepted_by", "accepted_scope", "source_code_license", "non_source_license", "python_runtime_third_party_license"]
    if all(field in data for field in required) and data.get("accepted") is True and data.get("product_owner_acceptance") is True:
        return data
    return None

def persist_acceptance(accepted_by="Ingolf Lohmann", accepted_scope="V29 launcher execution"):
    """Persist launcher acceptance record."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "accepted": True,
        "product_owner_acceptance": True,
        "accepted_by": accepted_by,
        "accepted_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "accepted_scope": accepted_scope,
        "source_code_license": "Apache-2.0",
        "non_source_license": "CC-BY-NC-ND-4.0",
        "python_runtime_third_party_license": "Python Software Foundation License Version 2",
    }
    ACCEPTANCE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    append_event("acceptance_persisted", status="ACCEPTED", persisted=True, acceptance_record=json_safe_path(ACCEPTANCE_FILE), accepted_by=accepted_by)
    return data

def require_acceptance():
    """Require acceptance before effect."""
    data = load_acceptance()
    if data is not None:
        append_event("acceptance_verified", status="ACCEPTED", persisted=True, acceptance_record=json_safe_path(ACCEPTANCE_FILE))
        return True
    append_event(
        "acceptance_required",
        status="CONTINUE_ACCEPTANCE_REQUIRED",
        persisted=False,
        error_class="BATCH_START_WITHOUT_INITIAL_ACCEPTANCE_GATE",
        continue_path="PERSIST_LAUNCHER_ACCEPTANCE_BEFORE_ANY_EFFECT",
        repair_hint="Run qikvrt.cmd accept or qikvrt.py --accept before executing master-gate.",
        acceptance_record=json_safe_path(ACCEPTANCE_FILE),
    )
    append_event(
        "run_end",
        status="CONTINUE",
        exit_code=30,
        error_class="CONTINUE_ACCEPTANCE_REQUIRED",
        continue_path="PERSIST_LAUNCHER_ACCEPTANCE_BEFORE_ANY_EFFECT",
        repair_hint="Persist launcher acceptance before executing any effectful command.",
        logfile=json_safe_path(LOG_FILE),
    )
    return False

def validate_log_order(path=LOG_FILE):
    """Validate acceptance before any effectful event."""
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    accepted_index = None
    for index, event in enumerate(events):
        name = event.get("event")
        if name in {"acceptance_verified", "acceptance_persisted"} and event.get("persisted") is True:
            accepted_index = index if accepted_index is None else min(accepted_index, index)
        if name in EFFECTFUL_EVENTS:
            assert accepted_index is not None and accepted_index < index, "effectful event occurred before persisted acceptance"
    return True

def main(argv=None):
    """CLI."""
    argv = argv or []
    if "--accept" in argv:
        persist_acceptance()
        print("PASS launcher acceptance persisted")
        return 0
    if "--validate-log" in argv:
        validate_log_order()
        print("PASS initial acceptance order")
        return 0
    if require_acceptance():
        print("PASS launcher acceptance verified")
        return 0
    print("CONTINUE launcher acceptance required")
    return 30

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
