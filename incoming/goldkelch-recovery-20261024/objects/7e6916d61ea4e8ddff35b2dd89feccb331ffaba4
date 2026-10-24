#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Real offline Git recovery; no mocked successful restore or platform rights."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_node_genesis as node
from tools import qikvrt_integrity as integrity
from tools import qikvrt_autonomous_pre_effect_controller as controller

ROOT = Path(__file__).resolve().parents[1]


class NodeGenesisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / "source"
        self.source.mkdir()
        node.git(self.source, "init", "--quiet", "--initial-branch=main")
        for path in ("tools/qikvrt_integrity.py", "tools/qikvrt_subprocess.py",
                     "tools/qikvrt_node_genesis.py", "LEGACY_INTEGRITY_INVENTORIES.md",
                     node.REMOTE_POLICY, "policy/QIKVRT_NODE_GENESIS_RECOVERY_V1.json"):
            target = self.source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        self.write(".gitignore", b".qikvrt-integrity.lock\n__pycache__/\n.qikvrt/\n")
        self.write("registry/nodes.tsv", b"node\trole\noriginal\tMIRROR\n")
        self.write("qikvrt/runtime/onboarding/NODE_HEALTH.json", b'{"state":"HISTORICAL"}\n')
        self.write("state/lifecycle.json", b'{"receipt":"historic","effect_ack_done":false}\n')
        self.write("payload.bin", bytes(range(256)) + b"\x00\xff\r\n")
        self.commit("first complete node")
        self.first = node.git(self.source, "rev-parse", "HEAD").strip()
        node.git(self.source, "branch", "retained-side", self.first)
        node.git(self.source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "tag", "-a", "retained-tag", "-m", "historical annotation")
        self.write("payload.bin", b"next persisted state\x00\xff")
        self.commit("second complete node")
        node.git(self.source, "update-ref", "refs/remotes/lost/main", self.first)
        node.git(self.source, "symbolic-ref", "refs/remotes/lost/HEAD", "refs/remotes/lost/main")
        # Network URLs exist but must never be contacted or restored as config.
        node.git(self.source, "remote", "add", "lost", "https://unavailable.invalid/other-node.git")
        node.git(self.source, "config", "credential.helper", "!exit 97")
        self.snapshot = self.base / "snapshot"
        self.sha = node.export_snapshot(self.source, self.snapshot, "ingolf-lohmann/qik-vrt")
        self.head = node.git(self.source, "rev-parse", "HEAD").strip()
        self.original = node.observe(self.source)

    def write(self, path: str, raw: bytes) -> None:
        target = self.source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    def commit(self, message: str) -> None:
        integrity.generate(self.source)
        node.git(self.source, "add", ".")
        node.git(self.source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", message)

    def reanchor(self, transform=None) -> str:
        value = node.load_json(self.snapshot / "snapshot.json")
        if transform:
            transform(value)
        value["bundle"]["bytes"], value["bundle"]["sha256"] = node.digest_file(
            self.snapshot / "node.bundle", node.MAX_BUNDLE_BYTES)
        raw = node.canonical(value)
        sha = hashlib.sha256(raw).hexdigest()
        (self.snapshot / "snapshot.json").write_bytes(raw)
        (self.snapshot / "snapshot.sha256").write_text(sha + "\n")
        return sha

    def test_full_restore_after_loss_of_every_remote_and_source(self) -> None:
        all_objects = node.git(self.source, "cat-file", "--batch-all-objects", "--batch")
        history = node.git(self.source, "rev-list", "--all", "--parents")
        source_bytes = {p: (self.source / p).read_bytes() for p in
                        ("payload.bin", "registry/nodes.tsv", "state/lifecycle.json",
                         "qikvrt/runtime/onboarding/NODE_HEALTH.json", node.REMOTE_POLICY)}
        shutil.rmtree(self.source)
        destination = self.base / "restored"
        with mock.patch.object(node, "git", wraps=node.git) as calls:
            receipt = node.restore_snapshot(self.snapshot, destination, self.sha)
        self.assertEqual(node.observe(destination), self.original)
        self.assertEqual(node.git(destination, "cat-file", "--batch-all-objects", "--batch"), all_objects)
        self.assertEqual(node.git(destination, "rev-list", "--all", "--parents"), history)
        for path, raw in source_bytes.items():
            self.assertEqual((destination / path).read_bytes(), raw)
        self.assertEqual(node.git(destination, "remote"), "")
        self.assertEqual(node.git(destination, "config", "--get", "credential.helper", optional=True), "")
        self.assertFalse(any("fetch" in call.args or "push" in call.args or "ls-remote" in call.args
                             for call in calls.call_args_list))
        self.assertTrue(receipt["fresh_git_closure_verified"])
        self.assertTrue(receipt["fresh_integrity_verified"])
        self.assertFalse(receipt["predecessor_evidence_transfer"])
        self.assertFalse(receipt["effect_ack_done"])

    def test_repeated_reconstruction_is_byte_identical_but_observation_is_fresh(self) -> None:
        one, two = self.base / "one", self.base / "two"
        first = node.restore_snapshot(self.snapshot, one, self.sha)
        second = node.restore_snapshot(self.snapshot, two, self.sha)
        third = node.restore_snapshot(self.snapshot, one, self.sha)
        self.assertEqual(node.observe(one), node.observe(two))
        self.assertEqual(node.git(one, "cat-file", "--batch-all-objects", "--batch"),
                         node.git(two, "cat-file", "--batch-all-objects", "--batch"))
        self.assertEqual(len({r["observation_id"] for r in (first, second, third)}), 3)
        self.assertEqual((one / "payload.bin").read_bytes(), (two / "payload.bin").read_bytes())
        node.export_snapshot(one, self.base / "self-clone", "ingolf-lohmann/qik-vrt")
        self.assertEqual(node.load_json(self.base / "self-clone/snapshot.json")["subject"], self.original)

    def test_authority_and_mirror_sources_have_same_recovery_semantics(self) -> None:
        sha = node.export_snapshot(self.source, self.base / "authority-snapshot", "Goldkelch/qik-vrt")
        receipt = node.restore_snapshot(self.base / "authority-snapshot", self.base / "authority-restored", sha)
        self.assertEqual(receipt["subject"], self.original)
        self.assertEqual(receipt["state"], "RECOVERED_ISOLATED")

    def test_corrupt_bundle_fails_before_destination_exists(self) -> None:
        path = self.snapshot / "node.bundle"
        raw = bytearray(path.read_bytes())
        raw[len(raw) // 2] ^= 1
        path.write_bytes(raw)
        destination = self.base / "bad"
        with self.assertRaisesRegex(node.GenesisBlock, "bundle bytes/digest mismatch"):
            node.restore_snapshot(self.snapshot, destination, self.sha)
        self.assertFalse(destination.exists())

    def test_incomplete_bundle_and_surplus_members_fail_closed(self) -> None:
        path = self.snapshot / "snapshot.sha256"
        raw = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(node.GenesisBlock, "snapshot files"):
            node.restore_snapshot(self.snapshot, self.base / "missing", self.sha)
        path.write_bytes(raw)
        (self.snapshot / "surplus").write_bytes(b"unexpected")
        with self.assertRaisesRegex(node.GenesisBlock, "snapshot files"):
            node.restore_snapshot(self.snapshot, self.base / "extra", self.sha)

    def test_prerequisite_bundle_cannot_borrow_source_or_other_remotes(self) -> None:
        node.git(self.source, "bundle", "create", "--quiet", str(self.snapshot / "node.bundle"),
                 "HEAD~1..HEAD")
        sha = self.reanchor()
        destination = self.base / "thin"
        with self.assertRaisesRegex(node.GenesisBlock, "Git bundle failed"):
            node.restore_snapshot(self.snapshot, destination, sha)
        self.assertFalse(destination.exists())

    def test_reanchored_malformed_pack_still_fails_full_import(self) -> None:
        path = self.snapshot / "node.bundle"
        path.write_bytes(path.read_bytes()[:-80])
        sha = self.reanchor()
        destination = self.base / "truncated"
        with self.assertRaises(node.GenesisBlock):
            node.restore_snapshot(self.snapshot, destination, sha)
        self.assertFalse(destination.exists())

    def test_stale_or_tampered_trusted_root_fails(self) -> None:
        with self.assertRaisesRegex(node.GenesisBlock, "root digest mismatch"):
            node.restore_snapshot(self.snapshot, self.base / "wrong-root", "0" * 64)
        (self.snapshot / "snapshot.json").write_bytes(b"{}\n")
        with self.assertRaisesRegex(node.GenesisBlock, "root digest mismatch"):
            node.restore_snapshot(self.snapshot, self.base / "tampered", self.sha)

    def test_noncanonical_and_duplicate_metadata_fail_even_with_matching_digest(self) -> None:
        for raw in (b'{"schema":"one","schema":"two"}\n',
                    json.dumps(node.load_json(self.snapshot / "snapshot.json")).encode()):
            (self.snapshot / "snapshot.json").write_bytes(raw)
            sha = hashlib.sha256(raw).hexdigest()
            (self.snapshot / "snapshot.sha256").write_text(sha + "\n")
            with self.assertRaises(node.GenesisBlock):
                node.restore_snapshot(self.snapshot, self.base / "noncanonical", sha)

    def test_ref_coverage_cannot_be_silently_narrowed(self) -> None:
        sha = self.reanchor(lambda v: v["subject"]["refs"].pop())
        with self.assertRaisesRegex(node.GenesisBlock, "ref coverage differs"):
            node.restore_snapshot(self.snapshot, self.base / "missing-ref", sha)

    def test_reconstructed_tree_must_match_declared_exact_subject(self) -> None:
        sha = self.reanchor(lambda v: v["subject"].update(tree="f" * 40))
        destination = self.base / "wrong-tree"
        with self.assertRaisesRegex(node.GenesisBlock, "history/refs/tree/bytes differ"):
            node.restore_snapshot(self.snapshot, destination, sha)
        self.assertFalse(destination.exists())

    def test_existing_modified_destination_is_not_overwritten(self) -> None:
        destination = self.base / "existing"
        node.restore_snapshot(self.snapshot, destination, self.sha)
        (destination / "payload.bin").write_bytes(b"local bytes must survive")
        with self.assertRaises(node.GenesisBlock):
            node.restore_snapshot(self.snapshot, destination, self.sha)
        self.assertEqual((destination / "payload.bin").read_bytes(), b"local bytes must survive")

    def test_symlink_snapshot_members_and_destinations_fail(self) -> None:
        member = self.snapshot / "snapshot.sha256"
        outside = self.base / "detached"
        member.rename(outside)
        member.symlink_to(outside)
        with self.assertRaises(node.GenesisBlock):
            node.restore_snapshot(self.snapshot, self.base / "unsafe", self.sha)
        link = self.base / "linked-destination"
        link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(node.GenesisBlock):
            node.restore_snapshot(self.snapshot, link, self.sha)

    def test_uncommitted_node_cannot_claim_full_persisted_state(self) -> None:
        self.write("uncommitted", b"not in Git")
        with self.assertRaisesRegex(node.GenesisBlock, "dirty/untracked"):
            node.export_snapshot(self.source, self.base / "dirty", "ingolf-lohmann/qik-vrt")

    def test_shallow_promisor_alternate_and_replace_sources_fail(self) -> None:
        for name in ("shallow", "objects/info/alternates", "objects/pack/fake.promisor"):
            path = self.source / ".git" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.first + "\n" if name == "shallow" else "external\n")
            try:
                with self.subTest(name=name), self.assertRaises(node.GenesisBlock):
                    node.export_snapshot(self.source, self.base / "incomplete", "ingolf-lohmann/qik-vrt")
            finally:
                path.unlink()
        node.git(self.source, "config", "remote.lost.promisor", "true")
        with self.assertRaisesRegex(node.GenesisBlock, "partial/promisor"):
            node.export_snapshot(self.source, self.base / "promisor", "ingolf-lohmann/qik-vrt")
        node.git(self.source, "config", "--unset", "remote.lost.promisor")
        node.git(self.source, "update-ref", "refs/replace/" + self.first, self.head)
        with self.assertRaisesRegex(node.GenesisBlock, "replace refs"):
            node.export_snapshot(self.source, self.base / "replace", "ingolf-lohmann/qik-vrt")

    def test_missing_historical_object_is_a_real_closure_failure(self) -> None:
        oid = node.git(self.source, "rev-parse", self.first + ":payload.bin").strip()
        path = self.source / ".git/objects" / oid[:2] / oid[2:]
        self.assertTrue(path.exists())
        path.unlink()
        with self.assertRaises(node.GenesisBlock):
            node.export_snapshot(self.source, self.base / "missing-history", "ingolf-lohmann/qik-vrt")

    def test_unreachable_persisted_objects_must_be_retained_instead_of_dropped(self) -> None:
        blob_file = self.base / "orphan.bin"
        blob_file.write_bytes(b"previously persisted but unreferenced")
        oid = node.git(self.source, "hash-object", "-w", str(blob_file)).strip()
        with self.assertRaisesRegex(node.GenesisBlock, "retention refs"):
            node.export_snapshot(self.source, self.base / "orphan", "ingolf-lohmann/qik-vrt")
        node.git(self.source, "update-ref", "refs/qikvrt-retained/" + oid, oid)
        sha = node.export_snapshot(self.source, self.base / "retained", "ingolf-lohmann/qik-vrt")
        node.restore_snapshot(self.base / "retained", self.base / "retained-restore", sha)
        self.assertEqual(node.git(self.base / "retained-restore", "cat-file", "blob", oid),
                         "previously persisted but unreferenced")

    def test_active_gitlink_requires_own_payload_materialization(self) -> None:
        node.git(self.source, "update-index", "--add", "--cacheinfo", "160000," + self.first + ",external-module")
        node.git(self.source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", "external gitlink")
        # A missing checkout may appear dirty before the stricter gitlink gate;
        # either observation is an actual fail-closed result, never a full node.
        with self.assertRaises(node.GenesisBlock):
            node.export_snapshot(self.source, self.base / "gitlink", "ingolf-lohmann/qik-vrt")

    def test_detached_head_is_restored_without_inventing_a_branch(self) -> None:
        node.git(self.source, "update-ref", "--no-deref", "HEAD", self.head)
        sha = node.export_snapshot(self.source, self.base / "detached", "ingolf-lohmann/qik-vrt")
        receipt = node.restore_snapshot(self.base / "detached", self.base / "detached-restore", sha)
        self.assertIsNone(receipt["subject"]["head_symbolic_ref"])
        self.assertEqual(node.git(self.base / "detached-restore", "symbolic-ref", "-q", "HEAD", optional=True), "")

    def test_roles_create_one_exact_parent_successor_with_preserved_lifecycle(self) -> None:
        cases = (("RECOVERY_AUTHORITY", "ingolf-lohmann/qik-vrt", "AUTHORITY"),
                 ("MIRROR", "ingolf-lohmann/new-mirror", "MIRROR"),
                 ("CHILD", "Goldkelch/new-child", "AUTHORITY"))
        for kind, repository, role in cases:
            with self.subTest(kind=kind):
                target = self.base / kind
                result = node.genesis(self.snapshot, target, self.sha, repository=repository,
                                      kind=kind, expected_head=self.head, authorize_local_candidate=True)
                self.assertEqual(result["role"], role)
                self.assertEqual(result["state"], "CANDIDATE_ISOLATED")
                self.assertFalse(result["effect_ack_done"])
                self.assertEqual(result["external_effects"], [])
                self.assertEqual(node.git(target, "rev-parse", "HEAD^1").strip(), self.head)
                self.assertEqual(node.git(target, "rev-parse", "refs/heads/main").strip(), self.head)
                for path in ("registry/nodes.tsv", "state/lifecycle.json",
                             "qikvrt/runtime/onboarding/NODE_HEALTH.json", "payload.bin"):
                    self.assertEqual((target / path).read_bytes(), (self.source / path).read_bytes())
                self.assertTrue(integrity.verify(target).ok)
                changed = node.git(target, "diff", "--name-only", self.head, "HEAD").splitlines()
                self.assertEqual(set(changed), {node.BINDING, node.REMOTE_POLICY, *integrity.INTEGRITY_PATHS})
                binding = node.load_json(target / node.BINDING, canonical_required=True)
                self.assertEqual(binding["ancestry"][0], "Goldkelch/qik-vrt")
                self.assertEqual(binding["ancestry"][-1], repository)
                self.assertFalse(binding["predecessor_evidence_transfer"])
                with mock.patch.object(controller, "REMOTE_ROLE_POLICY", target / node.REMOTE_POLICY), \
                     mock.patch.object(controller.self_heal, "run", side_effect=AssertionError("external execution")):
                    with self.assertRaisesRegex(controller.PreEffectBlock, "isolated"):
                        controller._execution_source_remote()

    def test_genesis_commit_and_identity_are_deterministic(self) -> None:
        results = [node.genesis(self.snapshot, self.base / name, self.sha,
                               repository="Goldkelch/repeat-child", kind="CHILD", expected_head=self.head,
                               authorize_local_candidate=True) for name in ("child-one", "child-two")]
        self.assertEqual(results[0], results[1])
        for name in integrity.INTEGRITY_PATHS | {node.BINDING, node.REMOTE_POLICY}:
            self.assertEqual((self.base / "child-one" / name).read_bytes(),
                             (self.base / "child-two" / name).read_bytes())

    def test_genesis_rejects_unbound_permission_stale_head_and_invalid_hierarchy(self) -> None:
        cases = [dict(authorize_local_candidate=False), dict(expected_head="0" * 40),
                 dict(kind="CHILD", repository="someone/child"),
                 dict(kind="MIRROR", repository="Goldkelch/qik-vrt"),
                 dict(kind="RECOVERY_AUTHORITY", repository="Goldkelch/another-node")]
        for overrides in cases:
            args = dict(repository="ingolf-lohmann/qik-vrt", kind="RECOVERY_AUTHORITY",
                        expected_head=self.head, authorize_local_candidate=True)
            args.update(overrides)
            with self.subTest(overrides=overrides), self.assertRaises(node.GenesisBlock):
                node.genesis(self.snapshot, self.base / "blocked-genesis", self.sha, **args)
            self.assertFalse((self.base / "blocked-genesis").exists())

    def test_fresh_integrity_failure_cannot_be_exported_as_success(self) -> None:
        self.write(integrity.DETACHED_NAME, b"0" * 64 + b"\n")
        node.git(self.source, "add", integrity.DETACHED_NAME)
        node.git(self.source, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", "broken integrity")
        with self.assertRaisesRegex(node.GenesisBlock, "fresh repository integrity failed"):
            node.export_snapshot(self.source, self.base / "bad-integrity", "ingolf-lohmann/qik-vrt")

    def test_machine_contract_agrees_with_executable_boundaries(self) -> None:
        policy = json.loads((ROOT / "policy/QIKVRT_NODE_GENESIS_RECOVERY_V1.json").read_text())
        self.assertEqual(policy["capabilities_to_rebind"], node.REBIND)
        self.assertEqual(policy["role_genesis"]["kinds"], list(node.KINDS))
        self.assertEqual(policy["snapshot_schema"], node.SCHEMA)
        self.assertFalse(policy["effects"]["external_repository_creation_implemented"])
        self.assertFalse(policy["effects"]["predecessor_evidence_transfer"])
        self.assertFalse(policy["effects"]["force_push"])


if __name__ == "__main__":
    unittest.main()
