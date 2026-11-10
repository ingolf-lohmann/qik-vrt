import QIKVRTFormalization.Decision.ObservationSufficiency
import QIKVRTFormalization.WorldFormula.Relations

/-!
# Cognitive effect-bound learning — formal v1 candidate

A bounded bridge to the existing observation-sufficiency and epistemic round-trip
modules. Statements are about an abstract model. A Boolean in this model is NOT
a native receipt, authenticated observer, deployed writer fence, or physical
readback; only independently validated runtime evidence may provide those facts.
This model does not prove comparative cognitive superiority or a physical theory.
-/

namespace QIKVRT.V2.CognitiveEffectLearning

universe u v w

structure GateEvidence where
  observationBound : Bool
  modelBound : Bool
  decisionAuthorized : Bool
  receiptAuthenticated : Bool
  independentEffectReadback : Bool
  durableJournal : Bool
  writerFenced : Bool
  deriving DecidableEq, Repr

/-- Effect eligibility is a conjunction of individually required gate facts. -/
def AcceptedEffect (e : GateEvidence) : Prop :=
  e.decisionAuthorized = true ∧
  e.receiptAuthenticated = true ∧
  e.independentEffectReadback = true ∧
  e.durableJournal = true ∧
  e.writerFenced = true

/-- Learning from a claimed effect additionally requires a bound observation and model. -/
def AdmissibleLearning (e : GateEvidence) : Prop :=
  e.observationBound = true ∧ e.modelBound = true ∧ AcceptedEffect e

/-- No learning from a claimed effect without the accepted effect predicates. -/
theorem learning_requires_accepted_effect (e : GateEvidence)
    (h : AdmissibleLearning e) : AcceptedEffect e := h.2.2

/-- Missing independent effect observation is fail-closed. -/
theorem missing_independent_readback_blocks_learning (e : GateEvidence)
    (hMissing : e.independentEffectReadback = false) :
    ¬ AdmissibleLearning e := by
  intro hLearning
  have hObserved : e.independentEffectReadback = true := hLearning.2.2.2.2.1
  rw [hMissing] at hObserved
  cases hObserved

/-- Missing writer fencing is fail-closed, even if other booleans are true. -/
theorem missing_writer_fence_blocks_learning (e : GateEvidence)
    (hMissing : e.writerFenced = false) :
    ¬ AdmissibleLearning e := by
  intro hLearning
  have hFenced : e.writerFenced = true := hLearning.2.2.2.2.2
  rw [hMissing] at hFenced
  cases hFenced

/-- A model without a bound observation cannot count as learned experience. -/
theorem missing_observation_blocks_learning (e : GateEvidence)
    (hMissing : e.observationBound = false) :
    ¬ AdmissibleLearning e := by
  intro hLearning
  have hBound : e.observationBound = true := hLearning.1
  rw [hMissing] at hBound
  cases hBound

/-- The existing massive kernel supplies the observation/action factorization law. -/
theorem correct_choice_requires_observation_sufficiency
    {History : Type u} {Observation : Type v} {Action : Type w}
    (observe : History → Observation) (correct : History → Action)
    (selector : Observation → Action)
    (hCorrect : ∀ history, selector (observe history) = correct history) :
    QIKVRT.V2.DecisionSufficiency.ObservationSufficient observe correct :=
  QIKVRT.V2.DecisionSufficiency.factorization_implies_sufficiency
    observe correct selector hCorrect

/-- Imported countermodel: mixed observation fibers bar universal deterministic action. -/
theorem indistinguishable_histories_block_correct_choice
    {History : Type u} {Observation : Type v} {Action : Type w}
    (observe : History → Observation) (correct : History → Action)
    (h₁ h₂ : History)
    (sameObservation : observe h₁ = observe h₂)
    (differentAction : correct h₁ ≠ correct h₂) :
    ¬ ∃ selector : Observation → Action,
      ∀ history, selector (observe history) = correct history :=
  QIKVRT.V2.DecisionSufficiency.impossibility_of_mixed_fiber
    observe correct h₁ h₂ sameObservation differentAction

/-- Connects the bound to the pre-existing epistemic round-trip successor kernel. -/
theorem cognitive_stage_has_declared_successor
    (stage : QIKVRT.V2.WorldFormula.EpistemicStage) :
    ∃ next, QIKVRT.V2.WorldFormula.RoundTripStep stage next :=
  QIKVRT.V2.WorldFormula.every_stage_has_a_successor stage

end QIKVRT.V2.CognitiveEffectLearning
