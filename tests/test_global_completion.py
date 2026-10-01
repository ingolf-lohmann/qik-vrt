#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
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



class LeanKernelAuditTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='qikvrt-kernel-test-')
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        paths = set(load(KERNEL)['tag_protected_paths']) | {'GLOBAL_CLAIM_INVENTORY.json', 'GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json',
            'tools/qikvrt_global_completion.py', 'policy/QIKVRT_CLAIM_AUDIT_V1.json',
            'tools/lean/ClaimKernel.lean', 'third_party/lean4checker/Replay.lean'}
        paths |= {p.relative_to(ROOT).as_posix() for p in (ROOT/'formalization/QIKVRT_Formalization_v2.0').rglob('*.lean') if '.lake' not in p.parts}
        paths |= {'formalization/QIKVRT_Formalization_v2.0/'+p for p in ('lean-toolchain', 'lakefile.toml', 'lake-manifest.json')}
        for path in paths:
            target = self.root/path; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/path, target)
        self.git('init', '-q')
        objects = subprocess.check_output(['git', 'rev-parse', '--git-path', 'objects'], cwd=ROOT, text=True).strip()
        (self.root/'.git/objects/info/alternates').write_text(str((ROOT/objects).resolve())+'\n')
        (self.root/'.git/info/exclude').write_text('.lake/\n')
        tag_commit = subprocess.check_output(['git', 'rev-parse', generator.TAG+'^{commit}'], cwd=ROOT, text=True).strip()
        self.git('update-ref', 'refs/tags/'+generator.TAG, tag_commit)
        self.freeze()
        spec = importlib.util.spec_from_file_location('kernel_fixture', self.root/'tools/qikvrt_global_completion.py')
        self.engine = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.engine)
        registered = self.engine.normalize_audit_input(load(self.root/'GLOBAL_CLAIM_INVENTORY.json'))['claims']
        self.claim = next(c for c in registered if c['claim_id'] == 'MANUSCRIPT::DEF-001')
        self.data = {'schema':'qikvrt_claim_audit_input_v1', 'claims':[self.claim], 'invariants':[], 'relations':[]}

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.STDOUT, text=True).strip()

    def freeze(self):
        self.git('add', '.')
        self.git('-c', 'user.name=Kernel test fixture', '-c', 'user.email=kernel-test@example.invalid',
                 'commit', '-q', '--allow-empty', '-m', 'Freeze exact kernel test candidate')

    def parameters(self, execution_id='fixture/run-1/attempt-1'):
        subject = self.engine.audit_subject(self.root)
        return {'root':self.root, 'formal_verifier':True, 'expected_head':subject['head_sha'],
                'expected_tree':subject['tree_sha'], 'execution_id':execution_id}

    def audit(self):
        return self.engine.claim_audit(self.data, timestamp='2026-10-02T00:00:00Z', **self.parameters())

    def require_runtime(self):
        if shutil.which('lake') is None:
            if os.environ.get('QIKVRT_REQUIRE_LEAN_AUDIT_TESTS') == '1': self.fail('mandatory locked Lean runtime missing')
            self.skipTest('native Lean tests are mandatory in the global completion workflow')

    def assert_denied(self):
        report = self.audit()
        self.assertEqual(report['formal_verifier']['status'], 'FAIL', report['formal_verifier'])
        self.assertFalse(report['claims'][0]['verification_checklist']['formal_verified'])
        self.assertFalse(report['claims'][0]['audit_result']['verification_sufficient'])

    def corrupt_receipt(self, mutate):
        path = self.root/'GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json'
        value = load(path); mutate(value)
        path.write_text(self.engine.pretty(value)); self.freeze(); self.assert_denied()

    def test_tampered_lean_source_is_rejected_even_after_receipt_resealing(self):
        source = self.root/self.engine.build_kernel(*self.engine.build_inventory())['primary_receipts'][12]['source']['path']
        source.write_text(source.read_text()+'\n-- manipulated source bytes\n')
        (self.root/'GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json').write_text(self.engine.pretty(self.engine.build_kernel(*self.engine.build_inventory())))
        self.freeze(); self.assert_denied()

    def test_stale_tag_is_rejected(self):
        self.git('update-ref', 'refs/tags/'+generator.TAG, self.git('rev-parse', 'HEAD'))
        self.assert_denied()

    def test_stale_receipt_is_rejected(self):
        self.corrupt_receipt(lambda v: v['tag_binding'].update(shared_git_tree_sha1='0'*40))

    def test_wrong_proof_constant_is_rejected(self):
        self.corrupt_receipt(lambda v: v['primary_receipts'][12].update(proof_constants=['QIKVRT.V2.Definitions.DEF002_checked']))

    def test_wrong_registry_constant_is_rejected(self):
        self.corrupt_receipt(lambda v: v['primary_receipts'][12].update(registry_constant='QIKVRT.V2.Claims.DEF002'))

    def test_expected_head_tree_and_execution_id_cannot_be_inferred_from_report(self):
        for changes in ({'expected_head':'0'*40}, {'expected_tree':'0'*40}, {'execution_id':None}):
            with self.assertRaises(ValueError):
                self.engine.claim_audit(self.data, timestamp='2026-10-02T00:00:00Z', **{**self.parameters(), **changes})
        self.claim.update(verification={'formal_verified':True}, verified=True, historical_disposition='KERNEL_PROVED')
        report = self.engine.claim_audit(self.data, root=self.root, timestamp='2026-10-02T00:00:00Z')
        self.assertEqual(report['claims'][0]['status'], 'HOLD')
        self.assertFalse(report['claims'][0]['verification_checklist']['formal_verified'])

    def test_unregistered_claim_is_not_admitted(self):
        self.claim['claim_id'] = 'UNREGISTERED::DEF-001'
        report = self.audit()
        self.assertEqual(report['claims'][0]['status'], 'HOLD')
        self.assertFalse(report['claims'][0]['verification_checklist']['formal_verified'])

    def test_fresh_native_kernel_verifies_registered_formal_claim_and_rejects_report_replay(self):
        self.require_runtime()
        report = self.audit()
        self.assertEqual(report['formal_verifier']['status'], 'PASS', report['formal_verifier'])
        claim = report['claims'][0]
        self.assertEqual(claim['status'], 'PASS')
        self.assertTrue(claim['verification_checklist']['formal_verified'])
        self.assertTrue(claim['formal_kernel_receipt']['compiled_objects'])
        self.assertEqual(claim['formal_kernel_receipt']['native_kernel_result']['claim_id'], self.claim['claim_id'])
        self.assertTrue(self.engine.verify_claim_audit(report, self.data, **self.parameters()))
        for boundary in ('audit_pass_is_claim_truth', 'external_effect', 'effect_ack_done'):
            self.assertFalse(report['boundaries'][boundary])
        for flag in ('empirical_verified', 'peer_reviewed', 'reproduced'):
            self.assertFalse(claim['verification_checklist'][flag])
        self.assertFalse(self.engine.verify_claim_audit(report, self.data, **self.parameters('fixture/run-2/attempt-1')))
        changed = copy.deepcopy(report); changed['claims'][0]['formal_kernel_receipt']['compiled_objects'][0]['sha256'] = '0'*64
        changed.pop('report_sha256'); changed['report_sha256'] = self.engine.sha(self.engine.pretty(changed).encode())
        self.assertFalse(self.engine.verify_claim_audit(changed, self.data, **self.parameters()))
        self.freeze()
        self.assertFalse(self.engine.verify_claim_audit(report, self.data, **self.parameters()))

    def test_altered_compiled_object_is_rejected_after_fresh_build(self):
        self.require_runtime()
        plan = self.engine.kernel_plan(self.data, root=self.root, subject=self.engine.audit_subject(self.root))
        path = self.engine.FORM/plan[0]['objects'][0]
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'altered compiled proof object')
        self.assert_denied()

    def test_empirical_peer_review_and_reproduction_requirements_stay_hold(self):
        self.require_runtime()
        self.claim['required_verifiers'] = ['PEER_REVIEW','REPRODUCTION']
        report = self.audit()
        self.assertEqual(report['claims'][0]['status'], 'HOLD')
        self.assertFalse(report['claims'][0]['audit_result']['verification_sufficient'])
        self.assertFalse(report['claims'][0]['verification_checklist']['peer_reviewed'])
        self.assertFalse(report['claims'][0]['verification_checklist']['reproduced'])
        self.claim.update(epistemic_domain='EMPIRICAL', claim_class='HYPOTHESIS', required_verifiers=[])
        report = self.audit()
        self.assertEqual(report['claims'][0]['status'], 'HOLD')
        self.assertFalse(any(report['claims'][0]['verification_checklist'].values()))

    def test_native_replay_rejects_nonallowlisted_axiom_and_missing_proof(self):
        self.require_runtime()
        env = {k:v for k,v in os.environ.items() if k not in {'LEAN_PATH', 'LEAN_SRC_PATH'}}
        prefix = pathlib.Path(self.engine.kernel_command(['lake','env','lean','--print-prefix'], cwd=self.engine.FORM, env=env))
        lean = str(prefix/'bin/lean')
        with tempfile.TemporaryDirectory(prefix='qikvrt-kernel-negative-') as directory:
            work = pathlib.Path(directory)
            self.engine.kernel_command([lean,'-o',str(work/'Replay.olean'),str(self.engine.LEAN_REPLAY)], cwd=self.engine.LEAN_REPLAY.parent, env=env)
            (work/'QIKVRTFormalization.lean').write_text('import Std\nnamespace Fixture\naxiom forbidden : False\ntheorem proof : False := forbidden\nend Fixture\n')
            (work/'QIKVRTEffectAck.lean').write_text('import Std\n')
            for module in ('QIKVRTFormalization', 'QIKVRTEffectAck'):
                self.engine.kernel_command([lean,'-o',str(work/(module+'.olean')),str(work/(module+'.lean'))], cwd=work, env=env)
            for constant, origin, message in (('Fixture.proof','QIKVRTFormalization','forbidden axiom'),
                ('Fixture.missing','QIKVRTFormalization','missing constant'),
                ('Fixture.forbidden','QIKVRTFormalization','proof is not a theorem'),
                ('Fixture.proof','QIKVRTEffectAck','wrong constant source module')):
                request = work/'plan.json'
                request.write_text(self.engine.pretty({'claims':[{'claim_id':'FIXTURE','proof_constants':[constant],
                    'constants':[constant], 'constant_modules':{constant:origin}}]}))
                with self.assertRaisesRegex(ValueError, message):
                    self.engine.kernel_command([lean,'--run',str(self.engine.LEAN_CHECKER),str(request)], cwd=work, env={**env,'LEAN_PATH':str(work)})


if __name__ == "__main__":
    unittest.main(verbosity=2)
