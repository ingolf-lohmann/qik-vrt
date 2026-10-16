from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_lean_axioms import parse_axiom_reports

ROOT = Path(__file__).resolve().parents[1]


class HardwareReproductionConsumerTests(unittest.TestCase):
    """Run the actual workflow consumer with synthetic Lean-report fixtures."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "loop-01"
        self.out.mkdir()
        for name, source in (
            ("core.txt", "QIKVRTUniversalOntology/AxiomAudit.lean"),
            ("extended.txt", "QIKVRTUniversalOntology/ExtendedAxiomAudit.lean"),
            ("measurement.txt", "QIKVRTFormalization/QuantumFoundations/AxiomAudit.lean"),
            ("hardware.txt", "QIKVRTFormalization/Hardware/AxiomAudit.lean"),
        ):
            constants = [line.removeprefix("#print axioms ")
                         for line in (ROOT / source).read_text().splitlines()
                         if line.startswith("#print axioms ")]
            (self.out / name).write_text("".join(
                f"'{constant}' does not depend on any axioms\n" for constant in constants
            ))
        (self.out / "policy.txt").write_text("PASS axiom audit: synthetic fixture\n")
        workflow = (ROOT.parents[1] / ".github/workflows/qikvrt_mandelbrot_42_proof_reproduction.yml").read_text()
        self.consumer = textwrap.dedent(workflow.split("python3 - <<'PY'\n", 1)[1].split("\n          PY", 1)[0])
        self.original = (self.out / "hardware.txt").read_text()

    def run_consumer(self, output: str):
        (self.out / "hardware.txt").write_text(output)
        env = dict(os.environ, LOOP_DIR=str(self.out), HEAD_SHA="1" * 40,
                   TREE_SHA="2" * 40, LEAN_VERSION="SYNTHETIC_PARSER_FIXTURE")
        return subprocess.run([sys.executable, "-B", "-c", self.consumer], cwd=ROOT,
                              env=env, capture_output=True, text=True, check=False)

    def test_accepts_both_complete_groups_and_records_their_distinct_scope(self) -> None:
        result = self.run_consumer(self.original)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.out / "LOOP_RECEIPT.json").read_text())
        self.assertEqual(receipt["hardware_axiom_report_groups"], {
            "historical_authority_mirror": 22, "conditional_authority_succession": 18,
        })
        self.assertFalse(receipt["EFFECT_ACK_DONE"])

    def test_missing_or_replaced_theorem_in_either_group_is_rejected(self) -> None:
        lines = self.original.splitlines(keepends=True)
        for prefix in ("QIKVRT.V2.HardwareWitness.", "QIKVRT.V2.AuthoritySuccession."):
            index = next(i for i, line in enumerate(lines) if prefix in line)
            for replacement in ("", f"'{prefix}unapproved' does not depend on any axioms\n"):
                with self.subTest(group=prefix, replacement=replacement):
                    changed = lines.copy()
                    changed[index] = replacement
                    result = self.run_consumer("".join(changed))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("BLOCK", result.stderr)

    def test_duplicate_reports_custom_axioms_and_unexpected_output_are_rejected(self) -> None:
        cases = (
            self.original + self.original.splitlines(keepends=True)[0],
            self.original.replace("does not depend on any axioms", "depends on axioms: [sorryAx]", 1),
            self.original + "unexpected unverified output\n",
        )
        for index, changed in enumerate(cases):
            with self.subTest(case=index):
                result = self.run_consumer(changed)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("BLOCK", result.stderr)


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
