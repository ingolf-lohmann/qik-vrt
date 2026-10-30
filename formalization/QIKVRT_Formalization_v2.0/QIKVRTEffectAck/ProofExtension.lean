-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.Safety

/-!
# Proof-bound change admission

An append-only list of claims does not establish preservation of their meaning.
Every admitted step therefore carries an actual proof of invariant preservation
under one unchanged interpretation. The result below is conditional on that
proof, exact-subject matching and the existing EFFECT_ACK consumer checks.

This is not a proof of its own kernel, an arbitrary compiler or a Python/CPU
implementation. Those implementation bridges remain separate obligations.
-/
namespace QIKVRT.ProofExtension

universe u v

structure Corpus (Claim : Type u) where
  claims : List Claim

def Satisfies {Claim : Type u} {Machine : Type v}
    (meaning : Claim → Machine → Prop) (corpus : Corpus Claim)
    (machine : Machine) : Prop :=
  ∀ claim, claim ∈ corpus.claims → meaning claim machine

structure Extension {Claim : Type u} (before after : Corpus Claim) where
  added : List Claim
  appendOnly : after.claims = before.claims ++ added

private theorem append_membership_cases {Claim : Type u} {claim : Claim}
    (left right : List Claim) (member : claim ∈ left ++ right) :
    claim ∈ left ∨ claim ∈ right := by
  induction left with
  | nil => exact Or.inr member
  | cons head tail ih =>
    cases member with
    | head => exact Or.inl (List.Mem.head _)
    | tail _ member =>
      cases ih member with
      | inl old => exact Or.inl (List.Mem.tail head old)
      | inr new => exact Or.inr new

private theorem and_true_left (left right : Bool) (both : (left && right) = true) :
    left = true := by
  cases left <;> cases right <;> cases both <;> rfl

private theorem and_true_right (left right : Bool) (both : (left && right) = true) :
    right = true := by
  cases left <;> cases right <;> cases both <;> rfl

theorem extension_retains_claim {Claim : Type u}
    {before after : Corpus Claim} (extension : Extension before after)
    {claim : Claim} (old : claim ∈ before.claims) :
    claim ∈ after.claims := by
  rw [extension.appendOnly]
  exact List.mem_append_left extension.added old

theorem extended_satisfaction_includes_predecessor
    {Claim : Type u} {Machine : Type v}
    {meaning : Claim → Machine → Prop} {before after : Corpus Claim}
    (extension : Extension before after) {machine : Machine}
    (valid : Satisfies meaning after machine) :
    Satisfies meaning before machine := by
  intro claim old
  exact valid claim (extension_retains_claim extension old)

theorem checked_append_is_satisfied
    {Claim : Type u} {Machine : Type v}
    {meaning : Claim → Machine → Prop} {before : Corpus Claim}
    {added : List Claim} {machine : Machine}
    (old : Satisfies meaning before machine)
    (new : ∀ claim, claim ∈ added → meaning claim machine) :
    Satisfies meaning ⟨before.claims ++ added⟩ machine := by
  intro claim member
  rcases append_membership_cases before.claims added member with h | h
  · exact old claim h
  · exact new claim h

structure CheckedStep {Claim : Type u} {Machine : Type v}
    (meaning : Claim → Machine → Prop) (before after : Corpus Claim) where
  extension : Extension before after
  execute : Machine → Machine
  preserves : ∀ machine, Satisfies meaning before machine →
    Satisfies meaning after (execute machine)

theorem checked_step_preserves
    {Claim : Type u} {Machine : Type v}
    {meaning : Claim → Machine → Prop} {before after : Corpus Claim}
    (step : CheckedStep meaning before after) {machine : Machine}
    (valid : Satisfies meaning before machine) :
    Satisfies meaning after (step.execute machine) :=
  step.preserves machine valid

theorem checked_step_preserves_old_meaning
    {Claim : Type u} {Machine : Type v}
    {meaning : Claim → Machine → Prop} {before after : Corpus Claim}
    (step : CheckedStep meaning before after) {machine : Machine}
    (valid : Satisfies meaning before machine) :
    Satisfies meaning before (step.execute machine) :=
  extended_satisfaction_includes_predecessor step.extension
    (checked_step_preserves step valid)

inductive CheckedRun {Claim : Type u} {Machine : Type v}
    (meaning : Claim → Machine → Prop)
    (initial : Corpus Claim) (start : Machine) : Corpus Claim → Machine → Prop
  | initial : CheckedRun meaning initial start initial start
  | next {before after : Corpus Claim} {machine : Machine}
      (previous : CheckedRun meaning initial start before machine)
      (step : CheckedStep meaning before after) :
      CheckedRun meaning initial start after (step.execute machine)

