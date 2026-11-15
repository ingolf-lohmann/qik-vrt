import QIKVRTEffectAck.InformationBoundary

/-!
# Two-fixpoint serialization: bounded proof obligations

The two fixpoints delimit a byte interval [start, stop). The 64-bit and
8-bit seeds are parameters, NOT proofs of uniqueness, cryptographic
authentication, or physical correspondence. QR encoding and EAP readback
remain separate implementation and operational proof obligations.
-/

namespace QIKVRT.EffectAck.TwoFixpoints

structure Boundary where
  start : Nat
  stop : Nat
  ordered : start ≤ stop

def Width (b : Boundary) : Nat := b.stop - b.start

theorem stop_eq_start_add_width (b : Boundary) :
    b.stop = b.start + Width b := by
  unfold Width
  exact (Nat.add_sub_of_le b.ordered).symm

/-- The fixed endpoints determine a unique byte interval length. -/
theorem same_fixpoints_same_width (a b : Boundary)
    (hStart : a.start = b.start) (hStop : a.stop = b.stop) :
    Width a = Width b := by
  simp [Width, hStart, hStop]

/-- A verified left inverse makes serialization injective.
    The premise must be discharged against the actual codec. -/
theorem codec_roundtrip_implies_injective
    {Element Bytes : Type}
    (encode : Element → Bytes) (decode : Bytes → Element)
    (hRoundtrip : ∀ e, decode (encode e) = e) :
    Function.Injective encode := by
  intro a b h
  calc
    a = decode (encode a) := (hRoundtrip a).symm
    _ = decode (encode b) := congrArg decode h
    _ = b := hRoundtrip b

/-- Seed equality and byte equality imply deterministic QR equality
    only for a specified pure QR encoder. No collision-resistance claim. -/
theorem same_inputs_same_qr
    {Bytes QR : Type}
    (qr : UInt64 → UInt8 → Bytes → QR)
    (seed64 : UInt64) (seed8 : UInt8) (payload : Bytes) :
    qr seed64 seed8 payload = qr seed64 seed8 payload := rfl

/-- An implementation-level roundtrip and an independently established QR
    injectivity premise compose into an injective serialized QR representation.
    The premise on qr must be verified for the concrete payload domain; seeds
    alone do not discharge it. This theorem asserts no cryptographic security. -/
theorem codec_qr_injective_of_roundtrip
    {Element Bytes QR : Type}
    (encode : Element → Bytes) (decode : Bytes → Element)
    (qr : UInt64 → UInt8 → Bytes → QR)
    (seed64 : UInt64) (seed8 : UInt8)
    (hRoundtrip : ∀ e, decode (encode e) = e)
    (hQrInjective : Function.Injective (qr seed64 seed8)) :
    Function.Injective (fun e => qr seed64 seed8 (encode e)) := by
  intro a b h
  apply codec_roundtrip_implies_injective encode decode hRoundtrip
  exact hQrInjective h

/-- EAP acceptance cannot be inferred from a QR value alone:
    an independent observation hypothesis is explicitly required. -/
theorem observed_effect_requires_readback
    {QR : Type} (qr : QR) (observed : QR → Prop)
    (hReadback : observed qr) : observed qr := hReadback

/-! A failed or unverified transition cannot advance the accepted state.
    Attempts and their evidence must be journaled separately by the implementation. -/
def acceptedNext {State : Type} (current candidate : State)
    (verified : Bool) : State :=
  if verified then candidate else current

theorem rejected_transition_preserves_state {State : Type}
    (current candidate : State) :
    acceptedNext current candidate false = current := by
  rfl

theorem verified_transition_accepts_candidate {State : Type}
    (current candidate : State) :
    acceptedNext current candidate true = candidate := by
  rfl

/-- The next accepted state becomes the next iteration's starting state;
    no independent verification is inferred from a candidate alone. -/
theorem rejected_successor_remains_previous_fixpoint {State : Type}
    (current candidate nextCandidate : State) :
    acceptedNext (acceptedNext current candidate false) nextCandidate false
      = current := by
  rfl

end QIKVRT.EffectAck.TwoFixpoints
