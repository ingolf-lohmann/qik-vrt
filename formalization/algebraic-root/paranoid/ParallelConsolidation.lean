import EffectMachine

namespace QikVrtAlgebraicRoot

/-- Execution domains are labels; the equivalence proof depends on no shared memory. -/
inductive ExecutionDomain where
  | thread
  | process
  | interrupt
  | network
  deriving DecidableEq, Repr

/-- An admissible schedule is a bijection of the finite task indices.
    This models complete, nonduplicating delivery, NOT a proof of delivery. -/
structure CompleteSchedule (n : Nat) where
  forward : Fin n → Fin n
  backward : Fin n → Fin n
  left_inverse : ∀ i, backward (forward i) = i
  right_inverse : ∀ i, forward (backward i) = i

/-- Independent task computation with results indexed by their original task ID. -/
def sequential {n : Nat} {Input Output : Type}
    (task : Fin n → Input) (compute : Input → Output) : Fin n → Output :=
  fun i => compute (task i)

/-- Results arrive in an arbitrary admissible execution order. -/
def distributed {n : Nat} {Input Output : Type}
    (schedule : CompleteSchedule n)
    (task : Fin n → Input) (compute : Input → Output) : Fin n → Output :=
  fun arrival => compute (task (schedule.forward arrival))

/-- Canonical consolidation restores original task IDs, independent of arrival order. -/
def consolidate {n : Nat} {Output : Type}
    (schedule : CompleteSchedule n) (arrivals : Fin n → Output) : Fin n → Output :=
  fun original => arrivals (schedule.backward original)

theorem consolidation_equals_sequential {n : Nat} {Input Output : Type}
    (schedule : CompleteSchedule n)
    (task : Fin n → Input) (compute : Input → Output) :
    consolidate schedule (distributed schedule task compute) =
      sequential task compute := by
  funext i
  simp only [consolidate, distributed, sequential, schedule.right_inverse]

/-- A lossless bidirectional computation needs both inverse laws. -/
structure Reversible (A B : Type) where
  forward : A → B
  backward : B → A
  left_inverse : ∀ a, backward (forward a) = a
  right_inverse : ∀ b, forward (backward b) = b

theorem reversible_forward_backward {A B : Type}
    (r : Reversible A B) (a : A) :
    r.backward (r.forward a) = a :=
  r.left_inverse a

theorem reversible_backward_forward {A B : Type}
    (r : Reversible A B) (b : B) :
    r.forward (r.backward b) = b :=
  r.right_inverse b

/-- Domain-independent equivalence: transport must meet CompleteSchedule's
    bijection contract and computations must be independent and deterministic. -/
theorem domain_independent_consolidation {n : Nat} {Input Output : Type}
    (domain : ExecutionDomain) (schedule : CompleteSchedule n)
    (task : Fin n → Input) (compute : Input → Output) :
    consolidate schedule (distributed schedule task compute) =
      sequential task compute := by
  cases domain <;> exact consolidation_equals_sequential schedule task compute

#print axioms QikVrtAlgebraicRoot.consolidation_equals_sequential
#print axioms QikVrtAlgebraicRoot.reversible_forward_backward
#print axioms QikVrtAlgebraicRoot.reversible_backward_forward
#print axioms QikVrtAlgebraicRoot.domain_independent_consolidation

end QikVrtAlgebraicRoot
