#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Synthetic positive and negative controls for static instance IaC."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from tools.qikvrt_instance_iac import check

POLICY = Path(__file__).resolve().parents[1] / "policy/QIKVRT_SELF_CONTAINED_SERVICE_IAC_V1.json"

class InstanceIacTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        (self.root / "policy").mkdir()
        (self.root / "policy/QIKVRT_SELF_CONTAINED_SERVICE_IAC_V1.json").write_text(
            json.dumps(self.policy), encoding="utf-8")
        for item in self.policy["required_package_paths"]:
            target = self.root / item
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
        self.instance = {
            "instance_id":"node-01", "service_id":"terminal", "source_head":"a"*40,
            "source_tree":"b"*40, "package_digest_sha256":"c"*64,
            "deployment_adapter":"sealed-local-v1",
            "runtime_roles":list(self.policy["required_roles"]),
            "healthcheck":{"path":"/health","source":"native"},
            "rollback":{"mode":"fenced-ledger-reconcile"},
            "secret_refs":{"host":"env://QIKVRT_HOST_BINDING"},
            "evidence_sink":"original-readback"
        }
    def tearDown(self):
        self.tmp.cleanup()
    def test_static_valid(self):
        self.assertEqual(check(self.root, self.instance), [])
    def test_missing_carrier(self):
        (self.root / self.policy["required_package_paths"][0]).unlink()
        self.assertTrue(any(e.startswith("CARRIER_MISSING") for e in check(self.root,self.instance)))
    def test_missing_terminal(self):
        self.instance["runtime_roles"].remove("universal_terminal")
        self.assertIn("REQUIRED_ROLES_MISSING",check(self.root,self.instance))
    def test_missing_transputer(self):
        self.instance["runtime_roles"].remove("universal_transputer")
        self.assertIn("REQUIRED_ROLES_MISSING",check(self.root,self.instance))
    def test_embedded_secret(self):
        self.instance["password"] = "sensitive-placeholder"
        self.assertIn("SECRET_VALUE_FIELD:password",check(self.root,self.instance))
    def test_literal_secret(self):
        self.instance["secret_refs"]["host"] = "literal-credential"
        self.assertIn("SECRET_REFERENCE_INVALID",check(self.root,self.instance))
    def test_effect_flag(self):
        self.instance["EFFECT_ACK_DONE"]=True
        self.assertIn("EFFECT_STATE_IN_DECLARATION",check(self.root,self.instance))
    def test_incorrect_sha(self):
        self.instance["source_head"]="main"
        self.assertIn("BAD_GIT_ID:source_head",check(self.root,self.instance))
    def test_missing_policy(self):
        (self.root / "policy/QIKVRT_SELF_CONTAINED_SERVICE_IAC_V1.json").unlink()
        self.assertEqual(check(self.root,self.instance),["POLICY_MISSING"])
if __name__ == "__main__":
    unittest.main()
