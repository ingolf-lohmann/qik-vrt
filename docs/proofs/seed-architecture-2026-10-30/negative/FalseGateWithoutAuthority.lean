import QIKVRTEffectAck.SeedArchitecture
open QIKVRT.SeedArchitecture.V1
-- Deliberately false: a missing authority guard cannot admit continuation.
theorem false_gate : continueAllowed ⟨true, false, true, false⟩ = true := by decide

