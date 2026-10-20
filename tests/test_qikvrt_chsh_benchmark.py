# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Independent analytic controls and deliberately invalid CHSH inputs."""
import itertools
import json
import hashlib
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src import qikvrt_chsh_benchmark as ch


def relabel_alice(box, setting=None):
    return {(x, y): {(a, b): row[-a if setting is None or x == setting else a, b]
                     for a, b in ch.OUTCOMES} for (x, y), row in box.items()}


ORIGINAL_PUBLICATION_README = "docs/publications/2026-09-23-qik-scientific-revision/README.md"
ARCHIVED_PUBLICATION_README = "docs/publications/2026-09-23-qik-scientific-revision/evidence/zenodo-readback-20261019/files/README.md"


def validate_original_package_locations(locations):
    """Only the already archived historical README may relocate; never a manuscript."""
    if locations != {ORIGINAL_PUBLICATION_README: ARCHIVED_PUBLICATION_README}:
        raise ValueError("EXACT_HISTORICAL_README_RELOCATION_REQUIRED")
    return locations


class CHSHReferenceTests(unittest.TestCase):
    def test_shared_bit_joint_table_and_correlations(self):
        box = ch.classical_reference()
        for row in box.values():
            self.assertEqual(row, {(-1, -1): .5, (-1, 1): 0., (1, -1): 0., (1, 1): .5})
        self.assertEqual(list(ch.correlations(box).values()), [1.] * 4)
        self.assertEqual(ch.chsh(box), 2.)

    def test_born_joint_table_against_analytic_formula(self):
        box = ch.quantum_reference()
        for (x, y), row in box.items():
            expected_e = (-1 if x == y == 1 else 1) / math.sqrt(2)
            for (a, b), p in row.items():
                self.assertAlmostEqual(p, (1 + a * b * expected_e) / 4, delta=ch.TOLERANCE)
            self.assertAlmostEqual(ch.correlations(box)[x, y], expected_e, delta=ch.TOLERANCE)
        self.assertAlmostEqual(ch.chsh(box), 2 * math.sqrt(2), delta=ch.TOLERANCE)

    def test_born_nonoptimal_settings_not_hardcoded_maximum(self):
        aa, bb = (.13, .59), (.36, -.72)
        box = ch.quantum_reference(aa, bb)
        for (x, y), row in box.items():
            for (a, b), p in row.items():
                self.assertAlmostEqual(p, (1 + a * b * math.cos(aa[x] - bb[y])) / 4,
                                       delta=ch.TOLERANCE)
        self.assertLess(abs(ch.chsh(box)), ch.TSIRELSON - .1)
        ch.require_chsh_ceiling(box, ch.TSIRELSON)

    def test_born_coincident_settings_have_nonnegative_probabilities(self):
        for angle in (0., math.pi / 4, math.pi / 2, math.pi):
            box = ch.quantum_reference((angle, angle), (angle, angle))
            self.assertAlmostEqual(ch.correlations(box)[0, 0], 1.)
            self.assertGreaterEqual(min(p for row in box.values() for p in row.values()), 0.)

    def test_pr_parity_and_algebraic_maximum(self):
        box = ch.pr_reference()
        for (x, y), row in box.items():
            for (a, b), p in row.items():
                # Independent bit convention alpha=(1-a)/2, beta=(1-b)/2.
                parity = ((1 - a) // 2) ^ ((1 - b) // 2)
                self.assertEqual(p, .5 if parity == x * y else 0.)
        self.assertEqual(ch.chsh(box), 4.)

    def test_all_three_are_normalized_unbiased_and_no_signalling(self):
        for factory in (ch.classical_reference, ch.quantum_reference, ch.pr_reference):
            with self.subTest(case=factory.__name__):
                box = factory()
                ch.validate_box(box)
                self.assertLessEqual(max(ch.no_signalling_residuals(box).values()), ch.TOLERANCE)
                for row in box.values():
                    for v in (-1, 1):
                        self.assertAlmostEqual(sum(row[v, b] for b in (-1, 1)), .5)
                        self.assertAlmostEqual(sum(row[a, v] for a in (-1, 1)), .5)

    def test_all_sixteen_local_vertices(self):
        count = 0
        for responses in itertools.product((-1, 1), repeat=4):
            box = ch.local_deterministic(responses)
            self.assertEqual(abs(ch.chsh(box)), 2.)
            self.assertEqual(len(ch.chsh_facets(box)), 8)
            ch.require_chsh_ceiling(box, 2.)
            count += 1
        self.assertEqual(count, 16)

    def test_nonuniform_local_convex_mixture_stays_local(self):
        boxes = [ch.local_deterministic(v) for v in itertools.product((-1, 1), repeat=4)]
        # Positive weights sum to 136. This tests mixed rather than just vertex inputs.
        mix = {xy: {ab: sum((i + 1) * box[xy][ab] for i, box in enumerate(boxes)) / 136
                    for ab in ch.OUTCOMES} for xy in ch.SETTINGS}
        ch.require_chsh_ceiling(mix, 2.)

    def test_positive_ceiling_controls(self):
        ch.require_chsh_ceiling(ch.classical_reference(), 2.)
        ch.require_chsh_ceiling(ch.quantum_reference(), ch.TSIRELSON)
        ch.require_chsh_ceiling(ch.pr_reference(), 4.)

    def test_quantum_rejected_by_classical_control(self):
        with self.assertRaisesRegex(ValueError, "CHSH ceiling"):
            ch.require_chsh_ceiling(ch.quantum_reference(), 2.)

    def test_pr_rejected_by_quantum_control_despite_no_signalling(self):
        self.assertEqual(ch.no_signalling_residuals(ch.pr_reference()), {"alice": 0., "bob": 0.})
        with self.assertRaisesRegex(ValueError, "CHSH ceiling"):
            ch.require_chsh_ceiling(ch.pr_reference(), ch.TSIRELSON)

    def test_negative_signed_quantum_value_uses_absolute_bound(self):
        box = relabel_alice(ch.quantum_reference())
        self.assertAlmostEqual(ch.chsh(box), -ch.TSIRELSON)
        ch.require_chsh_ceiling(box, ch.TSIRELSON)
        with self.assertRaises(ValueError):
            ch.require_chsh_ceiling(box, 2.)

    def test_single_oriented_chsh_can_miss_pr_violation(self):
        box = relabel_alice(ch.pr_reference(), setting=0)
        self.assertEqual(ch.chsh(box), 0.)
        self.assertEqual(max(map(abs, ch.chsh_facets(box))), 4.)
        with self.assertRaisesRegex(ValueError, "CHSH ceiling"):
            ch.require_chsh_ceiling(box, ch.TSIRELSON)

    def test_chsh_ceiling_pass_does_not_certify_quantum_membership(self):
        # NS box E=(1,1,1,1/2): S=2.5, but the first three perfect quantum
        # correlations would force the fourth to be perfect too (see the doc).
        box = {xy: {(a, b): (1 + a * b * (.5 if xy == (1, 1) else 1)) / 4
                    for a, b in ch.OUTCOMES} for xy in ch.SETTINGS}
        ch.require_chsh_ceiling(box, ch.TSIRELSON)
        self.assertEqual(ch.chsh(box), 2.5)
        self.assertEqual(ch.candidate_report(box)["quantum_membership"],
                         "NOT_DECIDED_BY_THIS_BENCHMARK")

    def test_candidate_records_roundtrip(self):
        for case in ch.reference_report()["cases"]:
            box = ch.box_from_records(case["probabilities"])
            self.assertAlmostEqual(ch.candidate_report(box)["S"], case["S"])

    def test_candidate_cli_reports_pr_violation_without_claiming_membership(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "candidate.json"
            p.write_text(json.dumps(ch.reference_report()["cases"][2]["probabilities"]))
            r = subprocess.run([sys.executable, "-B", "-m", "src.qikvrt_chsh_benchmark",
                                "--candidate", str(p)], cwd=root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertTrue(report["no_signalling"])
        self.assertEqual(report["S"], 4.)
        self.assertFalse(report["within_quantum_CHSH_ceiling"])
        self.assertFalse(report["qik_derivation"])

    def test_original_publication_package_is_byte_unchanged(self):
        root = Path(__file__).resolve().parents[1]
        binding_raw = (root / "evidence/chsh-reference/SOURCE_BINDINGS.json").read_bytes()
        binding = json.loads(binding_raw)
        integration = json.loads((root / "evidence/chsh-reference/INTEGRATION_BINDINGS_20261020.json").read_text())
        self.assertEqual(hashlib.sha256(binding_raw).hexdigest(), integration["historical_source_binding_sha256"])
        locations = validate_original_package_locations(integration["historical_source_locations"])
        for item in binding["unchanged_original_files"]:
            raw = (root / locations.get(item["path"], item["path"])).read_bytes()
            self.assertEqual(len(raw), item["bytes"], item["path"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"], item["path"])
            self.assertEqual(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
                             item["git_blob_sha1"], item["path"])

    def test_current_readme_is_an_exact_bound_status_successor(self):
        root = Path(__file__).resolve().parents[1]
        integration = json.loads((root / "evidence/chsh-reference/INTEGRATION_BINDINGS_20261020.json").read_text())
        item = integration["current_status_readme"]
        self.assertEqual(item["path"], ORIGINAL_PUBLICATION_README)
        raw = (root / item["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), item["sha256"])
        self.assertEqual(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(), item["git_blob_sha1"])
        self.assertNotEqual(raw, (root / ARCHIVED_PUBLICATION_README).read_bytes())

    def test_original_package_relocation_cannot_hide_manuscript_changes(self):
        expected = {ORIGINAL_PUBLICATION_README: ARCHIVED_PUBLICATION_README}
        self.assertEqual(validate_original_package_locations(expected), expected)
        manuscript = ORIGINAL_PUBLICATION_README.rsplit("/", 1)[0] + "/QIK_Publikationsfassung_revidiert.md"
        for invalid in ({}, {**expected, manuscript: ARCHIVED_PUBLICATION_README},
                        {ORIGINAL_PUBLICATION_README: "../README.md"},
                        {ORIGINAL_PUBLICATION_README: "unbound-copy.md"}):
            with self.subTest(locations=invalid), self.assertRaisesRegex(ValueError, "HISTORICAL_README"):
                validate_original_package_locations(invalid)

    def test_deterministic_json_cli_and_committed_result(self):
        root = Path(__file__).resolve().parents[1]
        raw = subprocess.check_output([sys.executable, "-B", "-m", "src.qikvrt_chsh_benchmark"], cwd=root)
        self.assertEqual(raw, subprocess.check_output(
            [sys.executable, "-B", "-m", "src.qikvrt_chsh_benchmark"], cwd=root))
        report = json.loads(raw)
        self.assertEqual(report, ch.reference_report())
        expected = root / "evidence/chsh-reference/REFERENCE_RESULTS.json"
        def compare(actual, frozen):
            if type(actual) is float:
                self.assertAlmostEqual(actual, frozen, delta=ch.TOLERANCE)
            elif isinstance(actual, dict):
                self.assertEqual(set(actual), set(frozen))
                for k in actual:
                    compare(actual[k], frozen[k])
            elif isinstance(actual, list):
                self.assertEqual(len(actual), len(frozen))
                for a, b in zip(actual, frozen):
                    compare(a, b)
            else:
                self.assertEqual(actual, frozen)
        compare(report, json.loads(expected.read_text()))
        self.assertFalse(report["empirical_measurement"])
        self.assertFalse(report["formal_kernel_proof"])
        for case in report["cases"]:
            self.assertFalse(case["qik_derivation"])
            self.assertFalse(case["quantum_membership_certified_by_ceiling"])


class CHSHNegativeControls(unittest.TestCase):
    def test_bad_probabilities(self):
        for value in (-1e-15, 1.1, math.nan, math.inf, -math.inf, True, "0.5", 10**1000):
            with self.subTest(value=value):
                box = ch.classical_reference()
                box[0, 0][-1, -1] = value
                with self.assertRaises(ValueError):
                    ch.validate_box(box)

    def test_bad_normalization(self):
        box = ch.classical_reference()
        box[0, 0][-1, -1] = .4
        with self.assertRaisesRegex(ValueError, "normalized"):
            ch.chsh(box)

    def test_missing_settings(self):
        box = ch.pr_reference()
        del box[1, 1]
        with self.assertRaises(ValueError):
            ch.validate_box(box)

    def test_missing_zero_is_not_silently_imputed(self):
        box = ch.pr_reference()
        del box[0, 0][-1, 1]
        with self.assertRaises(ValueError):
            ch.validate_box(box)

    def test_extra_outcome(self):
        box = ch.pr_reference()
        box[0, 0][0, 0] = 0.
        with self.assertRaises(ValueError):
            ch.validate_box(box)

    def test_boolean_and_float_setting_aliases(self):
        for alias in ((False, 0), (0., 0)):
            box = ch.pr_reference()
            row = box.pop((0, 0))
            box[alias] = row
            with self.assertRaises(ValueError):
                ch.validate_box(box)

    def test_signalling_in_both_directions_rejected_below_chsh_ceiling(self):
        for party in ("alice", "bob"):
            box = {}
            for x, y in ch.SETTINGS:
                outcome = ((-1 if y else 1), 1) if party == "alice" else (1, (-1 if x else 1))
                box[x, y] = {ab: float(ab == outcome) for ab in ch.OUTCOMES}
            ch.validate_box(box)
            residuals = ch.no_signalling_residuals(box)
            self.assertEqual(residuals[party], 1.)
            self.assertLessEqual(abs(ch.chsh(box)), 2.)
            with self.assertRaisesRegex(ValueError, "no-signalling"):
                ch.require_chsh_ceiling(box, 4.)

    def test_invalid_ceilings(self):
        for value in (-1, math.nan, math.inf, True, 10**1000):
            with self.assertRaises(ValueError):
                ch.require_chsh_ceiling(ch.pr_reference(), value)

    def test_bad_local_responses(self):
        for values in ((1, 1), (1, 1, 1, 0), (True, 1, 1, 1)):
            with self.assertRaises(ValueError):
                ch.local_deterministic(values)

    def test_bad_quantum_settings(self):
        for angles in ((0,), (0, math.nan), (False, 0)):
            with self.assertRaises(ValueError):
                ch.quantum_reference(alice_angles=angles)

    def test_invalid_candidate_records(self):
        records = ch.reference_report()["cases"][0]["probabilities"]
        duplicate = [dict(r) for r in records]
        duplicate[-1] = dict(duplicate[0])
        wrong_type = [dict(r) for r in records]
        wrong_type[0]["x"] = False
        for invalid in (records[:-1], duplicate, wrong_type):
            with self.assertRaises(ValueError):
                ch.box_from_records(invalid)

    def test_candidate_cli_rejects_invalid_table(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "candidate.json"
            p.write_text("[]")
            r = subprocess.run([sys.executable, "-B", "-m", "src.qikvrt_chsh_benchmark",
                                "--candidate", str(p)], cwd=root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertIn("sixteen", r.stderr)


if __name__ == "__main__":
    unittest.main()
