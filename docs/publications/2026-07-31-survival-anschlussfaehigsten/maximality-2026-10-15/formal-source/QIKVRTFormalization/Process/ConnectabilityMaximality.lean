-- SPDX-License-Identifier: Apache-2.0
-- QIK-VRT architecture and task: Ingolf Lohmann.
-- Formal proof contribution: OpenAI Codex, 2026-10-15.

import QIKVRTFormalization.Process.ConnectabilitySimulation

/-!
# Greatest connectability: the missing instantiation obligation

This extends FIT-003 without changing its viable-trace semantics. A greatest
element is relative to a declared family and a common, semantically aligned
label alphabet. A family of pointed viability simulations is sufficient.

No concrete QIK-VRT implementation, historical inventory of all virtual
realities, physical correspondence, resource budget, or runtime refinement is
instantiated here. In particular, the countermodel is an abstract interface
model, not an experiment on physical reality. It refutes the inference from
one shared viable interface event to greatest connectability.
-/

namespace QIKVRT.V2.ConnectabilityMaximality

open QIKVRT.V2.ConnectabilitySimulation

universe u v w x

/-- A family may contain systems with different state types. -/
structure Model (Label : Type v) where
  State : Type u
  pointed : PointedTransitionSystem State Label

def Dominates
    {TargetState : Type u} {SourceState : Type v} {Label : Type w}
    (target : PointedTransitionSystem TargetState Label)
    (source : PointedTransitionSystem SourceState Label) : Prop :=
  ∀ labels, PointedViableLanguage source labels →
    PointedViableLanguage target labels

/-- Greatest, not merely maximal; ties are permitted. -/
def GreatestIn
    {TargetState : Type u} {Label : Type v} {Index : Type w}
    (target : PointedTransitionSystem TargetState Label)
    (family : Index → Model.{x, v} Label) : Prop :=
  ∀ i, Dominates target (family i).pointed

/-- MAX-001: FIT-003 lifts a family of simulations to a greatest-element proof. -/
theorem MAX001_simulation_family_implies_greatest
    {TargetState : Type u} {Label : Type v} {Index : Type w}
    (target : PointedTransitionSystem TargetState Label)
    (family : Index → Model.{x, v} Label)
    (relation : ∀ i, (family i).State → TargetState → Prop)
    (simulations : ∀ i,
      PointedViabilitySimulation (family i).pointed target (relation i)) :
    GreatestIn target family := by
  intro i
  exact pointed_simulation_implies_viable_language_inclusion (simulations i)

/-- MAX-002: the exact missing coverage obligation is union inclusion. -/
theorem MAX002_greatest_iff_union_inclusion
    {TargetState : Type u} {Label : Type v} {Index : Type w}
    (target : PointedTransitionSystem TargetState Label)
    (family : Index → Model.{x, v} Label) :
    GreatestIn target family ↔
      ∀ labels, (∃ i, PointedViableLanguage (family i).pointed labels) →
        PointedViableLanguage target labels := by
  constructor
  · intro greatest labels member
    rcases member with ⟨i, accepted⟩
    exact greatest i labels accepted
  · intro covers i labels accepted
    exact covers labels ⟨i, accepted⟩

/-- MAX-003: all-finite dominance covers every finite horizon. -/
theorem MAX003_greatest_implies_every_finite_horizon
    {TargetState : Type u} {Label : Type v} {Index : Type w}
    {target : PointedTransitionSystem TargetState Label}
    {family : Index → Model.{x, v} Label}
    (greatest : GreatestIn target family) :
    ∀ (horizon : Nat) i labels, labels.length ≤ horizon →
      PointedViableLanguage (family i).pointed labels →
        PointedViableLanguage target labels := by
  intro _ i labels _ accepted
  exact greatest i labels accepted

/-- MAX-004: one missing viable member trace refutes greatestness. -/
theorem MAX004_missing_trace_refutes_greatest
    {TargetState : Type u} {Label : Type v} {Index : Type w}
    {target : PointedTransitionSystem TargetState Label}
    {family : Index → Model.{x, v} Label}
    (i : Index) (labels : List Label)
    (accepted : PointedViableLanguage (family i).pointed labels)
    (missing : ¬ PointedViableLanguage target labels) :
    ¬ GreatestIn target family := by
  intro greatest
  exact missing (greatest i labels accepted)

