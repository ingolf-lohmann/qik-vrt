# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
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
WRITER_SUCCESSOR = "state/work_units/QIKVRT_SHARED_WRITER_POSTCONDITIONS_20261005_V1.json"
HOLD = "HOLD_NEW_MIRROR_IDENTITY_AND_API_CREATION_CAPABILITY"
LIFECYCLE_PROJECTIONS = {
    "evidence/node_health/LATEST.json",
    "evidence/node_registration_renewal/LATEST.json",
    "qikvrt/runtime/onboarding/NODE_HEALTH.json",
    "qikvrt/runtime/onboarding/NODE_REGISTRATION_RENEWAL.json",
}


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class AuthorityCutoverTests(unittest.TestCase):
    def git_bytes(self, *args):
        return subprocess.check_output(["git", *args], cwd=ROOT, timeout=30)

    def assert_main_lifecycle_successor(self, inventory):
        successor = inventory["main_lifecycle_successor"]
        main = successor["source_main_head"]
        self.assertEqual(self.git_bytes("rev-parse", main + "^{tree}").decode().strip(),
                         successor["source_main_tree"])
        self.assertEqual(self.git_bytes("merge-base", successor["predecessor_cutover_head"], main).decode().strip(),
                         successor["merge_base"])
        self.assertFalse(successor["current_authority_liveness_proof"])
        bindings = successor["main_projection_bindings"]
        paths = [binding["path"] for binding in bindings]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual(set(paths), set(self.git_bytes(
            "diff", "--name-only", successor["merge_base"], main).decode().splitlines()))
        self.assertTrue(LIFECYCLE_PROJECTIONS <= set(paths))
        for binding in bindings:
            path = binding["path"]
            if path not in LIFECYCLE_PROJECTIONS:
                self.assertIn(str(Path(path).parent),
                              {"evidence/node_health", "evidence/node_registration_renewal"})
                self.assertRegex(Path(path).name, r"^[0-9]+-[0-9]+\.json$")
            data = self.git_bytes("show", main + ":" + path)
            self.assertEqual(len(data), binding["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), binding["sha256"])
            self.assertEqual(hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
                             binding["git_blob_sha1"])
            self.assertEqual((ROOT / path).read_bytes(), data)
        return set(paths)

    def assert_preserved_binding(self, inventory, binding, successor_paths):
        path = binding["path"]
        # A later Main projection changes the current path, never its old receipt.
        # Resolve the original binding through the retained source commit instead.
        data = (self.git_bytes("show", inventory["source_head"] + ":" + path)
                if path in successor_paths else (ROOT / path).read_bytes())
        self.assertEqual(hashlib.sha256(data).hexdigest(), binding["source_worktree_sha256"])
        if path in successor_paths:
            self.assertEqual(hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest(),
                             binding["source_git_blob_sha1"])

    def assert_operational_writer_successor(self, successor=None, current=None):
        successor = successor or read_json(WRITER_SUCCESSOR)["operational_writer_successor"]
        path = successor["path"]
        self.assertEqual(path, ".github/workflows/qikvrt_global_completion.yml")
        self.assertEqual(successor["source_commit"], "ca2678839c4170871d2624e21df614b295f55477")
        self.assertEqual(successor["historical_source_commit"], read_json(CLASSIFICATION)["source_head"])
        self.assertFalse(successor["PREDECESSOR_EVIDENCE_TRANSFER"])
        self.assertFalse(successor["current_authority_liveness_proof"])
        self.assertEqual(self.git_bytes("merge-base", successor["source_commit"], "HEAD").decode().strip(),
                         successor["source_commit"])
        predecessor = self.git_bytes("show", successor["source_commit"] + ":" + path)
        historical = self.git_bytes("show", successor["historical_source_commit"] + ":" + path)
        self.assertEqual(predecessor, historical)
        self.assertEqual(hashlib.sha256(historical).hexdigest(), successor["predecessor_sha256"])
        self.assertEqual(hashlib.sha1(b"blob " + str(len(historical)).encode() + b"\0" + historical).hexdigest(),
                         successor["predecessor_git_blob_sha1"])
        current = (ROOT / path).read_bytes() if current is None else current
        self.assertEqual(hashlib.sha256(current).hexdigest(), successor["successor_sha256"])
        def scopes(data):
            prefix, rest = data.decode().split("  materialize:\n", 1)
            writer, verifier = rest.split("  verify-global-completion:\n", 1)
            header, steps = writer.split("    steps:\n", 1)
            rows = [row.strip() for row in re.split(r"(?m)(?=^      - name: )", steps) if row.strip()]
            return prefix, header, rows, verifier

        old_prefix, old_header, old_steps, old_verifier = scopes(predecessor)
        new_prefix, new_header, new_steps, new_verifier = scopes(current)
        # Compare bytes directly: this gate also runs in stdlib-only workflows.
        # Triggers, concurrency and the whole verification job stay identical.
        self.assertEqual(old_prefix, new_prefix)
        self.assertEqual(old_verifier, new_verifier)
        self.assertEqual(new_header, old_header.replace("      contents: write\n",
                         "      contents: write\n      actions: read\n      pull-requests: write\n"))
        self.assertEqual(len(old_steps), 8)
        self.assertEqual(len(new_steps), 11)
        self.assertEqual(old_steps[:2], new_steps[:2])
        self.assertEqual(old_steps[2:-1], new_steps[3:-3])
        self.assertEqual(new_steps[-3], old_steps[-1].replace(
            'git push origin "HEAD:${GITHUB_REF_NAME}"',
            "# Branch/PR/verifier writes are resumed by the shared postcondition step."))
        self.assertIn("observe-writer", new_steps[2])
        self.assertIn("publish-writer", new_steps[-2])
        self.assertIn("        if: always()\n", new_steps[-1])
        return {path}

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
        successor_paths = self.assert_main_lifecycle_successor(inventory)
        successor_paths |= self.assert_operational_writer_successor()
        for reference in inventory["references"]:
            if reference["disposition"] == "HISTORICAL_OR_SCOPED_REFERENCE_PRESERVED":
                with self.subTest(path=reference["path"]):
                    self.assert_preserved_binding(inventory, reference, successor_paths)
        for binding in inventory["additional_preserved_bindings"]:
            with self.subTest(path=binding["path"]):
                self.assert_preserved_binding(inventory, binding, successor_paths)

    def test_main_successor_retains_original_classification_bindings(self):
        inventory = read_json(CLASSIFICATION)
        successor = inventory.pop("main_lifecycle_successor")
        original = json.loads(self.git_bytes("show", successor["predecessor_cutover_head"] + ":" + CLASSIFICATION))
        self.assertEqual(inventory, original)
        self.assertEqual(self.git_bytes("merge-base", successor["predecessor_cutover_head"], "HEAD").decode().strip(),
                         successor["predecessor_cutover_head"])

    def test_main_successor_rejects_unbound_path_or_projection_digest(self):
        for key, value in (("path", "AI_PROGRESS.json"), ("sha256", "0" * 64)):
            with self.subTest(key=key):
                inventory = read_json(CLASSIFICATION)
                inventory["main_lifecycle_successor"]["main_projection_bindings"][0][key] = value
                with self.assertRaises(AssertionError):
                    self.assert_main_lifecycle_successor(inventory)

    def test_main_projection_cannot_become_new_authority_liveness(self):
        inventory = read_json(CLASSIFICATION)
        inventory["main_lifecycle_successor"]["current_authority_liveness_proof"] = True
        with self.assertRaises(AssertionError):
            self.assert_main_lifecycle_successor(inventory)

    def test_operational_writer_successor_retains_historical_subject_and_verification(self):
        self.assert_operational_writer_successor()

    def test_operational_writer_successor_rejects_unbound_path_digest_and_liveness(self):
        for key, value in (("path", "AI_PROGRESS.json"), ("successor_sha256", "0" * 64),
                           ("predecessor_sha256", "0" * 64), ("current_authority_liveness_proof", True),
                           ("PREDECESSOR_EVIDENCE_TRANSFER", True)):
            with self.subTest(key=key):
                successor = read_json(WRITER_SUCCESSOR)["operational_writer_successor"]
                successor[key] = value
                with self.assertRaises(AssertionError):
                    self.assert_operational_writer_successor(successor)

    def test_operational_writer_successor_rejects_scheduler_or_verifier_changes_even_with_new_digest(self):
        successor = read_json(WRITER_SUCCESSOR)["operational_writer_successor"]
        current = (ROOT / successor["path"]).read_bytes()
        for before, after in ((b"cancel-in-progress: false", b"cancel-in-progress: true"),
                              (b"run: make test", b"run: echo accepted")):
            with self.subTest(before=before):
                self.assertIn(before, current)
                tampered = current.replace(before, after)
                binding = dict(successor, successor_sha256=hashlib.sha256(tampered).hexdigest())
                with self.assertRaises(AssertionError):
                    self.assert_operational_writer_successor(binding, tampered)


if __name__ == "__main__":
    unittest.main()
