#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Destructive-source, offline roundtrip and failure controls for Mesh recovery."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_mesh_recovery as recovery
from tools.qikvrt_seed_common import canonical_json_bytes
from tools.qikvrt_seed_common import NodeRecord, SeedError, validate_registration_request
from tests.test_seed_workflows import request_document, SOURCE, SEED, GUID, REQUEST_URL

REPO = "ingolf-lohmann/qik-vrt"
NODE_ID = "a" * 64
STAMP = "2026-10-01T11:18:38Z"


class MeshRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="qikvrt-recovery-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        recovery.git_command(self.source, "init", "-q", "--initial-branch=main")
        recovery.git_command(self.source, "config", "user.name", "Recovery Fixture")
        recovery.git_command(self.source, "config", "user.email", "fixture@example.invalid")
        (self.source / "data.bin").write_bytes(bytes(range(256)))
        recovery.git_command(self.source, "add", "data.bin")
        recovery.git_command(self.source, "commit", "-qm", "initial checkpoint")
        recovery.git_command(self.source, "branch", "retained-history")
        recovery.git_command(self.source, "tag", "-a", "v1", "-m", "retained annotated tag")
        (self.source / "data.bin").write_bytes(bytes(range(255, -1, -1)))
        recovery.git_command(self.source, "add", "data.bin")
        recovery.git_command(self.source, "commit", "-qm", "successor checkpoint")
        self.payload = self.root / "payload"
        self.payload.mkdir()
        self.signature = (recovery.ROOT / "canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin").read_bytes()
        (self.payload / "QIKVRT_SIGNATURE.bin").write_bytes(self.signature)
        self.plan = {
            "schema": recovery.PLAN_SCHEMA, "repository": REPO,
            "root_repository": recovery.ROOT_REPOSITORY,
            "lineage": [recovery.ROOT_REPOSITORY, REPO], "node_id": NODE_ID,
            "role": "MIRROR", "checkpoint_utc": STAMP, "authority_epoch": 7,
            "signature_sha256": recovery.digest(self.signature),
            "git": recovery.git_snapshot(self.source), "assets": [],
        }
        self.scheduler = {
            "schema": "qikvrt_scheduler_checkpoint_v1", "checkpoint_utc": STAMP,
            "schedules": [{
                "schedule_id": "regulatory-watch", "owner_node_id": NODE_ID,
                "target": "personal-digital-twin", "definition": "FREQ=DAILY;BYHOUR=9",
                "timezone": "Europe/Paris", "enabled": True,
                "next_due_utc": "2026-10-02T07:00:00Z", "last_completed_cursor": "done:42",
                "provider_schedule_id": "fixture-provider:1",
                "pending_work": [{"work_unit_id": "watch:43", "idempotency_key": "effect:43"}],
            }],
        }
        for category in sorted(recovery.CATEGORIES):
            raw = canonical_json_bytes(self.scheduler) if category == "scheduler" else (
                ("encrypted-fixture-only:" if category == "capability_recovery" else "fixture:")
                + category
            ).encode()
            path = category + ".bin"
            mode = 0o600 if category == "capability_recovery" else 0o644
            (self.payload / path).write_bytes(raw)
            os.chmod(self.payload / path, mode)
            self.plan["assets"].append({
                "path": path, "category": category, "bytes": len(raw),
                "sha256": recovery.digest(raw), "mode": mode,
                "confidentiality": "PRIVATE_ENCRYPTED" if category == "capability_recovery" else "PUBLIC",
            })
        raw = canonical_json_bytes(json.loads((recovery.ROOT / "policy/QIKVRT_FULL_NODE_RECOVERY_AND_DERIVATION_V1.json").read_bytes()))
        path = recovery.INDEPENDENCE_POLICY_PATH
        (self.payload / path).parent.mkdir()
        (self.payload / path).write_bytes(raw)
        self.plan["assets"].append({"path": path, "category": "governance",
                                  "bytes": len(raw), "sha256": recovery.digest(raw),
                                  "mode": 0o644, "confidentiality": "PUBLIC"})
        self.plan["assets"].sort(key=lambda a: a["path"])
        self.plan_path = self.root / "plan.json"
        self.package = self.root / "checkpoint"

    def write_plan(self, value: dict | None = None) -> str:
        raw = canonical_json_bytes(value if value is not None else self.plan)
        self.plan_path.write_bytes(raw)
        return recovery.digest(raw)

    def test_independence_requirement_cannot_be_deleted_or_weakened_even_with_new_hashes(self) -> None:
        policy = json.loads((self.payload / recovery.INDEPENDENCE_POLICY_PATH).read_bytes())
        recovery.validate_independence_requirement(policy)
        cases = []
        removed = copy.deepcopy(policy)
        del removed["technology_independence"]
        cases.append(removed)
        for key, value in policy["technology_independence"].items():
            if key in {"owner_universal_reverse_engineering_requirement",
                       "life_preserving_requirement_must_survive_every_successor",
                       "independence_bypasses_authority_permit_epoch_or_fence",
                       "universal_capability_inferred_from_requirement_or_checkpoint"}:
                changed = copy.deepcopy(policy)
                changed["technology_independence"][key] = not value
                cases.append(changed)
        weakened = copy.deepcopy(policy)
        weakened["technology_independence"]["required_recovery_material"] = []
        cases.append(weakened)
        dropped = copy.deepcopy(policy)
        dropped["full_node_predicate"].remove(recovery.INDEPENDENCE_PREDICATE)
        cases.append(dropped)
        for changed in cases:
            with self.subTest(changed=changed.get("technology_independence")):
                raw = canonical_json_bytes(changed)
                (self.payload / recovery.INDEPENDENCE_POLICY_PATH).write_bytes(raw)
                asset = next(a for a in self.plan["assets"] if a["path"] == recovery.INDEPENDENCE_POLICY_PATH)
                asset.update(bytes=len(raw), sha256=recovery.digest(raw))
                with self.assertRaisesRegex(recovery.RecoveryError, "technology independence"):
                    self.create()
                self.assertFalse(self.package.exists())

    def test_independence_policy_survives_source_loss_and_rehashed_checkpoint_tampering_is_denied(self) -> None:
        binding = self.create()
        raw = (self.payload / recovery.INDEPENDENCE_POLICY_PATH).read_bytes()
        shutil.rmtree(self.source)
        shutil.rmtree(self.payload)
        destination = self.root / "clone"
        recovery.restore_checkpoint(self.package, destination, binding, clone=True)
        self.assertEqual((destination / "payload" / recovery.INDEPENDENCE_POLICY_PATH).read_bytes(), raw)
        changed = json.loads(raw)
        del changed["technology_independence"]
        raw = canonical_json_bytes(changed)
        (self.package / "payload" / recovery.INDEPENDENCE_POLICY_PATH).write_bytes(raw)
        def rebind(manifest):
            asset = next(a for a in manifest["plan"]["assets"] if a["path"] == recovery.INDEPENDENCE_POLICY_PATH)
            asset.update(bytes=len(raw), sha256=recovery.digest(raw))
        rebound = self.rebind_manifest(rebind)
        with self.assertRaisesRegex(recovery.RecoveryError, "technology independence"):
            recovery.verify_checkpoint(self.package, rebound)

    def test_independence_payload_and_versioned_contract_are_mandatory(self) -> None:
        (self.payload / recovery.INDEPENDENCE_POLICY_PATH).unlink()
        (self.payload / "governance").rmdir()
        self.plan["assets"] = [a for a in self.plan["assets"] if a["path"] != recovery.INDEPENDENCE_POLICY_PATH]
        with self.assertRaisesRegex(recovery.RecoveryError, "technology independence governance payload missing"):
            self.create()
        self.plan["schema"] = "qikvrt_full_node_closure_plan_v1"
        with self.assertRaisesRegex(recovery.RecoveryError, "closure schema"):
            recovery.validate_plan(self.plan)

    def create(self) -> str:
        result = recovery.create_checkpoint(self.source, self.payload, self.plan_path,
                                            self.package, self.write_plan())
        self.assertFalse(result["effect_ack_done"])
        return result["manifest_sha256"]

    def rebind_manifest(self, update) -> str:
        path = self.package / "manifest.json"
        manifest = json.loads(path.read_bytes())
        update(manifest)
        manifest["closure_plan_sha256"] = recovery.digest(canonical_json_bytes(manifest["plan"]))
        raw = canonical_json_bytes(manifest)
        path.write_bytes(raw)
        return recovery.digest(raw)

    def test_restores_every_ref_history_signature_asset_and_scheduler_after_source_loss(self) -> None:
        binding = self.create()
        expected = copy.deepcopy(self.plan)
        shutil.rmtree(self.source)
        shutil.rmtree(self.payload)
        destination = self.root / "restored"
        # A poisoned inherited Git directory must not substitute for the new
        # empty object store, or trigger source/network lookup.
        with mock.patch.dict(os.environ, {"GIT_DIR": "/missing-mesh/.git", "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/missing-mesh/objects"}):
            result = recovery.restore_checkpoint(self.package, destination, binding)
        self.assertEqual(recovery.git_snapshot(destination / "repository.git"), expected["git"])
        self.assertEqual(recovery.git_command(destination / "repository.git", "rev-list", "--count", "main"), "2")
        self.assertEqual((destination / "signature.bin").read_bytes(), self.signature)
        for asset in expected["assets"]:
            path = destination / "payload" / asset["path"]
            self.assertEqual(recovery.digest(path.read_bytes()), asset["sha256"])
            self.assertEqual(path.stat().st_mode & 0o777, asset["mode"])
        self.assertEqual(json.loads((destination / "payload/scheduler.bin").read_bytes()), self.scheduler)
        self.assertEqual(result["node_id"], NODE_ID)
        self.assertFalse(result["writer_enabled"])
        self.assertFalse(result["full_node_admitted"])
        self.assertFalse(result["authority_changed"])
        self.assertFalse(result["effect_ack_done"])

    def test_clone_assigns_distinct_identities_and_preserves_parent_and_global_signature(self) -> None:
        binding = self.create()
        clones = [recovery.restore_checkpoint(self.package, self.root / f"clone-{i}", binding, clone=True) for i in range(2)]
        identities = {NODE_ID, *(c["node_id"] for c in clones)}
        self.assertEqual(len(identities), 3)
        for i, result in enumerate(clones):
            self.assertRegex(result["node_id"], r"^[0-9a-f]{64}$")
            self.assertEqual(result["parent_node_id"], NODE_ID)
            self.assertTrue(result["runtime_rebinding_required"])
            self.assertEqual(result["lineage"][0], recovery.ROOT_REPOSITORY)
            self.assertEqual((self.root / f"clone-{i}/signature.bin").read_bytes(), self.signature)

    def test_authority_and_mirror_share_the_same_offline_contract(self) -> None:
        self.plan["role"] = "AUTHORITY"
        self.plan["repository"] = recovery.ROOT_REPOSITORY
        self.plan["lineage"] = [recovery.ROOT_REPOSITORY]
        binding = self.create()
        self.assertEqual(recovery.verify_checkpoint(self.package, binding)["plan"]["role"], "AUTHORITY")

    def test_both_roles_recheckpoint_and_seed_recursive_clones_after_all_sources_are_lost(self) -> None:
        for role in ("AUTHORITY", "MIRROR"):
            with self.subTest(role=role):
                fixture = MeshRecoveryTests()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                fixture.plan["role"] = role
                if role == "AUTHORITY":
                    fixture.plan.update(repository=recovery.ROOT_REPOSITORY,
                                        lineage=[recovery.ROOT_REPOSITORY])
                binding = fixture.create()
                expected = copy.deepcopy(fixture.plan)
                original_assets = {a["path"]: (fixture.payload / a["path"]).read_bytes()
                                   for a in expected["assets"]}
                current = fixture.root / "survivor"
                recovery.restore_checkpoint(fixture.package, current, binding)
                for path in (fixture.source, fixture.payload, fixture.package):
                    shutil.rmtree(path)
                # No original bundle, source node or remote is used by either
                # generation. Fixture digests stand for owner-pinned plans;
                # they do not authenticate a human or admit a productive node.
                for generation in range(2):
                    plan = recovery.recheckpoint_plan(current, binding)
                    self.assertEqual(plan, expected)
                    plan_path = fixture.root / f"closure-{generation}.json"
                    raw = canonical_json_bytes(plan)
                    plan_path.write_bytes(raw)
                    package = fixture.root / f"generation-{generation}"
                    with mock.patch("socket.create_connection", side_effect=AssertionError("offline test")):
                        result = recovery.recheckpoint(current, binding, plan_path,
                                                       recovery.digest(raw), package)
                        next_node = fixture.root / f"node-{generation}"
                        binding = result["manifest_sha256"]
                        recovery.restore_checkpoint(package, next_node, binding)
                    shutil.rmtree(current)
                    shutil.rmtree(package)
                    current = next_node
                    recovery.verify_restored_node(current, binding)
                    self.assertFalse(result["predecessor_evidence_transfer"])
                    self.assertFalse(result["effect_ack_done"])
                    self.assertEqual(recovery.git_snapshot(current / "repository.git"), expected["git"])
                    for asset in expected["assets"]:
                        target = current / "payload" / asset["path"]
                        self.assertEqual(target.read_bytes(), original_assets[asset["path"]])
                        self.assertEqual(target.stat().st_mode & 0o777, asset["mode"])
                # The survivor can produce another mirror with a distinct ID.
                plan_path = fixture.root / "parent-closure.json"
                raw = canonical_json_bytes(recovery.recheckpoint_plan(current, binding))
                plan_path.write_bytes(raw)
                parent_package = fixture.root / "parent-package"
                parent_binding = recovery.recheckpoint(current, binding, plan_path,
                                                        recovery.digest(raw), parent_package)["manifest_sha256"]
                child = fixture.root / "child"
                clone = recovery.restore_checkpoint(parent_package, child, parent_binding, clone=True)
                clone_identity = (child / "node.json").read_bytes()
                clone_source = (child / "manifest.json").read_bytes()
                self.assertNotEqual(clone["node_id"], expected["node_id"])
                self.assertEqual(clone["parent_node_id"], expected["node_id"])
                self.assertFalse(clone["writer_enabled"])
                shutil.rmtree(current)
                shutil.rmtree(parent_package)
                proposal = recovery.recheckpoint_plan(child, parent_binding)
                self.assertEqual(proposal["role"], "MIRROR")
                self.assertEqual(proposal["node_id"], clone["node_id"])
                self.assertEqual(proposal["lineage"], expected["lineage"])
                plan_path = fixture.root / "child-closure.json"
                raw = canonical_json_bytes(proposal)
                plan_path.write_bytes(raw)
                child_package = fixture.root / "child-package"
                result = recovery.recheckpoint(child, parent_binding, plan_path,
                                               recovery.digest(raw), child_package)
                restored_child = fixture.root / "restored-child"
                recovery.restore_checkpoint(child_package, restored_child, result["manifest_sha256"])
                shutil.rmtree(child)
                recovery.verify_restored_node(restored_child, result["manifest_sha256"])
                identity = json.loads((restored_child / "node.json").read_bytes())
                self.assertEqual(identity["node_id"], clone["node_id"])
                history = restored_child / "payload/governance/clone_lineage" / (clone["node_id"] + ".json")
                snapshot = json.loads(history.read_bytes())
                self.assertEqual(canonical_json_bytes(snapshot["source_manifest"]), clone_source)
                self.assertEqual(canonical_json_bytes(snapshot["source_node_identity"]), clone_identity)
                self.assertFalse(snapshot["predecessor_evidence_transfer"])
                schedule = json.loads((restored_child / "payload/scheduler.bin").read_bytes())
                self.assertEqual(schedule["schedules"][0]["owner_node_id"], clone["node_id"])
                for field in ("last_completed_cursor", "pending_work", "provider_schedule_id"):
                    self.assertEqual(schedule["schedules"][0][field], fixture.scheduler["schedules"][0][field])
                for path, raw in original_assets.items():
                    if path != "scheduler.bin":
                        self.assertEqual((restored_child / "payload" / path).read_bytes(), raw)
                project = recovery.plan_effect(child_package, result["manifest_sha256"], "Goldkelch/derived-fixture")
                self.assertEqual(project["lineage"], expected["lineage"] + ["Goldkelch/derived-fixture"])
                self.assertEqual(project["parent_node_id"], clone["node_id"])
                self.assertFalse(project["remote_repository_created"])

    def test_recheckpoint_rejects_owner_pinned_drift_and_never_overwrites_a_survivor(self) -> None:
        binding = self.create()
        node = self.root / "node"
        recovery.restore_checkpoint(self.package, node, binding)
        proposal = recovery.recheckpoint_plan(node, binding)
        for field, value in (("node_id", "c" * 64), ("authority_epoch", 8), ("role", "AUTHORITY")):
            with self.subTest(field=field):
                changed = {**proposal, field: value}
                raw = canonical_json_bytes(changed)
                self.plan_path.write_bytes(raw)
                with self.assertRaisesRegex(recovery.RecoveryError, "differs from the retained node"):
                    recovery.recheckpoint(node, binding, self.plan_path, recovery.digest(raw), self.root / "rejected")
                self.assertFalse((self.root / "rejected").exists())
        raw = canonical_json_bytes(proposal)
        self.plan_path.write_bytes(raw)
        for output in (node, node / "nested"):
            with self.assertRaisesRegex(recovery.RecoveryError, "outside the restored node"):
                recovery.recheckpoint(node, binding, self.plan_path, recovery.digest(raw), output)
        output = self.root / "existing"
        output.mkdir()
        with self.assertRaisesRegex(recovery.RecoveryError, "refusing overwrite"):
            recovery.recheckpoint(node, binding, self.plan_path, recovery.digest(raw), output)

    def test_recheckpoint_marks_output_incomplete_when_survivor_changes_after_capture(self) -> None:
        binding = self.create()
        node = self.root / "node"
        recovery.restore_checkpoint(self.package, node, binding)
        raw = canonical_json_bytes(recovery.recheckpoint_plan(node, binding))
        self.plan_path.write_bytes(raw)
        creator = recovery.create_checkpoint
        def drift(*args, **kwargs):
            result = creator(*args, **kwargs)
            (node / "payload/runtime.bin").write_bytes(b"changed")
            return result
        output = self.root / "changed-output"
        with mock.patch.object(recovery, "create_checkpoint", side_effect=drift):
            with self.assertRaises(recovery.RecoveryError):
                recovery.recheckpoint(node, binding, self.plan_path, recovery.digest(raw), output)
        self.assertTrue((output / "INCOMPLETE").exists())
        manifest_sha = recovery.digest((output / "manifest.json").read_bytes())
        with self.assertRaisesRegex(recovery.RecoveryError, "incomplete output"):
            recovery.verify_checkpoint(output, manifest_sha)

    def test_cli_recheckpoint_from_survivor_and_project_plan_keep_effects_closed(self) -> None:
        binding = self.create()
        node = self.root / "node"
        recovery.restore_checkpoint(self.package, node, binding)
        for path in (self.source, self.payload, self.package):
            shutil.rmtree(path)
        base = [sys.executable, "-B", str(recovery.ROOT / "tools/qikvrt_mesh_recovery.py")]
        target = ["--node", str(node), "--expect-manifest-sha256", binding]
        result = subprocess.run(base + ["plan-recheckpoint"] + target, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.plan_path.write_bytes(result.stdout)
        output = self.root / "self-package"
        result = subprocess.run(base + ["recheckpoint"] + target + [
            "--plan", str(self.plan_path), "--expect-plan-sha256", recovery.digest(result.stdout),
            "--output", str(output)], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout)
        receipt = json.loads(result.stdout)
        self.assertFalse(receipt["effect_ack_done"])
        self.assertFalse(receipt["full_node_admitted"])
        project = recovery.plan_effect(output, receipt["manifest_sha256"], "Goldkelch/new-fixture")
        self.assertFalse(project["remote_repository_created"])
        self.assertEqual(project["state"], "HOLD_EXTERNAL_EFFECT_PRECONDITIONS")

    def test_signature_manipulation_or_wrong_size_is_blocked(self) -> None:
        binding = self.create()
        path = self.package / "signature.bin"
        for raw in (self.signature[:-1], self.signature + b"x", b"x" + self.signature[1:]):
            with self.subTest(length=len(raw)):
                path.write_bytes(raw)
                with self.assertRaises(recovery.RecoveryError):
                    recovery.verify_checkpoint(self.package, binding)

    def test_rehashed_foreign_400_byte_signature_cannot_replace_shared_v1_image(self) -> None:
        foreign = bytes(range(256)) + bytes(range(144))
        self.plan["signature_sha256"] = recovery.digest(foreign)
        (self.payload / "QIKVRT_SIGNATURE.bin").write_bytes(foreign)
        with self.assertRaisesRegex(recovery.RecoveryError, "foreign or rehashed signature"):
            self.create()
        self.assertFalse(self.package.exists())

    def test_manifest_and_bundle_tampering_is_blocked_by_pinned_readback(self) -> None:
        binding = self.create()
        original = (self.package / "manifest.json").read_bytes()
        (self.package / "manifest.json").write_bytes(original.replace(b'"MIRROR"', b'"AUTHORITY"'))
        with self.assertRaisesRegex(recovery.RecoveryError, "trusted digest mismatch"):
            recovery.verify_checkpoint(self.package, binding)
        (self.package / "manifest.json").write_bytes(original)
        path = self.package / "repository.bundle"
        raw = path.read_bytes()
        path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaisesRegex(recovery.RecoveryError, "payload digest mismatch"):
            recovery.verify_checkpoint(self.package, binding)

    def test_missing_surplus_or_incomplete_files_are_blocked(self) -> None:
        binding = self.create()
        path = self.package / "payload/artifacts.bin"
        original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(recovery.RecoveryError, "missing or surplus"):
            recovery.verify_checkpoint(self.package, binding)
        path.write_bytes(original)
        for name in ("extra.bin", "INCOMPLETE"):
            extra = self.package / name
            extra.write_bytes(b"unexpected")
            with self.assertRaisesRegex(recovery.RecoveryError, "missing or surplus"):
                recovery.verify_checkpoint(self.package, binding)
            extra.unlink()
        (self.package / "unexpected-empty").mkdir()
        with self.assertRaisesRegex(recovery.RecoveryError, "surplus payload directory"):
            recovery.verify_checkpoint(self.package, binding)

    def test_incremental_bundle_cannot_borrow_ancestors_from_live_source(self) -> None:
        self.create()
        bundle = self.root / "incremental.bundle"
        recovery.git_command(self.source, "bundle", "create", str(bundle), "HEAD~1..main")
        shutil.copyfile(bundle, self.package / "repository.bundle")
        # Even with new self-consistent byte bindings, this is not a standalone
        # bundle. The source exists and holds its ancestors during the test.
        binding = self.rebind_manifest(lambda m: m.update(bundle={
            "bytes": bundle.stat().st_size, "sha256": recovery.digest(bundle.read_bytes()),
        }))
        with self.assertRaisesRegex(recovery.RecoveryError, "offline Git operation failed"):
            recovery.verify_checkpoint(self.package, binding)

    def test_required_historical_source_object_must_survive_in_the_standalone_bundle(self) -> None:
        tree = self.plan["git"]["tree"]
        orphan = recovery.git_command(self.source, "commit-tree", tree, "-m", "historical source outside current history")
        self.plan["git"]["required_objects"] = {orphan: "commit"}
        with self.assertRaisesRegex(recovery.RecoveryError, "offline Git operation failed"):
            self.create()
        self.assertTrue((self.package / "INCOMPLETE").exists())
        # Bind the actual source object to a durable recovery ref; no remapping
        # to another commit and no inherited predecessor receipt.
        shutil.rmtree(self.package)
        recovery.git_command(self.source, "update-ref", f"refs/qikvrt/recovery/{orphan}", orphan)
        self.plan["git"] = recovery.git_snapshot(self.source, {orphan: "commit"})
        binding = self.create()
        shutil.rmtree(self.source)
        destination = self.root / "historical-restore"
        recovery.restore_checkpoint(self.package, destination, binding)
        self.assertEqual(recovery.git_command(destination / "repository.git", "cat-file", "-t", orphan), "commit")

    def test_shallow_partial_alternates_grafts_and_replacement_refs_are_blocked(self) -> None:
        shallow = self.root / "shallow"
        recovery.git_command(self.root, "clone", "--depth=1", self.source.as_uri(), str(shallow))
        with self.assertRaisesRegex(recovery.RecoveryError, "SHALLOW"):
            recovery.git_snapshot(shallow)
        for name, raw in (("objects/info/alternates", b"/missing\n"), ("info/grafts", b""), ("objects/pack/fixture.promisor", b"")):
            path = self.source / ".git" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            with self.assertRaises(recovery.RecoveryError):
                recovery.git_snapshot(self.source)
            path.unlink()
        recovery.git_command(self.source, "update-ref", "refs/replace/" + self.plan["git"]["head"], self.plan["git"]["head"])
        with self.assertRaisesRegex(recovery.RecoveryError, "replacement ref"):
            recovery.git_snapshot(self.source)

    def test_head_or_ref_change_after_plan_is_blocked(self) -> None:
        binding = self.write_plan()
        recovery.git_command(self.source, "branch", "unexpected")
        with self.assertRaisesRegex(recovery.RecoveryError, "source HEAD, TREE or ref inventory drift"):
            recovery.create_checkpoint(self.source, self.payload, self.plan_path, self.package, binding)
        self.assertFalse(self.package.exists())

    def test_mid_capture_writer_drift_is_blocked(self) -> None:
        binding = self.write_plan()
        original = recovery.git_command
        def concurrent_writer(repository, *args):
            result = original(repository, *args)
            if args[:2] == ("bundle", "create"):
                original(self.source, "branch", "concurrent-writer")
            return result
        with mock.patch.object(recovery, "git_command", side_effect=concurrent_writer):
            with self.assertRaisesRegex(recovery.RecoveryError, "source changed"):
                recovery.create_checkpoint(self.source, self.payload, self.plan_path, self.package, binding)
        self.assertTrue((self.package / "INCOMPLETE").exists())

    def test_canonical_json_duplicate_keys_unknown_fields_and_incomplete_scope(self) -> None:
        raw = canonical_json_bytes(self.plan)
        candidates = [
            json.dumps(self.plan).encode(),
            raw.replace(b'  "authority_epoch": 7,', b'  "authority_epoch": 7,\n  "authority_epoch": 7,'),
            canonical_json_bytes({**self.plan, "scope_complete": True}),
        ]
        for raw in candidates:
            with self.subTest(raw=raw[:60]):
                self.plan_path.write_bytes(raw)
                with self.assertRaises((recovery.RecoveryError, RuntimeError)):
                    plan = recovery.load_json(self.plan_path, recovery.digest(raw))
                    recovery.validate_plan(plan)
        for category in recovery.CATEGORIES:
            plan = copy.deepcopy(self.plan)
            plan["assets"] = [a for a in plan["assets"] if a["category"] != category]
            with self.subTest(category=category), self.assertRaisesRegex(recovery.RecoveryError, "incomplete closure"):
                recovery.validate_plan(plan)

    def test_root_cycles_duplicate_ids_and_traversal_are_blocked(self) -> None:
        for lineage in ([REPO], [recovery.ROOT_REPOSITORY, REPO, REPO], [recovery.ROOT_REPOSITORY, "goldkelch/qik-vrt", REPO]):
            plan = copy.deepcopy(self.plan)
            plan["lineage"] = lineage
            with self.assertRaisesRegex(recovery.RecoveryError, "acyclic"):
                recovery.validate_plan(plan)
        for value in ("../secret", "/absolute", "a//b", "a/./b", "a\\b", "a/.git/config"):
            plan = copy.deepcopy(self.plan)
            plan["assets"][0]["path"] = value
            with self.assertRaises(recovery.RecoveryError):
                recovery.validate_plan(plan)
        plan = copy.deepcopy(self.plan)
        plan["assets"].append(copy.deepcopy(plan["assets"][0]))
        with self.assertRaisesRegex(recovery.RecoveryError, "unique and sorted"):
            recovery.validate_plan(plan)

    def test_symlink_payload_and_existing_output_are_blocked(self) -> None:
        path = self.payload / "artifacts.bin"
        path.unlink()
        path.symlink_to(self.source / "data.bin")
        with self.assertRaisesRegex(recovery.RecoveryError, "symlink"):
            recovery.create_checkpoint(self.source, self.payload, self.plan_path, self.package, self.write_plan())
        path.unlink()
        path.write_bytes(b"fixture:artifacts")
        binding = self.create()
        sentinel = (self.package / "manifest.json").read_bytes()
        with self.assertRaisesRegex(recovery.RecoveryError, "refusing overwrite"):
            recovery.restore_checkpoint(self.package, self.package, binding)
        self.assertEqual((self.package / "manifest.json").read_bytes(), sentinel)
        with self.assertRaisesRegex(recovery.RecoveryError, "outside the checkpoint"):
            recovery.restore_checkpoint(self.package, self.package / "new-child", binding)

    def test_mode_tampering_is_blocked(self) -> None:
        binding = self.create()
        os.chmod(self.package / "payload/capability_recovery.bin", 0o644)
        with self.assertRaisesRegex(recovery.RecoveryError, "payload mode mismatch"):
            recovery.verify_checkpoint(self.package, binding)

    def test_scheduler_requires_definitions_cursor_timezone_and_unique_idempotency(self) -> None:
        for mutate in (
            lambda s: s["schedules"][0].pop("last_completed_cursor"),
            lambda s: s["schedules"][0].update(timezone="Invalid/Timezone"),
            lambda s: s["schedules"].append(copy.deepcopy(s["schedules"][0])),
            lambda s: s["schedules"][0]["pending_work"].append({"work_unit_id": "another", "idempotency_key": "effect:43"}),
            lambda s: s["schedules"][0].update(owner_node_id="b" * 64),
            lambda s: s.update(checkpoint_utc="2026-10-02T00:00:00Z"),
        ):
            state = copy.deepcopy(self.scheduler)
            mutate(state)
            raw = canonical_json_bytes(state)
            (self.payload / "scheduler.bin").write_bytes(raw)
            plan = copy.deepcopy(self.plan)
            asset = next(a for a in plan["assets"] if a["category"] == "scheduler")
            asset.update(bytes=len(raw), sha256=recovery.digest(raw))
            with self.assertRaises(recovery.RecoveryError):
                recovery.validate_scheduler(self.payload, plan)

    def test_promotion_plan_does_not_grant_an_authority_role_or_transfer_old_epoch_evidence(self) -> None:
        binding = self.create()
        result = recovery.plan_effect(self.package, binding)
        self.assertEqual(result["candidate_repository"], REPO)
        self.assertEqual(result["checkpoint_epoch"], 7)
        self.assertEqual(result["proposed_successor_epoch"], 8)
        self.assertIn("FRESH_CONTROL_PLANE_EPOCH_AND_TARGET_HEAD_READBACK", result["required_effects"])
        self.assertEqual(result["root_repository"], recovery.ROOT_REPOSITORY)
        self.assertFalse(result["authority_changed"])
        self.assertEqual(result["state"], "HOLD_EXTERNAL_EFFECT_PRECONDITIONS")

    def test_project_plan_remains_under_goldkelch_root_and_does_not_create_remote(self) -> None:
        binding = self.create()
        target = "Goldkelch/independent-project"
        result = recovery.plan_effect(self.package, binding, target)
        self.assertEqual(result["lineage"], [recovery.ROOT_REPOSITORY, REPO, target])
        self.assertEqual(result["parent_repository"], REPO)
        self.assertEqual(result["parent_node_id"], NODE_ID)
        self.assertEqual(result["source_checkpoint_sha256"], binding)
        self.assertIn("CREATE_ONLY_PROJECT_REGISTRATION_AT_GOLDKELCH_ROOT", result["required_effects"])
        self.assertFalse(result["remote_repository_created"])
        for invalid in ("another-owner/project", recovery.ROOT_REPOSITORY, "Goldkelch/../project", "goldkelch/project"):
            with self.subTest(target=invalid), self.assertRaises(recovery.RecoveryError):
                recovery.plan_effect(self.package, binding, invalid)

    def test_policy_entrypoint_tool_cache_and_aggregate_test_bindings(self) -> None:
        root = recovery.ROOT
        policy = json.loads((root / "policy/QIKVRT_FULL_NODE_RECOVERY_AND_DERIVATION_V1.json").read_bytes())
        self.assertEqual(set(policy["checkpoint"]["required_asset_categories"]), recovery.CATEGORIES)
        self.assertEqual(policy["signature_and_identity"]["global_signature_bytes"], 400)
        signature_binding = policy["signature_and_identity"]["canonical_v1_binding"]
        self.assertEqual(signature_binding["sha256"], recovery.CANONICAL_SIGNATURE_SHA256_V1)
        self.assertEqual(recovery.digest(self.signature), signature_binding["sha256"])
        self.assertFalse(policy["authority_recovery"]["peer_unreachability_alone_authorizes_promotion"])
        context = json.loads((root / "AI_CONTEXT.json").read_bytes())
        self.assertIn(context["full_node_recovery"]["policy"], context["required_read_order"])
        discovery = json.loads((root / "registry/NODE_DISCOVERY_POLICY.json").read_bytes())
        self.assertFalse(discovery["full_node_admission"]["offline_receipt_alone_grants_full_node_status"])
        cache = json.loads((root / "runtime/toolchains/CACHE_REGISTRY.json").read_bytes())
        self.assertIn("git", cache["components"])
        self.assertIn("test: mesh-recovery-test", (root / "Makefile").read_text())

    def test_seed_does_not_admit_self_asserted_full_node_from_a_remote_receipt(self) -> None:
        node = NodeRecord(GUID, SOURCE, SEED, REQUEST_URL, "main", 1500, "ACTIVE",
                          "registry/node_request_queue/OPEN_NODE_REQUESTS.tsv", 2)
        for claim in (True, "true", 1, {"offline_checkpoint_verified": True}):
            document = request_document()
            document["full_node"] = claim
            document["full_node_receipt"] = {"offline_checkpoint_verified": True, "effect_ack_done": True}
            with self.subTest(claim=claim), self.assertRaises(SeedError):
                validate_registration_request(document, node)
        document = request_document()
        document["full_node"] = False
        self.assertIsInstance(validate_registration_request(document, node), str)


if __name__ == "__main__":
    unittest.main()
