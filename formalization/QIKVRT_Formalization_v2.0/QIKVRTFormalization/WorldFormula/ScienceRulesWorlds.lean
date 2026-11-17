import QIKVRTFormalization.WorldFormula.Relations

/-!
# Science is, fiction not <=> science rules worlds

This is an *epistemic admission* formalization, not a physical law.
"Fiction" here denotes a claim lacking qualification for the specified world
state; it does not denote literature, imagination or mathematical conjecture.
The `↔` below is a theorem about two independently stated forms of the same
soundness policy (exclusion of unsupported admission vs. evidence obligation
for admitted claims), NOT an unconditional theorem that every operational
system already obeys that policy or that science causes physical laws.

Existing `PhysicallyQualified` keeps formal derivation, artifact binding,
reference, operationalization, supporting evidence, prediction, limit recovery
and independent validation separate. World-specific satisfaction is additional.
-/

namespace QIKVRT.V2.WorldFormula

universe u v w

variable {FormalState : Type u} {Observable : Type v} {Evidence : Type w}

/-- A claim has the existing full physical-qualification evidence and is
satisfied in the designated model/world state. This is a logical predicate;
its truth about any real-world claim requires external evidence. -/
def EvidenceAdmissible
    (relations : EpistemicRelations FormalState Observable Evidence)
    (state : FormalState) (claim : FormalClaim) : Prop :=
  PhysicallyQualified relations claim ∧ relations.satisfies state claim

/-- The negative form: a world-claim without the required qualification
cannot be admitted. `fiction` means *unqualified claim* in this model. -/
def ScienceIsFictionNot
    (relations : EpistemicRelations FormalState Observable Evidence)
    (admitted : FormalState → FormalClaim → Prop) : Prop :=
  ∀ state claim, ¬ EvidenceAdmissible relations state claim → ¬ admitted state claim

/-- The positive form: every admitted world-claim must carry the required
qualification, including model/world satisfaction. -/
def ScienceRulesWorlds
    (relations : EpistemicRelations FormalState Observable Evidence)
    (admitted : FormalState → FormalClaim → Prop) : Prop :=
  ∀ state claim, admitted state claim → EvidenceAdmissible relations state claim

/-- The exact equivalence of negative and positive gate policies in classical
logic. No empirical premises, ad-hoc axioms, `sorry`, or `admit` are introduced.
The theorem does NOT assert that an arbitrary gate satisfies either property. -/
theorem science_is_fiction_not_iff_science_rules_worlds
    (relations : EpistemicRelations FormalState Observable Evidence)
    (admitted : FormalState → FormalClaim → Prop) :
    ScienceIsFictionNot relations admitted ↔ ScienceRulesWorlds relations admitted := by
  classical
  constructor
  · intro exclusion state claim hAdmitted
    by_contra hNotQualified
    exact (exclusion state claim hNotQualified) hAdmitted
  · intro sound state claim hNotQualified hAdmitted
    exact hNotQualified (sound state claim hAdmitted)

/-- A reusable strict admission policy; downstream components can import
this gate without changing the archived manuscript or previous claim ledger. -/
def VerifiedGate
    (relations : EpistemicRelations FormalState Observable Evidence) :
    FormalState → FormalClaim → Prop :=
  fun state claim => EvidenceAdmissible relations state claim

/-- A system *using* this strict gate obeys the policy by construction.
This does not claim that an actual EAP consumer uses the gate. -/
theorem verified_gate_science_rules_worlds
    (relations : EpistemicRelations FormalState Observable Evidence) :
    ScienceRulesWorlds relations (VerifiedGate relations) := by
  intro state claim hAdmitted
  exact hAdmitted

/-- Downstream model-level consequence of the evidence-bearing admission rule. -/
theorem science_rules_worlds_implies_model_establishment
    (relations : EpistemicRelations FormalState Observable Evidence)
    (admitted : FormalState → FormalClaim → Prop)
    (sound : ScienceRulesWorlds relations admitted)
    (state : FormalState) (claim : FormalClaim)
    (hAdmitted : admitted state claim) :
    ModelEstablished relations state claim := by
  rcases sound state claim hAdmitted with ⟨qualified, satisfied⟩
  exact ⟨physicallyQualified_implies_formallyEstablished qualified, satisfied⟩

/-- The stronger admissibility rule rejects an unqualified claim. -/
theorem science_rules_worlds_rejects_unsupported
    (relations : EpistemicRelations FormalState Observable Evidence)
    (admitted : FormalState → FormalClaim → Prop)
    (sound : ScienceRulesWorlds relations admitted)
    (state : FormalState) (claim : FormalClaim)
    (hMissing : ¬ EvidenceAdmissible relations state claim) :
    ¬ admitted state claim := by
  intro hAdmitted
  exact hMissing (sound state claim hAdmitted)

/-- Negative control: a gate admitting every claim is not universally sound.
The already existing `formalOnlyRelations` witness has a trivially established
claim, but reference binding and empirical qualification are deliberately absent. -/
def UnrestrictedGate : Unit → FormalClaim → Prop := fun _ _ => True

theorem unrestricted_admission_is_not_scientific :
    ¬ ScienceRulesWorlds formalOnlyRelations UnrestrictedGate := by
  intro supposedlySound
  have qualified : PhysicallyQualified formalOnlyRelations witnessClaim :=
    (supposedlySound () witnessClaim (by trivial)).1
  have missingReference : formalOnlyRelations.referenceBound witnessClaim :=
    physicallyQualified_implies_referenceBound qualified
  exact missingReference

end QIKVRT.V2.WorldFormula
