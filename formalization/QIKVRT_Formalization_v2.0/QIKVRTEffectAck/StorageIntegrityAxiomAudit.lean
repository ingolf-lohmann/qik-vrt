-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
-- Copyright 2026 Ingolf Lohmann.
import QIKVRTEffectAck.StorageIntegrity

#print axioms QIKVRT.StorageIntegrity.V1.valid_requires_rights
#print axioms QIKVRT.StorageIntegrity.V1.valid_requires_signature
#print axioms QIKVRT.StorageIntegrity.V1.single_bit_changes_bits
#print axioms QIKVRT.StorageIntegrity.V1.single_signature_bit_rejected
#print axioms QIKVRT.StorageIntegrity.V1.single_rights_bit_rejected
#print axioms QIKVRT.StorageIntegrity.V1.removed_nonempty_signature_rejected
#print axioms QIKVRT.StorageIntegrity.V1.removed_nonempty_rights_rejected
#print axioms QIKVRT.StorageIntegrity.V1.payload_independent_notice_check
#print axioms QIKVRT.StorageIntegrity.V1.public_notice_does_not_authenticate_payload
#print axioms QIKVRT.StorageIntegrity.V1.changed_subject_rejected
#print axioms QIKVRT.StorageIntegrity.V1.missing_checker_is_unverified
#print axioms QIKVRT.StorageIntegrity.V1.mismatch_is_rejected
#print axioms QIKVRT.StorageIntegrity.V1.stopped_checker_cannot_signal
#print axioms QIKVRT.StorageIntegrity.V1.missing_channel_cannot_signal
#print axioms QIKVRT.StorageIntegrity.V1.live_detection_signals
#print axioms QIKVRT.StorageIntegrity.V1.lossless_reconstruction
#print axioms QIKVRT.StorageIntegrity.V1.canonical_reencoding
#print axioms QIKVRT.StorageIntegrity.V1.codec_is_injective
#print axioms QIKVRT.StorageIntegrity.V1.adaptation_preserves_checked_property
#print axioms QIKVRT.StorageIntegrity.V1.every_finite_verified_adaptation_preserves
#print axioms QIKVRT.StorageIntegrity.V1.no_lossless_boolean_storage_in_unit
#print axioms QIKVRT.StorageIntegrity.V1.accepted_example_exists
