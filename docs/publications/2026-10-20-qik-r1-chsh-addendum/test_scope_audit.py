# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Controls for the new narrow diagnostic and the explicit open-claim boundary."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import audit_reference_scope as audit

ROOT=Path(os.environ['QIK_R1_BENCHMARK_ROOT']).resolve()
ch=audit.load_benchmark(ROOT)

class ScopeAuditTests(unittest.TestCase):
    def test_local_reference_is_on_arcsine_boundary(self):
        r=audit.arcsine_diagnostic(ch,ch.classical_reference())
        self.assertAlmostEqual(r['max_abs_arcsine_facet'],math.pi)
        self.assertFalse(r['exact_membership_proof'])

    def test_born_reference_numeric_arcsine_control(self):
        r=audit.arcsine_diagnostic(ch,ch.quantum_reference())
        self.assertTrue(r['within_correlator_bound_numeric'])
        self.assertAlmostEqual(r['max_abs_arcsine_facet'],math.pi,delta=1e-12)
        self.assertFalse(r['full_probability_table_certified'])

    def test_pr_box_violates_arcsine_by_pi(self):
        r=audit.arcsine_diagnostic(ch,ch.pr_reference())
        self.assertFalse(r['within_correlator_bound_numeric'])
        self.assertAlmostEqual(r['excess_over_pi'],math.pi)

    def test_counterexample_passes_chsh_but_violates_arcsine_by_pi_over_three(self):
        box=audit.counterexample(ch)
        self.assertTrue(ch.candidate_report(box)['within_quantum_CHSH_ceiling'])
        self.assertAlmostEqual(audit.arcsine_diagnostic(ch,box)['excess_over_pi'],math.pi/3)

    def test_biased_table_is_not_certified_from_correlators(self):
        r=audit.arcsine_diagnostic(ch,ch.local_deterministic((1,1,1,1)))
        self.assertTrue(r['biased_full_table_requires_additional_constraints'])
        self.assertFalse(r['full_probability_table_certified'])

    def test_no_silent_clipping_at_tolerance_boundary(self):
        box=ch.classical_reference()
        box[0,0][-1,-1]+=2e-13
        box[0,0][1,1]+=2e-13
        ch.validate_box(box)
        self.assertGreater(ch.correlations(box)[0,0],1)
        r=audit.arcsine_diagnostic(ch,box)
        self.assertEqual(r['status'],'OPEN_CORRELATOR_OUTSIDE_EXACT_ASIN_DOMAIN')
        self.assertFalse(r['silent_clipping'])

    def test_signalling_table_has_cli_exit_zero_without_acceptance(self):
        box={(x,y):{ab:float(ab==((-1 if y else 1),1)) for ab in ch.OUTCOMES}
             for x,y in ch.SETTINGS}
        records=[dict(x=x,y=y,a=a,b=b,p=box[x,y][a,b]) for x,y in ch.SETTINGS for a,b in ch.OUTCOMES]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'table.json';p.write_text(json.dumps(records))
            result=subprocess.run([sys.executable,'-B','-m','src.qikvrt_chsh_benchmark','--candidate',str(p)],
                                  cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(json.loads(result.stdout)['no_signalling'])

    def test_reference_or_external_table_cannot_close_model_obligations(self):
        records=ch.reference_report()['cases'][1]['probabilities']
        r=audit.report(ch,records)
        self.assertEqual(r['full_R1'],'OPEN')
        self.assertEqual(r['QIK_internal_derivation'],'OPEN')
        self.assertFalse(r['candidate_law_supplied'])
        self.assertFalse(r['universal_QIK_proof_checker_implemented'])

if __name__=='__main__': unittest.main()
