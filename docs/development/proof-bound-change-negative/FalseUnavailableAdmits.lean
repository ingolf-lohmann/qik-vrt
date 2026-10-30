-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.ProofExtension
open QIKVRT.ProofExtension
example : verified (Verification.unavailable : Verification True) = true := by decide
