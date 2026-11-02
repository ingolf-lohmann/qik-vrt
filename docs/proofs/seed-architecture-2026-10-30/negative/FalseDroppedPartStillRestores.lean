import QIKVRTEffectAck.SeedArchitecture
open QIKVRT.SeedArchitecture.V1
-- Deliberately false: a rejected part cannot produce a complete result.
theorem false_decode : decodeAll (fun b : Bool => if b then some b else none) [false] = some [false] := by decide

