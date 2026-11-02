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
  requiredTarget : List Nat
  observedTarget : List Nat
  requiredEffect : List Nat
  observedEffect : List Nat
  origin : List Nat
  checker : List Nat
  requiredSha256 : List Nat
  observedSha256 : List Nat
  fromCache : Bool
  completedUtc : Nat
  observedUtc : Nat
  closedUtc : Nat
  deriving Repr

/- Text fields use scalar-code lists; conversion of actual strings belongs
only to the finite executable bridge, not the theorem dependency graph. -/
def journalEffect : List Nat := [74, 79, 85, 82, 78, 65, 76, 95, 87, 82, 73, 84, 69] -- JOURNAL_WRITE
def sourceEffect : List Nat := [83, 79, 85, 82, 67, 69, 95, 67, 72, 65, 78, 71, 69] -- SOURCE_CHANGE
def installationEffect : List Nat := [65, 82, 84, 73, 70, 65, 67, 84, 95, 73, 78, 83, 84, 65, 76, 76, 65, 84, 73, 79, 78] -- ARTIFACT_INSTALLATION
def dataReadEffect : List Nat := [68, 65, 84, 65, 95, 82, 69, 65, 68, 66, 65, 67, 75] -- DATA_READBACK
def runtimeEffect : List Nat := [82, 85, 78, 84, 73, 77, 69, 95, 69, 70, 70, 69, 67, 84] -- RUNTIME_EFFECT
def directOrigin : List Nat := [68, 73, 82, 69, 67, 84, 95, 84, 79, 79, 76, 95, 82, 69, 65, 68, 66, 65, 67, 75] -- DIRECT_TOOL_READBACK
def verifiedChecker : List Nat := [86, 69, 82, 73, 70, 73, 69, 68] -- VERIFIED

def workEffects : List (List Nat) :=
  [journalEffect, sourceEffect, installationEffect, dataReadEffect, runtimeEffect]

def workDigest (codes : List Nat) : Bool :=
  -- Model text as scalar codes, independent of either Lean version's String
  -- storage. The vector bridge maps original strings with Char.toNat.
  codes.length == 64 && codes.all (fun c =>
    (48 ≤ c && c ≤ 57) || (97 ≤ c && c ≤ 102))

def WorkInputs (r : WorkReport) : Prop :=
  r.requiredTarget ≠ [] ∧ r.requiredEffect ∈ workEffects ∧
  r.observedEffect ∈ workEffects ∧
  (r.requiredSha256 = [] ∨ workDigest r.requiredSha256 = true) ∧
  (r.requiredEffect ≠ installationEffect ∨ r.requiredSha256 ≠ [])

instance (r : WorkReport) : Decidable (WorkInputs r) := by
  unfold WorkInputs
  infer_instance

def WorkAdmissible (r : WorkReport) : Prop :=
  WorkInputs r ∧ r.requiredTarget = r.observedTarget ∧
  r.requiredEffect = r.observedEffect ∧ r.origin = directOrigin ∧
  r.checker = verifiedChecker ∧
  (r.completedUtc < r.observedUtc ∧ r.observedUtc ≤ r.closedUtc) ∧
  (r.requiredSha256 = [] ∨ r.requiredSha256 = r.observedSha256) ∧
  (r.requiredEffect ≠ dataReadEffect ∨ r.fromCache = false)

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
theorem T7 (r : WorkReport) (reported : r.origin ≠ directOrigin) :
    workDecide r = .reject := by
  unfold workDecide
  exact if_neg (fun h : WorkAdmissible r => reported h.2.2.2.1)

/-- An unavailable or failed checker cannot establish completion. -/
theorem T8 (r : WorkReport) (unverified : r.checker ≠ verifiedChecker) :
    workDecide r = .reject := by
  unfold workDecide
  exact if_neg (fun h : WorkAdmissible r => unverified h.2.2.2.2.1)

/-- Replayed observation time does not establish useful new progress. -/
theorem T9 (r : WorkReport) (stale : r.observedUtc ≤ r.completedUtc) :
    workDecide r = .reject := by
  unfold workDecide
  exact if_neg (fun h : WorkAdmissible r => Nat.not_lt_of_ge stale h.2.2.2.2.2.1.1)

/-- A fresh data read requires explicit non-cache metadata. -/
theorem T10 (r : WorkReport) (dataRead : r.requiredEffect = dataReadEffect)
    (cached : r.fromCache ≠ false) : workDecide r = .reject := by
  unfold workDecide
  exact if_neg (fun h : WorkAdmissible r =>
    Or.elim h.2.2.2.2.2.2.2 (fun other => other dataRead) cached)

end QIKVRT.DeliveryReporting
