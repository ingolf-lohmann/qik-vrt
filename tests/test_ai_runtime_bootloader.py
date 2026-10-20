#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import json
import hashlib
import copy
import contextlib
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

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


class SessionHarmonizationTests(unittest.TestCase):
    """A capability difference must not become rule drift or peer adoption."""

    def receipt(self):
        fixture = ClientContinuationRegressionTests()
        fixture.setUp()
        value = copy.deepcopy(fixture.receipt)
        value["schema"] = "qikvrt-client-continuation/2"
        value["session_contract"] = fixture.handoff.session_rule_contract()
        value["session"] = {
            "id": "fixture:session", "node_id": "fixture:node",
            "repository": value["subject"]["repository"],
            "evidence": "fixture:own-native-input-and-independent-terminal-readback",
            "all_nodes_adopted": False,
            "capability_observations": [{
                "session_id": "fixture:session", "node_id": "fixture:node",
                "repository": value["subject"]["repository"],
                "scope": "THIS_SESSION_ONLY", "operation": "create-commit",
                "method": "POST", "route": "existing-github-rest-connector",
                "state": "UNKNOWN", "evidence": "fixture:bounded-inventory",
                "observed_at": "2026-10-20T10:00:00Z",
            }],
        }
        return fixture.handoff, value

    def rejected(self, handoff, value, error):
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit):
                handoff.validate_client_receipt(value, require_session_contract=True)
        self.assertIn(error, errors.getvalue())

    def test_different_capabilities_preserve_identical_rules_and_authorization(self):
        handoff, value = self.receipt()
        original = copy.deepcopy(value["session_contract"])
        for state in ("AVAILABLE", "UNAVAILABLE", "UNKNOWN"):
            value["session"]["capability_observations"][0]["state"] = state
            self.assertEqual(handoff.validate_client_receipt(value, require_session_contract=True), "CONTINUE")
            self.assertEqual(value["session_contract"], original)
            self.assertTrue(value["authorization"]["granted"])

    def test_missing_or_stale_rule_binding_blocks_current_session(self):
        handoff, value = self.receipt()
        del value["session_contract"]["rule_bindings"]["AGENTS.md"]
        self.rejected(handoff, value, "CLIENT_SHARED_RULE_CONTRACT_DRIFT")

    def test_new_rule_bytes_invalidate_previous_receipt(self):
        handoff, value = self.receipt()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for name in value["session_contract"]["rule_bindings"]:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            with (root / "CLAUDE.md").open("a") as file:
                file.write("\nChanged adapter rule\n")
            with patch.object(handoff, "ROOT", root):
                self.rejected(handoff, value, "CLIENT_SHARED_RULE_CONTRACT_DRIFT")

    def test_capability_cannot_escape_its_node_session_or_repository(self):
        for field, replacement in (("node_id", "other-node"), ("session_id", "other-session"),
                                   ("repository", "other/repository"), ("scope", "ALL_NODES")):
            handoff, value = self.receipt()
            value["session"]["capability_observations"][0][field] = replacement
            self.rejected(handoff, value, "CLIENT_CAPABILITY_SCOPE_LEAK")

    def test_byte_agreement_cannot_claim_global_adoption(self):
        handoff, value = self.receipt()
        value["session"]["all_nodes_adopted"] = True
        self.rejected(handoff, value, "CLIENT_UNVERIFIED_GLOBAL_ADOPTION")

    def test_conflicting_or_duplicate_local_capability_blocks(self):
        handoff, value = self.receipt()
        item = copy.deepcopy(value["session"]["capability_observations"][0])
        item["state"] = "AVAILABLE"
        value["session"]["capability_observations"].append(item)
        self.rejected(handoff, value, "CLIENT_DUPLICATE_CAPABILITY_OBSERVATION")

    def test_rule_harmonization_cannot_renew_same_authorization(self):
        handoff, value = self.receipt()
        value["requested_authorization_again"] = True
        self.rejected(handoff, value, "CLIENT_REPEATED_AUTHORIZATION_REQUEST")

    def test_legacy_remains_readable_but_is_rejected_at_current_boundary(self):
        handoff, value = self.receipt()
        value["schema"] = "qikvrt-client-continuation/1"
        del value["session"], value["session_contract"]
        self.assertEqual(handoff.validate_client_receipt(value), "CONTINUE")
        self.rejected(handoff, value, "CLIENT_CURRENT_SESSION_REQUIRES_V2")

    def test_every_existing_adapter_is_bound_without_new_provider_selection(self):
        handoff, value = self.receipt()
        adapters = json.loads((ROOT / "AI_ADAPTERS.json").read_text())["adapters"]
        self.assertEqual(len(adapters), 14)
        for item in adapters:
            self.assertIn(item["path"], value["session_contract"]["rule_bindings"])
            if item["path"] != "AGENTS.md":
                self.assertIn("--require-session-contract", (ROOT / item["path"]).read_text())

    def test_cli_defaults_to_current_admission_and_requires_explicit_legacy_mode(self):
        handoff, value = self.receipt()
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "receipt.json"
            def run(*flags):
                path.write_text(json.dumps(value))
                return subprocess.run([sys.executable, "-B", str(ROOT / "tools/ai_handoff.py"),
                                       "--client-receipt", str(path), *flags],
                                      capture_output=True, text=True, timeout=30)
            self.assertEqual(run().returncode, 0)
            value["schema"] = "qikvrt-client-continuation/1"
            del value["session"], value["session_contract"]
            self.assertIn("CLIENT_CURRENT_SESSION_REQUIRES_V2", run().stderr)
            historical = run("--historical-client-receipt")
            self.assertEqual(historical.returncode, 0, historical.stderr)
            self.assertIn("LEGACY_NOT_ASSESSED", historical.stdout)


