-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.InformationBoundary
import QIKVRTEffectAck.StorageIntegrity
import QIKVRTEffectAck.CanonicalTemporalMemory

/-!
# Mathematical supplement to the unchanged 27-page Raumzeit EN/DE manuscript

Section 3 A: unique inversion ON THE IMAGE is stated relationally. This needs
neither a choice axiom nor a default inhabitant for an empty source type. It
does not construct an executable inverse for an arbitrary injective function.
Section 3 B: retaining the predecessor makes any step injective.
Section 3 C: only the observation-fibre / information-loss part is formalized.
Real-valued conditional Shannon entropy, its probability assumptions and the
physical literature remain separately source-bound.

All functions below have specified inputs. Unknown physical inputs, operating
system schedules, a compiler, HTTP delivery and consciousness are not proved
correct by giving them a function type.
-/
namespace QIKVRT.ReconstructibleVirtuality.V1

open QIKVRT.EffectAck.V1
open QIKVRT.StorageIntegrity.V1 (CanonicalCodec)

universe u v w

def UniquePredecessorsOnImage {Source : Type u} {Target : Type v}
    (step : Source → Target) : Prop :=
  ∀ target, (∃ source, step source = target) →
    ∃ source, step source = target ∧
      ∀ other, step other = target → other = source

theorem injective_iff_unique_predecessors_on_image
    {Source : Type u} {Target : Type v} (step : Source → Target) :
    Injective step ↔ UniquePredecessorsOnImage step := by
  constructor
  · intro injective target reached
    obtain ⟨source, equal⟩ := reached
    exact ⟨source, equal, fun other same => injective (same.trans equal.symm)⟩
  · intro unique left right equal
    obtain ⟨source, _, predecessor⟩ := unique (step right) ⟨right, rfl⟩
    exact (predecessor left equal).trans (predecessor right rfl).symm

theorem inverse_on_image_is_unique {Source : Type u} {Target : Type v}
    (step : Source → Target) (injective : Injective step)
    (target : Target) (left right : Source)
    (leftReaches : step left = target) (rightReaches : step right = target) :
    left = right := injective (leftReaches.trans rightReaches.symm)

def withHistory {Source : Type u} {Target : Type v}
    (step : Source → Target) (source : Source) : Target × Source :=
  (step source, source)

theorem history_projection_restores {Source : Type u} {Target : Type v}
    (step : Source → Target) (source : Source) :
    (withHistory step source).2 = source := rfl

theorem history_extension_is_injective {Source : Type u} {Target : Type v}
    (step : Source → Target) : Injective (withHistory step) := by
  intro left right equal
  exact congrArg Prod.snd equal

theorem history_has_unique_predecessors {Source : Type u} {Target : Type v}
    (step : Source → Target) : UniquePredecessorsOnImage (withHistory step) :=
  (injective_iff_unique_predecessors_on_image _).1 (history_extension_is_injective step)

theorem encoded_history_restores_predecessor {Source Target Wire : Type}
    (codec : CanonicalCodec (Target × Source) Wire)
    (step : Source → Target) (source : Source) :
    (codec.decode (codec.encode (withHistory step source))).map Prod.snd = some source := by
  rw [codec.roundTrip]
  rfl

def replay {State : Type u} {Input : Type v}
    (step : State → Input → State) (start : State) : List Input → State
  | [] => start
  | input :: rest => replay step (step start input) rest

theorem replay_append {State : Type u} {Input : Type v}
    (step : State → Input → State) (start : State) (first rest : List Input) :
    replay step start (first ++ rest) = replay step (replay step start first) rest := by
  induction first generalizing start with
  | nil => rfl
  | cons input inputs inductionHypothesis =>
      exact inductionHypothesis (step start input)

theorem complete_recording_replays_identically {State : Type u} {Input : Type v}
    (step : State → Input → State) (left right : State) (first second : List Input)
    (sameStart : left = right) (sameInputs : first = second) :
    replay step left first = replay step right second := by
  cases sameStart
  cases sameInputs
  rfl

-- The erasure counterexample in Section 2 is an actual deterministic function.
def eraseBit (_ : Bool) : Bool := false

theorem deterministic_erasure_is_not_injective : ¬ Injective eraseBit := by
  intro injective
  have impossible : (false : Bool) = true := injective rfl
  cases impossible

