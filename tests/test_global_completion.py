#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCOPE = ROOT / "GLOBAL_COMPLETION_SCOPE.json"
INVENTORY = ROOT / "GLOBAL_CLAIM_INVENTORY.json"
TRACEABILITY = ROOT / "GLOBAL_SOURCE_CLAIM_DISPOSITION_TRACEABILITY.json"
KERNEL = ROOT / "GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json"
FINAL_INPUT = ROOT / "GLOBAL_COMPLETION_FINALIZATION_INPUT.json"
FINAL_RECEIPT = ROOT / "GLOBAL_COMPLETION_RECEIPT.json"
FORMAL_STATUS = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "GLOBAL_COMPLETION_STATUS.json"
AI_PROGRESS = ROOT / "AI_PROGRESS.json"
GENERATOR = ROOT / "tools/qikvrt_global_completion.py"
spec = importlib.util.spec_from_file_location("global_completion", GENERATOR)
generator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(generator)

ALLOWED = {
    "KERNEL_PROVED",
    "KERNEL_PROVED_CONDITIONAL",
    "EMPIRICAL_EVIDENCE_BOUND",
    "INTERPRETIVE",
    "NORMATIVE",
    "OPEN",
    "OUT_OF_SCOPE",
}


def load(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} is not an object")
    return value