class ClientContinuationRegressionTests(unittest.TestCase):
    """Client behavior receipts are fixtures, never productive effect evidence."""

    def setUp(self) -> None:
        from tools import ai_handoff
        self.handoff = ai_handoff
        self.subject = {
            "repository": "ingolf-lohmann/qik-vrt", "ref": "main",
            "head": "a" * 40, "tree": "b" * 40,
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
            "action_window": {"id": "fixture:action-1",
                              "completed_at": "2026-10-11T10:00:00Z",
                              "closed_at": "2026-10-11T10:00:03Z"},
            "readback": {
                "repository": {**self.subject, "source": "fixture:fresh-rest-read",
                               "action_id": "fixture:action-1",
                               "observed_at": "2026-10-11T10:00:01Z"},
                "delivery": {"hostname": "raumzeitterminal.de", "state": "UNKNOWN",
                             "source": "fixture:exact-host-access-unavailable",
                             "url": "https://raumzeitterminal.de/", "method": "GET",
                             "action_id": "fixture:action-1",
                             "observed_at": "2026-10-11T10:00:02Z"},
            },
        }

    def check(self, value=None):
        with contextlib.redirect_stderr(io.StringIO()):
            return self.handoff.validate_client_receipt(value or self.receipt)

    def inherited_work(self) -> None:
        self.receipt["previous_run"] = {"execution_id": "fixture:previous-run",
                                        "open_work": ["failure", "omission", "gap"]}
        self.receipt["work"] = [{"id": task, "state": "OPEN", "evidence": "",
                                 "next_action": "fixture:causal-repair:" + task}
                                for task in ("failure", "omission", "gap")]

    def test_failures_omissions_and_gaps_are_accepted_as_successor_work(self) -> None:
        self.inherited_work()
        self.assertEqual(self.check(), "CONTINUE")

    @staticmethod
    def seal_knowledge(record):
        payload = {k: v for k, v in record.items() if k != "record_sha256"}
        wire = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
        return dict(payload, record_sha256=hashlib.sha256(wire).hexdigest())

    def inherited_knowledge(self):
        self.inherited_work()
        record = self.seal_knowledge({
            "id": "fixture:ionos-reference", "epistemic_class": "SOURCE_OBSERVATION",
            "subject": {"repository": self.subject["repository"], "blob": "c" * 40},
            "scope": "Secret reference in source; live token delivery and rights UNKNOWN",
            "statement": "The existing source references secrets.IONOS_TOKEN.",
            "evidence": ["fixture:exact-source-read"], "supersedes": [],
        })
        self.receipt["knowledge"] = [record]
        self.receipt["previous_run"]["knowledge"] = copy.deepcopy([record])
        return record

    def test_handoff_retains_prior_knowledge_and_its_limits(self):
        self.inherited_knowledge()
        self.assertEqual(self.check(), "CONTINUE")

    def historical_knowledge(self):
        canonical = self.inherited_knowledge()
        payload = {k: v for k, v in canonical.items() if k != "record_sha256"}
        historical = dict(payload, record_sha256=hashlib.sha256(json.dumps(
            payload, sort_keys=True, ensure_ascii=False,
            separators=(", ", ": "), allow_nan=False).encode()).hexdigest())
        self.receipt["knowledge"] = [historical]
        self.receipt["previous_run"]["knowledge"] = copy.deepcopy([historical])
        directory = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(directory.cleanup)
        path = pathlib.Path(directory.name) / "prior.json"
        raw = json.dumps({"execution_id": "fixture:previous-run",
                          "knowledge": [historical],
                          "work": copy.deepcopy(self.receipt["work"])}).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        self.receipt["previous_run"].update(
            receipt_path=str(path.relative_to(ROOT)), receipt_sha256=digest)
        self.receipt["knowledge_encoding_migration"] = {
            "schema": "qikvrt-knowledge-historical-encoding-migration/v1",
            "predecessor_sha256": digest,
            "records": [{"id": historical["id"],
                         "codec": "json-sorted-spaced-utf8/v1",
                         "record_sha256": historical["record_sha256"],
                         "canonical_sha256": canonical["record_sha256"]}],
        }
        return path, raw, copy.deepcopy(historical)

    def test_historical_encoding_requires_explicit_migration_and_preserves_bytes(self):
        path, raw, historical = self.historical_knowledge()
        migration = self.receipt.pop("knowledge_encoding_migration")
        self.rejected("CLIENT_KNOWLEDGE_DIGEST_DRIFT")
        self.receipt["knowledge_encoding_migration"] = migration
        self.assertEqual(self.check(), "CONTINUE")
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(self.receipt["knowledge"], [historical])
        self.assertEqual(self.receipt["previous_run"]["knowledge"], [historical])

    def test_historical_encoding_requires_actual_pinned_predecessor(self):
        self.historical_knowledge()
        del self.receipt["previous_run"]["receipt_path"]
        del self.receipt["previous_run"]["receipt_sha256"]
        self.rejected("CLIENT_KNOWLEDGE_MIGRATION_PREDECESSOR_REQUIRED")

    def test_historical_encoding_rejects_changed_predecessor_bytes(self):
        path, raw, _ = self.historical_knowledge()
        path.write_bytes(raw + b" ")
        self.rejected("CLIENT_PREVIOUS_RECEIPT_DIGEST_DRIFT")

    def test_historical_encoding_rejects_other_source_schema_and_unknown_fields(self):
        self.historical_knowledge()
        valid = copy.deepcopy(self.receipt)
        for change in ({"predecessor_sha256": "0" * 64},
                       {"schema": "unversioned-guess"}, {"accept_all": True}):
            with self.subTest(change=change):
                self.receipt = copy.deepcopy(valid)
                self.receipt["knowledge_encoding_migration"].update(change)
                self.rejected("CLIENT_KNOWLEDGE_MIGRATION_BINDING_INVALID")

    def test_historical_encoding_rejects_unknown_codec_duplicates_and_empty_mapping(self):
        self.historical_knowledge()
        valid = copy.deepcopy(self.receipt)
        entry = valid["knowledge_encoding_migration"]["records"][0]
        for records in ([], [entry, entry], [dict(entry, codec="try-both")],
                        [dict(entry, unverified=True)], [entry] * 129):
            with self.subTest(records=records):
                self.receipt = copy.deepcopy(valid)
                self.receipt["knowledge_encoding_migration"]["records"] = records
                self.rejected("CLIENT_KNOWLEDGE_MIGRATION_RECORDS_INVALID")

    def test_historical_encoding_rejects_wrong_original_or_canonical_digest(self):
        self.historical_knowledge()
        valid = copy.deepcopy(self.receipt)
        for key in ("record_sha256", "canonical_sha256"):
            with self.subTest(key=key):
                self.receipt = copy.deepcopy(valid)
                self.receipt["knowledge_encoding_migration"]["records"][0][key] = "0" * 64
                self.rejected("CLIENT_KNOWLEDGE_MIGRATION_ENCODING_MISMATCH")

    def test_historical_encoding_rejects_payload_and_epistemic_promotion(self):
        self.historical_knowledge()
        valid = copy.deepcopy(self.receipt)
        for change in ({"statement": "Protected remote credentials are absent."},
                       {"scope": "All hosts and all times"},
                       {"epistemic_class": "LIVE_EFFECT_VERIFIED"},
                       {"evidence": ["fixture:unrelated"]}):
            with self.subTest(change=change):
                self.receipt = copy.deepcopy(valid)
                self.receipt["knowledge"][0].update(change)
                self.rejected("CLIENT_KNOWLEDGE_HISTORY_REWRITTEN")

    def test_historical_encoding_rejects_missing_record_and_duplicate_source_id(self):
        self.historical_knowledge()
        valid = copy.deepcopy(self.receipt)
        self.receipt["knowledge"] = []
        self.rejected("CLIENT_KNOWLEDGE_MIGRATION_RECORD_NOT_IN_PREDECESSOR")
        self.receipt = copy.deepcopy(valid)
        self.receipt["knowledge"].append(copy.deepcopy(self.receipt["knowledge"][0]))
        self.rejected("CLIENT_KNOWLEDGE_MIGRATION_RECORD_NOT_IN_PREDECESSOR")

    def test_new_records_cannot_use_historical_codec(self):
        self.historical_knowledge()
        record = copy.deepcopy(self.receipt["knowledge"][0])
        record["id"] = "fixture:new-spaced-record"
        payload = {k: v for k, v in record.items() if k != "record_sha256"}
        record["record_sha256"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        self.receipt["knowledge"].append(record)
        self.rejected("CLIENT_KNOWLEDGE_DIGEST_DRIFT")
        self.receipt["knowledge_encoding_migration"]["records"].append({
            "id": record["id"], "codec": "json-sorted-spaced-utf8/v1",
            "record_sha256": record["record_sha256"],
            "canonical_sha256": self.seal_knowledge(record)["record_sha256"],
        })
        self.rejected("CLIENT_KNOWLEDGE_MIGRATION_RECORD_NOT_IN_PREDECESSOR")

    def test_historical_encoding_keeps_correction_graph_and_open_work_gates(self):
        self.historical_knowledge()
        valid = copy.deepcopy(self.receipt)
        original = self.receipt["knowledge"][0]
        self.receipt["knowledge"].append(self.seal_knowledge(dict(original,
            id="fixture:orphan", supersedes=["fixture:missing"])))
        self.rejected("CLIENT_KNOWLEDGE_CORRECTION_TARGET_MISSING")
        self.receipt = copy.deepcopy(valid)
        self.receipt["work"] = []
        self.rejected("CLIENT_PREDECESSOR_OPEN_WORK_DROPPED")

    def test_historical_encoding_does_not_turn_undelivered_receipt_into_done(self):
        self.historical_knowledge()
        self.receipt["state"] = "DONE"
        self.receipt["next_actions"] = []
        self.rejected("CLIENT_DONE_WITH_OPEN_WORK")

    def test_direct_knowledge_reader_remains_strict(self):
        self.historical_knowledge()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.handoff.client_knowledge_records(self.receipt["knowledge"])

    def test_historical_encoding_requires_versioned_policy_admission(self):
        self.historical_knowledge()
        predecessor = self.handoff.client_previous_receipt(self.receipt)
        for contract in ({}, None, {"schema": "unversioned"}):
            with self.subTest(contract=contract):
                policy = {"client_continuation": {"knowledge_continuity": {
                    "historical_encoding_migration": contract}}}
                stream = io.StringIO()
                with patch.object(self.handoff, "load_json", return_value=policy), \
                        contextlib.redirect_stderr(stream), self.assertRaises(SystemExit):
                    self.handoff.client_historical_knowledge_encodings(self.receipt, predecessor)
                self.assertIn("CLIENT_KNOWLEDGE_MIGRATION_POLICY_UNAVAILABLE", stream.getvalue())

    def test_knowledge_contract_reuses_the_existing_epistemic_continuity_policy(self):
        policy = json.loads((ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json").read_text())
        rule = policy["client_continuation"]["knowledge_continuity"]
        raw = (ROOT / rule["existing_policy"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), rule["existing_policy_sha256"])
        self.assertIn("failure_and_correction_history", json.loads(raw)["required_preservation"])
        self.assertFalse(rule["local_environment_absence_proves_remote_binding_absent"])

    def test_handoff_rejects_discarding_known_records(self):
        self.inherited_knowledge()
        self.receipt["knowledge"] = []
        self.rejected("CLIENT_PREDECESSOR_KNOWLEDGE_DROPPED")

    def test_handoff_rejects_rewriting_knowledge_or_promoting_its_scope(self):
        for changes in ({"statement": "The protected remote binding is absent."},
                        {"epistemic_class": "LIVE_EFFECT_VERIFIED"},
                        {"scope": "All providers and all runtimes"}):
            with self.subTest(changes=changes):
                original = self.inherited_knowledge()
                self.receipt["knowledge"] = [self.seal_knowledge(dict(original, **changes))]
                self.rejected("CLIENT_KNOWLEDGE_HISTORY_REWRITTEN")

    def test_handoff_retains_correction_as_a_bound_successor(self):
        original = self.inherited_knowledge()
        correction = self.seal_knowledge(dict(original, id="fixture:correction",
            epistemic_class="CORRECTION", statement="Source presence does not prove live delivery.",
            evidence=["fixture:owner-correction"], supersedes=[original["id"]]))
        self.receipt["knowledge"].append(correction)
        self.assertEqual(self.check(), "CONTINUE")

    def test_handoff_rejects_changed_knowledge_bytes_and_orphan_corrections(self):
        original = self.inherited_knowledge()
        self.receipt["knowledge"][0]["statement"] = "Changed without a new record"
        self.rejected("CLIENT_KNOWLEDGE_DIGEST_DRIFT")
        original = self.inherited_knowledge()
        self.receipt["knowledge"].append(self.seal_knowledge(dict(original,
            id="fixture:correction", supersedes=["fixture:lost-history"])))
        self.rejected("CLIENT_KNOWLEDGE_CORRECTION_TARGET_MISSING")

    def test_pinned_predecessor_prevents_hiding_known_records(self):
        original = self.inherited_knowledge()
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = pathlib.Path(directory) / "prior.json"
            prior = {"execution_id": "fixture:previous-run", "knowledge": [original],
                     "work": copy.deepcopy(self.receipt["work"])}
            raw = json.dumps(prior).encode()
            path.write_bytes(raw)
            self.receipt["previous_run"].update(receipt_path=str(path.relative_to(ROOT)),
                receipt_sha256=hashlib.sha256(raw).hexdigest(), knowledge=[])
            self.receipt["knowledge"] = []
            self.rejected("CLIENT_PREDECESSOR_KNOWLEDGE_DROPPED")
            self.receipt["knowledge"] = [original]
            self.assertEqual(self.check(), "CONTINUE")
            self.receipt["previous_run"]["receipt_sha256"] = "0" * 64
            self.rejected("CLIENT_PREVIOUS_RECEIPT_DIGEST_DRIFT")

    def test_pinned_predecessor_prevents_hiding_open_work(self):
        original = self.inherited_knowledge()
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = pathlib.Path(directory) / "prior.json"
            prior = {"execution_id": "fixture:previous-run", "knowledge": [original],
                     "work": copy.deepcopy(self.receipt["work"])}
            raw = json.dumps(prior).encode()
            path.write_bytes(raw)
            self.receipt["previous_run"].update(receipt_path=str(path.relative_to(ROOT)),
                receipt_sha256=hashlib.sha256(raw).hexdigest(), open_work=[])
            self.receipt["work"] = []
            self.rejected("CLIENT_PREDECESSOR_OPEN_WORK_DROPPED")

    def test_handoff_rejects_cyclic_correction_history(self):
        original = self.inherited_knowledge()
        self.receipt["knowledge"].extend([
            self.seal_knowledge(dict(original, id="fixture:a", supersedes=["fixture:b"])),
            self.seal_knowledge(dict(original, id="fixture:b", supersedes=["fixture:a"])),
        ])
        self.rejected("CLIENT_KNOWLEDGE_CORRECTION_CYCLE")

    def test_long_unordered_knowledge_history_is_preserved_without_recursion(self):
        original = self.inherited_knowledge()
        self.receipt["knowledge"].extend(reversed([
            self.seal_knowledge(dict(original, id=f"fixture:revision:{i}",
                supersedes=[f"fixture:revision:{i-1}"] if i else []))
            for i in range(1100)
        ]))
        self.assertEqual(self.check(), "CONTINUE")

    def test_pinned_predecessor_rejects_changed_identity_and_outside_path(self):
        original = self.inherited_knowledge()
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = pathlib.Path(directory) / "prior.json"
            raw = json.dumps({"execution_id": "fixture:unrelated-run", "knowledge": [original],
                              "work": copy.deepcopy(self.receipt["work"])}).encode()
            path.write_bytes(raw)
            self.receipt["previous_run"].update(receipt_path=str(path.relative_to(ROOT)),
                receipt_sha256=hashlib.sha256(raw).hexdigest())
            self.rejected("CLIENT_PREVIOUS_RECEIPT_IDENTITY_DRIFT")
            self.receipt["previous_run"]["receipt_path"] = str(path)
            self.rejected("CLIENT_PREVIOUS_RECEIPT_BINDING_INVALID")
            self.receipt["previous_run"]["receipt_path"] = "invalid\x00name"
            self.rejected("CLIENT_PREVIOUS_RECEIPT_BINDING_INVALID")

    def test_each_predecessor_open_obligation_must_be_carried(self) -> None:
        for identifier in ("failure", "omission", "gap"):
            with self.subTest(obligation=identifier):
                self.inherited_work()
                self.receipt["work"] = [task for task in self.receipt["work"] if task["id"] != identifier]
                self.rejected("CLIENT_PREDECESSOR_OPEN_WORK_DROPPED")

    def test_predecessor_work_requires_evidence_to_close(self) -> None:
        self.inherited_work()
        self.receipt["work"][0]["state"] = "VERIFIED"
        self.rejected("CLIENT_WORK_CLOSED_WITHOUT_EVIDENCE")
        self.receipt["work"][0]["evidence"] = "fixture:exact-subject-closing-readback"
        self.assertEqual(self.check(), "CONTINUE")

    def test_open_predecessor_work_rejects_done_even_with_a_delivery_fixture(self) -> None:
        self.inherited_work()
        self.done()
        self.rejected("CLIENT_DONE_WITH_OPEN_WORK")

    def test_open_predecessor_work_requires_concrete_next_action(self) -> None:
        self.inherited_work()
        self.receipt["work"][0]["next_action"] = ""
        self.rejected("CLIENT_OPEN_WORK_WITHOUT_SUCCESSOR")

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
                "action_window": copy.deepcopy(self.receipt["action_window"]),
                "readback": copy.deepcopy(self.receipt["readback"]),
                "ambiguous_effect": False, "readback_before_effect": False}

    def done(self) -> None:
        self.receipt["state"] = "DONE"
        self.receipt["next_actions"] = []
        self.receipt["readback"]["delivery"].update(
            state="VERIFIED", working_software=True, tls=True, independent=True,
            http_status=200, final_url="https://raumzeitterminal.de/",
            response_sha256="6" * 64,
            head=self.subject["head"], tree=self.subject["tree"])

    def test_existing_grant_and_callable_successor_continue(self) -> None:
        self.assertEqual(self.check(), "CONTINUE")

    def anticipated_transition(self) -> dict:
        action = copy.deepcopy(self.receipt["next_actions"][0])
        preparation = copy.deepcopy(action)
        preparation.update(operation="read-signing-source", observed_operation="read-signing-source",
                           method="GET", observed_method="GET")
        action["authenticated"] = False
        transition = {
            "id": "signed-xpi", "evidence": "fixture:signing-credential-not-delivered",
            "activation": [{"id": "credential-delivery", "satisfied": False,
                            "evidence": "fixture:credential-presence-readback"}],
            "action": action, "preparation": [preparation],
        }
        self.receipt["input_sha256"] = "7" * 64
        self.receipt["transition_plan"] = {
            "subject": copy.deepcopy(self.subject), "input_sha256": "7" * 64,
            "transitions": [transition],
        }
        self.receipt["next_actions"] = []
        return transition

    def test_available_preparation_prevents_return_while_target_is_blocked(self) -> None:
        self.anticipated_transition()
        self.receipt["blocker"] = {
            "operation": "sign-xpi", "reason": "credential delivery missing",
            "evidence": "fixture:credential-presence-readback",
            "retry_condition": "credential delivered", "next_action": "bind existing credential",
        }
        self.receipt["state"] = "BLOCK"
        self.rejected("CLIENT_PREMATURE_RETURN_WITH_EXECUTABLE_SUCCESSOR")
        self.receipt["state"] = "CONTINUE"
        self.assertEqual(self.check(), "CONTINUE")

    def test_plan_exposes_preparation_and_exact_waiting_condition(self) -> None:
        self.anticipated_transition()
        plan = self.handoff.client_transition_plan(self.receipt)
        self.assertEqual([(a["transition_id"], a["stage"]) for a in plan["ready"]],
                         [("signed-xpi", "PREPARE")])
        self.assertEqual(plan["waiting"][0]["activation"], ["credential-delivery"])
        self.assertEqual(plan["scope"], "PLANNING_ONLY_NOT_EXECUTION_OR_EFFECT_PROOF")

    def test_transition_activation_does_not_supply_credentials_or_admission(self) -> None:
        transition = self.anticipated_transition()
        transition["preparation"] = []
        transition["activation"][0]["satisfied"] = True
        self.assertEqual(self.handoff.client_transition_plan(self.receipt)["ready"], [])
        transition["action"]["authenticated"] = True
        transition["action"]["admitted"] = False
        self.assertEqual(self.handoff.client_transition_plan(self.receipt)["ready"], [])
        transition["action"]["admitted"] = True
        plan = self.handoff.client_transition_plan(self.receipt)
        self.assertEqual([a["stage"] for a in plan["ready"]], ["EXECUTE"])

    def test_changed_human_input_invalidates_prepared_plan(self) -> None:
        self.anticipated_transition()
        self.receipt["pending_execution"] = "fixture:existing-native-execution"
        self.receipt["input_sha256"] = "8" * 64
        self.rejected("CLIENT_TRANSITION_INPUT_DRIFT")
        self.receipt["transition_plan"]["input_sha256"] = "8" * 64
        self.assertEqual(self.check(), "CONTINUE")

    def test_transition_plan_cannot_reuse_predecessor_subject(self) -> None:
        self.anticipated_transition()
        self.receipt["transition_plan"]["subject"]["head"] = "c" * 40
        self.rejected("CLIENT_TRANSITION_SUBJECT_DRIFT")

    def test_preparation_preserves_rest_route_and_exact_operation_binding(self) -> None:
        transition = self.anticipated_transition()
        transition["preparation"][0]["transport"] = "BROWSER"
        self.rejected("CLIENT_GITHUB_ROUTE_FORBIDDEN")
        transition["preparation"][0]["transport"] = "REST_API_ONLY"
        transition["preparation"][0]["observed_method"] = "POST"
        self.rejected("CLIENT_CALLABLE_OPERATION_BINDING_MISMATCH")

    def test_independent_transition_remains_available_when_another_is_blocked(self) -> None:
        first = self.anticipated_transition()
        first["preparation"] = []
        second = copy.deepcopy(first)
        second["id"] = "original-archive"
        second["activation"][0]["satisfied"] = True
        second["action"]["authenticated"] = True
        self.receipt["transition_plan"]["transitions"].append(second)
        self.assertEqual(self.check(), "CONTINUE")
        plan = self.handoff.client_transition_plan(self.receipt)
        self.assertEqual([a["transition_id"] for a in plan["ready"]], ["original-archive"])
        self.assertEqual([a["transition_id"] for a in plan["waiting"]], ["signed-xpi"])

    def test_changed_input_or_observation_clock_does_not_admit_unchanged_retry(self) -> None:
        retry = self.attempt(count=0)
        transition = self.anticipated_transition()
        transition["preparation"] = []
        transition["activation"][0]["satisfied"] = True
        action = transition["action"]
        action["authenticated"] = True
        action["retry"] = {"current": retry["current"], "previous": retry["previous"]}
        action["retry"]["current"]["observed_at"] = "later"
        self.assertEqual(self.handoff.client_transition_plan(self.receipt)["ready"], [])
        action["retry"]["current"]["capability"] = "9" * 64
        self.assertEqual(len(self.handoff.client_transition_plan(self.receipt)["ready"]), 1)

    def test_pending_transition_cannot_be_reported_done(self) -> None:
        transition = self.anticipated_transition()
        transition["preparation"] = []
        self.done()
        self.rejected("CLIENT_DONE_WITH_PENDING_TRANSITION")

    def test_invalid_transition_inputs_fail_closed(self) -> None:
        self.anticipated_transition()
        original = copy.deepcopy(self.receipt)
        for key, value in (("input_sha256", True), ("transitions", {})):
            with self.subTest(key=key):
                self.receipt = copy.deepcopy(original)
                self.receipt["transition_plan"][key] = value
                self.rejected("CLIENT_TRANSITION_")
        self.receipt = copy.deepcopy(original)
        transition = self.receipt["transition_plan"]["transitions"][0]
        transition["activation"][0]["satisfied"] = "yes"
        self.rejected("CLIENT_TRANSITION_ACTIVATION_INVALID")

    def test_duplicate_transition_ids_are_rejected(self) -> None:
        transition = self.anticipated_transition()
        self.receipt["transition_plan"]["transitions"].append(copy.deepcopy(transition))
        self.rejected("CLIENT_TRANSITION_ID_INVALID")

    def test_receipt_cli_emits_actionable_transition_plan_without_executing_it(self) -> None:
        self.anticipated_transition()
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "client.json"
            path.write_text(json.dumps(self.receipt))
            result = subprocess.run(
                [sys.executable, "-B", "tools/ai_handoff.py", "--client-receipt", str(path), "--historical-client-receipt"],
                cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        line = next(line for line in result.stdout.splitlines()
                    if line.startswith("CLIENT_TRANSITION_PLAN="))
        plan = json.loads(line.split("=", 1)[1])
        self.assertEqual(plan["ready"][0]["action"]["operation"], "read-signing-source")
        self.assertIn("LIVE_EFFECT_VERIFICATION=NOT_PERFORMED", result.stdout)

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

    def test_ionos_browser_or_missing_transport_is_rejected_before_admission(self) -> None:
        original = copy.deepcopy(self.receipt)
        for route in ("connector", "cli", "mesh"):
            for service in ("ionos", "IONOS"):
                for transport in ("BROWSER", None):
                    with self.subTest(route=route, service=service, transport=transport):
                        self.receipt = copy.deepcopy(original)
                        action = self.receipt["next_actions"][0]
                        action.update(route=route, service=service, transport=transport)
                        # An unavailable action must not reintroduce a forbidden login route.
                        action["authenticated"] = False
                        self.rejected("CLIENT_IONOS_ROUTE_FORBIDDEN")

    def test_effectful_ionos_attempt_cannot_hide_browser_transport(self) -> None:
        attempt = self.attempt(changed=True)
        attempt["action"].update(service="ionos", transport="BROWSER")
        self.receipt["attempts"] = [attempt]
        self.rejected("CLIENT_IONOS_ROUTE_FORBIDDEN")

    def test_ready_ionos_rest_action_continues_without_another_permission_request(self) -> None:
        action = self.receipt["next_actions"][0]
        action.update(service="ionos", operation="dns-record-update",
                      observed_operation="dns-record-update", method="PUT", observed_method="PUT")
        self.assertEqual(self.check(), "CONTINUE")
        self.receipt["state"] = "BLOCK"
        self.rejected("CLIENT_PREMATURE_RETURN_WITH_EXECUTABLE_SUCCESSOR")

    def test_rest_only_does_not_supply_missing_ionos_credentials_or_delivery(self) -> None:
        self.block()
        action = self.receipt["next_actions"][0]
        action.update(service="ionos", authenticated=False)
        self.receipt["blocker"].update(
            operation="IONOS Hosting DNS REST write",
            reason="No securely delivered target-bound Hosting credential",
            retry_condition="Existing secure Hosting REST binding becomes callable and admitted")
        self.assertEqual(self.check(), "BLOCK")
        self.receipt["state"] = "DONE"
        self.rejected("CLIENT_DONE_WITHOUT_EXACT_EFFECT_READBACK")

    def test_ionos_route_is_bound_to_the_explicit_owner_choice(self) -> None:
        policy = json.loads((ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json").read_text())
        rule = policy["client_continuation"]
        self.assertEqual(rule["ionos_route"], "REST_API_ONLY")
        self.assertEqual(rule["ionos_route_owner_instruction"]["exact_text"], "REST-only beibehalten")
        self.assertFalse(rule["ionos_route_owner_instruction"]["browser_login_fallback"])

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
        self.rejected("CLIENT_REPOSITORY_READBACK_SUBJECT_DRIFT")

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
                        [sys.executable, "-B", "tools/ai_handoff.py", "--client-receipt", str(path), "--historical-client-receipt"],
                        cwd=ROOT, capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("AI_HANDOFF_BLOCK", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_receipt_cli_success_explicitly_does_not_claim_live_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "client.json"
            path.write_text(json.dumps(self.receipt))
            result = subprocess.run(
                [sys.executable, "-B", "tools/ai_handoff.py", "--client-receipt", str(path), "--historical-client-receipt"],
                cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CLIENT_HANDOFF_CONSISTENCY=VALID", result.stdout)
        self.assertIn("LIVE_EFFECT_VERIFICATION=NOT_PERFORMED", result.stdout)
        self.assertNotIn("FINAL_PASS", result.stdout)

    def test_missing_closing_head_or_tree_is_rejected_in_every_state(self) -> None:
        valid = copy.deepcopy(self.receipt)
        for state in ("CONTINUE", "BLOCK", "DONE"):
            for key in ("head", "tree"):
                with self.subTest(state=state, key=key):
                    self.receipt = copy.deepcopy(valid)
                    if state == "BLOCK":
                        self.block()
                    elif state == "DONE":
                        self.done()
                    del self.receipt["readback"]["repository"][key]
                    self.rejected("CLIENT_REPOSITORY_READBACK_INVALID")

    def test_predecessor_head_tree_or_wrong_ref_cannot_close_action(self) -> None:
        valid = copy.deepcopy(self.receipt)
        for key, wrong in (("head", "c" * 40), ("tree", "d" * 40),
                           ("ref", "work/other")):
            with self.subTest(key=key):
                self.receipt = copy.deepcopy(valid)
                self.receipt["readback"]["repository"][key] = wrong
                self.rejected("CLIENT_REPOSITORY_READBACK_SUBJECT_DRIFT")

    def test_readback_before_or_at_action_completion_is_rejected(self) -> None:
        valid = copy.deepcopy(self.receipt)
        for kind in ("repository", "delivery"):
            for timestamp in ("2026-10-11T09:59:59Z", "2026-10-11T10:00:00Z"):
                with self.subTest(kind=kind, timestamp=timestamp):
                    self.receipt = copy.deepcopy(valid)
                    self.receipt["readback"][kind]["observed_at"] = timestamp
                    self.rejected("CLIENT_READBACK_NOT_FRESH:" + kind)

    def test_readback_after_receipt_closure_is_rejected(self) -> None:
        valid = copy.deepcopy(self.receipt)
        for kind in ("repository", "delivery"):
            with self.subTest(kind=kind):
                self.receipt = copy.deepcopy(valid)
                self.receipt["readback"][kind]["observed_at"] = "2026-10-11T10:00:04Z"
                self.rejected("CLIENT_READBACK_NOT_FRESH:" + kind)

    def test_missing_naive_or_invalid_observation_time_is_rejected(self) -> None:
        valid = copy.deepcopy(self.receipt)
        for kind in ("repository", "delivery"):
            for wrong in (None, "", "yesterday", "2026-10-11T10:00:01", True):
                with self.subTest(kind=kind, value=wrong):
                    self.receipt = copy.deepcopy(valid)
                    self.receipt["readback"][kind]["observed_at"] = wrong
                    self.rejected("CLIENT_READBACK_TIME_INVALID:" + kind)

    def test_readback_from_another_action_is_rejected(self) -> None:
        valid = copy.deepcopy(self.receipt)
        for kind in ("repository", "delivery"):
            with self.subTest(kind=kind):
                self.receipt = copy.deepcopy(valid)
                self.receipt["readback"][kind]["action_id"] = "fixture:predecessor-action"
                self.rejected("CLIENT_READBACK_ACTION_DRIFT:" + kind)

    def test_invalid_or_missing_action_window_is_rejected(self) -> None:
        valid = copy.deepcopy(self.receipt)
        for wrong in (None, {}, {"id": "fixture:action-1", "completed_at": "bad",
                                 "closed_at": "2026-10-11T10:00:03Z"},
                      {"id": "fixture:action-1", "completed_at": "2026-10-11T10:00:04Z",
                       "closed_at": "2026-10-11T10:00:03Z"}):
            with self.subTest(window=wrong):
                self.receipt = copy.deepcopy(valid)
                self.receipt["action_window"] = wrong
                self.rejected("CLIENT_ACTION_WINDOW_INVALID")

    def test_empty_or_nonstring_readback_sources_are_rejected(self) -> None:
        valid = copy.deepcopy(self.receipt)
        for kind, code in (("repository", "CLIENT_REPOSITORY_READBACK_MISSING"),
                           ("delivery", "CLIENT_EXACT_HOST_READBACK_MISSING")):
            for wrong in (" ", True, 1):
                with self.subTest(kind=kind, source=wrong):
                    self.receipt = copy.deepcopy(valid)
                    self.receipt["readback"][kind]["source"] = wrong
                    self.rejected(code)

    def test_public_delivery_url_cannot_substitute_another_origin(self) -> None:
        valid = copy.deepcopy(self.receipt)
        for wrong in ("https://other.example/", "http://raumzeitterminal.de/",
                      "https://raumzeitterminal.de.other.example/",
                      "https://user:password@raumzeitterminal.de/",
                      "https://raumzeitterminal.de:444/", "https://[", None):
            with self.subTest(url=wrong):
                self.receipt = copy.deepcopy(valid)
                self.receipt["readback"]["delivery"]["url"] = wrong
                self.rejected("CLIENT_PUBLIC_DELIVERY_URL_INVALID")

    def test_public_delivery_observation_must_be_read_only(self) -> None:
        self.receipt["readback"]["delivery"]["method"] = "POST"
        self.rejected("CLIENT_PUBLIC_DELIVERY_URL_INVALID")

    def test_verified_delivery_requires_http_body_and_exact_final_origin(self) -> None:
        self.done()
        valid = copy.deepcopy(self.receipt)
        for key, wrong in (("http_status", 404), ("http_status", "200"),
                           ("response_sha256", ""), ("response_sha256", True),
                           ("final_url", "https://other.example/"),
                           ("final_url", "http://raumzeitterminal.de/")):
            with self.subTest(key=key, value=wrong):
                self.receipt = copy.deepcopy(valid)
                self.receipt["readback"]["delivery"][key] = wrong
                self.rejected("CLIENT_PUBLIC_DELIVERY_PROOF_INCOMPLETE")

    def test_fresh_unobservable_delivery_is_unknown_and_never_done(self) -> None:
        self.block()
        self.receipt["readback"]["delivery"].update(
            diagnostic="fixture:client-DNS-unavailable", state="UNKNOWN")
        self.assertEqual(self.check(), "BLOCK")
        self.done()
        self.receipt["readback"]["delivery"]["state"] = "UNKNOWN"
        self.rejected("CLIENT_DONE_WITHOUT_EXACT_EFFECT_READBACK")

    def test_every_effectful_attempt_requires_its_own_closing_readback(self) -> None:
        attempt = self.attempt(changed=True)
        self.receipt["attempts"] = [attempt]
        del attempt["readback"]
        self.rejected("CLIENT_CLOSING_READBACK_MISSING")

    def test_terminal_readback_cannot_hide_stale_attempt_readback(self) -> None:
        attempt = self.attempt(changed=True)
        self.receipt["attempts"] = [attempt]
        attempt["readback"]["repository"]["observed_at"] = "2026-10-11T09:59:59Z"
        self.rejected("CLIENT_READBACK_NOT_FRESH:repository")

    def test_three_existing_routes_obey_same_closing_gate_through_cli(self) -> None:
        valid = copy.deepcopy(self.receipt)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "client.json"
            for route in ("connector", "cli", "mesh"):
                for fresh in (True, False):
                    with self.subTest(route=route, fresh=fresh):
                        receipt = copy.deepcopy(valid)
                        receipt["next_actions"][0]["route"] = route
                        if not fresh:
                            receipt["readback"]["repository"]["observed_at"] = "2026-10-11T09:59:59Z"
                        path.write_text(json.dumps(receipt))
                        result = subprocess.run(
                            [sys.executable, "-B", "tools/ai_handoff.py", "--client-receipt", str(path), "--historical-client-receipt"],
                            cwd=ROOT, capture_output=True, text=True, timeout=10)
                        self.assertEqual(result.returncode, 0 if fresh else 2, result.stderr)
                        self.assertNotIn("Traceback", result.stderr)

    def test_changing_only_delivery_clock_does_not_admit_failed_action_retry(self) -> None:
        self.receipt["readback"]["delivery"]["observed_at"] = "2026-10-11T10:00:03Z"
        self.receipt["attempts"] = [self.attempt()]
        self.rejected("CLIENT_UNCHANGED_FAILURE_RETRIED")

    def test_separate_effectful_actions_cannot_reuse_one_observation_pair(self) -> None:
        first = self.attempt(changed=True)
        second = copy.deepcopy(first)
        second["current"]["cause"] = "6" * 64
        self.receipt["attempts"] = [first, second]
        self.rejected("CLIENT_CLOSING_ACTION_REUSED")
        second["action_window"]["id"] = "fixture:action-2"
        for kind in ("repository", "delivery"):
            second["readback"][kind]["action_id"] = "fixture:action-2"
        self.assertEqual(self.check(), "CONTINUE")

    def test_timezone_offsets_are_compared_as_instants(self) -> None:
        self.receipt["readback"]["repository"]["observed_at"] = "2026-10-11T13:00:01+03:00"
        self.receipt["readback"]["delivery"]["observed_at"] = "2026-10-11T12:00:02+02:00"
        self.assertEqual(self.check(), "CONTINUE")
        self.receipt["readback"]["delivery"]["observed_at"] = "2026-10-11T13:00:00+03:00"
        self.rejected("CLIENT_READBACK_NOT_FRESH:delivery")

    def test_registered_adapters_share_authority_but_are_not_live_client_witnesses(self) -> None:
        registry = json.loads((ROOT / "AI_ADAPTERS.json").read_text())
        self.assertEqual(registry["canonical_entrypoint"], "AI")
        self.assertIn("compatibility shims only", registry["rule"])
        context = json.loads((ROOT / "AI_CONTEXT.json").read_text())
        _, count = self.handoff.validate_adapters(context)
        self.assertEqual(count, len(registry["adapters"]))

    def test_regression_contract_reuses_exact_owner_rule_from_pr507(self) -> None:
        import hashlib
        policy = json.loads((ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json").read_text())
        binding = policy["client_continuation"]["end_of_action_rule"]
        path = ROOT / binding["path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), binding["sha256"])
        self.assertEqual(binding["source_head"], "42008f98a94c28e9bfc1ae902fb190296c6ac5a6")
        rule = json.loads(path.read_text())
        self.assertEqual(rule["delegation_id"], "OWNER-END-OF-ACTION-VERIFICATION-GRUNDREGEL-V1")
        self.assertTrue(rule["boundaries"]["readback_is_not_effect_ack"])
        self.assertEqual(rule["continuation_rules"]["unchanged_error"], "DO_NOT_TRIGGER_A_RENEWED_ATTEMPT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