theorem deterministic_erasure_has_no_exact_decoder :
    ¬ ExactHistoricalReconstruction eraseBit :=
  noninjectiveObservation_blocksExactReconstruction eraseBit
    deterministic_erasure_is_not_injective

def Ambiguous {Source : Type u} {Observation : Type v}
    (possible : Source → Prop) (observe : Source → Observation) : Prop :=
  ∃ left right, possible left ∧ possible right ∧ left ≠ right ∧ observe left = observe right

theorem ambiguous_observation_blocks_exact_estimator
    {Source : Type u} {Observation : Type v}
    (possible : Source → Prop) (observe : Source → Observation)
    (ambiguous : Ambiguous possible observe) :
    ¬ ∃ estimate : Observation → Source, ∀ source,
      possible source → estimate (observe source) = source := by
  obtain ⟨left, right, leftPossible, rightPossible, distinct, same⟩ := ambiguous
  rintro ⟨estimate, exactEstimate⟩
  exact distinct ((exactEstimate left leftPossible).symm.trans
    ((congrArg estimate same).trans (exactEstimate right rightPossible)))

theorem deterministic_world_can_have_ambiguous_observation :
    ∃ step : Bool → Bool, ∃ observe : Bool → Unit,
      Injective step ∧ Ambiguous (fun _ => True) observe := by
  exact ⟨id, fun _ => (), (by intro left right equal; exact equal),
    false, true, trivial, trivial, Bool.false_ne_true, rfl⟩

-- Additional information refines compatible-state sets; this is NOT a proof
-- of a general Shannon entropy inequality without a probability model.
theorem refined_observation_preserves_compatibility
    {Source : Type u} {Coarse : Type v} {Fine : Type w}
    (coarse : Source → Coarse) (fine : Source → Fine) (forget : Fine → Coarse)
    (refinement : ∀ source, forget (fine source) = coarse source)
    (left right : Source) (sameFine : fine left = fine right) :
    coarse left = coarse right := by
  exact (refinement left).symm.trans ((congrArg forget sameFine).trans (refinement right))

def coinWords : Nat → List (List Bool)
  | 0 => [[]]
  | n + 1 => (coinWords n).map (false :: ·) ++ (coinWords n).map (true :: ·)

def heads (word : List Bool) : Nat := (word.filter id).length

theorem coinWords_membership (n : Nat) (word : List Bool) :
    word ∈ coinWords n ↔ word.length = n := by
  induction n generalizing word with
  | zero => simp [coinWords]
  | succ n ih =>
      cases word with
      | nil => simp [coinWords]
      | cons bit rest => cases bit <;> simp [coinWords, List.mem_map, ih]

theorem coinWords_length (n : Nat) : (coinWords n).length = 2 ^ n := by
  induction n with
  | zero => rfl
  | succ n ih => simp [coinWords, ih, Nat.pow_succ, Nat.mul_two]

-- Section 5: a finite counting witness, not a thermodynamic time-arrow theorem.
theorem ten_coin_microstates : (coinWords 10).length = 1024 := by
  rw [coinWords_length]

set_option maxRecDepth 65536 in
set_option maxHeartbeats 2000000 in
theorem ten_coin_five_heads :
    ((coinWords 10).filter (fun word => heads word == 5)).length = 252 := by decide

theorem encoded_history_and_effect_readback {Source Target Wire : Type}
    (codec : CanonicalCodec (Target × Source) Wire)
    (step : Source → Target) (source : Source)
    (prospective : QIKVRT.CanonicalTemporalMemory.V1.ProspectiveRelease)
    (receipt : QIKVRT.CanonicalTemporalMemory.V1.EffectReceipt)
    (closed : QIKVRT.CanonicalTemporalMemory.V1.reciprocalClosure prospective receipt = true) :
    (codec.decode (codec.encode (withHistory step source))).map Prod.snd = some source ∧
    prospective.causeId = receipt.causeId ∧
    prospective.anticipatedEffectId = receipt.observedEffectId ∧
    receipt.effectObserved = true := by
  have bound := QIKVRT.CanonicalTemporalMemory.V1.reciprocal_closure_requires_cause_and_effect
    prospective receipt closed
  exact ⟨encoded_history_restores_predecessor codec step source,
    bound.2.2.1, bound.2.2.2.1, bound.2.2.2.2⟩

end QIKVRT.ReconstructibleVirtuality.V1
