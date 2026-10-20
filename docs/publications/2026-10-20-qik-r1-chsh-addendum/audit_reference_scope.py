# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Artificial-cognitive contribution: OpenAI Codex, commissioned by Ingolf Lohmann.
"""Reuse PR552's pinned evaluator; diagnose its scope, never accept full QIK R1.

python3 audit_reference_scope.py --benchmark-root reference --output AUDIT_RESULT.json
Only the standard library and the supplied unchanged reference source are used.
The arcsine diagnostic concerns the (2,2,2) correlator projection. It is a
floating-point diagnostic, not an exact certificate or a general membership test.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import itertools
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent

def load_benchmark(root):
    root = Path(root).resolve()
    binding = json.loads((HERE/'SOURCE_BINDINGS.json').read_text())
    for item in binding['executed_reference_sources']:
        raw = (root/item['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('PINNED_REFERENCE_SOURCE_MISMATCH: '+item['path'])
    sys.path.insert(0, str(root))
    module = importlib.import_module('src.qikvrt_chsh_benchmark')
    if Path(module.__file__).resolve() != root/'src/qikvrt_chsh_benchmark.py':
        raise ValueError('REFERENCE_IMPORT_ORIGIN_MISMATCH')
    return module

def arcsine_diagnostic(ch, box):
    ch.validate_box(box)
    e = ch.correlations(box)
    a = {x: sum(av*box[x,0][av,bv] for av,bv in ch.OUTCOMES) for x in (0,1)}
    b = {y: sum(bv*box[0,y][av,bv] for av,bv in ch.OUTCOMES) for y in (0,1)}
    ns = max(ch.no_signalling_residuals(box).values()) <= ch.TOLERANCE
    unbiased = max(map(abs, [*a.values(), *b.values()])) <= ch.TOLERANCE
    out = {'evidence_class':'FINITE_NUMERICAL_DIAGNOSTIC',
           'target':'BIPARTITE_222_CORRELATOR_PROJECTION',
           'no_signalling':ns, 'unbiased_within_tolerance':unbiased,
           'full_probability_table_certified':False,
           'qik_derivation_certified':False,
           'exact_membership_proof':False,
           'tolerance':ch.TOLERANCE,
           'biased_full_table_requires_additional_constraints':not unbiased}
    if any(not -1 <= v <= 1 for v in e.values()):
        return {**out,'status':'OPEN_CORRELATOR_OUTSIDE_EXACT_ASIN_DOMAIN',
                'silent_clipping':False,'max_abs_arcsine_facet':None,'excess_over_pi':None}
    maximum = max(abs(math.fsum(s*math.asin(e[xy]) for s,xy in zip(signs,ch.SETTINGS)))
                  for signs in itertools.product((-1,1),repeat=4) if math.prod(signs)==-1)
    return {**out,'status':'NUMERICAL_CORRELATOR_CHECK_ONLY',
            'max_abs_arcsine_facet':maximum,'limit_pi':math.pi,
            'excess_over_pi':maximum-math.pi,
            'within_correlator_bound_numeric':maximum <= math.pi+ch.TOLERANCE,
            'certified_error_interval_available':False}

def counterexample(ch):
    return {xy:{(a,b):(1+a*b*(.5 if xy==(1,1) else 1))/4 for a,b in ch.OUTCOMES}
            for xy in ch.SETTINGS}

def report(ch, candidate_records=None):
    cases=[]
    for name, box in [('local_shared_bit',ch.classical_reference()),
                      ('imported_born_phi_plus',ch.quantum_reference()),
                      ('pr_box',ch.pr_reference()),
                      ('chsh_ceiling_counterexample',counterexample(ch))]:
        cases.append({'name':name,'benchmark':ch.candidate_report(box),
                      'arcsine':arcsine_diagnostic(ch,box)})
    out={'schema':'qik-r1-reference-scope-audit/1','reference_cases':cases,
         'universal_QIK_proof_checker_implemented':False,
         'candidate_law_supplied':False,'candidate_numeric_acceptance':'OPEN',
         'QIK_internal_derivation':'OPEN','full_R1':'OPEN',
         'empirical_experiment':False,'repository_integration_established':False}
    if candidate_records is not None:
        box=ch.box_from_records(candidate_records)
        out['external_table']={'benchmark':ch.candidate_report(box),'arcsine':arcsine_diagnostic(ch,box),
            'provenance':'INPUT_TABLE_ONLY_NO_LAW_OR_PREPARATION_WITNESS',
            'candidate_law_supplied':False}
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark-root',required=True,type=Path)
    parser.add_argument('--candidate',type=Path,help='optional 16-cell table; no law acceptance')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        ch=load_benchmark(args.benchmark_root)
        result=report(ch,json.loads(args.candidate.read_text()) if args.candidate else None)
    except (ValueError,OSError,TypeError) as error:
        parser.error(str(error))
    raw=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
    if args.output: args.output.write_text(raw)
    else: print(raw,end='')

if __name__=='__main__': main()
