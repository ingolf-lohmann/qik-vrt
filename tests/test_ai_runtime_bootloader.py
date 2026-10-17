#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import json
import hashlib
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools import ai_runtime_bootloader as bootloader

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AIRuntimeBootloaderContractTests(unittest.TestCase):
    def test_root_entrypoint_names_executable_bootloader(self) -> None:
        entry = (ROOT / "AI").read_text(encoding="utf-8")
        self.assertIn("QIK-VRT AI RUNTIME ENTRYPOINT", entry)
        self.assertIn("python3 -B tools/ai_runtime_bootloader.py --profile all", entry)
        self.assertIn("It performs no network access", entry)
        self.assertIn(
            "Installation, task execution, commits, merges, releases, and publication remain separate authorized effects",
            entry,
        )

    def test_context_binds_complete_runtime_lifecycle(self) -> None:
        context = json.loads((ROOT / "AI_CONTEXT.json").read_text(encoding="utf-8"))
        boot = context["runtime_bootloader"]
        self.assertEqual(boot["implementation"], "tools/ai_runtime_bootloader.py")
        self.assertFalse(boot["network_required"])
        self.assertFalse(boot["writes_repository"])
        self.assertEqual(boot["accepted_states"], ["PASS", "CONTINUE"])
        self.assertEqual(boot["blocking_state"], "BLOCK")
        self.assertGreaterEqual(len(boot["lifecycle"]), 8)
        self.assertEqual(
            context["progress_protocol"]["machine_schema"],
            "schemas/human_machine_progress.schema.json",
        )
        self.assertIn(
            "docs/HUMAN_MACHINE_PROGRESS_STANDARD.md",
            context["required_read_order"],
        )
        self.assertIn(
            "schemas/human_machine_progress.schema.json",
            context["required_read_order"],
        )
        for authority in (
            "tools/ai_handoff.py",
            "tools/qikvrt_integrity.py",
            "tools/qikvrt_tool_cache.py",
            "tools/bootstrap-runtime.sh",
        ):
            self.assertIn(authority, boot["reused_authorities"])

    def test_bootloader_is_standard_library_and_exposes_cli(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", "tools/ai_runtime_bootloader.py", "--help"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--profile", completed.stdout)
        self.assertIn("--json", completed.stdout)
        self.assertIn("--task", completed.stdout)

    def test_handoff_accepts_current_context_schema(self) -> None:
        context = json.loads((ROOT / "AI_CONTEXT.json").read_text(encoding="utf-8"))
        completed = subprocess.run(
            [sys.executable, "-B", "tools/ai_handoff.py"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"current context schema {context['schema']!r} rejected: "
            f"{completed.stderr}",
        )
        self.assertIn("AI_HANDOFF_STATUS=VALID", completed.stdout)
        self.assertIn("AI_PROGRESS_CHECK=", completed.stdout)

    def test_bootloader_source_preserves_effect_boundary(self) -> None:
        source = (ROOT / "tools/ai_runtime_bootloader.py").read_text(encoding="utf-8")
        self.assertIn("no network access", source)
        self.assertIn("tools/qikvrt_integrity.py", source)
        self.assertIn("tools/qikvrt_tool_cache.py", source)
        self.assertIn("tools/bootstrap-runtime.sh", source)
        self.assertIn('report["state"] = "BLOCK"', source)
        self.assertNotIn("shell=True", source)

    def test_ci_retains_full_history_as_authority_side_cross_check(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "qikvrt_ci.yml"
        ).read_text(encoding="utf-8")
        checkout = (
            "      - uses: "
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 "
            "# v7.0.1\n"
            "        with:\n"
        )
        self.assertIn(checkout, workflow)
        self.assertIn(
            "          ref: ${{ github.event_name == 'pull_request' && "
            "github.event.pull_request.head.sha || github.sha }}\n"
            "          fetch-depth: 0\n",
            workflow,
        )

    def test_manuscript_workflow_provisions_declared_poppler_before_h5(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "qikvrt_manuscript_proof.yml"
        ).read_text(encoding="utf-8")
        provision = workflow.index("Provision and verify declared Poppler runtime")
        verify_h5 = workflow.index("Verify VRTCore SMG H5 package")
        self.assertLess(provision, verify_h5)
        for command in ("pdfinfo", "pdftotext", "pdftoppm"):
            self.assertIn(f"command -v {command}", workflow)
            self.assertIn(f"{command} -v", workflow)
        self.assertIn("apt-get update -o Acquire::Retries=3", workflow)
        self.assertIn(
            "apt-get install --yes --no-install-recommends poppler-utils",
            workflow,
        )
        self.assertIn("poppler-utils-package=${Version}", workflow)

    def test_handoff_is_portable_when_source_commit_is_not_in_local_git(self) -> None:
        with tempfile.TemporaryDirectory() as empty_objects:
            environment = dict(os.environ)
            environment.update(
                {
                    "GIT_OBJECT_DIRECTORY": empty_objects,
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES": "",
                    "GIT_NO_LAZY_FETCH": "1",
                    "GIT_NO_REPLACE_OBJECTS": "1",
                    "GIT_TERMINAL_PROMPT": "0",
                }
            )
            completed = subprocess.run(
                [sys.executable, "-B", "tools/ai_handoff.py"],
                cwd=ROOT,
                env=environment,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("AI_HANDOFF_STATUS=VALID", completed.stdout)
        self.assertNotIn("source commit is unavailable", completed.stderr)


class StandpointDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.context = json.loads((ROOT / "AI_CONTEXT.json").read_text())
        self.signature_path = self.root / bootloader.SIGNATURE_PATH
        self.signature_path.parent.mkdir()
        self.signature_path.write_bytes((ROOT / bootloader.SIGNATURE_PATH).read_bytes())
        self.contract_path = self.root / bootloader.CODEC_CONTRACT_PATH
        self.contract_path.parent.mkdir()
        self.contract_path.write_bytes((ROOT / bootloader.CODEC_CONTRACT_PATH).read_bytes())

    def resolve(self):
        return bootloader.load_standpoint(self.context, self.root)

    def test_exact_local_bytes_are_resolved_with_provenance_and_effect_limits(self):
        report = self.resolve()
        self.assertEqual(report["bytes"], 400)
        self.assertEqual(report["path"], bootloader.SIGNATURE_PATH)
        self.assertEqual(report["sha256"],
                         "27a84a7e19e1b46f50d3a855b87da65f5fe07b806575b0d15ca0587b7cab5792")
        self.assertEqual(report["git_blob_sha1"], "9b06a2b407fb99d99d2bda5a3decc80ab68a092b")
        self.assertFalse(report["recovered_historical_owner_seed"])
        self.assertFalse(report["github_authentication_or_account_recovery"])
        self.assertFalse(report["main_adoption_or_external_effect_verified"])

    def test_missing_signature_is_not_replaced_by_an_archive_search(self):
        self.signature_path.rename(self.signature_path.parent / "handshake_core.c")
        with self.assertRaisesRegex(bootloader.BootBlock, "missing"):
            self.resolve()

    def test_wrong_byte_count_is_never_truncated_or_padded(self):
        for size in (0, 399, 401, 417):
            with self.subTest(size=size):
                self.signature_path.write_bytes(b"x" * size)
                with self.assertRaisesRegex(bootloader.BootBlock, "exactly 400"):
                    self.resolve()

    def test_changed_400_byte_artifact_is_rejected(self):
        data = bytearray(self.signature_path.read_bytes())
        data[-1] = 1
        self.signature_path.write_bytes(data)
        with self.assertRaisesRegex(bootloader.BootBlock, "byte identity"):
            self.resolve()

    def test_rehashed_foreign_standpoint_and_context_do_not_create_authority(self):
        data = bytearray(self.signature_path.read_bytes())
        data[48:329] = data[48:329].replace(b"QIKVRT", b"QIKvRT")
        data[16:48] = hashlib.sha256(b"QIKVRT-STANDPOINT-V1\0" + data[:16] + data[48:329]).digest()
        self.signature_path.write_bytes(data)
        self.context["standpoint_codex"]["signature_sha256"] = hashlib.sha256(data).hexdigest()
        with self.assertRaisesRegex(bootloader.BootBlock, "context binding"):
            self.resolve()

    def test_legacy_path_size_boolean_and_digest_drift_are_blocking(self):
        binding = self.context["standpoint_codex"]
        for key, value in (("signature_path", "../handshake.c"),
                           ("signature_bytes", True),
                           ("signature_sha256", "0" * 64),
                           ("signature_git_blob_sha1", "0" * 40)):
            old = binding[key]
            with self.subTest(key=key):
                binding[key] = value
                with self.assertRaises(bootloader.BootBlock):
                    self.resolve()
            binding[key] = old

    def test_codec_contract_drift_or_historical_recovery_claim_is_blocking(self):
        contract = json.loads(self.contract_path.read_text())
        for field, value in (("signature", {"path": "handshake.c"}),
                             ("semantic_source", {"recovered_historical_400_byte_image": True})):
            altered = json.loads(json.dumps(contract))
            altered["standpoint"][field] = value
            self.contract_path.write_text(json.dumps(altered))
            with self.subTest(field=field), self.assertRaises(bootloader.BootBlock):
                self.resolve()

    def test_missing_binding_and_invalid_contract_are_blocking(self):
        with self.assertRaises(bootloader.BootBlock):
            bootloader.load_standpoint({}, self.root)
        for data in (b"[]", b"{", b"\xff"):
            self.contract_path.write_bytes(data)
            with self.subTest(data=data), self.assertRaises(bootloader.BootBlock):
                self.resolve()

    def test_symlink_is_not_treated_as_canonical_repository_bytes(self):
        external = self.root / "external.bin"
        self.signature_path.rename(external)
        self.signature_path.symlink_to(external)
        with self.assertRaisesRegex(bootloader.BootBlock, "symlink"):
            self.resolve()

    def test_startup_reports_the_standpoint_and_does_not_hide_a_block(self):
        gate = {"name": "fixture", "state": "PASS", "stdout": "", "stderr": "", "exit_code": 0}
        for invalid in (False, True):
            with self.subTest(invalid=invalid), patch.object(bootloader, "run_gate", return_value=gate), \
                    patch.object(bootloader, "git_value", return_value="fixture"), \
                    patch.object(sys, "argv", ["bootloader", "--json"]):
                if invalid:
                    standpoint = patch.object(bootloader, "load_standpoint",
                                               side_effect=bootloader.BootBlock("fixture signature missing"))
                else:
                    standpoint = patch.object(bootloader, "load_standpoint", return_value=self.resolve())
                output = io.StringIO()
                with standpoint, redirect_stdout(output):
                    status = bootloader.main()
                report = json.loads(output.getvalue())
                self.assertEqual(status, 2 if invalid else 0)
                self.assertEqual(report["state"], "BLOCK" if invalid else "PASS")
                if invalid:
                    self.assertIn("signature missing", report["blocker"])
                else:
                    self.assertEqual(report["standpoint"]["bytes"], 400)
                    self.assertIn("400 byte standpoint", [g["name"] for g in report["gates"]])


if __name__ == "__main__":
    unittest.main(verbosity=2)
