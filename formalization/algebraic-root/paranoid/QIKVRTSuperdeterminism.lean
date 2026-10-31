import ParallelConsolidation

namespace QikVrtAlgebraicRoot

/-- QIK-VRT's *logical* superdeterminism, not the homonymous physical theory.
    Reversibility is specified by an explicit two-sided inverse. -/
structure QIKVRTSuperdeterminism (State : Type) where
  forward : State → State
  backward : State → State
  backward_forward : ∀ s, backward (forward s) = s
  forward_backward : ∀ s, forward (backward s) = s

/-- A reproducible transition is the same pure function on the same full state. -/
theorem qikvrt_reproducible {State : Type}
    (spec : QIKVRTSuperdeterminism State) (s : State) :
    spec.forward s = spec.forward s := rfl

/-- Logical zero information loss: distinct full states cannot collapse. -/
theorem qikvrt_no_logical_information_loss {State : Type}
    (spec : QIKVRTSuperdeterminism State) :
    Function.Injective spec.forward := by
  intro a b h
  have h' := congrArg spec.backward h
  simpa [spec.backward_forward] using h'

theorem qikvrt_exact_recovery {State : Type}
    (spec : QIKVRTSuperdeterminism State) (s : State) :
    spec.backward (spec.forward s) = s :=
  spec.backward_forward s

theorem qikvrt_exact_forward_recovery {State : Type}
    (spec : QIKVRTSuperdeterminism State) (s : State) :
    spec.forward (spec.backward s) = s :=
  spec.forward_backward s

/-- Independent reversible per-task computation and bijective delivery yield
    the identical indexed full result vector as sequential execution. -/
theorem qikvrt_parallel_equals_sequential {n : Nat} {State : Type}
    (spec : QIKVRTSuperdeterminism State)
    (schedule : CompleteSchedule n) (initial : Fin n → State) :
    consolidate schedule (distributed schedule initial spec.forward) =
      sequential initial spec.forward :=
  consolidation_equals_sequential schedule initial spec.forward

/-- Exact recovery after distribution, canonical consolidation and inverse. -/
theorem qikvrt_parallel_recover_initial {n : Nat} {State : Type}
    (spec : QIKVRTSuperdeterminism State)
    (schedule : CompleteSchedule n) (initial : Fin n → State) :
    (fun i => spec.backward
      (consolidate schedule (distributed schedule initial spec.forward) i)) =
      initial := by
  funext i
  rw [qikvrt_parallel_equals_sequential]
  exact spec.backward_forward (initial i)

/-- The domain is not relevant to the abstract equivalence, conditional on
    complete delivery and independent deterministic operations. -/
theorem qikvrt_domain_independent {n : Nat} {State : Type}
    (domain : ExecutionDomain)
    (spec : QIKVRTSuperdeterminism State)
    (schedule : CompleteSchedule n) (initial : Fin n → State) :
    consolidate schedule (distributed schedule initial spec.forward) =
      sequential initial spec.forward :=
  domain_independent_consolidation domain schedule initial spec.forward

#print axioms QikVrtAlgebraicRoot.qikvrt_reproducible
#print axioms QikVrtAlgebraicRoot.qikvrt_no_logical_information_loss
#print axioms QikVrtAlgebraicRoot.qikvrt_exact_recovery
#print axioms QikVrtAlgebraicRoot.qikvrt_exact_forward_recovery
#print axioms QikVrtAlgebraicRoot.qikvrt_parallel_equals_sequential
#print axioms QikVrtAlgebraicRoot.qikvrt_parallel_recover_initial
#print axioms QikVrtAlgebraicRoot.qikvrt_domain_independent

end QikVrtAlgebraicRoot
