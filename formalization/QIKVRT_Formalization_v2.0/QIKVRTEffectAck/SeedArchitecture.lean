-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann. Formalization: OpenAI Codex.
import QIKVRTEffectAck.StorageIntegrity
import QIKVRTFormalization.Process.ConnectabilitySimulation
import QIKVRTFormalization.Physics.EmpiricalBridge

/-!
# Seed / metatransistor architecture: finite compositional closure
This extends the EXISTING codec, viable-trace simulation and empirical-bridge
contracts. It specifies no new byte format, physical transistor or Docker ABI.
A deterministic step fixes the result GIVEN its state and input trace.
Concrete codec refinement, hardware realization, available memory, operating
system/container support and thermodynamic evidence remain explicit duties.
No theorem here establishes physical superdeterminism or unconditional
correctness of every future program, chip or environment.
-/
namespace QIKVRT.SeedArchitecture.V1

open QIKVRT.StorageIntegrity.V1
open QIKVRT.V2.ConnectabilitySimulation


/-- Sequential composition of two ALREADY proved canonical codecs. -/
def composeCodec {A : Type} {B : Type} {C : Type}
    (first : CanonicalCodec A B) (second : CanonicalCodec B C) :
    CanonicalCodec A C where
  encode a := second.encode (first.encode a)
  decode c := (second.decode c).bind first.decode
  roundTrip a := by
    simp [second.roundTrip, first.roundTrip]

theorem composed_codec_lossless {A : Type} {B : Type} {C : Type}
    (first : CanonicalCodec A B) (second : CanonicalCodec B C) (a : A) :
    (composeCodec first second).decode ((composeCodec first second).encode a) =
      some a :=
  (composeCodec first second).roundTrip a

/-- Model-level lifting of the existing codec, NOT another wire format. -/
def decodeAll {A : Type} {B : Type} (decode : B → Option A) :
    List B → Option (List A)
  | [] => some []
  | b :: bs => do
      let a ← decode b
      let rest ← decodeAll decode bs
      pure (a :: rest)

theorem decodeAll_map_encode {A : Type} {B : Type}
    (codec : CanonicalCodec A B) (values : List A) :
    decodeAll codec.decode (values.map codec.encode) = some values := by
  induction values with
  | nil => rfl
  | cons a rest ih =>
      simp [decodeAll, codec.roundTrip, ih]

theorem failed_part_prevents_complete_decode {A : Type} {B : Type}
    (decode : B → Option A) (initialPart suffix : List B) (bad : B)
    (rejected : decode bad = none) :
    decodeAll decode (initialPart ++ bad :: suffix) = none := by
  induction initialPart with
  | nil => simp [decodeAll, rejected]
  | cons b rest ih =>
      simp [decodeAll, ih]

def execute {S : Type} {Input : Type} (step : S → Input → S) :
    S → List Input → S
  | state, [] => state
  | state, input :: inputs => execute step (step state input) inputs

theorem execute_append {S : Type} {Input : Type}
    (step : S → Input → S) (state : S) (before after : List Input) :
    execute step state (before ++ after) =
      execute step (execute step state before) after := by
  induction before generalizing state with
  | nil => rfl
  | cons input rest ih => exact ih (step state input)

/-- Checkpoint/restart at ANY finite trace boundary gives the same final state. -/
theorem checkpoint_restart_exact {S : Type} {Input : Type} {Wire : Type}
    (codec : CanonicalCodec S Wire) (step : S → Input → S)
    (seed : S) (before after : List Input) :
    (codec.decode (codec.encode (execute step seed before))).map
      (fun restored => execute step restored after) =
        some (execute step seed (before ++ after)) := by
  rw [codec.roundTrip]
  rw [execute_append]
  rfl

theorem execute_preserves {S : Type} {Input : Type}
    (step : S → Input → S) (invariant : S → Prop)
    (preserves : ∀ s i, invariant s → invariant (step s i))
    (seed : S) (seedValid : invariant seed) (inputs : List Input) :
    invariant (execute step seed inputs) := by
  induction inputs generalizing seed with
  | nil => exact seedValid
  | cons input rest ih =>
      exact ih (step seed input) (preserves seed input seedValid)

