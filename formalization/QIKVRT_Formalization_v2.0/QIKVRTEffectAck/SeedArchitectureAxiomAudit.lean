-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.SeedArchitecture

#print axioms QIKVRT.SeedArchitecture.V1.composed_codec_lossless
#print axioms QIKVRT.SeedArchitecture.V1.decodeAll_map_encode
#print axioms QIKVRT.SeedArchitecture.V1.failed_part_prevents_complete_decode
#print axioms QIKVRT.SeedArchitecture.V1.execute_append
#print axioms QIKVRT.SeedArchitecture.V1.checkpoint_restart_exact
#print axioms QIKVRT.SeedArchitecture.V1.execute_preserves
#print axioms QIKVRT.SeedArchitecture.V1.deterministic_step_unique
#print axioms QIKVRT.SeedArchitecture.V1.execute_is_viable_trace
#print axioms QIKVRT.SeedArchitecture.V1.architecture_closure
#print axioms QIKVRT.SeedArchitecture.V1.finite_mesh_preserves
#print axioms QIKVRT.SeedArchitecture.V1.finite_mesh_codec_roundtrip
#print axioms QIKVRT.SeedArchitecture.V1.extension_preserves_existing_cell
#print axioms QIKVRT.SeedArchitecture.V1.extension_preserves_invariant
#print axioms QIKVRT.SeedArchitecture.V1.continue_requires_all_guards
#print axioms QIKVRT.SeedArchitecture.V1.missing_authority_blocks
#print axioms QIKVRT.SeedArchitecture.V1.gating_preserves_payload
#print axioms QIKVRT.SeedArchitecture.V1.repeated_gating_preserves_payload
#print axioms QIKVRT.SeedArchitecture.V1.decimal_add_exact
#print axioms QIKVRT.SeedArchitecture.V1.decimal_multiply_exact
#print axioms QIKVRT.SeedArchitecture.V1.decimal_denominator_composes
#print axioms QIKVRT.SeedArchitecture.V1.decimal_tenths_example
#print axioms QIKVRT.SeedArchitecture.V1.different_inputs_can_produce_different_results
#print axioms QIKVRT.SeedArchitecture.V1.physical_support_requires_observation
#print axioms QIKVRT.SeedArchitecture.V1.missing_observation_prevents_physical_support
#print axioms QIKVRT.SeedArchitecture.V1.total_erasure_heat_lower_bound
#print axioms QIKVRT.SeedArchitecture.V1.valid_controls_allow_continuation
#print axioms QIKVRT.SeedArchitecture.V1.concrete_finite_reconstruction_witness
#print axioms QIKVRT.SeedArchitecture.V1.encoded_reference_is_fixedpoint
#print axioms QIKVRT.SeedArchitecture.V1.normalization_is_idempotent
#print axioms QIKVRT.SeedArchitecture.V1.two_bound_references_are_fixedpoints
