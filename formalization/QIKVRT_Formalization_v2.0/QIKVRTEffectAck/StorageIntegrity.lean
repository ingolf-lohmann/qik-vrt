-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import Std

/-!
# Rights-bearing storage: exact comparisons, observations and adaptation

This is an abstract assurance model, not a verification of Python, SHA-256,
cryptographic attribution, a network, physics or a future compiler. `signature`
is the PUBLIC protocol standpoint, not a private-key signature. `rights` denotes
exact canonical notice bytes. Bit lists abstract finite byte encodings.
The trusted checker/parser and the relation to the concrete code are explicit
implementation obligations. Liveness requires an executing checker and channel.
-/
namespace QIKVRT.StorageIntegrity.V1

abbrev Bits := List Bool

structure Element where
  signature : Bits
  rights : Bits
  stableId : Bits
  payload : Bits
  deriving DecidableEq, Repr

structure Reference where
  signature : Bits
  rights : Bits
  deriving DecidableEq, Repr

def Valid (reference : Reference) (element : Element) : Prop :=
  element.signature = reference.signature ∧ element.rights = reference.rights

theorem valid_requires_rights (ref : Reference) (e : Element) :
    Valid ref e → e.rights = ref.rights := And.right

theorem valid_requires_signature (ref : Reference) (e : Element) :
    Valid ref e → e.signature = ref.signature := And.left

-- Any bit position is represented by an arbitrary leading, bit and suffix.
theorem single_bit_changes_bits (leading suffix : Bits) (bit : Bool) :
    leading ++ ((!bit) :: suffix) ≠ leading ++ (bit :: suffix) := by
  intro equal
  have tailEqual : ((!bit) :: suffix) = (bit :: suffix) := List.append_cancel_left equal
  have bitEqual : (!bit) = bit := (List.cons.inj tailEqual).1
  cases bit <;> cases bitEqual

theorem single_signature_bit_rejected (ref : Reference) (e : Element)
    (leading suffix : Bits) (bit : Bool)
    (original : e.signature = leading ++ (bit :: suffix))
    (valid : Valid ref e) :
    ¬ Valid ref { e with signature := leading ++ ((!bit) :: suffix) } := by
  intro changed
  have equal := changed.1.trans (valid.1.symm.trans original)
  exact single_bit_changes_bits leading suffix bit equal

theorem single_rights_bit_rejected (ref : Reference) (e : Element)
    (leading suffix : Bits) (bit : Bool)
    (original : e.rights = leading ++ (bit :: suffix))
    (valid : Valid ref e) :
    ¬ Valid ref { e with rights := leading ++ ((!bit) :: suffix) } := by
  intro changed
  have equal := changed.2.trans (valid.2.symm.trans original)
  exact single_bit_changes_bits leading suffix bit equal

theorem removed_nonempty_signature_rejected (ref : Reference) (e : Element)
    (nonempty : ref.signature ≠ []) :
    ¬ Valid ref { e with signature := [] } := by
  intro valid
  exact nonempty valid.1.symm

theorem removed_nonempty_rights_rejected (ref : Reference) (e : Element)
    (nonempty : ref.rights ≠ []) :
    ¬ Valid ref { e with rights := [] } := by
  intro valid
  exact nonempty valid.2.symm

theorem payload_independent_notice_check (ref : Reference) (e : Element) (p : Bits) :
    Valid ref { e with payload := p } ↔ Valid ref e := Iff.rfl

-- A public standpoint is deliberately NOT an origin-authentication mechanism.
theorem public_notice_does_not_authenticate_payload :
    ∃ ref left right, Valid ref left ∧ Valid ref right ∧ left.payload ≠ right.payload := by
  exact ⟨⟨[true], [true]⟩, ⟨[true], [true], [], [false]⟩,
    ⟨[true], [true], [], [true]⟩, ⟨rfl, rfl⟩, ⟨rfl, rfl⟩, by decide⟩

