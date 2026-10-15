from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_lean_axioms import parse_axiom_reports


class MeasurementTransferAuditTests(unittest.TestCase):
    def test_actual_wrapped_lean_report_preserves_all_dependencies(self) -> None:
        name = "QIKVRT.V2.Physics.MeasurementTransfer.bounded_prediction_transfers"
        output = f"'{name}' depends on axioms: [propext,\n Classical.choice,\n Quot.sound]\n"
        self.assertEqual(parse_axiom_reports(output), [
            (name, {"propext", "Classical.choice", "Quot.sound"})
        ])

    def test_unapproved_dependency_is_retained_across_line_break(self) -> None:
        reports = parse_axiom_reports(
            "'scoped' depends on axioms: [propext,\n sorryAx]\n"
        )
        self.assertEqual(reports, [("scoped", {"propext", "sorryAx"})])

    def test_adjacent_zero_and_multi_line_reports_remain_separate(self) -> None:
        reports = parse_axiom_reports(
            "'first' does not depend on any axioms\n"
            "'second' depends on axioms: [propext,\n Quot.sound]\n"
        )
        self.assertEqual(reports, [
            ("first", set()), ("second", {"propext", "Quot.sound"})
        ])


if __name__ == "__main__":
    unittest.main()
