import EffectIntegrity

namespace QikVrtAlgebraicRoot

/-- A serialized payload is accepted only if decoding reproduces its exact source. -/
structure Serialization (Payload Bytes : Type) where
  encode : Payload → Bytes
  decode : Bytes → Option Payload
  roundtrip : ∀ p, decode (encode p) = some p

theorem serialization_injective {Payload Bytes : Type}
    (codec : Serialization Payload Bytes) :
    Function.Injective codec.encode := by
  intro a b h
  have ha := codec.roundtrip a
  have hb := codec.roundtrip b
  rw [h] at ha
  exact Option.some.inj (ha.symm.trans hb)

def serializations_compose
    {A B C : Type}
    (first : Serialization A B)
    (second : Serialization B C) :
    Serialization A C where
  encode := second.encode ∘ first.encode
  decode := fun c => (second.decode c).bind first.decode
  roundtrip := by
    intro a
    simp [Function.comp, second.roundtrip, first.roundtrip]

/-- A cascade preserves each stage's round-trip guarantee. -/
theorem cascade_roundtrip
    {A B C : Type}
    (first : Serialization A B)
    (second : Serialization B C)
    (a : A) :
    (serializations_compose first second).decode
      ((serializations_compose first second).encode a) = some a :=
  (serializations_compose first second).roundtrip a

#print axioms QikVrtAlgebraicRoot.serialization_injective
#print axioms QikVrtAlgebraicRoot.serializations_compose
#print axioms QikVrtAlgebraicRoot.cascade_roundtrip

end QikVrtAlgebraicRoot
