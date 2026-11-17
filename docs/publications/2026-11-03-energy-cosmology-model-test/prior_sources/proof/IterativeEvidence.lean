import Std

/- Finite conditional verification model.
   No empirical claim, physical-space emergence, or production admission follows.
   The natural-number budget is an explicitly discretized energy accounting model.
   Requirements and authorization: Ingolf Lohmann.
   Formalization: OpenAI Codex, 2026-11-02. -/
namespace IterativeEvidence

inductive Outcome where
  | verified | failed | unverified
  deriving DecidableEq, Repr

structure Observation where
  checkerRan : Bool
  sourceBound : Bool
  readbackAvailable : Bool
  fresh : Bool
  agrees : Bool
  deriving DecidableEq, Repr

def evaluate (o : Observation) : Outcome :=
  if o.checkerRan && o.sourceBound && o.readbackAvailable && o.fresh
  then if o.agrees then .verified else .failed
  else .unverified

structure State where
  history : List Observation
  status : Outcome

def step (s : State) (o : Observation) : State :=
  { history := s.history ++ [o], status := evaluate o }

def supported (s : State) : Nat :=
  if s.status = .verified then 1 else 0

def positive : Observation := ⟨true, true, true, true, true⟩
def negative : Observation := ⟨true, true, true, true, false⟩
def stale : Observation := { positive with fresh := false }
def checkerMissing : Observation := { positive with checkerRan := false }
def initial : State := ⟨[positive], .verified⟩

theorem old_observations_preserved (s : State) (o old : Observation)
    (h : old ∈ s.history) : old ∈ (step s o).history := by
  exact List.mem_append.mpr (Or.inl h)

theorem journal_strictly_grows (s : State) (o : Observation) :
    s.history.length < (step s o).history.length := by
  simp [step]

theorem checker_unavailable_is_unknown (o : Observation)
    (h : o.checkerRan = false) : evaluate o = .unverified := by
  simp [evaluate, h]

theorem wrong_source_is_unknown (o : Observation)
    (h : o.sourceBound = false) : evaluate o = .unverified := by
  simp [evaluate, h]

theorem unavailable_readback_is_unknown (o : Observation)
    (h : o.readbackAvailable = false) : evaluate o = .unverified := by
  simp [evaluate, h]

theorem stale_evidence_is_unknown (o : Observation)
    (h : o.fresh = false) : evaluate o = .unverified := by
  simp [evaluate, h]

theorem checked_positive_is_verified :
    evaluate positive = .verified := by decide

theorem checked_negative_is_failed :
    evaluate negative = .failed := by decide

theorem evidence_outcomes_are_distinct :
    Outcome.unverified ≠ .verified ∧ Outcome.unverified ≠ .failed ∧
    Outcome.failed ≠ .verified := by decide

theorem revision_can_append_and_retract :
    (step initial negative).history.length = initial.history.length + 1 ∧
    supported (step initial negative) < supported initial := by decide

theorem supported_claims_are_not_universally_monotone :
    ¬ (∀ s o, supported s ≤ supported (step s o)) := by
  intro h
  have bad := h initial negative
  have no : ¬ (supported initial ≤ supported (step initial negative)) := by decide
  exact no bad

theorem conditional_budget (cost bits work available : Nat)
    (landauer : bits * cost ≤ work) (supply : work ≤ available) :
    bits * cost ≤ available :=
  Nat.le_trans landauer supply

theorem conditional_bit_bound (cost bits work available : Nat)
    (positiveCost : 0 < cost)
    (landauer : bits * cost ≤ work) (supply : work ≤ available) :
    bits ≤ available / cost := by
  exact (Nat.le_div_iff_mul_le positiveCost).mpr
    (conditional_budget cost bits work available landauer supply)

theorem rest_energy_counterexample :
    ¬ ((1 : Nat) * 1 * 1 = 0 * 1) := by decide

#print axioms old_observations_preserved
#print axioms journal_strictly_grows
#print axioms checker_unavailable_is_unknown
#print axioms wrong_source_is_unknown
#print axioms unavailable_readback_is_unknown
#print axioms stale_evidence_is_unknown
#print axioms checked_positive_is_verified
#print axioms checked_negative_is_failed
#print axioms evidence_outcomes_are_distinct
#print axioms revision_can_append_and_retract
#print axioms supported_claims_are_not_universally_monotone
#print axioms conditional_budget
#print axioms conditional_bit_bound
#print axioms rest_energy_counterexample

end IterativeEvidence

