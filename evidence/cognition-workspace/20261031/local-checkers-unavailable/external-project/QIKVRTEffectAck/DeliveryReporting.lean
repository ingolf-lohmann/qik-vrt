/-
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann.
-/
import Std

/-! A finite, decidable model of *declared* delivery evidence.
Host classification, authenticity, independence, original-byte retention and
clock interpretation are adapter preconditions, not properties of the network.
R3-R5 (durable correction, continuation and actual peer adoption) are outside
this model. No theorem asserts that a report describes a real observation. -/
namespace QIKVRT.DeliveryReporting

inductive Target where
  | local
  | authority (host : String)
  deriving DecidableEq, Repr

inductive Claim where
  | pending
  | delivered
  deriving DecidableEq, Repr

inductive Verdict where
  | accept
  | reject
  deriving DecidableEq, Repr

structure Observation where
  target : Target
  status : Nat
  subjectRef : String
  observationId : String
  utc : Nat
  deriving Repr

structure Report where
  claim : Claim
  authorityHost : String
  subjectRef : String
  observations : List Observation
  completedUtc : Nat
  closedUtc : Nat
  provenanceBound : Bool
  deriving Repr

def Qualified (r : Report) (o : Observation) : Prop :=
  o.target = .authority r.authorityHost ∧ o.status = 200 ∧
  o.subjectRef = r.subjectRef ∧ r.completedUtc < o.utc ∧ o.utc ≤ r.closedUtc

instance (r : Report) (o : Observation) : Decidable (Qualified r o) :=
  inferInstanceAs (Decidable (_ ∧ _ ∧ _ ∧ _ ∧ _))

def remoteEvidence (r : Report) : Bool :=
  r.observations.any (fun o => Decidable.decide (Qualified r o))

def Admissible (r : Report) : Prop :=
  (r.observations.map Observation.observationId).Nodup ∧
  r.provenanceBound = true ∧
  (r.claim = .pending ∨ remoteEvidence r = true)

instance (r : Report) : Decidable (Admissible r) :=
  inferInstanceAs (Decidable (_ ∧ _ ∧ _))

def decide (r : Report) : Verdict :=
  if Admissible r then .accept else .reject

theorem T1 (r : Report) : decide r = .accept ↔ Admissible r := by
  unfold decide
  split <;> simp_all

theorem T3 (r : Report) (accepted : decide r = .accept)
    (delivered : r.claim = .delivered) :
    ∃ o ∈ r.observations, Qualified r o := by
  have h := (T1 r).mp accepted
  have remote : remoteEvidence r = true := by
    rcases h.2.2 with pending | remote
    · simp [delivered] at pending
    · exact remote
  simpa [remoteEvidence] using remote

theorem T2 (r : Report) (delivered : r.claim = .delivered)
    (localOnly : ∀ o ∈ r.observations, o.target = .local) :
    decide r = .reject := by
  cases h : decide r with
  | reject => rfl
  | accept =>
    obtain ⟨o, member, qualified⟩ := T3 r h delivered
    have localTarget := localOnly o member
    have remoteTarget := qualified.1
    rw [localTarget] at remoteTarget
    cases remoteTarget

theorem T4 (r : Report)
    (replayed : ¬ (r.observations.map Observation.observationId).Nodup) :
    decide r = .reject := by
  unfold decide
  split
  · rename_i h
    exact False.elim (replayed h.1)
  · rfl

end QIKVRT.DeliveryReporting
