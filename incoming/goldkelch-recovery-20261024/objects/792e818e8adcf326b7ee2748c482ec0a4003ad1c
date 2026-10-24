import hashlib
import json
import pathlib
import unittest

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


if __name__ == "__main__":
    unittest.main()