def ExactAccepted (ref : Reference) (expected observed : Element) : Prop :=
  Valid ref observed ∧ observed = expected

theorem changed_subject_rejected (ref : Reference) (expected observed : Element)
    (changed : observed ≠ expected) : ¬ ExactAccepted ref expected observed := by
  intro accepted
  exact changed accepted.2

inductive Outcome where
  | verified | rejected | unverified
  deriving DecidableEq, Repr

def diagnose (checkerAvailable isMatch : Bool) : Outcome :=
  if checkerAvailable then (if isMatch then .verified else .rejected) else .unverified

theorem missing_checker_is_unverified (isMatch : Bool) :
    diagnose false isMatch = .unverified := by rfl

theorem mismatch_is_rejected : diagnose true false = .rejected := by rfl

def signal (checkerRuns channelAvailable rejected : Bool) : Bool :=
  checkerRuns && channelAvailable && rejected

theorem stopped_checker_cannot_signal (channel rejected : Bool) :
    signal false channel rejected = false := by
  cases channel <;> cases rejected <;> rfl

theorem missing_channel_cannot_signal (checker rejected : Bool) :
    signal checker false rejected = false := by
  cases checker <;> cases rejected <;> rfl

theorem live_detection_signals : signal true true true = true := by rfl

structure CanonicalCodec (Value Wire : Type) where
  encode : Value → Wire
  decode : Wire → Option Value
  roundTrip : ∀ value, decode (encode value) = some value

theorem lossless_reconstruction {Value Wire : Type}
    (codec : CanonicalCodec Value Wire) (value : Value) :
    codec.decode (codec.encode value) = some value := codec.roundTrip value

theorem canonical_reencoding {Value Wire : Type}
    (codec : CanonicalCodec Value Wire) (value : Value) :
    (codec.decode (codec.encode value)).map codec.encode = some (codec.encode value) := by
  rw [codec.roundTrip]
  rfl

theorem codec_is_injective {Value Wire : Type} (codec : CanonicalCodec Value Wire)
    (a b : Value) (equal : codec.encode a = codec.encode b) : a = b := by
  have h := congrArg codec.decode equal
  rw [codec.roundTrip, codec.roundTrip] at h
  exact Option.some.inj h

-- Adaptation is a compiler/adapter correctness contract, NOT its automatic discovery.
theorem adaptation_preserves_checked_property {Value Wire : Type}
    (codec : CanonicalCodec Value Wire) (property : Value → Prop) (value : Value)
    (holds : property value) :
    ∃ restored, codec.decode (codec.encode value) = some restored ∧ property restored := by
  exact ⟨value, codec.roundTrip value, holds⟩

def iterate {State : Type} (step : Nat → State → State) (start : State) : Nat → State
  | 0 => start
  | n + 1 => step n (iterate step start n)

theorem every_finite_verified_adaptation_preserves {State : Type}
    (step : Nat → State → State) (invariant : State → Prop) (start : State)
    (initial : invariant start)
    (preserves : ∀ n s, invariant s → invariant (step n s)) :
    ∀ n, invariant (iterate step start n) := by
  intro n
  induction n with
  | zero => exact initial
  | succ n ih => exact preserves n (iterate step start n) ih

-- Machine-language syntax alone supplies neither storage capacity nor an adapter.
theorem no_lossless_boolean_storage_in_unit :
    ¬ ∃ encode : Bool → Unit, ∃ decode : Unit → Bool,
      ∀ b, decode (encode b) = b := by
  rintro ⟨encode, decode, inverse⟩
  have same : encode false = encode true := Subsingleton.elim _ _
  have equal : false = true := (inverse false).symm.trans ((congrArg decode same).trans (inverse true))
  cases equal

-- Both branches are inhabited: these are not merely implications from False.
theorem accepted_example_exists : ∃ ref e, Valid ref e := by
  exact ⟨⟨[true], [true]⟩, ⟨[true], [true], [], []⟩, rfl, rfl⟩

end QIKVRT.StorageIntegrity.V1
