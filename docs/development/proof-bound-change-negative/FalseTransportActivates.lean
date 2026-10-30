-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.ProofExtension
open QIKVRT.ProofExtension
open QIKVRT.EffectAck.V1
def subject : Subject := ⟨"repository", "head", "tree", "node", 1⟩
example : mayActivate (.verified True.intro) subject subject
    fullyValidConsumerChecks transportAckOnly .nack false = true := by decide
