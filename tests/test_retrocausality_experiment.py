#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Adversarial regressions for the prospective retrocausality analysis."""
import copy
import importlib.util
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "docs/publications/2026-08-12-observer-relative-retrocausality/experiment-2026-10-15"
SPEC = importlib.util.spec_from_file_location("retro_experiment", BUNDLE / "analyze_experiment.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def fixture(n=100):
    rows = []
    for i in range(n):
        row = {"trial_id": i, "early_bit": i % 2, "later_bit": (i // 2) % 2}
        for j, name in enumerate(("early_end", "locked", "custody_ack", "entropy_start", "choice_complete")):
            row[name] = {"lo_ns": i * 1000 + j * 100, "hi_ns": i * 1000 + j * 100 + 1,
                         "clock_id": "SIMULATED_CLOCK"}
        rows.append(row)
    return {"schema": "qikvrt_retrocausality_trial_table_v1", "config": {
        "n": n, "alpha": .001, "rng_bias_bound": .001, "origin_class": "SIMULATED",
        "time_coordinate": "SIMULATED_NS"}, "trials": rows}


class RetrocausalityExperimentTests(unittest.TestCase):
    def test_exact_original_report_regenerated(self):
        r = M.check_original_witness()
        self.assertTrue(r["original_report_equal"])
        self.assertEqual(r["gradient"], "-10")
        self.assertEqual((r["source_gap"], r["old_delay"], r["new_delay"]), ("1", "3", "1"))
        self.assertEqual(r["physical_backward_effect"], "NOT_ESTABLISHED")

    def test_binomial_against_exact_enumeration(self):
        for n in range(1, 35):
            for k in range(n + 2):
                exact = sum(math.comb(n, j) for j in range(k, n + 1)) / 2 ** n
                self.assertAlmostEqual(M.upper_binomial_tail(n, k), exact, places=12)

    def test_asymmetric_binomial_against_enumeration(self):
        for p in (.1, .3, .51, .9):
            for k in range(21):
                exact = sum(math.comb(20, j) * p ** j * (1 - p) ** (20 - j) for j in range(k, 21))
                self.assertAlmostEqual(M.upper_binomial_tail(20, k, p), exact, places=12)

    def test_fixed_effect_power_and_conservative_threshold(self):
        r = M.planned_sensitivity()
        self.assertEqual(r["positive_critical_matches"], 101072)
        self.assertGreater(r["power_lower_bound_under_independent_alternative"], .99)
        self.assertGreaterEqual(r["power_numeric_under_independent_alternative"],
                                r["power_lower_bound_under_independent_alternative"])
        self.assertFalse(M.match_statistics(200000, 101071)["reject_bounded_randomness_null"])
        self.assertTrue(M.match_statistics(200000, 101072)["reject_bounded_randomness_null"])
        self.assertFalse(r["effect_size_predicted_by_qikvrt"])

    def test_two_sided_test_detects_fixed_anticode(self):
        self.assertTrue(M.match_statistics(2048, 0)["reject_bounded_randomness_null"])
        self.assertTrue(M.match_statistics(2048, 2048)["reject_bounded_randomness_null"])
        self.assertFalse(M.match_statistics(2048, 1024)["reject_bounded_randomness_null"])

    def test_missing_results_are_adversarially_bounded(self):
        # Keeping just the matching half is not a 100% success observation.
        r = M.match_statistics(2048, 1024, missing=1024)
        self.assertEqual(r["feasible_matches"], [1024, 2048])
        self.assertFalse(r["reject_bounded_randomness_null"])
        self.assertEqual(M.match_statistics(20, 0, missing=20)["p_upper_bound"], 1)

    def test_bias_is_included_in_null(self):
        self.assertFalse(M.match_statistics(200000, 101000, rng_bias_bound=.01)["reject_bounded_randomness_null"])

    def test_common_cause_oracle_can_pass_coherence_but_not_confirm_physics(self):
        d = fixture(2048)
        for row in d["trials"]:
            row["early_bit"] = row["later_bit"]
        r = M.analyze_dataset(d)
        self.assertTrue(r["statistics"]["reject_bounded_randomness_null"])
        self.assertFalse(r["physical_confirmation"])
        self.assertFalse(r["independent_reproduction"])
        self.assertTrue(r["external_checks_not_certified_by_json"])

    def test_full_null_fixture_has_no_detection(self):
        r = M.analyze_dataset(fixture())
        self.assertFalse(r["statistics"]["reject_bounded_randomness_null"])

    def test_time_uncertainty_overlap_rejected(self):
        d = fixture()
        d["trials"][0]["early_end"]["hi_ns"] = 100
        with self.assertRaisesRegex(ValueError, "ROBUST_TEMPORAL_ORDER"):
            M.analyze_dataset(d)

    def test_early_entropy_with_later_output_rejected(self):
        d = fixture()
        d["trials"][0]["entropy_start"]["lo_ns"] = 0
        with self.assertRaisesRegex(ValueError, "ROBUST_TEMPORAL_ORDER"):
            M.analyze_dataset(d)

    def test_reordering_missing_or_duplicate_slots_rejected(self):
        for mode in ("reorder", "remove", "duplicate"):
            d = fixture()
            if mode == "reorder":
                d["trials"].reverse()
            elif mode == "remove":
                d["trials"].pop()
            else:
                d["trials"][1]["trial_id"] = 0
            with self.assertRaisesRegex(ValueError, "FULL_FIXED_TRIAL_ORDER"):
                M.analyze_dataset(d)

    def test_shared_host_clock_is_not_physical_clock_binding(self):
        d = fixture()
        d["config"]["origin_class"] = "PHYSICAL_CANDIDATE"
        d["config"]["time_coordinate"] = "SHARED_HOST_MONOTONIC_NS"
        with self.assertRaisesRegex(ValueError, "PHYSICAL_CLOCK_BINDING_MISSING"):
            M.analyze_dataset(d)

    def test_self_declared_physical_candidate_never_self_certifies(self):
        d = fixture()
        d["config"]["origin_class"] = "PHYSICAL_CANDIDATE"
        d["config"]["time_coordinate"] = "CALIBRATED_TAI_NS"
        self.assertFalse(M.analyze_dataset(d)["physical_confirmation"])

    def test_invalid_bit_and_nan_or_boolean_time_rejected(self):
        for bad in (True, 2, float("nan")):
            d = fixture()
            d["trials"][0]["early_bit"] = bad
            with self.assertRaisesRegex(ValueError, "BINARY_OR_MISSING"):
                M.analyze_dataset(d)
        d = fixture()
        d["trials"][0]["early_end"]["lo_ns"] = True
        with self.assertRaisesRegex(ValueError, "INVALID_TIME_INTERVAL"):
            M.analyze_dataset(d)

    def test_missing_bits_remain_in_denominator(self):
        d = fixture()
        for row in d["trials"]:
            if row["early_bit"] != row["later_bit"]:
                row["later_bit"] = None
        r = M.analyze_dataset(d)["statistics"]
        self.assertEqual(r["n_attempted"], 100)
        self.assertEqual(r["missing"], 50)
        self.assertFalse(r["reject_bounded_randomness_null"])


if __name__ == "__main__":
    unittest.main()
