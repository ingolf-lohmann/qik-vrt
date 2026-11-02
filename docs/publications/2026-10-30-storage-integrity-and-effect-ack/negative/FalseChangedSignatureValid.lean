-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.StorageIntegrity
open QIKVRT.StorageIntegrity.V1
example : Valid ⟨[true], [true]⟩ ⟨[false], [true], [], []⟩ := by
  change ([false] : Bits) = [true] ∧ ([true] : Bits) = [true]
  decide