/--
MAX-008: a common environment closes the bridge only with both obligations:
all member traces occur in it, and its viable behavior is simulated by target.
The environment's correspondence to physical reality remains external.
-/
theorem MAX008_environment_bridge_implies_greatest
    {TargetState : Type u} {EnvironmentState : Type v}
    {Label : Type w} {Index : Type x}
    (target : PointedTransitionSystem TargetState Label)
    (environment : PointedTransitionSystem EnvironmentState Label)
    (family : Index → Model.{v, w} Label)
    (relation : EnvironmentState → TargetState → Prop)
    (environmentSimulation :
      PointedViabilitySimulation environment target relation)
    (memberCoverage : ∀ i, Dominates environment (family i).pointed) :
    GreatestIn target family := by
  intro i labels accepted
  exact pointed_simulation_implies_viable_language_inclusion
    environmentSimulation labels (memberCoverage i labels accepted)

/-! A constructive one-state, two-label countermodel. -/

def limited : PointedTransitionSystem Unit Bool where
  system := { step := fun _ label _ => label = false, viable := fun _ => True }
  initial := ()
  initialViable := True.intro

def extended : PointedTransitionSystem Unit Bool where
  system := { step := fun _ _ _ => True, viable := fun _ => True }
  initial := ()
  initialViable := True.intro

theorem limited_has_shared_event : PointedViableLanguage limited [false] := by
  exact ⟨(), (), ⟨True.intro, rfl, True.intro⟩, rfl, True.intro⟩

theorem extended_accepts_every_word (labels : List Bool) :
    PointedViableLanguage extended labels := by
  have trace : ∀ labels : List Bool, ViableTrace extended.system () labels () := by
    intro word
    induction word with
    | nil => exact ⟨rfl, True.intro⟩
    | cons label tail ih =>
      exact ⟨(), ⟨True.intro, True.intro, True.intro⟩, ih⟩
  exact ⟨(), trace labels⟩

theorem limited_lacks_second_event :
    ¬ PointedViableLanguage limited [true] := by
  rintro ⟨finalState, next, valid, tail⟩
  have impossible : true = false := valid.transition
  cases impossible

/-- MAX-005: a shared interface event does not imply dominance. -/
theorem MAX005_shared_interface_does_not_imply_greatest :
    PointedViableLanguage limited [false] ∧
    PointedViableLanguage extended [false] ∧
    Dominates extended limited ∧ ¬ Dominates limited extended := by
  refine ⟨limited_has_shared_event, extended_accepts_every_word [false], ?_, ?_⟩
  · intro labels _
    exact extended_accepts_every_word labels
  · intro dominates
    exact limited_lacks_second_event
      (dominates [true] (extended_accepts_every_word [true]))

/-- MAX-006: the explicit universal toy system is greatest in any Bool family. -/
theorem MAX006_extended_greatest_in_any_bool_family
    {Index : Type u} (family : Index → Model.{v, 0} Bool) :
    GreatestIn extended family := by
  intro _ labels _
  exact extended_accepts_every_word labels

def counterexampleFamily : Bool → Model Bool
  | false => { State := Unit, pointed := limited }
  | true => { State := Unit, pointed := extended }

/-- MAX-007: the limited system is not greatest in the explicit two-member family. -/
theorem MAX007_limited_not_greatest_in_counterexample_family :
    ¬ GreatestIn limited counterexampleFamily := by
  apply MAX004_missing_trace_refutes_greatest true [true]
  · exact extended_accepts_every_word [true]
  · exact limited_lacks_second_event

/--
MAX-009: covering every behavior of one declared environment alone still
does not cover a comparison family containing a behavior outside it.
-/
theorem MAX009_environment_inclusion_alone_insufficient :
    Dominates limited limited ∧
    ¬ GreatestIn limited counterexampleFamily := by
  refine ⟨?_, MAX007_limited_not_greatest_in_counterexample_family⟩
  intro _ accepted
  exact accepted

#print axioms MAX001_simulation_family_implies_greatest
#print axioms MAX002_greatest_iff_union_inclusion
#print axioms MAX003_greatest_implies_every_finite_horizon
#print axioms MAX004_missing_trace_refutes_greatest
#print axioms MAX005_shared_interface_does_not_imply_greatest
#print axioms MAX006_extended_greatest_in_any_bool_family
#print axioms MAX007_limited_not_greatest_in_counterexample_family
#print axioms MAX008_environment_bridge_implies_greatest
#print axioms MAX009_environment_inclusion_alone_insufficient

end QIKVRT.V2.ConnectabilityMaximality
