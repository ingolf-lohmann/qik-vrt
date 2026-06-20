#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""QIK-VRT V16 non-recursive CI/CD evidence runner."""
from __future__ import annotations
import argparse, datetime as dt, importlib.util, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]

def build_parser():
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(description="QIKVRT V16 CI/CD dry-run/evidence runner.")
    parser.add_argument("--mode", choices=["dry-run","execute"], default="dry-run")
    parser.add_argument("--no-interactive", action="store_true")
    parser.add_argument("--github-enable", action="store_true")
    parser.add_argument("--zenodo-enable", action="store_true")
    parser.add_argument("--evidence-dir", default="evidence")
    return parser

def parse_args(argv=None):
    """Parse runtime arguments."""
    return build_parser().parse_args(argv)

def load_gate():
    """Load the master gate in-process."""
    spec = importlib.util.spec_from_file_location("gate", ROOT / "tools/qikvrt_master_acceptance_gate.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

def evidence_payload(args, returncode):
    """Build a secret-free evidence payload."""
    return {"_license":{"copyright":"Copyright 2026 Ingolf Lohmann","rights_holder":"Ingolf Lohmann","license":"CC-BY-NC-ND-4.0","license_text_ref":"LICENSES/CC-BY-NC-ND-4.0.txt","classification":"cicd_evidence_ledger_json"},"schema":"qikvrt_cicd_evidence_ledger_v16","created_utc":dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"mode":args.mode,"master_gate_returncode":returncode,"github":{"enabled":bool(args.github_enable),"status":"DRY_RUN" if args.mode=="dry-run" else "EXECUTE_REQUIRES_REAL_EXTERNAL_EVIDENCE"},"zenodo":{"enabled":bool(args.zenodo_enable),"status":"DRY_RUN" if args.mode=="dry-run" else "EXECUTE_REQUIRES_REAL_EXTERNAL_EVIDENCE"}}

def write_evidence(args, returncode):
    """Write an evidence ledger."""
    directory = ROOT / args.evidence_dir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "QIKVRT_CICD_EVIDENCE_LEDGER.json"
    path.write_text(json.dumps(evidence_payload(args, returncode), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path

def run_gate():
    """Run the master gate without spawning child processes."""
    return load_gate().main()

def main(argv=None):
    """Run dry-run evidence or block execute without real external evidence."""
    args = parse_args(argv)
    returncode = run_gate()
    if returncode:
        return returncode
    path = write_evidence(args, returncode)
    print(f"PASS QIKVRT V16 CI/CD dry-run/evidence gate. Evidence: {path}")
    if args.mode == "execute":
        print("BLOCK execute mode requires real external evidence before DONE can be claimed.", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
