import Root

namespace QikVrtAlgebraicRoot

/-- Abstract record of a proposed state change and its observed effect. -/
structure EffectRecord (State : Type) where
  before : State
  proposed : State
  observed : Option State
  acknowledged : Bool

/-- An acknowledgement is justified only by an observation equal to the proposal. -/
def SoundAcknowledgement {State : Type} (r : EffectRecord State) : Prop :=
  r.acknowledged = true → r.observed = some r.proposed

theorem sound_ack_requires_observation {State : Type}
    (r : EffectRecord State) (h : SoundAcknowledgement r)
    (ha : r.acknowledged = true) :
    r.observed = some r.proposed := h ha

theorem no_observation_no_sound_ack {State : Type}
    (r : EffectRecord State) (h : SoundAcknowledgement r)
    (hn : r.observed = none) :
    r.acknowledged = false := by
  cases hb : r.acknowledged with
  | false => rfl
  | true =>
    have ho := h hb
    rw [hn] at ho
    cases ho

/-- Integrity is conditional on a trusted, injective fingerprint function. -/
def VerifiedIntegrity {Payload Digest : Type}
    (fingerprint : Payload → Digest) (stored : Digest)
    (payload : Payload) : Prop :=
  fingerprint payload = stored

theorem integrity_equal_fingerprint_implies_equal_payload
    {Payload Digest : Type} (fingerprint : Payload → Digest)
    (injective_fingerprint : Function.Injective fingerprint)
    (a b : Payload)
    (h : fingerprint a = fingerprint b) : a = b :=
  injective_fingerprint h

theorem modified_payload_cannot_retain_fingerprint
    {Payload Digest : Type} (fingerprint : Payload → Digest)
    (injective_fingerprint : Function.Injective fingerprint)
    (a b : Payload) (changed : a ≠ b) :
    fingerprint a ≠ fingerprint b := by
  intro same
  exact changed (injective_fingerprint same)

#check sound_ack_requires_observation
#check no_observation_no_sound_ack
#check integrity_equal_fingerprint_implies_equal_payload
#check modified_payload_cannot_retain_fingerprint

#print axioms QikVrtAlgebraicRoot.sound_ack_requires_observation
#print axioms QikVrtAlgebraicRoot.no_observation_no_sound_ack
#print axioms QikVrtAlgebraicRoot.integrity_equal_fingerprint_implies_equal_payload
#print axioms QikVrtAlgebraicRoot.modified_payload_cannot_retain_fingerprint
end QikVrtAlgebraicRoot