theorem every_checked_prefix_preserves_invariants
    {Claim : Type u} {Machine : Type v}
    {meaning : Claim → Machine → Prop} {initial current : Corpus Claim}
    {start machine : Machine} (valid : Satisfies meaning initial start)
    (run : CheckedRun meaning initial start current machine) :
    Satisfies meaning current machine := by
  induction run with
  | initial => exact valid
  | next previous step ih => exact step.preserves _ ih

theorem every_checked_prefix_retains_initial_claim
    {Claim : Type u} {Machine : Type v}
    {meaning : Claim → Machine → Prop} {initial current : Corpus Claim}
    {start machine : Machine}
    (run : CheckedRun meaning initial start current machine)
    {claim : Claim} (member : claim ∈ initial.claims) :
    claim ∈ current.claims := by
  induction run with
  | initial => exact member
  | next previous step ih => exact extension_retains_claim step.extension ih

/-- Unknown verification is neither a successful check nor a detected failure. -/
inductive Verification (statement : Prop) where
  | verified : statement → Verification statement
  | refuted : (¬ statement) → Verification statement
  | unavailable : Verification statement

def verified {statement : Prop} : Verification statement → Bool
  | .verified _ => true
  | .refuted _ => false
  | .unavailable => false

theorem unavailable_never_admits (statement : Prop) :
    verified (Verification.unavailable : Verification statement) = false := rfl

theorem refuted_never_admits {statement : Prop} (failure : ¬ statement) :
    verified (Verification.refuted failure) = false := rfl

theorem verified_contains_actual_proof {statement : Prop}
    (check : Verification statement) (accepted : verified check = true) :
    statement := by
  cases check with
  | verified proof => exact proof
  | refuted failure => cases accepted
  | unavailable => cases accepted

structure Subject where
  repository : String
  head : String
  tree : String
  node : String
  epoch : Nat
deriving DecidableEq

def mayActivate {statement : Prop} (check : Verification statement)
    (expected observed : Subject)
    (consumer : QIKVRT.EffectAck.V1.ConsumerChecks)
    (snapshot : QIKVRT.EffectAck.V1.Snapshot)
    (record : QIKVRT.EffectAck.V1.State) (releaseClaim : Bool) : Bool :=
  (verified check && decide (expected = observed)) &&
    QIKVRT.EffectAck.V1.authorizeOrdinaryRelease consumer snapshot record releaseClaim

theorem activation_requires_proof {statement : Prop}
    (check : Verification statement) (expected observed : Subject)
    (consumer : QIKVRT.EffectAck.V1.ConsumerChecks)
    (snapshot : QIKVRT.EffectAck.V1.Snapshot)
    (record : QIKVRT.EffectAck.V1.State) (releaseClaim : Bool)
    (active : mayActivate check expected observed consumer snapshot record releaseClaim = true) :
    statement := by
  have group := and_true_left _ _ active
  have h : verified check = true := and_true_left _ _ group
  exact verified_contains_actual_proof check h

theorem activation_requires_exact_subject {statement : Prop}
    (check : Verification statement) (expected observed : Subject)
    (consumer : QIKVRT.EffectAck.V1.ConsumerChecks)
    (snapshot : QIKVRT.EffectAck.V1.Snapshot)
    (record : QIKVRT.EffectAck.V1.State) (releaseClaim : Bool)
    (active : mayActivate check expected observed consumer snapshot record releaseClaim = true) :
    expected = observed := by
  have group := and_true_left _ _ active
  have h : decide (expected = observed) = true := and_true_right _ _ group
  exact of_decide_eq_true h

theorem activation_requires_effect_ack {statement : Prop}
    (check : Verification statement) (expected observed : Subject)
    (consumer : QIKVRT.EffectAck.V1.ConsumerChecks)
    (snapshot : QIKVRT.EffectAck.V1.Snapshot)
    (record : QIKVRT.EffectAck.V1.State) (releaseClaim : Bool)
    (active : mayActivate check expected observed consumer snapshot record releaseClaim = true) :
    QIKVRT.EffectAck.V1.authorizeOrdinaryRelease consumer snapshot record releaseClaim = true :=
  and_true_right _ _ active

theorem unavailable_cannot_activate (statement : Prop) (expected observed : Subject)
    (consumer : QIKVRT.EffectAck.V1.ConsumerChecks)
    (snapshot : QIKVRT.EffectAck.V1.Snapshot)
    (record : QIKVRT.EffectAck.V1.State) (releaseClaim : Bool) :
    mayActivate (Verification.unavailable : Verification statement)
      expected observed consumer snapshot record releaseClaim = false := rfl

end QIKVRT.ProofExtension
