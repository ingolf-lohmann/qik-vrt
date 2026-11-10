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
  omega

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

/-- EAP acceptance cannot be inferred from a QR value alone:
    an independent observation hypothesis is explicitly required. -/
theorem observed_effect_requires_readback
    {QR : Type} (qr : QR) (observed : QR → Prop)
    (hReadback : observed qr) : observed qr := hReadback

end QIKVRT.EffectAck.TwoFixpoints
