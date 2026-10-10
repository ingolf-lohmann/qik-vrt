#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Execute the declared contract suite; presence is never execution evidence."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MANIFEST = "state/autonomy/PIPELINE_CONTRACT_TESTS_V1.json"


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executed = []
        self.rows = {}

    def startTest(self, test):
        super().startTest(test)
        row = {"id": test.id(), "outcome": "STARTED"}
        self.executed.append(row)
        self.rows[id(test)] = row

    def record(self, test, outcome):
        row = self.rows.get(id(test))
        if row is not None:
            # A failed subtest may not later become a successful parent test.
            if row["outcome"] not in {"FAILURE", "ERROR"}:
                row["outcome"] = outcome

    def addSuccess(self, test):
        self.record(test, "SUCCESS")
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.record(test, "FAILURE")
        super().addFailure(test, err)

    def addError(self, test, err):
        self.record(test, "ERROR")
        super().addError(test, err)

    def addSkip(self, test, reason):
        self.record(test, "SKIPPED")
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self.record(test, "EXPECTED_FAILURE")
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self.record(test, "UNEXPECTED_SUCCESS")
        super().addUnexpectedSuccess(test)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.record(test, "FAILURE")
        super().addSubTest(test, subtest, err)


def coverage(requirements, planned, executed):
    passed = {r["id"] for r in executed if r["outcome"] == "SUCCESS"}
    if not planned or len(planned) != len(set(planned)):
        return False
    if len(executed) != len(planned) or passed != set(planned):
        return False
    return bool(requirements) and all(ids and set(ids) <= passed for ids in requirements.values())


def identity(root):
    def call(*args):
        return subprocess.check_output(["git", "-C", str(root), *args],
                                       stderr=subprocess.DEVNULL, timeout=30).decode().strip()
    try:
        return {"head": call("rev-parse", "HEAD"), "tree": call("rev-parse", "HEAD^{tree}"),
                "worktree_clean": not bool(call("status", "--porcelain=v1", "--untracked-files=all"))}
    except (OSError, subprocess.SubprocessError):
        return {"head": None, "tree": None, "worktree_clean": False}


def source_digests(root, names):
    result = {}
    for name in names:
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or (root / path).is_symlink():
            raise ValueError("unsafe source inventory")
        result[name] = hashlib.sha256((root / path).read_bytes()).hexdigest()
    return result


def run(root=ROOT):
    mode = "optimized" if sys.flags.optimize else "normal"
    directory = Path(os.environ.get("QIKVRT_CONTRACT_EVIDENCE_DIR", str(root / ".qikvrt/runtime/pipeline-contracts/tests")))
    directory.mkdir(parents=True, exist_ok=True)
    value = {"schema": "qikvrt_executed_contract_tests_v1", "state": "HOLD",
             "optimization": bool(sys.flags.optimize), "python": sys.version,
             "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
             "PREDECESSOR_EVIDENCE_TRANSFER": False, "EFFECT_ACK_DONE": False,
             "executed": [], "requirements_satisfied": False, "committed_subject": False}
    try:
        manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
        if manifest.get("schema") != "qikvrt_pipeline_contract_test_manifest_v1":
            raise ValueError("manifest schema")
        names = [MANIFEST] + manifest["source_paths"]
        before = identity(root)
        value.update(head=before["head"], tree=before["tree"],
                     source_sha256=source_digests(root, names), requirements=manifest["requirements"])
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromNames(manifest["modules"])
        planned = [test.id() for test in flatten(suite)]
        value["planned_test_ids"] = planned
        result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
        value["executed"] = result.executed
        value["requirements_satisfied"] = coverage(manifest["requirements"], planned, result.executed)
        after = identity(root)
        source_current = source_digests(root, names) == value["source_sha256"]
        value["committed_subject"] = bool(before["head"] and before == after and before["worktree_clean"] and source_current)
        # Dirty local candidates can run tests, but cannot claim exact committed evidence.
        if result.wasSuccessful() and value["requirements_satisfied"] and source_current:
            value["state"] = "TESTS_PASSED"
        else:
            value["first_blocker"] = "TEST_FAILURE_MISSING_EXECUTION_OR_SOURCE_DRIFT"
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        value["first_blocker"] = "TEST_INVENTORY_OR_EXECUTION_INVALID"
        value["error_type"] = type(exc).__name__
    path = directory / (mode + ".json")
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"state": value["state"], "mode": mode, "tests_executed": len(value["executed"]),
                      "committed_subject": value["committed_subject"]}, sort_keys=True))
    return 0 if value["state"] == "TESTS_PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(run())
