import Std

/-!
# GAT-003: finite-prefix shift invariance

A trajectory is an infinite sequence. The exact PASS/BLOCK classifier returns
PASS precisely when the observed magnitude remains bounded. Removing any finite
prefix preserves boundedness and therefore preserves the exact classification.
-/

namespace QIKVRT.V2.Trajectory

abbrev Trajectory (α : Type) := Nat → α

def shift (trajectory : Trajectory α) : Trajectory α :=
  fun n => trajectory (n + 1)

def shiftBy : Nat → Trajectory α → Trajectory α
  | 0, trajectory => trajectory
  | k + 1, trajectory => shift (shiftBy k trajectory)

def BoundedBy (magnitude : α → Nat) (bound : Nat)
    (trajectory : Trajectory α) : Prop :=
  ∀ n, magnitude (trajectory n) ≤ bound

def Bounded (magnitude : α → Nat) (trajectory : Trajectory α) : Prop :=
  ∃ bound, BoundedBy magnitude bound trajectory

inductive ExactStatus where
  | pass
  | block
  deriving DecidableEq, Repr, BEq

noncomputable def exactStatus (magnitude : α → Nat)
    (trajectory : Trajectory α) : ExactStatus := by
  classical
  exact if Bounded magnitude trajectory then .pass else .block

theorem bounded_shift_forward (magnitude : α → Nat)
    (trajectory : Trajectory α) :
    Bounded magnitude trajectory → Bounded magnitude (shift trajectory) := by
  rintro ⟨bound, hBound⟩
  refine ⟨bound, ?_⟩
  intro n
  exact hBound (n + 1)

theorem bounded_shift_backward (magnitude : α → Nat)
    (trajectory : Trajectory α) :
    Bounded magnitude (shift trajectory) → Bounded magnitude trajectory := by
  rintro ⟨tailBound, hTail⟩
  refine ⟨Nat.max (magnitude (trajectory 0)) tailBound, ?_⟩
  intro n
  cases n with
  | zero => exact Nat.le_max_left _ _
  | succ n =>
      have h := hTail n
      exact Nat.le_trans h (Nat.le_max_right _ _)

theorem bounded_shift_iff (magnitude : α → Nat)
    (trajectory : Trajectory α) :
    Bounded magnitude (shift trajectory) ↔ Bounded magnitude trajectory := by
  constructor
  · exact bounded_shift_backward magnitude trajectory
  · exact bounded_shift_forward magnitude trajectory

theorem bounded_shiftBy_iff (magnitude : α → Nat)
    (trajectory : Trajectory α) :
    ∀ k, Bounded magnitude (shiftBy k trajectory) ↔ Bounded magnitude trajectory := by
  intro k
  induction k with
  | zero => rfl
  | succ k ih =>
      exact Iff.trans (bounded_shift_iff magnitude (shiftBy k trajectory)) ih

theorem exactStatus_shiftBy (magnitude : α → Nat)
    (trajectory : Trajectory α) (k : Nat) :
    exactStatus magnitude (shiftBy k trajectory) = exactStatus magnitude trajectory := by
  classical
  unfold exactStatus
  rw [bounded_shiftBy_iff magnitude trajectory k]

def GAT003Statement : Prop :=
  ∀ (α : Type) (magnitude : α → Nat) (trajectory : Trajectory α) (k : Nat),
    exactStatus magnitude (shiftBy k trajectory) = exactStatus magnitude trajectory

theorem GAT003_checked : GAT003Statement := by
  intro α magnitude trajectory k
  exact exactStatus_shiftBy magnitude trajectory k

#print axioms bounded_shiftBy_iff
#print axioms exactStatus_shiftBy
#print axioms GAT003_checked

end QIKVRT.V2.Trajectory
