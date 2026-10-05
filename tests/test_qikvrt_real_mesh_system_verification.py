#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Tests for the reflexive real-mesh system verification tool."""
from __future__ import annotations

import copy
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
from unittest.mock import patch

from tools import qikvrt_real_mesh as mesh
from tools import qikvrt_real_mesh_system_verification as sysverify

SOURCE_HEAD = "a" * 40
SOURCE_TREE = "b" * 40


def _minimal_receipt(*, overrides: dict | None = None) -> dict:
    """Build a minimal conformant execution receipt for contract testing."""
    base: dict = {
        "schema": "qikvrt_real_mesh_execution_receipt_v1",
        "mesh_id": mesh.MESH_ID,
        "source_head": SOURCE_HEAD,
        "source_tree": SOURCE_TREE,
        "pair_count": 2,
        "node_process_count": 4,
        "network_scope": mesh.NETWORK_SCOPE,
        "event_model": "SOCKET_EVENT_DRIVEN_NO_DOMAIN_POLLING",
        "redundant_path_observed": True,
        "routes": [
            {
                "observation": {
                    "path": [
                        "node-1",
                        "node-2",
                        "node-3",
                    ]
                },
                "bounded_effect_ack": {"state": "DONE"},
            },
            {
                "observation": {
                    "path": [
                        "node-3",
                        "node-4",
                        "node-1",
                    ]
                },
                "bounded_effect_ack": {"state": "DONE"},
            },
        ],
        "restart_replay": {
            "node_id": "node-1",
            "same_terminal_receipt": True,
            "ledger_record_count_unchanged": True,
            "observed": True,
        },
        "completion_claims": {
            "real_multi_pair_mesh_runtime_executed": True,
            "independent_tcp_node_processes_observed": True,
            "multi_hop_delivery_reobserved": True,
            "acknowledgement_return_path_observed": True,
            "append_only_restart_persistence_observed": True,
            "bounded_loopback_effect_ack_done": True,
            "general_effect_ack_done": False,
            "general_internet_reachability": False,
            "production_deployment": False,
            "physical_hardware_execution": False,
            "authority_mirror_synchronization": False,
            "authority_mirror_equality_claimed": False,
            "merge": False,
            "PASS": False,
            "FINAL_PASS": False,
        },
        "effect_ack_scope": mesh.EFFECT_ACK_SCOPE,
        "external_effect": "NONE",
        "receipt_created_utc": "2026-08-24T21:00:00.000000Z",
    }
    if overrides:
        base.update(overrides)
    return base


class VerifyReceiptPureContractTests(unittest.TestCase):
    """Pure-contract tests: verify_receipt against the declared specification."""

    def setUp(self) -> None:
        self.contract = sysverify.load_contract()

    def test_conformant_receipt_has_no_findings(self) -> None:
        r = _minimal_receipt()
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertEqual(findings, [])

    def test_wrong_schema_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"schema": "wrong_schema"})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("schema" in f for f in findings), findings)

    def test_wrong_mesh_id_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"mesh_id": "WRONG_MESH"})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("mesh_id" in f for f in findings), findings)

    def test_insufficient_pair_count_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"pair_count": 1})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("pair_count" in f for f in findings), findings)

    def test_insufficient_node_count_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"node_process_count": 2})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("node_process_count" in f for f in findings), findings)

    def test_non_redundant_path_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"redundant_path_observed": False})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("redundant" in f for f in findings), findings)

    def test_wrong_network_scope_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"network_scope": "PUBLIC_INTERNET"})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("network_scope" in f for f in findings), findings)

    def test_restart_replay_failure_is_a_finding(self) -> None:
        r = _minimal_receipt()
        r["restart_replay"]["same_terminal_receipt"] = False
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("same_terminal_receipt" in f for f in findings), findings)

    def test_false_general_effect_ack_done_required(self) -> None:
        r = _minimal_receipt()
        r["completion_claims"]["general_effect_ack_done"] = True
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(
            any("general_effect_ack_done" in f for f in findings), findings
        )

    def test_false_pass_claim_required(self) -> None:
        r = _minimal_receipt()
        r["completion_claims"]["PASS"] = True
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("PASS" in f for f in findings), findings)

    def test_wrong_effect_ack_scope_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"effect_ack_scope": "GENERAL"})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("effect_ack_scope" in f for f in findings), findings)

    def test_missing_routes_is_a_finding(self) -> None:
        r = _minimal_receipt(overrides={"routes": []})
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("route" in f or "path" in f for f in findings), findings)

    def test_receipt_sha256_mismatch_is_a_finding(self) -> None:
        r = _minimal_receipt()
        r["receipt_sha256"] = "0" * 64
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertTrue(any("sha256" in f for f in findings), findings)

    def test_receipt_sha256_match_is_not_a_finding(self) -> None:
        r = _minimal_receipt()
        r["receipt_sha256"] = sysverify.canonical_sha256(r)
        findings = sysverify.verify_receipt(r, self.contract)
        self.assertEqual(findings, [])


