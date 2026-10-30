-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import VRTCore_VirtualSphere
import QIKVRTEffectAck.ReconstructibleVirtuality

/-!
# Reuse of the H6 virtual sphere, with a disclosed physical-scale obligation

H6's radius is a natural-number shell index. Its population counts occupied
SHELLS, not spatial cells, bits, volume, phenomenal experience or galaxies.
The source is compiled unchanged from its archived directory by Lake.

`lightYearsPerShell` below is a freely supplied calibration, not an empirical
measurement. The Owner's 20-billion-light-year wording remains dimensionally
unresolved (radius, diameter or cubic light years); this model chooses none.
The countermodel shows that virtual correctness alone does not identify even
an integer linear calibration. It does not refute a future physical bridge.
-/
namespace QIKVRT.VirtualSphereBridge.V1

open QIKVRT.VRTCore.VirtualSphereH6

inductive PhysicalDimension where
  | length | volume
  deriving DecidableEq, Repr

theorem length_is_not_volume : PhysicalDimension.length ≠ .volume := by decide

def calibratedRadius (lightYearsPerShell : Nat) (state : VirtualSphereState) : Nat :=
  lightYearsPerShell * state.radius

theorem calibrated_run_radius (lightYearsPerShell stage : Nat) :
    calibratedRadius lightYearsPerShell (run stage) = lightYearsPerShell * stage := by
  rw [calibratedRadius, run_radius]

theorem virtual_correctness_does_not_identify_scale
    (state : VirtualSphereState) (positive : 0 < state.radius) :
    NoHole state ∧ calibratedRadius 1 state ≠ calibratedRadius 2 state := by
  refine ⟨state_noHole state, ?_⟩
  simp only [calibratedRadius, Nat.one_mul]
  omega

-- This is a syntax-level copy of the requested magnitude, never a measurement.
def ownerRequestedMagnitude : Nat := 20000000000

theorem scale_ambiguity_at_requested_magnitude :
    ∃ state : VirtualSphereState,
      Reachable state ∧ NoHole state ∧ state.radius = ownerRequestedMagnitude ∧
      calibratedRadius 1 state ≠ calibratedRadius 2 state := by
  let state : VirtualSphereState := canonicalState ownerRequestedMagnitude
  have positive : 0 < state.radius := by decide
  exact ⟨state, every_state_reachable state, state_noHole state, rfl,
    (virtual_correctness_does_not_identify_scale state positive).2⟩

-- One statement connects the new manuscript theorem to the original H6 model.
-- Neither source has been replaced by a redefined look-alike.
theorem stored_history_has_no_hole_sphere_projection {Source Target Wire : Type}
    (codec : QIKVRT.StorageIntegrity.V1.CanonicalCodec (Target × Source) Wire)
    (step : Source → Target) (source : Source) (stage : Nat) :
    (codec.decode (codec.encode
      (QIKVRT.ReconstructibleVirtuality.V1.withHistory step source))).map Prod.snd = some source ∧
    NoHole (run stage) ∧ population (run stage) = stage + 1 := by
  refine ⟨QIKVRT.ReconstructibleVirtuality.V1.encoded_history_restores_predecessor
    codec step source, state_noHole _, ?_⟩
  rw [population_eq_radius_succ, run_radius]

end QIKVRT.VirtualSphereBridge.V1
