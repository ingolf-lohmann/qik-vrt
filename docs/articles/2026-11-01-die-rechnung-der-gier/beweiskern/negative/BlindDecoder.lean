import QIKVRT.ZeroOneObservation

-- Expected rejection: a constant observation cannot determine every hidden bit.
example : ∃ decoder : Unit → Bool, ∀ bit : Bool, decoder () = bit := by
  refine ⟨fun _ => false, ?_⟩
  intro bit
  rfl