class AuditReceiptStructureTests(unittest.TestCase):
    """Verify that the audit receipt structure is well-formed."""

    def setUp(self) -> None:
        self.contract = sysverify.load_contract()
        self.reflexive_standard = sysverify.load_reflexive_standard()

    def _audit(self, findings: list[str]) -> dict:
        r = _minimal_receipt()
        return sysverify.build_audit_receipt(
            receipt_path="/tmp/test_receipt.json",
            receipt=r,
            contract=self.contract,
            findings=findings,
            reflexive_standard=self.reflexive_standard,
        )

    def test_conformant_receipt_produces_pass_status(self) -> None:
        audit = self._audit([])
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["finding_count"], 0)

    def test_findings_produce_block_status(self) -> None:
        audit = self._audit(["some finding"])
        self.assertEqual(audit["status"], "BLOCK")
        self.assertEqual(audit["finding_count"], 1)

    def test_audit_schema_is_correct(self) -> None:
        audit = self._audit([])
        self.assertEqual(audit["schema"], sysverify.AUDIT_SCHEMA)

    def test_audit_has_sha256(self) -> None:
        audit = self._audit([])
        self.assertIn("audit_sha256", audit)
        sha = audit["audit_sha256"]
        self.assertIsInstance(sha, str)
        self.assertTrue(sha.startswith("sha256:"), sha)
        self.assertEqual(len(sha), 71)  # "sha256:" (7) + 64 hex chars

    def test_general_effect_ack_done_always_false_in_audit(self) -> None:
        audit = self._audit([])
        self.assertIs(audit["general_effect_ack_done"], False)

    def test_external_effect_always_none_in_audit(self) -> None:
        audit = self._audit([])
        self.assertEqual(audit["external_effect"], "NONE")

    def test_transport_ack_is_not_effect_ack_in_audit(self) -> None:
        audit = self._audit([])
        self.assertIs(audit["transport_ack_is_effect_ack"], False)


class ContractAndStandardLoadTests(unittest.TestCase):
    """Verify that the declared artefacts are loadable and structurally valid."""

    def test_load_contract_succeeds(self) -> None:
        contract = sysverify.load_contract()
        self.assertEqual(contract["schema"], "qikvrt_real_mesh_contract_v1")
        self.assertEqual(contract["mesh_id"], "QIKVRT_REAL_MULTI_PAIR_MESH_V1")

    def test_load_reflexive_standard_succeeds(self) -> None:
        std = sysverify.load_reflexive_standard()
        self.assertIn("id", std)
        self.assertIn("status", std)
        self.assertIn("mandatory_correction_layers", std)
        self.assertIn("TESTS", std["mandatory_correction_layers"])

    def test_contract_minimum_topology_is_present(self) -> None:
        contract = sysverify.load_contract()
        topo = contract["minimum_topology"]
        self.assertGreaterEqual(topo["pair_count"], 2)
        self.assertGreaterEqual(topo["node_process_count"], 4)
        self.assertTrue(topo["redundant_routes_required"])

    def test_contract_effect_boundary_forbids_general_effect_ack(self) -> None:
        contract = sysverify.load_contract()
        self.assertFalse(contract["effect_boundary"]["general_effect_ack_done"])

    def test_contract_transport_scope_is_loopback_only(self) -> None:
        contract = sysverify.load_contract()
        self.assertEqual(
            contract["transport"]["network_scope"],
            "LOOPBACK_TCP_ONLY",
        )


