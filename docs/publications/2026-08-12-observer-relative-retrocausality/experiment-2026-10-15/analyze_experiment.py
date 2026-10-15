#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline statistical and interval checks; never certifies physical causality.

Extends the existing finite witness and A/B/C controls without changing their
frozen originals. Only the Python standard library is required. Simulations,
host measurements and physical candidate inputs always retain their class.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_witness():
    path = HERE.parent / "verify_observer_relative_retrocausality.py"
    spec = importlib.util.spec_from_file_location("original_orr_witness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return json.loads(json.dumps(module.canonical_report()))


def check_original_witness():
    report = canonical_witness()
    stored = json.loads((HERE.parent / "QIKVRT_RETROCAUSALITY_WITNESS.json").read_text())
    require(report == stored, "ORIGINAL_WITNESS_REGENERATION_DIFFERS")
    p = report["future_directed_physical_latency_witness"]
    gap = Fraction(p["new_emission_time"]) - Fraction(p["old_emission_time"])
    old_delay = Fraction(p["old_path_length"], p["c"])
    new_delay = Fraction(p["new_path_length"], p["c"])
    marker_delta = (report["records"]["old"]["source_mark"] -
                    report["records"]["new"]["source_mark"])
    local_delta = report["observer_o"]["delta_local_change_time"]
    require(gap > 0 and old_delay > 0 and new_delay > 0, "FORWARD_PREMISES_FAILED")
    require(gap < old_delay - new_delay, "OVERTAKING_THRESHOLD_FAILED")
    # Exhaustive bounded counterpart of the unbounded integer Lean theorem.
    cases = 0
    for old in range(-2, 3):
        for new in range(old + 1, old + 6):
            for do in range(1, 9):
                for dn in range(1, 9):
                    require((new + dn < old + do) == (new - old < do - dn),
                            "LATENCY_EQUIVALENCE_FAILED")
                    cases += 1
    # Exact rational mixture arithmetic, separately from five float samples.
    for numerator in range(-100, 101):
        x = Fraction(numerator, 100)
        require(((1 + x) / 2 + (1 - x) / 2) / 2 == Fraction(1, 2),
                "COMPLEMENTARY_MARGINAL_FAILED")
    return {
        "class": "EXECUTABLE_FINITE_MODEL_NOT_PHYSICAL_MEASUREMENT",
        "original_report_equal": True,
        "source_gap": str(gap), "old_delay": str(old_delay),
        "new_delay": str(new_delay), "gradient": str(Fraction(marker_delta, local_delta)),
        "gradient_units": "source_marker_units / local_change_index",
        "delay_grid_cases": cases, "rational_mixture_cases": 201,
        "physical_backward_effect": "NOT_ESTABLISHED",
    }


def upper_binomial_tail(n, k, p=0.5):
    """Stable numerical tail. The test decision below uses a separate bound."""
    require(type(n) is int and n >= 1 and type(k) is int, "INVALID_BINOMIAL_SIZE")
    require(math.isfinite(p) and 0 < p < 1, "INVALID_BINOMIAL_PROBABILITY")
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    if k <= n * p:
        return max(0.0, 1 - upper_binomial_tail(n, n - k + 1, 1 - p))
    mass = math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
                    + k * math.log(p) + (n - k) * math.log1p(-p))
    terms = [mass]
    for j in range(k, n):
        mass *= (n - j) * p / ((j + 1) * (1 - p))
        terms.append(mass)
        if mass == 0:
            break
    return min(1.0, max(0.0, math.fsum(terms)))


def match_statistics(n, matches, missing=0, alpha=0.001, rng_bias_bound=0.001):
    """Worst-case missing outcomes; two-sided bounded-increment null test.

    H0: conditional match probabilities remain within 1/2 +/- epsilon,
    including conditioning on the locked early data and all prior history.
    Independence of the early records is unnecessary under that assumption.
    Physical validity of the conditional-randomness premise is EXTERNAL.
    """
    require(type(n) is int and n > 0, "INVALID_N")
    require(type(matches) is int and type(missing) is int and
            0 <= missing <= n and 0 <= matches <= n - missing, "INVALID_COUNTS")
    require(math.isfinite(alpha) and 0 < alpha < 1 and
            math.isfinite(rng_bias_bound) and 0 <= rng_bias_bound < 0.5,
            "INVALID_TEST_PARAMETERS")
    low, high = matches, matches + missing
    min_abs = 0.0 if low <= n / 2 <= high else min(abs(low / n - .5), abs(high / n - .5))
    effective = max(0.0, min_abs - rng_bias_bound)
    log_bound = min(0.0, math.log(2) - 2 * n * effective * effective)
    radius99 = math.sqrt(math.log(200) / (2 * n))
    upper99 = min(.5, max(abs(low / n - .5), abs(high / n - .5)) + radius99)
    result = {
        "n_attempted": n, "known_matches": matches, "missing": missing,
        "feasible_matches": [low, high], "rng_conditional_bias_bound": rng_bias_bound,
        "alpha_two_sided": alpha, "log_p_upper_bound": log_bound,
        "p_upper_bound": math.exp(log_bound),
        "reject_bounded_randomness_null": log_bound <= math.log(alpha),
        "abs_match_advantage_upper_99": upper99,
        "interval_scope": "mean conditional match propensity; physical stationarity and transfer are separate",
        "physical_confirmation": False,
    }
    if missing == 0:
        result["two_sided_binomial_p_under_ideal_fair_null"] = min(
            1.0, 2 * upper_binomial_tail(n, max(matches, n - matches)))
    return result