class GlobalCompletionTests(unittest.TestCase):
    def test_alpha2_historical_status_freeze_is_byte_current(self) -> None:
        subprocess.run(
            [sys.executable, "-B", "tools/qikvrt_freeze_alpha2_status.py", "check"],
            cwd=ROOT,
            check=True,
        )

    def test_generator_is_byte_current(self) -> None:
        subprocess.run(
            [sys.executable, "-B", "tools/qikvrt_global_completion.py", "check"],
            cwd=ROOT,
            check=True,
        )

    def test_scope_is_exact_and_finite(self) -> None:
        scope = load(SCOPE)
        self.assertEqual(scope["scope_id"], "qikvrt-global-claim-scope-v1")
        self.assertEqual(
            [item["expected"] for item in scope["included_registries"]],
            [43, 34, 15],
        )
        self.assertEqual(set(scope["terminal_dispositions"]), ALLOWED)
        self.assertTrue(scope["excluded_classes"])
        tag = scope["exact_tag_binding"]
        self.assertEqual(
            tag["tag"],
            "v2026.07.28-authority-mirror-zenodo-equality-1.0.0",
        )
        self.assertEqual(tag["zenodo_doi"], "10.5281/zenodo.21633411")

    def test_inventory_is_complete_unique_and_terminal(self) -> None:
        inventory = load(INVENTORY)
        claims = inventory["claims"]
        self.assertEqual(len(claims), 92)
        identifiers = [item["inventory_id"] for item in claims]
        self.assertEqual(len(set(identifiers)), len(identifiers))
        self.assertEqual(
            {item["namespace"] for item in claims},
            {"MANUSCRIPT", "APPENDIX", "EFFECT_ACK"},
        )
        self.assertTrue(
            all(item["terminal_disposition"] in ALLOWED for item in claims)
        )
        self.assertTrue(all(item["source_refs"] for item in claims))
        self.assertEqual(inventory["counts"]["total"], 92)
        self.assertEqual(
            inventory["counts"]["kernel_eligible_primary_claims"], 54
        )

    def test_kernel_receipts_cover_every_primary_kernel_claim(self) -> None:
        inventory = load(INVENTORY)
        kernel = load(KERNEL)
        eligible = {
            item["inventory_id"]
            for item in inventory["claims"]
            if item["namespace"] in {"MANUSCRIPT", "EFFECT_ACK"}
            and item["terminal_disposition"]
            in {"KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL"}
        }
        receipts = {
            item["inventory_id"] for item in kernel["primary_receipts"]
        }
        self.assertEqual(eligible, receipts)
        self.assertEqual(len(receipts), 54)
        self.assertTrue(
            all(item["exact_tag_required"] for item in kernel["primary_receipts"])
        )
        self.assertTrue(kernel["tag_protected_paths"])

    def test_traceability_is_total_without_proof_inflation(self) -> None:
        inventory = load(INVENTORY)
        trace = load(TRACEABILITY)
        self.assertEqual(trace["counts"]["records"], 92)
        self.assertEqual(trace["counts"]["source_bound"], 92)
        self.assertEqual(
            {item["inventory_id"] for item in trace["records"]},
            {item["inventory_id"] for item in inventory["claims"]},
        )
        self.assertTrue(
            trace["completeness"]["every_primary_kernel_claim_has_native_receipt"]
        )
        self.assertTrue(
            trace["completeness"][
                "non_kernel_claims_are_not_misrepresented_as_lean_theorems"
            ]
        )
        for item in trace["records"]:
            requirement = item["proof_or_disposition"]["requirement"]
            if item["terminal_disposition"] in {
                "EMPIRICAL_EVIDENCE_BOUND",
                "INTERPRETIVE",
                "NORMATIVE",
                "OPEN",
                "OUT_OF_SCOPE",
            }:
                self.assertNotEqual(requirement, "NATIVE_LEAN_KERNEL_RECEIPT")

    def test_final_receipt_is_fail_closed_until_authorized(self) -> None:
        status = load(FORMAL_STATUS)
        if FINAL_INPUT.exists():
            receipt = load(FINAL_RECEIPT)
            self.assertEqual(receipt["state"], "FINAL_PASS")
            self.assertTrue(all(receipt["claims"].values()))
            self.assertTrue(receipt["claim_semantics"]["scope_qualified"])
            self.assertTrue(
                receipt["claim_semantics"]["open_claims_are_not_claimed_proved"]
            )
            self.assertEqual(status["state"], "FINAL_PASS")
        else:
            self.assertFalse(FINAL_RECEIPT.exists())
            self.assertEqual(status["state"], "CANDIDATE_MATERIALIZED")

    def test_root_projection_owner_is_explicit_and_supersedable(self) -> None:
        receipt = generator.terminal_batch_002_receipt()
        self.assertIsNotNone(receipt)
        progress = load(AI_PROGRESS)
        global_receipt = load(FINAL_RECEIPT)
        generator.validate_root_progress_owner(progress, global_receipt)
        future = copy.deepcopy(progress)
        future["operation_id"] = "future-content-disposition-owner"
        future["projection_owner"] = {
            "tool": "tools/qikvrt_global_completion.py",
            "check_command": "python3 -B tools/qikvrt_global_completion.py --check",
        }
        generator.validate_root_progress_owner(future, global_receipt)
        lost_scope = copy.deepcopy(future)
        del lost_scope["scopes"][receipt["union_id"]]
        with self.assertRaises(ValueError):
            generator.validate_root_progress_owner(
                lost_scope,
                global_receipt,
                receipt,
            )
        del future["projection_owner"]
        with self.assertRaises(ValueError):
            generator.validate_root_progress_owner(future, global_receipt)
        false_terminal = copy.deepcopy(receipt)
        false_terminal["completion_claims"]["pass"] = True
        with self.assertRaises(ValueError):
            generator.validate_terminal_batch_002_receipt(false_terminal)


class ClaimAuditTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.source = self.reference('source.json', {'statement':'declared rule'})

    def reference(self, path, value, kind='DOCUMENTARY'):
        raw=(json.dumps(value,sort_keys=True)+'\n').encode()
        (self.root/path).write_bytes(raw)
        return {'path':path,'sha256':generator.sha(raw),'source':'test fixture; no live effect','kind':kind}

    def input(self, **change):
        claim={'claim_id':'CLAIM_000001','claim_statement':'Preserve declared nodes.',
               'epistemic_domain':'NORMATIVE','claim_class':'NORMATIVE_REQUIREMENT',
               'sources':[self.source],'evidence':[]}
        claim.update(change)
        return {'schema':'qikvrt_claim_audit_input_v1','claims':[claim],'invariants':[],'relations':[]}

    def audit(self, value):
        return generator.claim_audit(value,root=self.root,timestamp='2026-10-01T20:24:10Z')

    def test_bounded_normative_audit_pass_does_not_claim_truth_or_effect(self):
        value=self.audit(self.input())
        self.assertEqual(value['claims'][0]['status'],'PASS')
        self.assertFalse(value['boundaries']['effect_ack_done'])
        self.assertFalse(value['boundaries']['audit_pass_is_claim_truth'])
        self.assertIn('INV_REALITY_001',[x['invariant_id'] for x in value['invariants']])

    def test_empirical_hypothesis_retains_verification_hold_and_no_spoofed_ack(self):
        data=self.input(epistemic_domain='EMPIRICAL',claim_class='HYPOTHESIS',
                        verification={'empirical_verified':True},effect_ack=True)
        value=self.audit(data)['claims'][0]
        self.assertEqual(value['status'],'HOLD')
        self.assertFalse(value['audit_result']['verification_sufficient'])
        self.assertFalse(any(value['verification_checklist'].values()))
        self.assertFalse(value['observed_reality_audit']['effect_ack'])

    def test_simulation_and_authority_do_not_become_observation_evidence(self):
        for kind in ('SIMULATION','DOCUMENTARY','AUTHORITY','FORMAL_PROOF','PREDICTION','CORRELATION','BELIEF'):
            evidence={**self.source,'kind':kind}
            value=self.audit(self.input(epistemic_domain='EMPIRICAL',claim_class='ASSERTION',evidence=[evidence]))
            self.assertEqual(value['claims'][0]['status'],'FAIL',kind)
            self.assertEqual(value['audit_summary']['category_errors'],1)

    def test_primary_observation_binding_does_not_authenticate_its_claim(self):
        value=self.audit(self.input(epistemic_domain='EMPIRICAL',claim_class='ASSERTION',
                                   evidence=[{**self.source,'kind':'OBSERVATION'}]))
        self.assertEqual(value['claims'][0]['status'],'HOLD')
        self.assertTrue(value['claims'][0]['evidence_checklist']['evidence_hash_valid'])
        self.assertFalse(value['claims'][0]['verification_checklist']['empirical_verified'])

    def test_duplicate_claim_and_cross_domain_theorem_fail(self):
        data=self.input();data['claims']*=2
        self.assertEqual(self.audit(data)['audit_summary']['claims_failed'],2)
        value=self.audit(self.input(epistemic_domain='EMPIRICAL',claim_class='THEOREM'))
        self.assertTrue(value['claims'][0]['epistemic_audit']['category_error'])

    def test_sources_and_reality_chain_cannot_escape_root_or_hide_drift(self):
        for path in ('../source.json','/etc/passwd'):
            value=self.audit(self.input(sources=[{**self.source,'path':path}]))
            self.assertEqual(value['claims'][0]['status'],'FAIL')
        (self.root/'link.json').symlink_to(self.root/'source.json')
        value=self.audit(self.input(sources=[{**self.source,'path':'link.json'}]))
        self.assertEqual(value['claims'][0]['status'],'FAIL')
        value=self.audit(self.input(observed_reality={'readback':{**self.source,'sha256':'0'*64}}))
        self.assertEqual(value['claims'][0]['status'],'FAIL')
        self.assertIsNone(value['claims'][0]['observed_reality_audit']['readback'])

    def test_indirect_forbidden_inference_is_detected(self):
        data=self.input();data['relations']=[{'subject':'TRANSPORT_ACK','relation':'IMPLIES','object':'BRIDGE'},
                                           {'subject':'BRIDGE','relation':'IMPLIES','object':'EFFECT_ACK'}]
        value=self.audit(data)
        self.assertEqual(value['audit_summary']['non_implication_violations'],1)
        self.assertEqual(value['invariants'][-1]['status'],'FAIL')

    def test_bound_subset_runs_and_missing_nodes_fail(self):
        old=self.reference('old.json',{'nodes':['A','B']})
        new=self.reference('new.json',{'nodes':['A','B','C']})
        data=self.input();data['invariants']=[{'invariant_id':'INV_000001','class':'STRUCTURAL',
            'statement':'OLD_NODES ⊆ NEW_NODES','predicate':{'type':'SET_SUBSET','old':old,'new':new}}]
        value=self.audit(data)['invariants'][0]
        self.assertEqual(value['status'],'PASS')
        self.assertTrue(value['runtime_audit']['rule_executable'])
        data['invariants'][0]['predicate']['new']=self.reference('new.json',{'nodes':['A']})
        value=self.audit(data)['invariants'][0]
        self.assertEqual(value['status'],'FAIL')
        self.assertTrue(value['runtime_audit']['runtime_violation'])

    def test_unknown_rule_and_source_absence_stay_hold(self):
        data=self.input(sources=[]);data['invariants']=[{'id':'INV_UNDECIDED','class':'RUNTIME','statement':'Arbitrary prose','status':'PASS'}]
        value=self.audit(data)
        self.assertEqual(value['claims'][0]['status'],'HOLD')
        self.assertEqual(value['invariants'][0]['status'],'HOLD')
        self.assertFalse(value['audit_of_audit']['sources_traceable'])

    def test_meta_audit_rejects_rehashed_summary_or_stale_source(self):
        data=self.input();report=self.audit(data)
        self.assertTrue(generator.verify_claim_audit(report,data,root=self.root))
        report['audit_summary']['claims_checked']=999
        report.pop('report_sha256');report['report_sha256']=generator.sha(generator.pretty(report).encode())
        self.assertFalse(generator.verify_claim_audit(report,data,root=self.root))
        report=self.audit(data)
        (self.root/'source.json').write_text('{}')
        self.assertFalse(generator.verify_claim_audit(report,data,root=self.root))

    def test_json_duplicates_nonfinite_and_override_are_rejected(self):
        for raw in ('{"claims":[],"claims":[]}','{"x":NaN}','[]'):
            with self.assertRaises(ValueError):generator.audit_json(raw)
        data=self.input();data['invariants']=[{'id':'INV_REALITY_001','status':'PASS'}]
        with self.assertRaises(ValueError):self.audit(data)

    def test_existing_inventory_is_audited_without_predecessor_proof_transfer(self):
        inventory=load(INVENTORY)
        raw=INVENTORY.read_bytes()
        report=generator.claim_audit(inventory,timestamp='2026-10-01T20:24:10Z')
        self.assertEqual(report['audit_summary']['claims_checked'],92)
        self.assertEqual(report['audit_summary']['claims_failed'],0)
        self.assertGreater(report['audit_summary']['claims_held'],0)
        self.assertEqual(INVENTORY.read_bytes(),raw)
        self.assertTrue(all(not x['audit_result']['verification_sufficient'] for x in report['claims']))

    def test_runtime_audit_precedes_historical_global_gates(self):
        text=(ROOT/'.github/workflows/qikvrt_global_completion.yml').read_text()
        self.assertLess(text.index('      - name: Audit claim domains'),text.index('      - name: Diagnose frozen inputs'))
        self.assertIn('qikvrt-claim-audit-${{ github.run_id }}-${{ github.run_attempt }}',text)

    def test_policy_and_schemas_match_implemented_classes_and_boundaries(self):
        policy=load(ROOT/'policy/QIKVRT_CLAIM_AUDIT_V1.json')
        self.assertEqual(set(policy['invariant_classes']),generator.INVARIANT_CLASSES)
        self.assertEqual({(x['subject'],x['object']) for x in policy['non_implications']},set(generator.NON_IMPLICATIONS))
        self.assertEqual(policy['automatically_required_invariant']['statement'],generator.REALITY_STATEMENT)
        self.assertFalse(policy['boundaries']['effect_ack_done'])
        schema=load(ROOT/'schemas/qikvrt_claim_audit_v1.schema.json')
        self.assertEqual(schema['properties']['schema']['const'],'qikvrt_claim_audit_v1')



if __name__ == "__main__":
    unittest.main(verbosity=2)
