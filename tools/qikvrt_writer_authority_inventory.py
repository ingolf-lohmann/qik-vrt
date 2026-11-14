# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Conservative inventory of workflow-level GitHub write authority.

This is an audit, not a claim that GitHub-side branch protections are installed.
No third-party YAML dependencies: inspect workflow files and emit a HOLD receipt
when a workflow can request write permission or invoke repository writes.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(".github/workflows")
WRITE_PERMISSIONS = re.compile(r"^\s*(?:contents|pull-requests|issues|actions|deployments|packages|attestations|checks|statuses|administration|workflows)\s*:\s*write\s*(?:#.*)?$", re.M)
WRITE_COMMANDS = re.compile(r"\b(?:git\s+push|gh\s+(?:pr\s+merge|api\s+--method\s+(?:POST|PUT|PATCH|DELETE)|release\s+create)|curl\b[^\n]*\s-X\s+(?:POST|PUT|PATCH|DELETE))\b", re.I)


def inventory(root: pathlib.Path = ROOT) -> dict:
    files = sorted([*root.glob("*.yml"), *root.glob("*.yaml")])
    writers = []
    for path in files:
        body = path.read_text(encoding="utf-8")
        reasons = []
        if WRITE_PERMISSIONS.search(body):
            reasons.append("declares-write-permission")
        if WRITE_COMMANDS.search(body):
            reasons.append("potential-write-command")
        if reasons:
            writers.append({"path": str(path), "reasons": reasons})
    return {
        "schema": "qikvrt-writer-inventory/v1",
        "workflows_scanned": len(files),
        "potential_writers": writers,
        "universal_writer_enforcement_proven": False,
        "state": "HOLD",
    }


if __name__ == "__main__":
    receipt = inventory()
    print(json.dumps(receipt, sort_keys=True, indent=2))
    if "--require-enforced" in sys.argv:
        raise SystemExit("HOLD: inventory is not GitHub ruleset/branch-protection enforcement")
