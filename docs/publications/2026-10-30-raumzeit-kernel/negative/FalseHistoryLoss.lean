-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.ReconstructibleVirtuality
open QIKVRT.ReconstructibleVirtuality.V1
example : (withHistory eraseBit true).2 = false := by decide
