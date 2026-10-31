#!/usr/bin/env python3
"""Local fail-closed mathematical approval gate. No GitHub writes in this program.

The trusted verifier is an independent executable, NOT a producer-supplied claim.
It must bind its approval to the exact SHA256 of the produced result. Its own
proof soundness and mathematical coverage require separate acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def invoke(command, output, timeout):
    try:
        p = subprocess.run([*command, str(output)], timeout=timeout, check=False,
                           capture_output=True, text=True)
        return p.returncode, p.stderr[-2048:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except OSError as exc:
        return 127, str(exc)

def run(producer, verifier, attempts, timeout, receipt_path):
    history = []
    with tempfile.TemporaryDirectory(prefix="qikvrt-math-gate-") as tmp:
        root = Path(tmp)
        feedback = root / "feedback.json"
        feedback.write_text(json.dumps({"attempt": 0, "reason": "initial"}))
        for attempt in range(1, attempts + 1):
            subject = root / ("result-%d.bin" % attempt)
            attestation = root / ("proof-%d.json" % attempt)
            # Producer receives prior rejection feedback before its output path.
            code, diagnostic = invoke([*producer, str(feedback)], subject, timeout)
            entry = {"attempt": attempt, "producer_exit": code}
            if code or not subject.is_file():
                entry["reason"] = "producer_failed"
                entry["diagnostic"] = diagnostic
            else:
                sha = digest(subject)
                entry["subject_sha256"] = sha
                # Verifier takes subject path followed by attestation output path.
                vcode, vdiag = invoke([*verifier, str(subject)], attestation, timeout)
                entry["verifier_exit"] = vcode
                try:
                    proof = json.loads(attestation.read_text(encoding="utf-8"))
                    valid = (type(proof) is dict
                             and proof.get("schema") == "qikvrt.math-verdict.v1"
                             and proof.get("verdict") == "verified"
                             and proof.get("subject_sha256") == sha
                             and vcode == 0)
                except (OSError, ValueError, UnicodeError):
                    valid = False
                if valid:
                    entry["reason"] = "verified"
                    history.append(entry)
                    # Persist approved result to a local file, not to GitHub.
                    approved = receipt_path.with_suffix(".approved.bin")
                    approved.write_bytes(subject.read_bytes())
                    receipt = {"schema": "qikvrt.math-gate.v1", "approved": True,
                               "subject_sha256": sha, "approved_file": str(approved),
                               "attempts": history}
                    receipt_path.write_text(json.dumps(receipt, indent=2)+"\n")
                    return 0
                entry["reason"] = "verifier_rejected"
                entry["diagnostic"] = vdiag
            history.append(entry)
            feedback.write_text(json.dumps({"attempt": attempt, "reason": entry["reason"],
                "subject_sha256": entry.get("subject_sha256"),
                "diagnostic": entry.get("diagnostic", "")}, sort_keys=True))
            print(json.dumps(entry, sort_keys=True), flush=True)
    receipt_path.write_text(json.dumps({"schema": "qikvrt.math-gate.v1",
        "approved": False, "attempts": history}, indent=2)+"\n")
    return 1

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--producer", nargs="+", required=True,
                   help="Trusted producer command; feedback path then result path appended")
    p.add_argument("--verifier", nargs="+", required=True,
                   help="Independent verifier command; subject and verdict paths appended")
    p.add_argument("--attempts", type=int, default=3)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--receipt", required=True)
    a = p.parse_args()
    if not 1 <= a.attempts <= 10 or not 1 <= a.timeout <= 3600:
        p.error("attempts must be 1..10 and timeout 1..3600")
    return run(a.producer, a.verifier, a.attempts, a.timeout, Path(a.receipt))

if __name__ == "__main__":
    sys.exit(main())
