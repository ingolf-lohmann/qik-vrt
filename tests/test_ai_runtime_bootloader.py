#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import json
import copy
import contextlib
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

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


class ClientContinuationRegressionTests(unittest.TestCase):
    """Client behavior receipts are fixtures, never productive effect evidence."""

    def setUp(self) -> None:
        from tools import ai_handoff
        self.handoff = ai_handoff
        self.subject = {
            "repository": "ingolf-lohmann/qik-vrt", "head": "a" * 40, "tree": "b" * 40,
        }
        self.receipt = {
            "schema": "qikvrt-client-continuation/1",
            "subject": self.subject,
            "authorization": {"granted": True, "source": "fixture:owner-authorized-task"},
            "requested_authorization_again": False,
            "inventory": {kind: "fixture:observed:" + kind
                          for kind in ("repository", "connector", "cli", "mesh")},
            "attempts": [],
            "next_actions": [{
                "subject": self.subject, "route": "connector", "service": "github",
                "operation": "leased-pr-ref-update", "method": "PATCH",
                "observed_operation": "leased-pr-ref-update", "observed_method": "PATCH",
                "observed_repository": self.subject["repository"],
                "transport": "REST_API_ONLY", "evidence": "fixture:callable-contract",
                **{key: True for key in ("authorized", "safe", "deterministic", "callable",
                                        "authenticated", "permitted", "admitted")},
            }],
            "state": "CONTINUE",
            "readback": {
                "repository": {**self.subject, "ref": "main", "source": "fixture:fresh-rest-read"},
                "delivery": {"hostname": "raumzeitterminal.de", "state": "UNKNOWN",
                             "source": "fixture:exact-host-access-unavailable"},
            },
        }

    def check(self, value=None):
        with contextlib.redirect_stderr(io.StringIO()):
            return self.handoff.validate_client_receipt(value or self.receipt)

    def rejected(self, code: str) -> None:
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream), self.assertRaises(SystemExit) as exc:
            self.handoff.validate_client_receipt(self.receipt)
        self.assertEqual(exc.exception.code, 2)
        self.assertIn(code, stream.getvalue())

    def block(self) -> None:
        self.receipt["state"] = "BLOCK"
        self.receipt["next_actions"][0]["callable"] = False
        self.receipt["blocker"] = {
            "operation": "workflow_dispatch POST", "reason": "operation not exposed",
            "evidence": "fixture:GET-only-connector;CLI-absent;mesh-denied403",
            "retry_condition": "supported authenticated POST operation restored",
            "next_action": "restore the existing native operation binding",
        }

    def attempt(self, changed=False, count=1) -> dict:
        previous = {key: str(i) * 64 for i, key in enumerate(
            ("subject", "error", "cause", "capability"), start=1)}
        current = dict(previous, cause="5" * 64) if changed else dict(previous)
        return {"previous": previous, "current": current, "effect_count": count,
                "action": copy.deepcopy(self.receipt["next_actions"][0]),
                "ambiguous_effect": False, "readback_before_effect": False}

    def done(self) -> None:
        self.receipt["state"] = "DONE"
        self.receipt["next_actions"] = []
        self.receipt["readback"]["delivery"].update(
            state="VERIFIED", working_software=True, tls=True, independent=True,
            head=self.subject["head"], tree=self.subject["tree"])

    def test_existing_grant_and_callable_successor_continue(self) -> None:
        self.assertEqual(self.check(), "CONTINUE")

    def test_renewed_generic_permission_request_is_rejected(self) -> None:
        self.receipt["requested_authorization_again"] = True
        self.rejected("CLIENT_REPEATED_AUTHORIZATION_REQUEST")

    def test_missing_owner_grant_is_not_invented(self) -> None:
        self.receipt["authorization"]["granted"] = False
        self.rejected("CLIENT_OWNER_AUTHORIZATION_MISSING")

    def test_block_despite_executable_successor_is_rejected(self) -> None:
        self.receipt["state"] = "BLOCK"
        self.rejected("CLIENT_PREMATURE_RETURN_WITH_EXECUTABLE_SUCCESSOR")

    def test_done_despite_executable_successor_is_rejected(self) -> None:
        self.receipt["state"] = "DONE"
        self.rejected("CLIENT_PREMATURE_RETURN_WITH_EXECUTABLE_SUCCESSOR")

    def test_missing_relevant_route_inventory_is_rejected(self) -> None:
        for kind in ("repository", "connector", "cli", "mesh"):
            with self.subTest(kind=kind):
                old = self.receipt["inventory"].pop(kind)
                self.rejected("CLIENT_EXISTING_ROUTE_NOT_INSPECTED:" + kind)
                self.receipt["inventory"][kind] = old

    def test_concrete_block_after_all_existing_routes_inspected(self) -> None:
        self.block()
        self.assertEqual(self.check(), "BLOCK")

    def test_authorization_does_not_invent_post_capability(self) -> None:
        self.block()
        self.receipt["next_actions"][0]["method"] = "POST"
        self.receipt["next_actions"][0]["observed_method"] = "GET"
        self.assertEqual(self.check(), "BLOCK")

    def test_get_capability_cannot_be_declared_callable_post(self) -> None:
        self.receipt["next_actions"][0]["observed_method"] = "GET"
        self.rejected("CLIENT_CALLABLE_OPERATION_BINDING_MISMATCH")

    def test_observed_target_cannot_be_substituted(self) -> None:
        self.receipt["next_actions"][0]["observed_repository"] = "Goldkelch/qik-vrt"
        self.rejected("CLIENT_CALLABLE_OPERATION_BINDING_MISMATCH")

    def test_admin_permission_does_not_replace_governance_admission(self) -> None:
        self.block()
        self.receipt["next_actions"][0].update(callable=True, admitted=False)
        self.assertEqual(self.check(), "BLOCK")

    def test_block_without_concrete_retry_condition_is_rejected(self) -> None:
        self.block()
        del self.receipt["blocker"]["retry_condition"]
        self.rejected("CLIENT_BLOCKER_NOT_CONCRETE:retry_condition")

    def test_unchanged_failure_is_noop(self) -> None:
        self.receipt["attempts"] = [self.attempt(count=0)]
        self.assertEqual(self.check(), "CONTINUE")

    def test_unchanged_failure_cannot_be_retried(self) -> None:
        self.receipt["attempts"] = [self.attempt()]
        self.rejected("CLIENT_UNCHANGED_FAILURE_RETRIED")

    def test_clocks_and_unrelated_heads_do_not_admit_retry(self) -> None:
        attempt = self.attempt()
        attempt["current"].update(observed_at="later", repository_head="c" * 40)
        attempt["previous"].update(observed_at="earlier", repository_head="d" * 40)
        self.receipt["attempts"] = [attempt]
        self.rejected("CLIENT_UNCHANGED_FAILURE_RETRIED")

    def test_materially_changed_cause_admits_single_attempt(self) -> None:
        self.receipt["attempts"] = [self.attempt(changed=True)]
        self.assertEqual(self.check(), "CONTINUE")

    def test_ambiguous_effect_requires_readback_before_retry(self) -> None:
        attempt = self.attempt(changed=True)
        attempt["ambiguous_effect"] = True
        self.receipt["attempts"] = [attempt]
        self.rejected("CLIENT_AMBIGUOUS_EFFECT_RETRIED_WITHOUT_READBACK")
        attempt["readback_before_effect"] = True
        self.assertEqual(self.check(), "CONTINUE")

    def test_multi_dispatch_and_boolean_counts_are_rejected(self) -> None:
        for count in (2, True, -1):
            with self.subTest(count=count):
                self.receipt["attempts"] = [self.attempt(changed=True, count=count)]
                self.rejected("CLIENT_EFFECT_COUNT_INVALID")

    def test_changed_cause_cannot_bypass_governance(self) -> None:
        attempt = self.attempt(changed=True)
        attempt["action"]["admitted"] = False
        self.receipt["attempts"] = [attempt]
        self.rejected("CLIENT_EFFECT_WITHOUT_ADMISSION")

    def test_changed_cause_cannot_replace_owner_authorization(self) -> None:
        attempt = self.attempt(changed=True)
        attempt["action"]["authorized"] = False
        self.receipt["attempts"] = [attempt]
        self.rejected("CLIENT_EFFECT_WITHOUT_ADMISSION")

    def test_same_causal_attempt_cannot_execute_twice(self) -> None:
        attempt = self.attempt(changed=True)
        self.receipt["attempts"] = [attempt, copy.deepcopy(attempt)]
        self.rejected("CLIENT_DUPLICATE_CAUSAL_ATTEMPT")

    def test_subject_drift_is_rejected(self) -> None:
        self.receipt["next_actions"][0]["subject"] = dict(self.subject, head="c" * 40)
        self.rejected("CLIENT_ACTION_SUBJECT_DRIFT")

    def test_browser_cannot_replace_rest_only(self) -> None:
        self.receipt["next_actions"][0]["transport"] = "BROWSER"
        self.rejected("CLIENT_GITHUB_ROUTE_FORBIDDEN")

    def test_predicates_cannot_use_truthy_nonbooleans(self) -> None:
        self.receipt["next_actions"][0]["admitted"] = "yes"
        self.rejected("CLIENT_ACTION_PREDICATE_INVALID")

    def test_exact_host_is_required_even_when_blocked(self) -> None:
        self.block()
        self.receipt["readback"]["delivery"]["hostname"] = "other.example"
        self.rejected("CLIENT_EXACT_HOST_READBACK_MISSING")

    def test_done_requires_tls_software_and_independent_same_subject_readback(self) -> None:
        self.done()
        valid = copy.deepcopy(self.receipt)
        self.assertEqual(self.check(), "DONE")
        for key, wrong in (("tls", False), ("working_software", False),
                           ("independent", False), ("head", "c" * 40),
                           ("tree", "d" * 40), ("state", "PENDING")):
            with self.subTest(key=key):
                self.receipt = copy.deepcopy(valid)
                self.receipt["readback"]["delivery"][key] = wrong
                self.rejected("CLIENT_DONE_WITHOUT_EXACT_EFFECT_READBACK")

    def test_candidate_tests_do_not_establish_main_integration(self) -> None:
        self.done()
        self.receipt["readback"]["repository"]["ref"] = "work/repair"
        self.rejected("CLIENT_DONE_WITHOUT_EXACT_EFFECT_READBACK")

    def test_pending_execution_retains_goal_without_permission_question(self) -> None:
        self.receipt["next_actions"] = []
        self.receipt["pending_execution"] = "fixture:admitted-native-run-id"
        self.assertEqual(self.check(), "CONTINUE")

    def test_receipt_cli_handles_empty_and_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "client.json"
            for body in ("", "{invalid", "[]"):
                with self.subTest(body=body):
                    path.write_text(body)
                    result = subprocess.run(
                        [sys.executable, "-B", "tools/ai_handoff.py", "--client-receipt", str(path)],
                        cwd=ROOT, capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("AI_HANDOFF_BLOCK", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_receipt_cli_success_explicitly_does_not_claim_live_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "client.json"
            path.write_text(json.dumps(self.receipt))
            result = subprocess.run(
                [sys.executable, "-B", "tools/ai_handoff.py", "--client-receipt", str(path)],
                cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CLIENT_HANDOFF_CONSISTENCY=VALID", result.stdout)
        self.assertIn("LIVE_EFFECT_VERIFICATION=NOT_PERFORMED", result.stdout)
        self.assertNotIn("FINAL_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
