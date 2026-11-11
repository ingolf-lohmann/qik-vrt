#!/usr/bin/env python3
"""Poisson sprinkling reference experiment in a unit-volume 1+1D Minkowski diamond.

Null coordinates u=t-x and v=t+x lie in [0,sqrt(2)]^2. The Lorentzian
volume is half the square's area, hence one. This is a numerical model,
not a continuum-limit proof. The inverse-CDF sampler is restricted to
rates at most 100 for floating-point stability.
"""
import argparse
import json
import math
import random
from statistics import fmean, pvariance

SIDE = math.sqrt(2.0)


def poisson_inverse(rate, rng):
    if not 0.0 < rate <= 100.0:
        raise ValueError("rate must satisfy 0 < rate <= 100")
    target = rng.random()
    probability = math.exp(-rate)
    cumulative = probability
    count = 0
    while target > cumulative:
        count += 1
        probability *= rate / count
        cumulative += probability
    return count


def sprinkle(rate, rng):
    return [(rng.random() * SIDE, rng.random() * SIDE)
            for _ in range(poisson_inverse(rate, rng))]


def precedes(a, b):
    return a != b and a[0] <= b[0] and a[1] <= b[1]


def check_strict_partial_order(points):
    for a in points:
        assert not precedes(a, a)
        for b in points:
            if precedes(a, b):
                assert not precedes(b, a)
                for c in points:
                    if precedes(b, c):
                        assert precedes(a, c)


def run(rate=20.0, trials=2000, epsilon=0.25, seed=20261111):
    if trials < 2 or epsilon <= 0:
        raise ValueError("trials must be >= 2 and epsilon must be positive")
    rng = random.Random(seed)
    counts, relation_counts = [], []
    order_checked = False
    for _ in range(trials):
        points = sprinkle(rate, rng)
        counts.append(len(points))
        relation_counts.append(sum(
            precedes(points[i], points[j])
            for i in range(len(points)) for j in range(len(points)) if i != j
        ))
        if not order_checked:
            check_strict_partial_order(points)
            order_checked = True
    mean, variance = fmean(counts), pvariance(counts)
    tail = sum(abs(n-rate) / rate >= epsilon for n in counts) / trials
    return {
        "model": "1+1D Minkowski Alexandrov diamond",
        "spacetime_volume": 1.0,
        "density_and_expected_count": rate,
        "trials": trials,
        "seed": seed,
        "sample_mean_count": mean,
        "sample_population_variance": variance,
        "theoretical_poisson_variance": rate,
        "mean_relative_error": abs(mean-rate) / rate,
        "empirical_relative_tail_probability": tail,
        "chebyshev_tail_upper_bound": min(1.0, 1.0/(epsilon*epsilon*rate)),
        "mean_causal_relations_per_sprinkle": fmean(relation_counts),
        "strict_partial_order_check": "passed on first sprinkle",
        "limitation": "simulation only; no manifold-likeness or continuum-limit claim"
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--density", type=float, default=20.0)
    parser.add_argument("--trials", type=int, default=2000)
    parser.add_argument("--epsilon", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=20261111)
    args = parser.parse_args()
    print(json.dumps(run(args.density, args.trials, args.epsilon, args.seed), indent=2))


if __name__ == "__main__":
    main()
