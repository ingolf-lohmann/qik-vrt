-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ingolf Lohmann.

import QIKVRTEffectAck.CausalDistance
import QIKVRTEffectAck.CanonicalTemporalMemory
import QIKVRTEffectAck.Safety

/-!
# Causal distance attached to the original dual-canonical memory and EAP

Only explicitly SELECTED confirmed links enter the graph. The fields below
are model-level propositions: their association with real archives, hashes,
events, authenticated principals and independent observations remains an
external evidence obligation. There is no axiom asserting those real effects.
The original temporal memory and authorization definitions are imported,
not copied or redefined. No biological/physical universality is inferred.
-/

namespace QIKVRT.CausalDistance.TemporalBridge.V1

open QIKVRT.CausalDistance.V1
open QIKVRT.CanonicalTemporalMemory.V1
open QIKVRT.EffectAck.V1

structure ConfirmedLink where
  prospective : QIKVRT.CanonicalTemporalMemory.V1.ProspectiveRelease
  receipt : QIKVRT.CanonicalTemporalMemory.V1.EffectReceipt
  checks : QIKVRT.EffectAck.V1.ConsumerChecks
  snapshot : QIKVRT.EffectAck.V1.Snapshot
  recordState : QIKVRT.EffectAck.V1.State
  ordinaryClaim : Bool
  closed : QIKVRT.CanonicalTemporalMemory.V1.reciprocalClosure prospective receipt = true
  protocolBinding : prospective.effectAckDone =
    QIKVRT.EffectAck.V1.authorizeOrdinaryRelease checks snapshot recordState ordinaryClaim

theorem confirmed_requires_original_authorization (link : ConfirmedLink) :
    QIKVRT.EffectAck.V1.authorizeOrdinaryRelease link.checks link.snapshot
      link.recordState link.ordinaryClaim = true := by
  have released := ((QIKVRT.CanonicalTemporalMemory.V1.reciprocal_closure_eq_true_iff _ _).mp link.closed).1
  have ack := QIKVRT.CanonicalTemporalMemory.V1.release_requires_effect_ack _ released
  rw [link.protocolBinding] at ack
  exact ack

theorem confirmed_requires_recomputed_done (link : ConfirmedLink) :
    link.recordState = .done ∧ QIKVRT.EffectAck.V1.selectState link.snapshot = .done :=
  QIKVRT.EffectAck.V1.authorized_implies_recorded_and_recomputed_done _ _ _ _
    (confirmed_requires_original_authorization link)

theorem confirmed_requires_responsible_owner (link : ConfirmedLink) :
    link.snapshot.responsibilityAssigned = true ∧
    link.snapshot.responsibilityOwnerPresent = true := by
  have core := QIKVRT.EffectAck.V1.selectedDone_implies_coreDone _
    (confirmed_requires_recomputed_done link).2
  rcases core with ⟨_, _, _, _, _, _, _, _, assigned, owner, _⟩
  exact ⟨assigned, owner⟩

theorem confirmed_requires_past_future_and_observation (link : ConfirmedLink) :
    QIKVRT.CanonicalTemporalMemory.V1.pastValid link.prospective = true ∧
    QIKVRT.CanonicalTemporalMemory.V1.futureValid link.prospective = true ∧
    link.prospective.causeId = link.receipt.causeId ∧
    link.prospective.anticipatedEffectId = link.receipt.observedEffectId ∧
    link.receipt.effectObserved = true ∧ link.receipt.receiptBound = true := by
  have closure := (QIKVRT.CanonicalTemporalMemory.V1.reciprocal_closure_eq_true_iff _ _).mp link.closed
  have ids := (QIKVRT.CanonicalTemporalMemory.V1.identifier_bound_eq_true_iff _ _).mp closure.2.1
  exact ⟨QIKVRT.CanonicalTemporalMemory.V1.release_requires_valid_past _ closure.1,
    QIKVRT.CanonicalTemporalMemory.V1.release_requires_valid_future _ closure.1,
    ids.1, ids.2, closure.2.2.1, closure.2.2.2⟩

/-- Unit cost counts a selected, confirmed cause/effect link. This does not
equate protocol hops to time, spatial length, probability or energy. -/
def confirmedGraph (links : List ConfirmedLink) : Graph Nat where
  edge a b n := n = 1 ∧ ∃ link, link ∈ links ∧
    link.prospective.causeId = a ∧ link.prospective.anticipatedEffectId = b
  positive h := by rcases h with ⟨rfl, _⟩; decide

theorem selected_confirmation_is_one_step (links : List ConfirmedLink)
    (link : ConfirmedLink) (selected : link ∈ links) :
    Path (confirmedGraph links) link.prospective.causeId
      link.prospective.anticipatedEffectId 1 := by
  have edge : (confirmedGraph links).edge link.prospective.causeId
      link.prospective.anticipatedEffectId 1 := ⟨rfl, link, selected, rfl, rfl⟩
  exact Path.snoc (Path.refl _) edge

theorem distinct_selected_confirmation_distance (links : List ConfirmedLink)
    (link : ConfirmedLink) (selected : link ∈ links)
    (distinct : link.prospective.causeId ≠ link.prospective.anticipatedEffectId) :
    distance (confirmedGraph links) link.prospective.causeId
      link.prospective.anticipatedEffectId = some 1 := by
  apply (distance_some_iff _ _ _ _).mpr
  refine ⟨selected_confirmation_is_one_step links link selected, ?_⟩
  intro n p
  by_cases zero : n = 0
  · exact False.elim (distinct (zero_path_endpoints p zero))
  · omega

theorem retrospective_confirmation_distance (links : List ConfirmedLink)
    (link : ConfirmedLink) (selected : link ∈ links)
    (distinct : link.prospective.causeId ≠ link.prospective.anticipatedEffectId) :
    distance (reverse (confirmedGraph links)) link.prospective.anticipatedEffectId
      link.prospective.causeId = some 1 := by
  rw [reverse_distance]
  exact distinct_selected_confirmation_distance links link selected distinct

theorem future_representation_preserves_original_past
    (past left right : QIKVRT.CanonicalTemporalMemory.V1.CanonicalArchive) :
    QIKVRT.CanonicalTemporalMemory.V1.pastProjection past left = QIKVRT.CanonicalTemporalMemory.V1.pastProjection past right :=
  QIKVRT.CanonicalTemporalMemory.V1.future_boundary_does_not_overwrite_past past left right

end QIKVRT.CausalDistance.TemporalBridge.V1
