import Mathlib.Probability.Distributions.Poisson

/-!
# Poisson counting law: normalization and first two moments

This file is part of the isolated Mathlib extension.  The proofs use
Mathlib's Poisson mass function and reduce the first two moments to
shifted exponential-series identities.  No project axioms or placeholders
are introduced.
-/

open scoped NNReal
open ProbabilityTheory

namespace QIKVRT.SpacetimeBridge.MathlibV1

/-- The real-valued Poisson mass function is normalized. -/
theorem poisson_mass_normalized (r : ℝ≥0) :
    HasSum (fun n : ℕ => poissonPMFReal r n) 1 :=
  poissonPMFRealSum r

/-- The first raw moment of the real-valued Poisson mass function. -/
theorem poisson_first_moment_hasSum (r : ℝ≥0) :
    HasSum (fun n : ℕ => poissonPMFReal r n * (n : ℝ)) r.toReal := by
  suffices HasSum
      (fun n : ℕ => poissonPMFReal r 0 * (0 : ℝ) +
        poissonPMFReal r (n + 1) * ((n + 1 : ℕ) : ℝ))
      (poissonPMFReal r 0 * (0 : ℝ) + r.toReal * 1) by
    simpa using this
  have hshift :
      (fun n : ℕ => poissonPMFReal r (n + 1) * ((n + 1 : ℕ) : ℝ)) =
        fun n : ℕ => r.toReal * poissonPMFReal r n := by
    funext n
    simp_rw [poissonPMFReal, div_mul, Nat.factorial_succ, pow_succ]
    field_simp [← mul_rotate']
  exact (hshift ▸ (poisson_mass_normalized r).mul_left r.toReal).zero_add

/-- The expectation, expressed as the real-valued weighted series. -/
theorem poisson_expectation_eq_rate (r : ℝ≥0) :
    ∑' n : ℕ, poissonPMFReal r n * (n : ℝ) = r.toReal :=
  (poisson_first_moment_hasSum r).tsum_eq

/-- The second raw moment of the real-valued Poisson mass function. -/
theorem poisson_second_moment_hasSum (r : ℝ≥0) :
    HasSum (fun n : ℕ => poissonPMFReal r n * (n : ℝ) ^ 2)
      (r.toReal ^ 2 + r.toReal) := by
  have hplus :
      HasSum (fun n : ℕ =>
        poissonPMFReal r n * ((n : ℝ) + 1)) (r.toReal + 1) := by
    have h := (poisson_first_moment_hasSum r).add (poisson_mass_normalized r)
    convert h using 1 <;> ext n <;> push_cast <;> ring
  have hshift :
      (fun n : ℕ =>
        poissonPMFReal r (n + 1) * ((n + 1 : ℕ) : ℝ) ^ 2) =
        fun n : ℕ =>
          r.toReal * (poissonPMFReal r n * ((n : ℝ) + 1)) := by
    funext n
    simp_rw [poissonPMFReal, div_mul, Nat.factorial_succ, pow_succ]
    field_simp [← mul_rotate']
    <;> ring
  have htail :
      HasSum (fun n : ℕ =>
        poissonPMFReal r (n + 1) * ((n + 1 : ℕ) : ℝ) ^ 2)
        (r.toReal * (r.toReal + 1)) := by
    rw [hshift]
    exact hplus.mul_left r.toReal
  have hfull := htail.zero_add
  simpa using hfull

/-- The second raw moment is λ² + λ. -/
theorem poisson_second_moment_eq (r : ℝ≥0) :
    ∑' n : ℕ, poissonPMFReal r n * (n : ℝ) ^ 2 =
      r.toReal ^ 2 + r.toReal :=
  (poisson_second_moment_hasSum r).tsum_eq

/-- Variance computed from the first two raw moments of the Poisson law. -/
def poissonVarianceFromRawMoments (r : ℝ≥0) : ℝ :=
  (∑' n : ℕ, poissonPMFReal r n * (n : ℝ) ^ 2) -
    (∑' n : ℕ, poissonPMFReal r n * (n : ℝ)) ^ 2

/-- The Poisson variance is equal to its rate. -/
theorem poisson_variance_eq_rate (r : ℝ≥0) :
    poissonVarianceFromRawMoments r = r.toReal := by
  rw [poissonVarianceFromRawMoments, poisson_second_moment_eq,
    poisson_expectation_eq_rate]
  ring

end QIKVRT.SpacetimeBridge.MathlibV1
