#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qikvrt_effect_ack import (  # noqa: E402
    EffectState,
    ResponsibilityProtocol,
    canonical_json,
    ordinary_release,
    verify_protocol,
)

RECEIPT = ROOT / "receipts/effects/pre-spacetime-ontology-zenodo-publication-v1.json"
PUBLICATION_RECEIPT = (
    ROOT
    / "evidence/receipts/zenodo/pre-spacetime-ontology-2026-08-05-publication.json"
)
RECIPROCAL_RECEIPT = (
    ROOT
    / "evidence/receipts/"
    "authority-mirror-equality-2026-08-05-pre-spacetime-ontology-zenodo-pr389-pr225.json"
)
RECEIPT_INDEX = ROOT / "evidence/receipts/index.json"


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


def bound_append_only_prefix(index_raw: bytes, bound_blob_sha1: str) -> int | None:
    """Return the entry count whose prefix reproduces the bound index blob.

    The receipt index is append-only and canonically serialized (indent 2,
    sorted keys, trailing newline). A later append keeps the earlier bytes
    reconstructible from the current file; editing or deleting an earlier
    entry, or changing any other field, makes every prefix differ.
    """
    current = json.loads(index_raw.decode("utf-8"))
    receipts = current["equality_receipts"]
    for count in range(len(receipts), -1, -1):
        candidate = dict(current, equality_receipts=receipts[:count])
        raw = (json.dumps(candidate, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        if git_blob_sha1(raw) == bound_blob_sha1:
            return count
    return None


class PreSpacetimeOntologyZenodoEffectAckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_closed_scoped_contract(self) -> None:
        self.assertEqual(
            self.value["schema"],
            "qikvrt_scoped_zenodo_publication_effect_ack_receipt_v1",
        )
        self.assertEqual(
            self.value["scope_id"],
            "pre-spacetime-ontology-zenodo-publication-20260805-v1",
        )
        self.assertEqual(
            self.value["effect_ack"]["state"],
            "EFFECT_ACK_DONE",
        )
        self.assertTrue(self.value["effect_ack"]["ordinary_release"])
        self.assertTrue(
            self.value["effect_completion"]["scoped_effect_ack_done"]
        )
        self.assertTrue(
            self.value["effect_completion"]["no_further_action_within_scope"]
        )

    def test_responsibility_protocol_is_intrinsically_valid(self) -> None:
        protocol = ResponsibilityProtocol.from_dict(
            self.value["effect_ack"]["responsibility_protocol"]
        )
        verify_protocol(protocol)
        self.assertIs(protocol.state, EffectState.EFFECT_ACK_DONE)
        self.assertTrue(protocol.ordinary_release)
        self.assertFalse(protocol.open_questions)
        self.assertFalse(protocol.next_required_checks)
        self.assertTrue(
            all(
                item in protocol.evidence_refs
                for item in protocol.required_evidence_refs
            )
        )

    def test_effect_input_is_exactly_hash_bound(self) -> None:
        payload = canonical_json(self.value["effect_input"]).encode("utf-8")
        expected = "sha256:" + hashlib.sha256(payload).hexdigest()
        protocol = self.value["effect_ack"]["responsibility_protocol"]
        self.assertEqual(protocol["input_hash"], expected)
        self.assertEqual(
            protocol["input_id"],
            "qikvrt-pre-spacetime-ontology-zenodo-request-20260805-v1",
        )

    def test_bound_repository_receipts_are_current(self) -> None:
        publication_raw = PUBLICATION_RECEIPT.read_bytes()
        reciprocal_raw = RECIPROCAL_RECEIPT.read_bytes()
        index_raw = RECEIPT_INDEX.read_bytes()
        source = self.value["source_binding"]
        self.assertEqual(
            git_blob_sha1(publication_raw),
            source["publication_receipt"]["git_blob_sha1"],
        )
        self.assertEqual(
            hashlib.sha256(publication_raw).hexdigest(),
            source["publication_receipt"]["sha256"],
        )
        self.assertEqual(
            git_blob_sha1(reciprocal_raw),
            source["reciprocal_receipt"]["git_blob_sha1"],
        )
        reciprocal = json.loads(reciprocal_raw.decode("utf-8"))
        self.assertEqual(
            reciprocal["reciprocal_repository_binding"][
                "binding_payload_sha256"
            ],
            source["reciprocal_receipt"]["binding_payload_sha256"],
        )
        # The bound index state of 2026-08-05 must survive unchanged as a prefix
        # of the append-only index; later appends are allowed (receipt untouched).
        self.assertIsNotNone(
            bound_append_only_prefix(index_raw, source["append_only_receipt_index"]["git_blob_sha1"]),
            "bound append-only receipt index state is no longer reconstructible",
        )

    def test_append_only_index_check_rejects_rewritten_or_removed_history(self) -> None:
        source = self.value["source_binding"]
        bound = source["append_only_receipt_index"]["git_blob_sha1"]
        index = json.loads(RECEIPT_INDEX.read_text(encoding="utf-8"))
        count = bound_append_only_prefix(RECEIPT_INDEX.read_bytes(), bound)
        self.assertIsNotNone(count)
        self.assertGreaterEqual(len(index["equality_receipts"]), count)
        def encode(value):
            return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
        edited = json.loads(json.dumps(index))
        edited["equality_receipts"][0]["file_sha256"] = "0" * 64
        removed = json.loads(json.dumps(index))
        del removed["equality_receipts"][0]
        retimed = dict(index, updated_at="2099-01-01T00:00:00Z")
        for name, value in (("edited", edited), ("removed", removed), ("retimed", retimed)):
            with self.subTest(case=name):
                self.assertIsNone(bound_append_only_prefix(encode(value), bound))
        appended = json.loads(json.dumps(index))
        appended["equality_receipts"].append({"fixture": "later append"})
        self.assertEqual(bound_append_only_prefix(encode(appended), bound), count)

    def test_publication_effect_predicates_are_complete(self) -> None:
        publication = json.loads(PUBLICATION_RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(publication["state"], "PUBLICATION_RECEIPT_PERSISTED")
        self.assertEqual(
            publication["zenodo"]["doi"],
            "10.5281/zenodo.21804399",
        )
        self.assertEqual(publication["zenodo"]["record_id"], 21804399)
        self.assertTrue(publication["public_redownload"]["performed"])
        self.assertTrue(
            publication["public_redownload"]["byte_equality_established"]
        )
        self.assertEqual(len(publication["public_redownload"]["files"]), 4)

    def test_scoped_done_does_not_inflate_global_completion(self) -> None:
        global_claims = self.value["repository_wide_completion_claims"]
        self.assertEqual(
            global_claims,
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )
        boundary = self.value["scope_boundary"]
        self.assertTrue(boundary["repository_wide_work_remains_open"])
        self.assertFalse(boundary["new_external_effect_authorized_by_this_receipt"])
        self.assertTrue(boundary["duplicate_zenodo_publication_forbidden"])
        self.assertFalse(boundary["epistemic_triad_jpegs_included"])


if __name__ == "__main__":
    unittest.main()