def deterministicSystem {S : Type} {Input : Type}
    (step : S → Input → S) (invariant : S → Prop) :
    TypedTransitionSystem S Input where
  step source input target := target = step source input
  viable := invariant

theorem deterministic_step_unique {S : Type} {Input : Type}
    (step : S → Input → S) (invariant : S → Prop)
    (source left right : S) (input : Input)
    (hl : (deterministicSystem step invariant).step source input left)
    (hr : (deterministicSystem step invariant).step source input right) :
    left = right := hl.trans hr.symm

theorem execute_is_viable_trace {S : Type} {Input : Type}
    (step : S → Input → S) (invariant : S → Prop)
    (preserves : ∀ s i, invariant s → invariant (step s i))
    (seed : S) (seedValid : invariant seed) (inputs : List Input) :
    ViableTrace (deterministicSystem step invariant)
      seed inputs (execute step seed inputs) := by
  induction inputs generalizing seed with
  | nil => exact ⟨rfl, seedValid⟩
  | cons input rest ih =>
      have nextValid := preserves seed input seedValid
      exact ⟨step seed input, ⟨seedValid, rfl, nextValid⟩,
        ih (step seed input) nextValid⟩

/-- Reuses FIT-002's proved simulation; the hardware relation must be supplied. -/
theorem architecture_closure
    {S : Type} {Input : Type} {Target : Type} {Wire : Type}
    (step : S → Input → S) (invariant : S → Prop)
    (preserves : ∀ s i, invariant s → invariant (step s i))
    (codec : CanonicalCodec S Wire)
    (target : TypedTransitionSystem Target Input)
    (relation : S → Target → Prop)
    (simulation : ViabilitySimulation (deterministicSystem step invariant)
      target relation)
    (seed : S) (targetSeed : Target) (seedValid : invariant seed)
    (seedRelated : relation seed targetSeed) (inputs : List Input) :
    ∃ targetFinal,
      ViableTrace target targetSeed inputs targetFinal ∧
      relation (execute step seed inputs) targetFinal ∧
      invariant (execute step seed inputs) ∧
      target.viable targetFinal ∧
      codec.decode (codec.encode (execute step seed inputs)) =
        some (execute step seed inputs) := by
  have sourceTrace := execute_is_viable_trace
    step invariant preserves seed seedValid inputs
  obtain ⟨targetFinal, targetTrace, finalRelated⟩ :=
    simulation_preserves_viable_trace simulation
      seed (execute step seed inputs) targetSeed inputs seedRelated sourceTrace
  exact ⟨targetFinal, targetTrace, finalRelated,
    execute_preserves step invariant preserves seed seedValid inputs,
    viable_trace_target_viable target targetSeed targetFinal inputs targetTrace,
    codec.roundTrip _⟩

/-- Any declared FINITE number of cells; physical capacity is not inferred. -/
def Mesh (n : Nat) (State : Type) := Fin n → State

def meshStep {n : Nat} {S : Type} {Input : Type}
    (step : S → Input → S) (states : Mesh n S) (inputs : Mesh n Input) :
    Mesh n S := fun i => step (states i) (inputs i)

theorem finite_mesh_preserves {n : Nat} {S : Type} {Input : Type}
    (step : S → Input → S) (invariant : S → Prop)
    (preserves : ∀ s input, invariant s → invariant (step s input))
    (states : Mesh n S) (inputs : Mesh n Input)
    (valid : ∀ i, invariant (states i)) :
    ∀ i, invariant (meshStep step states inputs i) := by
  intro i
  exact preserves (states i) (inputs i) (valid i)

theorem finite_mesh_codec_roundtrip {n : Nat} {S : Type} {Wire : Type}
    (codec : CanonicalCodec S Wire) (states : Mesh n S) :
    ∀ i, codec.decode (codec.encode (states i)) = some (states i) := by
  intro i
  exact codec.roundTrip (states i)

