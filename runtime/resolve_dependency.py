#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Platform-general dependency resolver for QIK-VRT."""
from __future__ import annotations
import json
import os
import pathlib
import shutil
import sys
import time

if str(pathlib.Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.qikvrt_subprocess import run_bounded

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "logs" / "qikvrt_last_run.jsonl"
EVIDENCE_FILE = ROOT / "runtime" / "dependency_resolution_evidence.json"
DEPENDENCIES_FILE = ROOT / "runtime" / "DEPENDENCIES.json"

def json_safe_path(path):
    """Return JSON-safe path string."""
    return pathlib.Path(path).as_posix()

def write_event(event, **fields):
    """Append one JSON event."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **fields}
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload

def load_dependencies():
    """Load dependency manifest."""
    return json.loads(DEPENDENCIES_FILE.read_text(encoding="utf-8"))["dependencies"]

def resolve_python_runtime():
    """Resolve Python runtime using the general dependency contract."""
    dep = [item for item in load_dependencies() if item["dependency_id"] == "python_runtime"][0]
    write_event("dependency_resolution_start", dependency_id=dep["dependency_id"], platform_scope=dep["platform_scope"], license_area=dep["license_area"])
    if os.name == 'nt':
        host = pathlib.Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        process = run_bounded(
            [str(host), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
             '-File', str(ROOT / 'tools/bootstrap-runtime.ps1'), '-CheckOnly',
             '-Profile', 'windows-start', '-PrintPath'], cwd=ROOT, timeout=30,
            max_output_bytes=128 * 1024,
        )
        code = process.returncode
        if process.timed_out or process.output_limit_exceeded or code not in (0, 20):
            code = 1
        paths = (process.stdout or '').strip().splitlines()
        if code == 0 and len(paths) != 1:
            code = 1
        result = {
            'status': 'PASS' if code == 0 else 'CONTINUE' if code == 20 else 'BLOCK',
            'dependency_id': 'python_runtime', 'source': 'verified_toolchain_cache',
            'path': paths[0] if code == 0 else None,
            'bootstrap_authority': 'tools/bootstrap-runtime.ps1 -Profile windows-start',
            'network_access_allowed': False, 'dependency_closed': False,
            'continue_path': 'MATERIALIZE_LOCKED_CACHE_THEN_FRESH_NATIVE_OFFLINE_WITNESS',
        }
        write_event('dependency_discovery_result', **result)
        EVIDENCE_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return code, result
    candidates = [ROOT / path for path in dep["preferred_embedded_paths"]]
    for candidate in candidates:
        if candidate.is_file():
            result = {"status": "PASS", "dependency_id": "python_runtime", "path": json_safe_path(candidate), "source": "embedded"}
            write_event("dependency_discovery_result", **result)
            EVIDENCE_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 0, result
    for command in dep["fallback_discovery_commands"]:
        executable = command.split()[0]
        resolved = shutil.which(executable)
        if resolved:
            result = {"status": "PASS", "dependency_id": "python_runtime", "path": json_safe_path(resolved), "source": "system", "command": command}
            write_event("dependency_discovery_result", **result)
            EVIDENCE_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 0, result
    result = {
        "status": "CONTINUE",
        "dependency_id": "python_runtime",
        "error_class": "DEPENDENCY_RUNTIME_NOT_RESOLVED",
        "continue_path": dep["continue_path"],
        "repair_hint": dep["repair_hint"],
        "license_or_rights_context": dep["license_or_rights_context"],
        "evidence_file": json_safe_path(EVIDENCE_FILE),
    }
    write_event("dependency_download_consent_required", **result)
    EVIDENCE_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 20, result

def main(argv=None):
    """CLI entrypoint."""
    rc, _ = resolve_python_runtime()
    return rc

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

# field normalization simulation v44