class MultitaskingCorpusTests(unittest.TestCase):
    def test_held_and_completed_history_survives_byte_exact_consolidation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            path = root / "node.jsonl"
            ledger = mesh.AppendOnlyNodeLedger(path, "node")
            ledger.append("ACCEPTED", "failed", accepted={"message_sha256": "original"})
            ledger.append("HELD", "failed", response={"reason": "unreachable", "ordinary_release": False})
            ledger.append("ACCEPTED", "completed", accepted={"message_sha256": "success"})
            ledger.append("COMPLETED", "completed", response={"source": "retained"})
            before = path.read_bytes()
            receipt = sysverify.consolidate_node_ledgers({"node": path}, root / "corpus.zip")
            with zipfile.ZipFile(root / "corpus.zip") as archive:
                self.assertEqual(archive.read("node.jsonl"), before)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(receipt["inputs"]["node"]["records"], 4)
            self.assertEqual(receipt["inputs"]["node"]["accepted"], ["completed", "failed"])
            self.assertEqual(receipt["inputs"]["node"]["completed"], ["completed"])
            self.assertTrue(receipt["zero_missing_or_changed_bytes"])
            with self.assertRaises(FileExistsError):
                sysverify.consolidate_node_ledgers({"node": path}, root / "corpus.zip")

    def test_corrupt_history_cannot_be_consolidated_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            path = root / "node.jsonl"
            ledger = mesh.AppendOnlyNodeLedger(path, "node")
            ledger.append("HELD", "failed", response={"reason": "unreachable"})
            path.write_bytes(path.read_bytes().replace(b"unreachable", b"fabricated"))
            with self.assertRaises(mesh.MeshRuntimeError):
                sysverify.consolidate_node_ledgers({"node": path}, root / "corpus.zip")
            self.assertFalse((root / "corpus.zip").exists())

    def test_unknown_scale_or_unbound_subject_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            workdir = pathlib.Path(directory) / "must-not-exist"
            args = dict(repository="Goldkelch/qik-vrt", source_head=SOURCE_HEAD, source_tree=SOURCE_TREE,
                        counterpart_head=SOURCE_HEAD, counterpart_tree=SOURCE_TREE)
            for counts in ((), (4, 4), (2,), (32,), (True,)):
                with self.assertRaises(sysverify.VerificationError):
                    sysverify.run_multitasking(workdir, node_counts=counts, **args)
            with self.assertRaises(sysverify.VerificationError):
                sysverify.run_multitasking(workdir, **{**args, "source_head": "main"})
            self.assertFalse(workdir.exists())

    def test_real_parallel_corpus_has_no_lost_effect_and_no_remote_execution_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            report = sysverify.run_multitasking(pathlib.Path(directory) / "run",
                repository="Goldkelch/qik-vrt", source_head=SOURCE_HEAD, source_tree=SOURCE_TREE,
                counterpart_head=SOURCE_HEAD, counterpart_tree=SOURCE_TREE, node_counts=(4,), repetitions=1)
            run = report["runs"][0]
            self.assertEqual(run["messages_completed"], 4)
            self.assertEqual(run["ledger_records"], 32)
            self.assertTrue(all(n >= 2 for n in run["peak_inflight_by_node"].values()))
            self.assertTrue(run["restart_recovery_success"])
            self.assertFalse(report["source_binding_verified"])
            self.assertFalse(report["counterpart_reference"]["execution_verified_by_this_run"])
            self.assertFalse(report["completion_claims"]["whole_repository_completion"])
            projection = dict(report)
            stored = projection.pop("receipt_sha256")
            self.assertEqual(stored, sysverify.canonical_sha256(projection))



