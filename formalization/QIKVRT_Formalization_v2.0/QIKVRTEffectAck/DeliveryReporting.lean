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

/-! Goal-bound work completion. These are consistency theorems about supplied
observations. Authenticity and execution by an external client remain adapter
obligations; no theorem gives a chat system access to another account. -/

structure WorkReport where
  requiredTarget : String
  observedTarget : String
  requiredEffect : String
  observedEffect : String
  origin : String
  checker : String
  requiredSha256 : String
  observedSha256 : String
  fromCache : Bool
  completedUtc : Nat
  observedUtc : Nat
  closedUtc : Nat
  deriving Repr

def workEffects : List String := ["JOURNAL_WRITE", "SOURCE_CHANGE",
  "ARTIFACT_INSTALLATION", "DATA_READBACK", "RUNTIME_EFFECT"]

def workDigest (s : String) : Bool :=
  s.length == 64 && s.toList.all (fun c => "0123456789abcdef".toList.contains c)

def WorkInputs (r : WorkReport) : Prop :=
  r.requiredTarget ≠ "" ∧ r.requiredEffect ∈ workEffects ∧
  r.observedEffect ∈ workEffects ∧
  (r.requiredSha256 = "" ∨ workDigest r.requiredSha256 = true) ∧
  (r.requiredEffect ≠ "ARTIFACT_INSTALLATION" ∨ r.requiredSha256 ≠ "")

instance (r : WorkReport) : Decidable (WorkInputs r) := by
  unfold WorkInputs
  infer_instance

def WorkAdmissible (r : WorkReport) : Prop :=
  WorkInputs r ∧ r.requiredTarget = r.observedTarget ∧
  r.requiredEffect = r.observedEffect ∧ r.origin = "DIRECT_TOOL_READBACK" ∧
  r.checker = "VERIFIED" ∧
  (r.completedUtc < r.observedUtc ∧ r.observedUtc ≤ r.closedUtc) ∧
  (r.requiredSha256 = "" ∨ r.requiredSha256 = r.observedSha256) ∧
  (r.requiredEffect ≠ "DATA_READBACK" ∨ r.fromCache = false)

instance (r : WorkReport) : Decidable (WorkAdmissible r) := by
  unfold WorkAdmissible
  infer_instance

def workDecide (r : WorkReport) : Verdict :=
  if WorkAdmissible r then .accept else .reject

/-- A journal effect cannot close a task requiring another effect. -/
theorem T5 (r : WorkReport) (different : r.requiredEffect ≠ r.observedEffect) :
    workDecide r = .reject := by
  unfold workDecide
  exact if_neg (fun h : WorkAdmissible r => different h.2.2.1)

/-- A new private copy is not readback of a different original target. -/
theorem T6 (r : WorkReport) (different : r.requiredTarget ≠ r.observedTarget) :
    workDecide r = .reject := by
  unfold workDecide
  exact if_neg (fun h : WorkAdmissible r => different h.2.1)

/-- Forwarding a report cannot turn it into this observer's direct readback. -/
theorem T7 (r : WorkReport) (reported : r.origin ≠ "DIRECT_TOOL_READBACK") :
    workDecide r = .reject := by
  unfold workDecide
  exact if_neg (fun h : WorkAdmissible r => reported h.2.2.2.1)

/-- An unavailable or failed checker cannot establish completion. -/
theorem T8 (r : WorkReport) (unverified : r.checker ≠ "VERIFIED") :
    workDecide r = .reject := by
  unfold workDecide
  exact if_neg (fun h : WorkAdmissible r => unverified h.2.2.2.2.1)

/-- Replayed observation time does not establish useful new progress. -/
theorem T9 (r : WorkReport) (stale : r.observedUtc ≤ r.completedUtc) :
    workDecide r = .reject := by
  unfold workDecide
  exact if_neg (fun h : WorkAdmissible r => Nat.not_lt_of_ge stale h.2.2.2.2.2.1.1)

/-- A fresh data read requires explicit non-cache metadata. -/
theorem T10 (r : WorkReport) (dataRead : r.requiredEffect = "DATA_READBACK")
    (cached : r.fromCache ≠ false) : workDecide r = .reject := by
  unfold workDecide
  exact if_neg (fun h : WorkAdmissible r =>
    Or.elim h.2.2.2.2.2.2.2 (fun other => other dataRead) cached)

end QIKVRT.DeliveryReporting