def extendMesh {n : Nat} {S : Type} (states : Mesh n S) (newCell : S) :
    Mesh (n + 1) S := Fin.cases newCell states

theorem extension_preserves_existing_cell {n : Nat} {S : Type}
    (states : Mesh n S) (newCell : S) (i : Fin n) :
    extendMesh states newCell i.succ = states i := rfl

theorem extension_preserves_invariant {n : Nat} {S : Type}
    (invariant : S → Prop) (states : Mesh n S) (newCell : S)
    (oldValid : ∀ i, invariant (states i)) (newValid : invariant newCell) :
    ∀ i, invariant (extendMesh states newCell i) := by
  intro i
  exact Fin.cases newValid oldValid i

structure Controls where
  bindingValid : Bool
  authorityValid : Bool
  distinctionValid : Bool
  driftDetected : Bool

def continueAllowed (c : Controls) : Bool :=
  c.bindingValid && c.authorityValid && c.distinctionValid && !c.driftDetected

theorem continue_requires_all_guards (c : Controls) :
    continueAllowed c = true ↔
      c.bindingValid = true ∧ c.authorityValid = true ∧
      c.distinctionValid = true ∧ c.driftDetected = false := by
  simp [continueAllowed, and_assoc]

theorem missing_authority_blocks (c : Controls) (missing : c.authorityValid = false) :
    continueAllowed c = false := by
  simp [continueAllowed, missing]

structure BufferedCell (Value : Type) where
  payload : Value
  enabled : Bool

/-- Disabling a successor retains its buffered payload in THIS abstract model. -/
def gateCell {Value : Type} (controls : Controls) (cell : BufferedCell Value) :
    BufferedCell Value :=
  { payload := cell.payload, enabled := cell.enabled && continueAllowed controls }

theorem gating_preserves_payload {Value : Type}
    (controls : Controls) (cell : BufferedCell Value) :
    (gateCell controls cell).payload = cell.payload := rfl

theorem repeated_gating_preserves_payload {Value : Type}
    (controls : Controls) (cell : BufferedCell Value) (n : Nat) :
    (QIKVRT.StorageIntegrity.V1.iterate
      (fun _ c => gateCell controls c) cell n).payload = cell.payload := by
  induction n with
  | zero => rfl
  | succ n ih =>
      simpa [QIKVRT.StorageIntegrity.V1.iterate, gateCell] using ih

/-- Exact UNBOUNDED integer coefficients; bounded hardware needs overflow proof. -/
structure DecimalFixed (scale : Nat) where
  coefficient : Int

def decimalAdd {scale : Nat} (a b : DecimalFixed scale) : DecimalFixed scale :=
  ⟨a.coefficient + b.coefficient⟩

def decimalMultiply {s t : Nat} (a : DecimalFixed s) (b : DecimalFixed t) :
    DecimalFixed (s + t) := ⟨a.coefficient * b.coefficient⟩

theorem decimal_add_exact {s : Nat} (a b : DecimalFixed s) :
    (decimalAdd a b).coefficient = a.coefficient + b.coefficient := rfl

theorem decimal_multiply_exact {s t : Nat} (a : DecimalFixed s) (b : DecimalFixed t) :
    (decimalMultiply a b).coefficient = a.coefficient * b.coefficient := rfl

theorem decimal_denominator_composes (s t : Nat) :
    10 ^ (s + t) = (10 : Nat) ^ s * 10 ^ t := Nat.pow_add 10 s t

theorem decimal_tenths_example :
    (decimalAdd (⟨1⟩ : DecimalFixed 1) ⟨2⟩).coefficient = 3 := by decide

/-- Determinism does not supply unknown external inputs. -/
theorem different_inputs_can_produce_different_results :
    execute (fun (_ : Bool) input => input) false [false] = false ∧
    execute (fun (_ : Bool) input => input) false [true] = true := by decide

