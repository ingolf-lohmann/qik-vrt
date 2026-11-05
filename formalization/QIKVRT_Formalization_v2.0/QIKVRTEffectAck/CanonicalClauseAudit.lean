-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
import QIKVRTEffectAck.CanonicalTemporalMemory
import QIKVRTEffectAck.Safety

/-!
The fourteen indices are an opt-in obligation profile, not a claim that the
published temporal-memory paper proves fourteen clauses. Predicate soundness,
SHA-256, exact bytes and the Python/model relation remain explicit obligations.
The original archive and EAP authorization functions are reused unchanged.
-/
namespace QIKVRT.CanonicalClauseAudit.V1

abbrev ClauseID := Fin 14

def allClauses (checks : ClauseID → Bool) : Bool :=
  decide (∀ id, checks id = true)

def authorize
    (pastFuture : QIKVRT.CanonicalTemporalMemory.V1.ProspectiveRelease)
    (consumer : QIKVRT.EffectAck.V1.ConsumerChecks)
    (snapshot : QIKVRT.EffectAck.V1.Snapshot)
    (state : QIKVRT.EffectAck.V1.State) (claim : Bool)
    (checks : ClauseID → Bool) : Bool :=
  QIKVRT.CanonicalTemporalMemory.V1.release
    { pastFuture with effectAckDone :=
      QIKVRT.EffectAck.V1.authorizeOrdinaryRelease consumer snapshot state claim } &&
    allClauses checks

theorem all_clauses_requires_every_index (checks : ClauseID → Bool)
    (accepted : allClauses checks = true) (id : ClauseID) :
    checks id = true := by
  have all : ∀ id, checks id = true := by simpa [allClauses] using accepted
  exact all id

theorem failed_clause_prevents_authorization
    (pastFuture) (consumer) (snapshot) (state) (claim)
    (checks : ClauseID → Bool) (id : ClauseID) (failed : checks id = false) :
    authorize pastFuture consumer snapshot state claim checks = false := by
  have noAll : allClauses checks = false := by
    cases h : allClauses checks with
    | false => rfl
    | true => have bad := all_clauses_requires_every_index checks h id
              simp [failed] at bad
  simp [authorize, noAll]

theorem authorized_requires_original_eap
    (pastFuture) (consumer) (snapshot) (state) (claim) (checks)
    (accepted : authorize pastFuture consumer snapshot state claim checks = true) :
    QIKVRT.EffectAck.V1.authorizeOrdinaryRelease consumer snapshot state claim = true := by
  have pair :
      QIKVRT.CanonicalTemporalMemory.V1.release
        { pastFuture with effectAckDone :=
          QIKVRT.EffectAck.V1.authorizeOrdinaryRelease consumer snapshot state claim } = true ∧
      allClauses checks = true := by simpa [authorize] using accepted
  have temporal := pair.1
  exact QIKVRT.CanonicalTemporalMemory.V1.release_requires_effect_ack _ temporal

theorem authorized_requires_recorded_and_recomputed_done
    (pastFuture) (consumer) (snapshot) (state) (claim) (checks)
    (accepted : authorize pastFuture consumer snapshot state claim checks = true) :
    state = .done ∧ QIKVRT.EffectAck.V1.selectState snapshot = .done :=
  QIKVRT.EffectAck.V1.authorized_implies_recorded_and_recomputed_done _ _ _ _
    (authorized_requires_original_eap _ _ _ _ _ _ accepted)

theorem authorized_checks_are_sound {Subject : Type}
    (value : Subject) (holds : ClauseID → Subject → Prop)
    (pastFuture) (consumer) (snapshot) (state) (claim) (checks)
    (sound : ∀ id, checks id = true → holds id value)
    (accepted : authorize pastFuture consumer snapshot state claim checks = true) :
    ∀ id, holds id value := by
  intro id
  have all : allClauses checks = true := by
    have pair := accepted
    simp only [authorize, Bool.and_eq_true] at pair
    exact pair.2
  exact sound id (all_clauses_requires_every_index checks
    all id)

end QIKVRT.CanonicalClauseAudit.V1
