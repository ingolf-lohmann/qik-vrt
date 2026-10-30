-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTUniversalOntology.Core

namespace QIKVRT.UniversalOntology
universe u

/-!
## Ontological origin of difference

"Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts."
Here "beginning" means ontological priority, not first physical time.  The
formal statement is deliberately bounded: determinate reality is represented
by the existence of at least one distinction.  A no-difference universe makes
all states propositionally equal and therefore excludes both determinate
reality and an information witness.
-/

def DeterminateReality (α : Type u) : Prop :=
  Nonempty (Distinction α)

def NoDifference (α : Type u) : Prop :=
  ∀ left right : α, left = right

theorem determinateReality_requires_difference
    {α : Type u} (h : DeterminateReality α) :
    ∃ left right : α, left ≠ right := by
  rcases h with ⟨difference⟩
  exact ⟨difference.left, difference.right, difference.different⟩

theorem noDifference_excludes_determinateReality
    {α : Type u} (h : NoDifference α) :
    ¬ DeterminateReality α := by
  intro determinate
  rcases determinate with ⟨difference⟩
  exact difference.different (h difference.left difference.right)

theorem noDifference_excludes_information
    {α : Type u} (h : NoDifference α) :
    ¬ Nonempty (InformationWitness α) := by
  intro information
  rcases information with ⟨witness⟩
  exact witness.source.different
    (h witness.source.left witness.source.right)

def ontologicalOriginChecked :
    CheckedClaim "UO-THM-026"
      (∀ {α : Type u}, DeterminateReality α → ∃ left right : α, left ≠ right) where
  checked := by
    intro α h
    exact determinateReality_requires_difference h

def noDifferenceBoundaryChecked :
    CheckedClaim "UO-THM-027"
      (∀ {α : Type u}, NoDifference α → ¬ DeterminateReality α) where
  checked := by
    intro α h
    exact noDifference_excludes_determinateReality h

def noDifferenceInformationChecked :
    CheckedClaim "UO-THM-028"
      (∀ {α : Type u}, NoDifference α → ¬ Nonempty (InformationWitness α)) where
  checked := by
    intro α h
    exact noDifference_excludes_information h

end QIKVRT.UniversalOntology
