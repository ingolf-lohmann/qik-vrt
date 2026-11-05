-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
import QIKVRTEffectAck.CanonicalClauseAudit
#print axioms QIKVRT.CanonicalClauseAudit.V1.all_clauses_requires_every_index
#print axioms QIKVRT.CanonicalClauseAudit.V1.failed_clause_prevents_authorization
#print axioms QIKVRT.CanonicalClauseAudit.V1.authorized_requires_original_eap
#print axioms QIKVRT.CanonicalClauseAudit.V1.authorized_requires_recorded_and_recomputed_done
#print axioms QIKVRT.CanonicalClauseAudit.V1.authorized_checks_are_sound
