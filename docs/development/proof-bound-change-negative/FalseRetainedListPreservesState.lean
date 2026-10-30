-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.ProofExtension
open QIKVRT.ProofExtension
example : Satisfies (fun (_ : Unit) (s : Bool) => s = true) ⟨[()]⟩ false := by
  intro claim member
  rfl