class WorkflowScratchBoundaryTests(unittest.TestCase):
    """Keep generated multitasking evidence outside the exact source checkout."""

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="qikvrt-workflow-source-")
        self.addCleanup(temporary.cleanup)
        self.source = pathlib.Path(temporary.name) / "checkout"
        self.scratch = pathlib.Path(temporary.name) / "runner-temp" / "multitasking"
        self.source.mkdir()
        self.repository = "Goldkelch/qik-vrt"
        self.workflow = (
            sysverify.ROOT
            / ".github/workflows/qikvrt_real_mesh_system_verification.yml"
        ).read_text(encoding="utf-8")
        # Commit the actual implementation and every input hashed by its report.
        for name in (
            "tools/__init__.py",
            "tools/qikvrt_real_mesh.py",
            "tools/qikvrt_real_mesh_system_verification.py",
            "src/qikvrt_effect_ack.py",
            "tests/test_qikvrt_real_mesh.py",
            "tests/test_qikvrt_real_mesh_system_verification.py",
            "state/mesh/QIKVRT_REAL_MESH_V1.json",
        ):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((sysverify.ROOT / name).read_bytes())
        self._git("init", "--quiet", "--template=")
        self._git("remote", "add", "origin", "https://github.com/Goldkelch/qik-vrt.git")
        self._git("add", ".")
        self._git("-c", "user.name=Workflow regression fixture",
                  "-c", "user.email=workflow-fixture@example.invalid",
                  "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Fixture")
        self.head = self._git("rev-parse", "HEAD").strip()
        self.tree = self._git("rev-parse", "HEAD^{tree}").strip()
        self.counterpart = {"sha": SOURCE_HEAD, "commit": {"tree": {"sha": SOURCE_TREE}}}

    def _git(self, *args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(self.source), *args], text=True, stderr=subprocess.PIPE
        )

    def _python(self, script: str, *, scratch: pathlib.Path | None = None):
        return subprocess.run(
            [sys.executable, "-B", "-c", script], cwd=self.source,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
                 "PYTHONPATH": str(self.source),
                 "REPOSITORY": self.repository, "GH_TOKEN": "OFFLINE_TEST_FIXTURE",
                 "MULTITASKING_DIR": str(scratch or self.scratch)},
            text=True, capture_output=True, timeout=120,
        )

    def _workflow_execution(self, *, scratch: pathlib.Path | None = None):
        step = self.workflow.split(
            "      - name: Execute bounded repository multitasking and lossless corpus\n", 1
        )[1].split("\n      - name:", 1)[0]
        script = textwrap.dedent(step.split("python3 - <<'PY'\n", 1)[1].split("\n          PY", 1)[0])
        # Reproduce mkdir + the actual workflow heredoc. Only the remote HTTP
        # observation is an explicit offline fixture; Git, CLI and TCP are real.
        (scratch or self.scratch).mkdir(parents=True)
        wrapper = (
            "import io\nfrom unittest.mock import patch\n"
            f"with patch('urllib.request.urlopen', return_value=io.BytesIO({json.dumps(self.counterpart).encode()!r})):\n"
            f"    exec({script!r}, {{'__name__': '__main__'}})\n"
        )
        return self._python(wrapper, scratch=scratch)

    def _cli(self) -> list[str]:
        return ["multitasking", "--repository", self.repository,
                "--source-head", self.head, "--source-tree", self.tree,
                "--counterpart-head", SOURCE_HEAD, "--counterpart-tree", SOURCE_TREE,
                "--workdir", str(self.scratch / "runtime"),
                "--output", str(self.scratch / "report.json")]

    def test_actual_workflow_runs_corpus_and_leaves_committed_source_clean(self) -> None:
        result = self._workflow_execution()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((self.scratch / "report.json").read_text())
        self.assertEqual(report["implementation_subject"], {
            "repository": self.repository, "head": self.head, "tree": self.tree,
        })
        self.assertTrue(report["source_binding_verified"])
        self.assertEqual(report["node_counts"], [4, 8, 16])
        self.assertEqual(report["repetitions"], 3)
        self.assertEqual(len(report["runs"]), 9)
        for run in report["runs"]:
            self.assertEqual(run["messages_completed"], run["node_count"])
            self.assertEqual(run["ledger_records"], 2 * run["node_count"] ** 2)
            self.assertTrue(run["restart_recovery_success"])
            self.assertTrue(run["consolidation"]["zero_missing_or_changed_bytes"])
        self.assertEqual(json.loads((self.scratch / "counterpart-reference.json").read_text()),
                         self.counterpart)
        self.assertFalse(report["counterpart_reference"]["execution_verified_by_this_run"])
        self.assertEqual(self._git("rev-parse", "HEAD").strip(), self.head)
        self.assertEqual(self._git("rev-parse", "HEAD^{tree}").strip(), self.tree)
        self.assertEqual(self._git("status", "--porcelain"), "")
        qualification = json.loads((self.scratch / "qualification.json").read_text())
        self.assertEqual(qualification["status"], "QUALIFIED_FOR_EXACT_BOUNDED_SCOPE")
        self.assertFalse(qualification["continuous_operation_proven"])
        self.assertFalse(qualification["remote_counterpart_execution"])
        # Recomputed digests cannot turn incomplete, stale or inflated evidence
        # into qualification. Use the original real corpus for every control.
        mutations = {
            "unbound": lambda r: r.update(source_binding_verified=False),
            "missing_trial": lambda r: r["runs"].pop(),
            "duplicate_trial": lambda r: r["runs"].__setitem__(1, copy.deepcopy(r["runs"][0])),
            "wrong_version": lambda r: r["input_sha256"].update({"tools/qikvrt_real_mesh.py": "0" * 64}),
            "wrong_runtime": lambda r: r["runtime"].update(python="unverified-runtime"),
            "remote_claim": lambda r: r["completion_claims"].update(remote_counterpart_executed=True),
            "unbounded_claim": lambda r: r["completion_claims"].update(unbounded_scalability=True),
            "lost_effect": lambda r: r["runs"][0].update(messages_completed=0),
            "restart_failure": lambda r: r["runs"][0].update(restart_recovery_success=False),
            "fake_overlap": lambda r: r["runs"][0]["peak_inflight_by_node"].update({"pair-a-authority": 999}),
        }
        with patch.object(sysverify, "ROOT", self.source):
            for name, mutate in mutations.items():
                with self.subTest(qualification_control=name):
                    candidate = copy.deepcopy(report)
                    mutate(candidate)
                    candidate.pop("receipt_sha256")
                    candidate["receipt_sha256"] = sysverify.canonical_sha256(candidate)
                    with self.assertRaises(sysverify.VerificationError):
                        sysverify.verify_multitasking_report(candidate, self.scratch / "runtime",
                            repository=self.repository, source_head=self.head, source_tree=self.tree)
            with self.assertRaises(sysverify.VerificationError):
                sysverify.verify_multitasking_report(report, self.scratch / "runtime",
                    repository=self.repository, source_head="0" * 40, source_tree=self.tree)
            ledger = self.scratch / "runtime/nodes-4-trial-1/ledgers/pair-a-authority.jsonl"
            original = ledger.read_bytes()
            ledger.write_bytes(original + b"{}\n")
            with self.assertRaises(sysverify.VerificationError):
                sysverify.verify_multitasking_report(report, self.scratch / "runtime",
                    repository=self.repository, source_head=self.head, source_tree=self.tree)
            ledger.write_bytes(original)

    def test_actual_mirror_workflow_requires_its_own_qualified_execution(self) -> None:
        self.repository = "ingolf-lohmann/qik-vrt"
        self._git("remote", "set-url", "origin", "https://github.com/ingolf-lohmann/qik-vrt.git")
        self.test_actual_workflow_runs_corpus_and_leaves_committed_source_clean()

    def test_legacy_in_worktree_observation_blocks_before_corpus(self) -> None:
        scratch = self.source / ".qikvrt" / "real-mesh-multitasking"
        result = self._workflow_execution(scratch=scratch)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact clean committed implementation", result.stderr)
        self.assertTrue((scratch / "counterpart-reference.json").is_file())
        self.assertFalse((scratch / "runtime").exists())
        self.assertFalse((scratch / "report.json").exists())

    def test_tracked_and_untracked_source_mutations_block_before_corpus(self) -> None:
        for name in ("src/qikvrt_effect_ack.py", "untracked-source.py"):
            with self.subTest(path=name):
                target = self.source / name
                original = target.read_bytes() if target.exists() else None
                target.write_bytes((original or b"") + b"\n# intentional source mutation\n")
                result = self._workflow_execution()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("exact clean committed implementation", result.stderr)
                self.assertFalse((self.scratch / "runtime").exists())
                self.assertFalse((self.scratch / "report.json").exists())
                if original is None:
                    target.unlink()
                else:
                    target.write_bytes(original)
                (self.scratch / "counterpart-reference.json").unlink()
                self.scratch.rmdir()

    def test_head_and_tree_mismatch_block_before_corpus(self) -> None:
        for field in ("--source-head", "--source-tree"):
            with self.subTest(field=field):
                args = self._cli()
                args[args.index(field) + 1] = "0" * 40
                result = self._python(
                    "from tools import qikvrt_real_mesh_system_verification as verifier\n"
                    f"raise SystemExit(verifier.main({args!r}))\n"
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("exact clean committed implementation", result.stderr)
                self.assertFalse((self.scratch / "runtime").exists())

    def test_tracked_and_untracked_mutations_during_execution_block_report(self) -> None:
        for name in ("src/qikvrt_effect_ack.py", "untracked-source.py"):
            with self.subTest(path=name):
                target = self.source / name
                original = target.read_bytes() if target.exists() else None
                self.scratch.mkdir(parents=True)
                # Execute real network work, then inject a mutation between
                # the opening and closing source snapshots. Do not mock Git.
                script = (
                    "from pathlib import Path\n"
                    "from tools import qikvrt_real_mesh_system_verification as verifier\n"
                    "original_run = verifier.run_multitasking\n"
                    "def mutate_during_run(*args, **kwargs):\n"
                    "    report = original_run(*args, **kwargs, node_counts=(4,), repetitions=1)\n"
                    f"    target = Path({name!r})\n"
                    "    target.write_bytes((target.read_bytes() if target.exists() else b'') + b'\\n# mutation during execution\\n')\n"
                    "    return report\n"
                    "verifier.run_multitasking = mutate_during_run\n"
                    f"raise SystemExit(verifier.main({self._cli()!r}))\n"
                )
                result = self._python(script)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("exact clean committed implementation", result.stderr)
                self.assertTrue((self.scratch / "runtime" / "nodes-4-trial-1" /
                                 "CONSOLIDATED_LEDGERS.zip").is_file(), result.stdout + result.stderr)
                self.assertFalse((self.scratch / "report.json").exists())
                self.assertNotEqual(self._git("status", "--porcelain"), "")
                if original is None:
                    target.unlink()
                else:
                    target.write_bytes(original)
                # Each subtest must execute in a fresh ephemeral runtime.
                self.scratch = self.scratch.with_name("multitasking-next")

    def test_multitasking_outputs_do_not_dirty_exact_checkout(self) -> None:
        workflow = self.workflow
        self.assertIn("'verify-multitasking'", workflow)
        self.assertIn("    - cron: '*/15 * * * *'", workflow)
        self.assertNotIn("    paths:", workflow)
        self.assertIn(
            "MULTITASKING_DIR: ${{ runner.temp }}/qikvrt-real-mesh-multitasking",
            workflow,
        )
        self.assertIn(
            "scratch = Path(os.environ['MULTITASKING_DIR'])",
            workflow,
        )
        self.assertIn(
            "path: ${{ runner.temp }}/qikvrt-real-mesh-multitasking",
            workflow,
        )
        self.assertNotIn(
            "mkdir -p .qikvrt/real-mesh-multitasking",
            workflow,
        )
        self.assertNotIn(
            "Path('.qikvrt/real-mesh-multitasking",
            workflow,
        )


class ReflexiveNetworkSystemTest(unittest.TestCase):
    """End-to-end system test: execute real TCP mesh, verify, audit."""

    def test_real_tcp_mesh_passes_all_contract_checks(self) -> None:
        """Execute four real TCP node processes and verify the receipt reflexively."""
        with tempfile.TemporaryDirectory(prefix="qikvrt-sysverify-") as tmp:
            workdir = pathlib.Path(tmp)
            receipt, contract, findings = sysverify.run_and_verify(
                source_head=SOURCE_HEAD,
                source_tree=SOURCE_TREE,
                workdir=workdir,
            )
        self.assertEqual(
            findings,
            [],
            f"Reflexive verification found {len(findings)} finding(s): {findings}",
        )
        self.assertEqual(receipt["pair_count"], 2)
        self.assertEqual(receipt["node_process_count"], 4)
        self.assertIs(receipt["completion_claims"]["general_effect_ack_done"], False)
        self.assertIs(receipt["completion_claims"]["PASS"], False)
        self.assertEqual(receipt["external_effect"], "NONE")

    def test_audit_receipt_is_well_formed_after_real_execution(self) -> None:
        """The audit receipt produced after real execution must be self-consistent."""
        contract = sysverify.load_contract()
        reflexive_standard = sysverify.load_reflexive_standard()

        with tempfile.TemporaryDirectory(prefix="qikvrt-sysverify-") as tmp:
            workdir = pathlib.Path(tmp)
            receipt, _contract, findings = sysverify.run_and_verify(
                source_head=SOURCE_HEAD,
                source_tree=SOURCE_TREE,
                workdir=workdir,
            )

        audit = sysverify.build_audit_receipt(
            receipt_path=None,
            receipt=receipt,
            contract=contract,
            findings=findings,
            reflexive_standard=reflexive_standard,
        )

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["finding_count"], 0)
        self.assertIs(audit["general_effect_ack_done"], False)
        self.assertEqual(audit["external_effect"], "NONE")
        self.assertTrue(audit["bounded_loopback_effect_ack_scope_confirmed"])
        # Verify the audit's own SHA-256
        stored = audit["audit_sha256"]
        body = {k: v for k, v in audit.items() if k != "audit_sha256"}
        self.assertEqual(stored, sysverify.canonical_sha256(body))


if __name__ == "__main__":
    import unittest

    unittest.main()
