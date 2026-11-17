#!/usr/bin/env python3
"""TEMDD static/finite-model checks; not a substitute for the Lean kernel."""

from itertools import product
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'formalization' / 'QIKVRT_Formalization_v2.0'
SOURCE = PROJECT / 'QIKVRTFormalization' / 'WorldFormula' / 'ScienceRulesWorlds.lean'
AUDIT = PROJECT / 'QIKVRTFormalization' / 'WorldFormula' / 'ScienceRulesWorldsAxiomAudit.lean'
DOC = ROOT / 'docs' / 'formalization' / 'SCIENCE_RULES_WORLDS_SEMANTICS.md'


class ScienceRulesWorldsContractTests(unittest.TestCase):
    def test_contract_exists_and_has_no_proof_holes(self):
        source = SOURCE.read_text(encoding='utf8')
        self.assertIn('import QIKVRTFormalization.WorldFormula.Relations', source)
        self.assertIsNone(re.search(r'(?m)^\s*(?:sorry|admit|axiom)\b', source))
        self.assertNotIn('by_contra', source)
        self.assertIn('Classical.byContradiction', source)
        for theorem in (
            'science_is_fiction_not_iff_science_rules_worlds',
            'verified_gate_science_rules_worlds',
            'unrestricted_admission_is_not_scientific',
            'science_rules_worlds_implies_model_establishment',
        ):
            self.assertRegex(source, rf'(?m)^theorem {theorem}\b')

    def test_both_exported_root_imports(self):
        target = 'import QIKVRTFormalization.WorldFormula.ScienceRulesWorlds'
        for entry in ('QIKVRTFormalization.lean', 'QIKVRTUniversalOntology.lean'):
            lines = (PROJECT / entry).read_text(encoding='utf8').splitlines()
            self.assertEqual(lines.count(target), 1, entry)

    def test_axiom_audit_is_present(self):
        audit = AUDIT.read_text(encoding='utf8')
        self.assertIn('import QIKVRTFormalization.WorldFormula.ScienceRulesWorlds', audit)
        self.assertIn('#print axioms QIKVRT.V2.WorldFormula.science_is_fiction_not_iff_science_rules_worlds', audit)
        self.assertIn('#print axioms QIKVRT.V2.WorldFormula.unrestricted_admission_is_not_scientific', audit)
        self.assertEqual((PROJECT / 'lean-toolchain').read_text().strip(), 'leanprover/lean4:v4.19.0')

    def test_logical_equivalence_all_four_boolean_cases(self):
        # One state and one claim suffice to enumerate the base truth table.
        # The general proof belongs to Lean, not to this finite check.
        for admitted, qualified in product((False, True), repeat=2):
            science_is_fiction_not = (not (not qualified)) or (not admitted)
            science_rules_worlds = (not admitted) or qualified
            self.assertEqual(science_is_fiction_not, science_rules_worlds)
        # Countermodel: unconditional admission with missing qualification.
        self.assertFalse((not True) or False)

    def test_epistemic_boundary_is_documented(self):
        doc = DOC.read_text(encoding='utf8')
        for phrase in ('not literary fiction', 'not establish', 'kernel receipt', 'PhysicallyQualified', 'single-writer'):
            self.assertIn(phrase, doc)


if __name__ == '__main__':
    unittest.main()