def planned_sensitivity(n=200000, alpha=.001, bias=.001, effect=.01):
    threshold = .5 + bias + math.sqrt(math.log(2 / alpha) / (2 * n))
    critical = math.ceil(n * threshold)
    # Bound for the explicitly specified alternative of independent matches.
    margin = max(0.0, .5 + effect - critical / n)
    miss_bound = math.exp(-2 * n * margin * margin) if margin else 1.0
    return {"class": "PROSPECTIVE_POWER_NOT_MEASURED_EFFECT", "n": n,
            "alpha": alpha, "rng_bias_bound": bias, "target_match_advantage": effect,
            "positive_critical_matches": critical, "negative_critical_matches": n - critical,
            "power_lower_bound_under_independent_alternative": 1 - miss_bound,
            "power_numeric_under_independent_alternative": upper_binomial_tail(n, critical, .5 + effect),
            "effect_size_predicted_by_qikvrt": False}


def interval(record, field):
    value = record[field]
    require(isinstance(value, dict) and type(value.get("lo_ns")) is int and
            type(value.get("hi_ns")) is int and value["lo_ns"] <= value["hi_ns"] and
            isinstance(value.get("clock_id"), str) and bool(value["clock_id"]),
            "INVALID_TIME_INTERVAL:" + field)
    return value


def analyze_dataset(data):
    """Data coherence only. An all-consistent fabrication can pass these checks."""
    require(data.get("schema") == "qikvrt_retrocausality_trial_table_v1", "SCHEMA_MISMATCH")
    config = data["config"]
    n = config["n"]
    require(type(n) is int and n > 0, "INVALID_N")
    require(config["origin_class"] in ("SIMULATED", "LOCAL_SHARED_HOST", "PHYSICAL_CANDIDATE"),
            "UNKNOWN_ORIGIN_CLASS")
    require(config["time_coordinate"] in ("CALIBRATED_TAI_NS", "SHARED_HOST_MONOTONIC_NS", "SIMULATED_NS"),
            "UNKNOWN_TIME_COORDINATE")
    require(config["origin_class"] != "PHYSICAL_CANDIDATE" or
            config["time_coordinate"] == "CALIBRATED_TAI_NS", "PHYSICAL_CLOCK_BINDING_MISSING")
    trials = data["trials"]
    require(len(trials) == n and all(type(t.get("trial_id")) is int for t in trials) and
            [t["trial_id"] for t in trials] == list(range(n)), "FULL_FIXED_TRIAL_ORDER_REQUIRED")
    matches = missing = 0
    min_margin = None
    clock_ids = set()
    for row in trials:
        for field in ("early_bit", "later_bit"):
            require(row[field] is None or type(row[field]) is int and row[field] in (0, 1),
                    "BINARY_OR_MISSING_REQUIRED")
        events = [interval(row, key) for key in
                  ("early_end", "locked", "custody_ack", "entropy_start", "choice_complete")]
        clock_ids.update(e["clock_id"] for e in events)
        require(all(a["hi_ns"] < b["lo_ns"] for a, b in zip(events, events[1:])),
                "ROBUST_TEMPORAL_ORDER_NOT_ESTABLISHED")
        margin = events[3]["lo_ns"] - events[0]["hi_ns"]
        min_margin = margin if min_margin is None else min(min_margin, margin)
        if row["early_bit"] is None or row["later_bit"] is None:
            missing += 1
        else:
            matches += row["early_bit"] == row["later_bit"]
    statistics = match_statistics(n, matches, missing, config["alpha"], config["rng_bias_bound"])
    return {"status": "DATA_COHERENCE_CHECKED_EXTERNAL_OBLIGATIONS_OPEN",
            "origin_class": config["origin_class"], "statistics": statistics,
            "min_early_to_entropy_margin_ns": min_margin, "clock_ids": sorted(clock_ids),
            "physical_confirmation": False, "independent_reproduction": False,
            "external_checks_not_certified_by_json": [
                "physical channel and distinctive prediction", "authentic capture and custody",
                "calibrated independent clocks and uncertainty budget", "fresh conditional randomness",
                "isolation and absence of ordinary leakage", "preregistration and complete run inventory",
                "independent physical reproduction"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.dataset:
        raw = args.dataset.read_bytes()
        report = analyze_dataset(json.loads(raw))
        report["input_sha256"] = hashlib.sha256(raw).hexdigest()
    else:
        report = {"witness": check_original_witness(), "sensitivity": planned_sensitivity(),
                  "physical_measurement": "NOT_PERFORMED"}
    text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