/-- Preserve the EXISTING empirical bridge rather than manufacture an observation. -/
theorem physical_support_requires_observation
    {C : QIKVRT.V2.Physics.EmpiricalContext}
    (bridge : QIKVRT.V2.Physics.EmpiricalBridge C)
    (state : C.ModelState) (observation : C.Observation) (claim : C.PhysicalClaim)
    (supported : QIKVRT.V2.Physics.PhysicallySupported bridge state observation claim) :
    bridge.evidenceSupports observation := supported.2.1

theorem missing_observation_prevents_physical_support
    {C : QIKVRT.V2.Physics.EmpiricalContext}
    (bridge : QIKVRT.V2.Physics.EmpiricalBridge C)
    (state : C.ModelState) (observation : C.Observation) (claim : C.PhysicalClaim)
    (missing : ¬ bridge.evidenceSupports observation) :
    ¬ QIKVRT.V2.Physics.PhysicallySupported bridge state observation claim := by
  intro supported
  exact missing (physical_support_requires_observation
    bridge state observation claim supported)


/-- Sum of erasure heats in an explicitly chosen exact integer unit.
The per-erasure lower bound is an EXTERNAL physical input, not Landauer's
law derived from program logic. Unit choice and rounding require calibration. -/
theorem total_erasure_heat_lower_bound (lowerBound : Nat) (heats : List Nat)
    (perErasure : ∀ heat ∈ heats, lowerBound ≤ heat) :
    heats.length * lowerBound ≤ heats.sum := by
  induction heats with
  | nil => simp
  | cons heat rest ih =>
      have headBound := perErasure heat (by simp)
      have tailBounds : ∀ value ∈ rest, lowerBound ≤ value := by
        intro value member
        exact perErasure value (by simp [member])
      have combined := Nat.add_le_add headBound (ih tailBounds)
      simpa [List.length_cons, List.sum_cons, Nat.succ_mul,
        Nat.add_comm] using combined

/-- Non-vacuous local Boolean gate witness; not a physical device receipt. -/
theorem valid_controls_allow_continuation :
    continueAllowed ⟨true, true, true, false⟩ = true := by decide

/-- Finite-list reconstruction has a concrete identity-codec witness.
It verifies the composition layer without asserting a native codec refinement. -/
theorem concrete_finite_reconstruction_witness (values : List Bool) :
    decodeAll (fun value : Bool => some value) values = some values := by
  let codec : CanonicalCodec Bool Bool :=
    ⟨(fun value => value), (fun value => some value), (by intro value; rfl)⟩
  simpa [codec] using decodeAll_map_encode codec values



/-- Partial normalisation through the EXISTING codec contract. -/
def normalize {Value Wire : Type} (codec : CanonicalCodec Value Wire)
    (wire : Wire) : Option Wire := (codec.decode wire).map codec.encode

theorem encoded_reference_is_fixedpoint {Value Wire : Type}
    (codec : CanonicalCodec Value Wire) (value : Value) :
    normalize codec (codec.encode value) = some (codec.encode value) := by
  simp [normalize, codec.roundTrip]

theorem normalization_is_idempotent {Value Wire : Type}
    (codec : CanonicalCodec Value Wire) (wire : Wire) :
    (normalize codec wire).bind (normalize codec) = normalize codec wire := by
  cases observed : codec.decode wire with
  | none => simp [normalize, observed]
  | some value => simp [normalize, observed, codec.roundTrip]

/-- The supplied references are fixed points; size extremality is NOT assumed proved. -/
theorem two_bound_references_are_fixedpoints {Value Wire : Type}
    (codec : CanonicalCodec Value Wire) (minimalReference maximalReference : Value) :
    normalize codec (codec.encode minimalReference) = some (codec.encode minimalReference) ∧
    normalize codec (codec.encode maximalReference) = some (codec.encode maximalReference) :=
  ⟨encoded_reference_is_fixedpoint codec minimalReference,
   encoded_reference_is_fixedpoint codec maximalReference⟩


end QIKVRT.SeedArchitecture.V1

