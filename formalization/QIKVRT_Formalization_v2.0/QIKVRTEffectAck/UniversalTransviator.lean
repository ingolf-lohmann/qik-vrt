import Std

/-!
# Universal Transviator: lossless reconnect contract

This module formalizes a bounded software statement for the owner-approved
"universal Transviator" connection through the Universal Terminal.

If a codec is lossless, and a reconnect reads the exact persisted carrier whose
recomputed digest and stored digest both match the expected digest, the readback
is the original payload.

The theorem does **not** prove network availability, physical delivery, a
running native runtime, cryptographic security of an abstract digest, domain
activation, or EFFECT_ACK_DONE.
-/

namespace QIKVRT.UniversalTransviator.V1

universe u v w

variable {Payload : Type u} {Carrier : Type v} {Digest : Type w}

/-- An encoding whose decoder recovers every encoded payload exactly. -/
structure LosslessCodec (Payload : Type u) (Carrier : Type v) where
  encode : Payload → Carrier
  decode : Carrier → Option Payload
  roundTrip : ∀ payload, decode (encode payload) = some payload

/-- The carrier and digest retained across a disconnected interval. -/
structure Persisted (Carrier : Type v) (Digest : Type w) where
  carrier : Carrier
  digest : Digest

/-- Persist a payload in the canonical carrier selected by the codec. -/
def persist
    (codec : LosslessCodec Payload Carrier)
    (digest : Carrier → Digest)
    (payload : Payload) : Persisted Carrier Digest where
  carrier := codec.encode payload
  digest := digest (codec.encode payload)

/--
Terminal readback accepts a persisted carrier only when an independent digest
recomputation and the stored digest both equal the expected digest.
-/
def terminalReadback
    [DecidableEq Digest]
    (codec : LosslessCodec Payload Carrier)
    (digest : Carrier → Digest)
    (expected : Digest)
    (stored : Persisted Carrier Digest) : Option Payload :=
  if digest stored.carrier = expected ∧ stored.digest = expected then
    codec.decode stored.carrier
  else
    none

/--
A freshly persisted payload can be disconnected and later read back without
loss, provided the reconnect uses the same codec and digest function.
-/
theorem terminal_reconnect_lossless
    [DecidableEq Digest]
    (codec : LosslessCodec Payload Carrier)
    (digest : Carrier → Digest)
    (payload : Payload) :
    terminalReadback codec digest (digest (codec.encode payload))
      (persist codec digest payload) = some payload := by
  simp [terminalReadback, persist, codec.roundTrip]

/-- A persisted record with a non-matching stored digest is rejected. -/
theorem altered_persisted_digest_rejected
    [DecidableEq Digest]
    (codec : LosslessCodec Payload Carrier)
    (digest : Carrier → Digest)
    (expected : Digest)
    (stored : Persisted Carrier Digest)
    (h : stored.digest ≠ expected) :
    terminalReadback codec digest expected stored = none := by
  simp [terminalReadback, h]

end QIKVRT.UniversalTransviator.V1
