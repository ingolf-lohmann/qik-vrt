-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
-- Negative fixture: the kernel must reject a claimed complete audit with c1 false.
import QIKVRTEffectAck.CanonicalClauseAudit
example : QIKVRT.CanonicalClauseAudit.V1.allClauses
    (fun id => decide (id.val ≠ 0)) = true := by decide
