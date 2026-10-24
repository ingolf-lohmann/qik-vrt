# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools import ai_handoff
from tools import qikvrt_seed_common as seed
from tools import qikvrt_workflow_executor as executor
from tools import qikvrt_reflexive_repository_watchdog as watchdog

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = "ingolf-lohmann/qik-vrt"
CLASSIFICATION = "state/work_units/QIKVRT_AUTHORITY_REFERENCE_CLASSIFICATION_20261004_V1.json"
HOLD = "HOLD_NEW_MIRROR_IDENTITY_AND_API_CREATION_CAPABILITY"


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class AuthorityCutoverTests(unittest.TestCase):
    def bootstrap_fixture(self, mutate=lambda value: None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        for path in (executor.CONTRACT_RELATIVE_PATH, executor.MIRROR_BOOTSTRAP_PATH):
            value = read_json(path)
            if path == executor.MIRROR_BOOTSTRAP_PATH:
                mutate(value)
            destination = root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(value), encoding="utf-8")
        return root

    def test_unknown_mirror_is_precise_identity_and_capability_hold(self):
        status = executor.mirror_bootstrap_status(ROOT)
        self.assertEqual(status["state"], "HOLD")
        self.assertEqual(status["hold"], HOLD)
        self.assertEqual(status["authority_repository"], AUTHORITY)
        self.assertIsNone(status["mirror_repository"])
        self.assertEqual(status["blockers"], [
            "NEW_MIRROR_IDENTITY_NOT_SPECIFIED_OR_VERIFIED",
            "API_NATIVE_REPOSITORY_CREATION_CAPABILITY_UNAVAILABLE",
        ])
        self.assertEqual(status["repository_creation_effect_count"], 0)
        self.assertFalse(status["mirror_created"])
        self.assertFalse(status["PREDECESSOR_EVIDENCE_TRANSFER"])
        self.assertFalse(status["EFFECT_ACK_DONE"])

    def test_target_alone_cannot_bypass_creation_capability(self):
        def target(value):
            value["target"].update(repository="fixture-owner/fixture-mirror", owner_target_verified=True)
        status = executor.mirror_bootstrap_status(self.bootstrap_fixture(target))
        self.assertEqual(status["blockers"], ["API_NATIVE_REPOSITORY_CREATION_CAPABILITY_UNAVAILABLE"])
        self.assertEqual(status["state"], "HOLD")

    def test_capability_alone_cannot_invent_target(self):
        def capability(value):
            value["execution_capability"]["api_repository_creation_callable"] = True
        status = executor.mirror_bootstrap_status(self.bootstrap_fixture(capability))
        self.assertEqual(status["blockers"], ["NEW_MIRROR_IDENTITY_NOT_SPECIFIED_OR_VERIFIED"])
        self.assertIsNone(status["mirror_repository"])

    def test_target_permission_is_required_and_preparation_is_not_effect(self):
        def target_and_route(value):
            value["target"].update(repository="fixture-owner/fixture-mirror", owner_target_verified=True)
            value["execution_capability"]["api_repository_creation_callable"] = True
        root = self.bootstrap_fixture(target_and_route)
        self.assertEqual(executor.mirror_bootstrap_status(root)["blockers"], ["NEW_MIRROR_TARGET_PERMISSION_UNVERIFIED"])
        path = root / executor.MIRROR_BOOTSTRAP_PATH
        value = json.loads(path.read_text())
        value["execution_capability"]["target_permission_verified"] = True
        path.write_text(json.dumps(value))
        status = executor.mirror_bootstrap_status(root)
        self.assertEqual(status["state"], "PREPARED_REQUIRES_FRESH_NATIVE_REOBSERVATION")
        self.assertFalse(status["mirror_created"])
        self.assertFalse(status["EFFECT_ACK_DONE"])

    def test_malformed_or_aliased_target_is_rejected(self):
        for repository in (AUTHORITY.upper(), "Goldkelch/qik-vrt", "https://example.invalid/mirror", "owner/repo/extra"):
            with self.subTest(repository=repository):
                root = self.bootstrap_fixture(lambda value: value["target"].update(repository=repository))
                with self.assertRaises(executor.ExecutorBlock):
                    executor.mirror_bootstrap_status(root)

    def test_authority_or_epoch_drift_is_rejected(self):
        for key in ("authority_repository", "succession_epoch"):
            with self.subTest(key=key):
                root = self.bootstrap_fixture(lambda value: value.update({key: "other"}))
                with self.assertRaises(executor.ExecutorBlock):
                    executor.mirror_bootstrap_status(root)

    def test_seed_holds_before_registry_fetch_or_write(self):
        root = self.bootstrap_fixture()
        fetch = mock.Mock(side_effect=AssertionError("unbound Mirror cannot fetch"))
        with mock.patch.object(seed, "load_policies") as policies, mock.patch.object(seed, "_atomic_write") as write:
            with self.assertRaisesRegex(seed.SeedError, HOLD):
                seed.run_acceptance(root, "cutover-test", fetch, seed_repository=AUTHORITY)
        policies.assert_not_called()
        fetch.assert_not_called()
        write.assert_not_called()

    def test_predecessor_liveness_is_not_admitted_as_current(self):
        root = self.bootstrap_fixture()
        contract = executor.load_contract(root)
        profile = contract["reflexive_deadlock_prevention"]["gatewatch"]["node_liveness"]
        old = root / profile["historical_records_root"]
        old.mkdir(parents=True)
        for key in ("seed_acceptance_path", "renewal_path", "health_path"):
            (old / Path(profile[key]).name).write_text('{"predecessor_receipt": true}')
        result = watchdog._node_liveness_observation(
            contract, root=root, directory=None, authority_head="a" * 40,
            now=datetime(2026, 10, 4, tzinfo=timezone.utc),
        )
        self.assertEqual(result["state"], "NOT_APPLICABLE")
        self.assertTrue(all(not record["present"] for record in result["records"].values()))
        self.assertIn(contract["authority"]["succession_epoch"], result["records_root"])

    def test_historical_capsule_requires_exact_scope_and_cannot_be_current_evidence(self):
        context = read_json("AI_CONTEXT.json")
        self.assertTrue(ai_handoff.validate_progress(context).startswith("python3 -B "))
        for key, value in (("is_current_authority_evidence", True), ("source_repository", AUTHORITY), ("commit", "a" * 40)):
            with self.subTest(key=key):
                changed = copy.deepcopy(context)
                changed["progress_protocol"]["historical_projection_source"][key] = value
                with self.assertRaises(SystemExit):
                    ai_handoff.validate_progress(changed)

    def test_classified_historical_files_are_byte_preserved(self):
        inventory = read_json(CLASSIFICATION)
        self.assertEqual(inventory["source_head"], "410dbaba6098074f05e2a5b4da7ca94d7edb90a3")
        self.assertEqual(inventory["source_reference_file_count"], len(inventory["references"]))
        self.assertFalse(inventory["PREDECESSOR_EVIDENCE_TRANSFER"])
        for reference in inventory["references"]:
            if reference["disposition"] == "HISTORICAL_OR_SCOPED_REFERENCE_PRESERVED":
                with self.subTest(path=reference["path"]):
                    digest = hashlib.sha256((ROOT / reference["path"]).read_bytes()).hexdigest()
                    self.assertEqual(digest, reference["source_worktree_sha256"])
        for binding in inventory["additional_preserved_bindings"]:
            self.assertEqual(hashlib.sha256((ROOT / binding["path"]).read_bytes()).hexdigest(), binding["source_worktree_sha256"])


if __name__ == "__main__":
    unittest.main()
