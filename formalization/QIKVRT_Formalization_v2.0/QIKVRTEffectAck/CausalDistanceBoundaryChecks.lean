-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ingolf Lohmann.

import QIKVRTEffectAck.CausalDistanceTemporalBridge

namespace QIKVRT.CausalDistance.BoundaryChecks.V1

open QIKVRT.CausalDistance.V1

def oneWay : Graph Bool where
  edge a b n := a = false ∧ b = true ∧ n = 2
  positive h := by rcases h with ⟨_, _, rfl⟩; decide

theorem forward_distance_two : distance oneWay false true = some 2 := by
  apply (distance_some_iff _ _ _ _).mpr
  have edge : oneWay.edge false true 2 := ⟨rfl, rfl, rfl⟩
  refine ⟨Path.snoc (Path.refl _) edge, ?_⟩
  intro n p
  cases p with
  | snoc p e => rcases e with ⟨_, _, rfl⟩; omega

theorem backward_distance_infinite : distance oneWay true false = none := by
  apply (distance_none_iff _ _ _).mpr
  intro ⟨n, p⟩
  cases p with
  | snoc p e => have bad : false = true := e.2.1; contradiction

theorem directed_distance_can_be_asymmetric :
    distance oneWay false true ≠ distance oneWay true false := by
  rw [forward_distance_two, backward_distance_infinite]
  decide

theorem undirected_projection_can_shorten_reverse_distance :
    distance (undirected oneWay) true false = some 2 := by
  rw [undirected_distance_symmetric]
  apply (distance_some_iff _ _ _ _).mpr
  have edge : (undirected oneWay).edge false true 2 := Or.inl ⟨rfl, rfl, rfl⟩
  refine ⟨Path.snoc (Path.refl _) edge, ?_⟩
  intro n p
  cases p with
  | snoc p e =>
    rcases e with e | e <;> rcases e with ⟨_, _, rfl⟩ <;> omega

theorem finite_distance_does_not_certify_release :
    distance oneWay false true = some 2 ∧
    QIKVRT.CanonicalTemporalMemory.V1.release
      QIKVRT.CanonicalTemporalMemory.V1.futureRejectedCandidate = false := by
  exact ⟨forward_distance_two, by decide⟩

theorem observed_is_not_an_anticipated_boundary :
    QIKVRT.CanonicalTemporalMemory.V1.futureValid
      { QIKVRT.CanonicalTemporalMemory.V1.admittedCandidate with
        futureArchive := QIKVRT.CanonicalTemporalMemory.V1.validPast } = false := by
  decide

/-- A kernel-checked inhabitant prevents a vacuous bridge over an empty model.
It is the original article's 7 -> 11 MODEL example, not a live effect receipt. -/
def admittedSnapshot : QIKVRT.EffectAck.V1.Snapshot where
  transportAck := true
  inputIdAvailable := true
  inputHashIsSha256Identifier := true
  predecessorInvalid := false
  deadlineExceeded := false
  integrityFailure := false
  originChecked := true
  contextChecked := true
  semanticsReconstructed := true
  effectAnticipated := true
  riskClassified := true
  riskKnown := true
  responsibilityAssigned := true
  responsibilityOwnerPresent := true
  connectionDecided := true
  policyAllowsRelease := true
  noOpenQuestions := true
  noNextRequiredChecks := true
  requiredEvidenceComplete := true
  connectionDecision := .release

def admittedModelLink : QIKVRT.CausalDistance.TemporalBridge.V1.ConfirmedLink where
  prospective := QIKVRT.CanonicalTemporalMemory.V1.admittedCandidate
  receipt := ⟨7, 11, true, true⟩
  checks := QIKVRT.EffectAck.V1.fullyValidConsumerChecks
  snapshot := admittedSnapshot
  recordState := .done
  ordinaryClaim := true
  closed := by decide
  protocolBinding := by decide

theorem inhabited_bridge_distance_one :
    distance (QIKVRT.CausalDistance.TemporalBridge.V1.confirmedGraph [admittedModelLink])
      7 11 = some 1 := by
  exact QIKVRT.CausalDistance.TemporalBridge.V1.distinct_selected_confirmation_distance
    [admittedModelLink] admittedModelLink (by simp) (by decide)

theorem missing_responsibility_never_authorized :
    QIKVRT.EffectAck.V1.authorizeOrdinaryRelease
      QIKVRT.EffectAck.V1.fullyValidConsumerChecks
      { admittedSnapshot with responsibilityAssigned := false } .done true = false := by
  decide

end QIKVRT.CausalDistance.BoundaryChecks.V1
