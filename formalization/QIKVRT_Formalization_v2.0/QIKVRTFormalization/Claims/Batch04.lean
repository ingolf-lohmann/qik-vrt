import QIKVRTFormalization.Process.ShiftInvariance

/-!
# Batch 04 checked claim registry

This registry binds manuscript claim `GAT-003` to its exact Lean proposition and
kernel proof. Downstream verification may reuse compiled proof objects when all
content-addressed inputs are unchanged, while cache misses still rebuild from
source and re-run the kernel checks.
-/

namespace QIKVRT.V2.Claims

inductive Batch04ClaimId where
  | gat003
  deriving DecidableEq, Repr, BEq

structure CheckedClaim04 (id : Batch04ClaimId) (statement : Prop) : Type where
  checked : statement

def batch04ClaimIds : List Batch04ClaimId := [.gat003]

theorem batch04ClaimIds_count : batch04ClaimIds.length = 1 := by decide

theorem batch04ClaimIds_pairwise : batch04ClaimIds.Pairwise (· ≠ ·) := by decide

def GAT003 : CheckedClaim04 .gat003 Trajectory.GAT003Statement :=
  ⟨Trajectory.GAT003_checked⟩

#print axioms GAT003

end QIKVRT.V2.Claims
