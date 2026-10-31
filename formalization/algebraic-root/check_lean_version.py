#!/usr/bin/env python3
"""Read-only Lean release discovery. Never installs or invents a verifier."""
import argparse
import json
from pathlib import Path
import re
import sys
import urllib.request

def version(tag):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", tag)
    return tuple(map(int, match.groups())) if match else None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    pinned = (root / "paranoid/lean-toolchain").read_text().strip().split(":")[-1]
    report = {"schema": "qikvrt.lean-version-discovery.v1",
              "pinned": pinned, "latest": None,
              "newer_available": None, "action": "retain_pinned"}
    try:
        request = urllib.request.Request(
            "https://api.github.com/repos/leanprover/lean4/releases/latest",
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "qikvrt-lean-version-check"})
        with urllib.request.urlopen(request, timeout=15) as response:
            latest = json.load(response)["tag_name"]
        a, b = version(pinned), version(latest)
        if a is None or b is None:
            raise ValueError("unparseable release tag")
        report["latest"] = latest
        report["newer_available"] = b > a
        report["action"] = ("stage_separate_compatibility_implementation_and_proof"
                            if b > a else "retain_pinned")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report["error"] = str(exc)
        Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
        return 1  # fail closed: release check was not performed
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
