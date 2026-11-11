import random
import unittest

from causal_sprinkling_demo import (
    check_strict_partial_order, poisson_inverse, run, sprinkle
)


class SprinklingTests(unittest.TestCase):
    def test_reproducible_poisson_sampler(self):
        self.assertEqual(poisson_inverse(4.0, random.Random(1234)),
                         poisson_inverse(4.0, random.Random(1234)))

    def test_diamond_and_partial_order(self):
        points = sprinkle(8.0, random.Random(42))
        self.assertTrue(all(0 <= u <= 2**0.5 and 0 <= v <= 2**0.5 for u, v in points))
        check_strict_partial_order(points)

    def test_poisson_moments_numerically(self):
        result = run(rate=3.0, trials=20000, epsilon=0.5, seed=20261111)
        self.assertLess(abs(result["sample_mean_count"] - 3.0), 0.06)
        self.assertLess(abs(result["sample_population_variance"] - 3.0), 0.12)

    def test_rate_limit(self):
        with self.assertRaises(ValueError):
            poisson_inverse(101.0, random.Random(0))


if __name__ == "__main__":
    unittest.main()
