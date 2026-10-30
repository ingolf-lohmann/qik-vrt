import hashlib
import json
import pathlib
import unittest
import copy
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

from tools.qikvrt_output_contract import (  # noqa: E402
    ARTICLE_BYTES,
    ARTICLE_PATH,
    ARTICLE_SHA256,
    BINDING_KEY,
    OutputContractError,
    bind_output,
    canonical_article_identity,
    load_policy,
    validate_output,
    validate_change_extension,
    proof_core_source_check,
)


class UniversalProofThoughtSchemaMirrorTests(unittest.TestCase):
    def base(self):
        return bind_output(
            {"schema": "mirror_test_payload_v1", "value": 1},
            node_id="mirror-test-node",
            repository="ingolf-lohmann/qik-vrt",
            subject={"head": "0" * 40, "tree": "1" * 40},
            claim_kind="SOURCE_BOUND",
            statement="Mirror output is bound to the canonical proof-and-thought schema.",
            assumptions=[],
            definitions=["QIKVRT-UNIVERSAL-PROOF-THOUGHT-SCHEMA-V1"],
            dependencies=[],
            exclusions=["physical correspondence", "general EFFECT_ACK_DONE"],
            evidence_refs=[],
            epistemic_state="RUNTIME_EVIDENCE",
            effect_state="NONE",
            transport_ack=False,
            effect_ack_done=False,
            new_difference="MIRROR_POLICY_BINDING_MATERIALIZED",
        )

    def test_article_identity_is_exact(self):
        raw = ARTICLE_PATH.read_bytes()
        self.assertEqual(len(raw), ARTICLE_BYTES)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ARTICLE_SHA256)
        self.assertEqual(canonical_article_identity()["sha256"], ARTICLE_SHA256)

    def test_policy_is_fail_closed(self):
        policy = load_policy()
        self.assertEqual(policy["status"], "MANDATORY_FAIL_CLOSED")
        self.assertTrue(policy["applies_to"]["current_and_future_node_outputs"])
        self.assertFalse(policy["invariants"]["predecessor_evidence_transfer"])

    def test_valid_binding_passes(self):
        value = self.base()
        self.assertEqual(validate_output(value), value)
        self.assertIn(BINDING_KEY, value)

    def test_missing_binding_fails(self):
        with self.assertRaises(OutputContractError):
            validate_output({"schema": "unbound"})

    def test_origin_binding_is_mandatory(self):
        value = self.base()
        del value[BINDING_KEY]["ontological_origin_proof_binding"]
        with self.assertRaisesRegex(OutputContractError, "origin"):
            validate_output(value)

    def test_predecessor_binding_cannot_be_replayed_as_successor(self):
        value = self.base()
        with self.assertRaisesRegex(OutputContractError, "successor"):
            bind_output(value, subject={"head": "a" * 40, "tree": "1" * 40})

    def test_truthy_acknowledgement_strings_are_rejected(self):
        for field in ("transport_ack", "effect_ack_done"):
            value = self.base()
            value[BINDING_KEY]["effect_status"][field] = "false"
            with self.subTest(field=field), self.assertRaises(OutputContractError):
                validate_output(value)

    def test_formal_to_empirical_promotion_is_rejected(self):
        value = self.base()
        value[BINDING_KEY]["claim"]["kind"] = "FORMAL_THEOREM"
        value[BINDING_KEY]["epistemic_status"] = "EMPIRICAL"
        with self.assertRaisesRegex(OutputContractError, "promoted"):
            validate_output(value)

    def test_missing_node_or_subject_is_rejected(self):
        for key in ("node", "subject"):
            value = self.base()
            del value[BINDING_KEY][key]
            with self.subTest(key=key), self.assertRaises(OutputContractError):
                validate_output(value)

    def test_declared_done_without_effect_receipt_and_readback_is_rejected(self):
        value = self.base()
        value[BINDING_KEY]["effect_status"].update(state="DONE_WITHIN_DECLARED_SCOPE", effect_ack_done=True)
        with self.assertRaisesRegex(OutputContractError, "receipt and readback"):
            validate_output(value)

    def test_missing_typed_evidence_field_is_rejected(self):
        value = self.base()
        del value[BINDING_KEY]["evidence"]["readback"]
        with self.assertRaisesRegex(OutputContractError, "evidence field"):
            validate_output(value)

    def test_ai_context_binds_policy_and_keeps_runtime_open(self):
        context = json.loads((ROOT / "AI_CONTEXT.json").read_text(encoding="utf-8"))
        order = context["required_read_order"]
        self.assertIn("docs/QIKVRT_UNIVERSAL_PROOF_AND_THOUGHT_SCHEMA_DE.md", order)
        self.assertIn("policy/QIKVRT_UNIVERSAL_PROOF_THOUGHT_SCHEMA_V1.json", order)
        binding = context["universal_proof_thought_schema"]
        self.assertEqual(
            binding["runtime_wiring_status"],
            "OPEN_UNTIL_RUNTIME_CARRIER_PRESENT_AND_FRESHLY_VERIFIED",
        )
        self.assertFalse(binding["predecessor_evidence_transfer"])

    def test_future_node_contract_requires_schema_before_acceptance(self):
        contract = json.loads(
            (ROOT / "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json")
            .read_text(encoding="utf-8")
        )
        acceptance = contract["mesh_node_split_acceptance"]
        self.assertIn(
            "UNIVERSAL_PROOF_THOUGHT_SCHEMA_BOUND",
            acceptance["connection_order"],
        )
        schema = acceptance["universal_proof_thought_schema"]
        self.assertTrue(schema["mandatory_for_node_acceptance"])
        self.assertTrue(schema["mandatory_for_every_node_output"])
        self.assertTrue(schema["fail_closed_on_missing_or_mismatch"])
        self.assertEqual(
            schema["runtime_enforcement_status"],
            "OPEN_UNTIL_RUNTIME_CARRIER_PRESENT_AND_FRESHLY_VERIFIED",
        )

    def test_existing_node_producer_cli_emits_the_required_binding(self):
        run = subprocess.run([sys.executable, "-B", str(ROOT / "tools/qikvrt_workflow_executor.py"),
            "node-receipt-template", "--node-repository", "ingolf-lohmann/qik-vrt",
            "--node-branch", "main", "--json"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        value = json.loads(run.stdout)
        validate_output(value)
        self.assertFalse(value["completion_claims"]["EFFECT_ACK_DONE"])


class ProofBoundChangeAdmissionTests(unittest.TestCase):
    """Fixtures model an independently obtained verifier response, not live proof."""

    def setUp(self):
        self.subject = {"repository": "ingolf-lohmann/qik-vrt", "head": "a" * 40,
                        "tree": "b" * 40, "node": "fixture-node", "epoch": 7}
        self.paths = ["src/example.py", "policy/example.json"]
        self.parent = "0" * 64
        self.extension = {"schema": "qikvrt_proof_extension_v1", "subject": self.subject,
                          "parent_root_sha256": self.parent, "changed_paths": self.paths,
                          "added_claims": ["Fixture.preserves_declared_scope"]}
        digest = hashlib.sha256(json.dumps(self.extension, sort_keys=True, separators=(",", ":"),
                                           ensure_ascii=False).encode()).hexdigest()
        self.proof = {"schema": "qikvrt_qualified_change_proof_readback_v1",
                      "state": "KERNEL_VERIFIED_IMPLEMENTATION_REFINEMENT",
                      "subject": copy.deepcopy(self.subject), "extension_sha256": digest,
                      "parent_root_sha256": self.parent, "covered_paths": list(self.paths),
                      "added_claims": list(self.extension["added_claims"]),
                      "kernel_receipt_sha256": "1" * 64, "compiled_witness_sha256": "2" * 64,
                      "new_root_sha256": "3" * 64}
        for key in ("preserves_predecessor_meaning", "conservative_extension", "fresh_kernel_check",
                    "qualified_implementation_bridge", "trusted_base_checker", "authenticated_readback"):
            self.proof[key] = True

    def check(self, proof="default"):
        return validate_change_extension(self.extension, expected_subject=self.subject,
            predecessor_root=self.parent, expected_changed_paths=self.paths,
            independently_read_proof=self.proof if proof == "default" else proof)

    def test_bound_separate_result_only_passes_structure_and_never_activates(self):
        value = self.check()
        self.assertEqual(value["state"], "BOUND_IMPLEMENTATION_PROOF_READBACK_CHECKED")
        self.assertFalse(value["activation_authorized"])
        self.assertFalse(value["native_append_executed"])
        self.assertFalse(value["effect_ack_done"])

    def test_embedded_pass_cannot_replace_unavailable_or_failed_checker(self):
        self.extension["PASS"] = True
        for value in (None, {}, {"state": "CHECKER_FAILED"}, {"state": "DECLARED_MODEL_KERNEL_VERIFIED"}):
            with self.subTest(value=value), self.assertRaisesRegex(OutputContractError, "UNVERIFIED"):
                self.check(value)

    def test_each_exact_subject_dimension_rejects_replay(self):
        for key, value in (("repository", "other/repo"), ("head", "c" * 40), ("tree", "d" * 40),
                           ("node", "other-node"), ("epoch", 6)):
            proof = copy.deepcopy(self.proof);proof["subject"][key] = value
            with self.subTest(key=key), self.assertRaises(OutputContractError):
                self.check(proof)

    def test_missing_changed_path_is_not_complete_refinement(self):
        self.extension["changed_paths"] = self.paths[:1]
        with self.assertRaisesRegex(OutputContractError, "inventory"):
            self.check()

    def test_each_proof_obligation_must_be_true_boolean(self):
        for key in ("preserves_predecessor_meaning", "conservative_extension", "fresh_kernel_check",
                    "qualified_implementation_bridge", "trusted_base_checker", "authenticated_readback"):
            for value in (None, False, "true", 1):
                proof = copy.deepcopy(self.proof);proof[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(OutputContractError):
                    self.check(proof)

    def test_predecessor_or_compiled_object_mismatch_is_rejected(self):
        for key, value in (("parent_root_sha256", "4" * 64), ("compiled_witness_sha256", "missing"),
                           ("extension_sha256", "5" * 64)):
            proof = copy.deepcopy(self.proof);proof[key] = value
            with self.subTest(key=key), self.assertRaises(OutputContractError):
                self.check(proof)

    def test_original_core_sources_are_retained_without_an_activation_claim(self):
        result = proof_core_source_check()
        self.assertEqual(result["preserved_source_count"], 69)
        self.assertFalse(result["activation_authorized"])
        self.assertFalse(result["effect_ack_done"])

    def test_existing_proof_workflow_is_not_path_filtered(self):
        workflow = (ROOT / ".github/workflows/qikvrt_manuscript_proof.yml").read_text()
        triggers = workflow.split("permissions:", 1)[0]
        self.assertIn("  push:", triggers)
        self.assertIn("  pull_request:", triggers)
        self.assertNotIn("paths:", triggers)
        self.assertIn("--proof-core-kernel", workflow)
        self.assertIn("proof-bound-change-contract", (ROOT / "Makefile").read_text())


if __name__ == "__main__":
    unittest.main()
