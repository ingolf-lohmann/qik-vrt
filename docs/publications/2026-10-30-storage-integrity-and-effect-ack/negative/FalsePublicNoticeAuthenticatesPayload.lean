-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.StorageIntegrity
open QIKVRT.StorageIntegrity.V1
example : (Element.mk [true] [true] [] [false]).payload =
    (Element.mk [true] [true] [] [true]).payload := by decide
