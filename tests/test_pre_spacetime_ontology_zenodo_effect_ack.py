#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import json
import copy
import os
import subprocess
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


def verify_append_only_index(current: dict, historical: dict) -> None:
    old = historical["equality_receipts"]
    rows = current["equality_receipts"]
    if ({k: v for k, v in current.items() if k != "equality_receipts"}
            != {k: v for k, v in historical.items() if k != "equality_receipts"}
            or rows[:len(old)] != old or len(rows) < len(old)
            or len({r["receipt_id"] for r in rows}) != len(rows)):
        raise ValueError("append-only receipt index was rewritten, truncated or duplicated")


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
        # The receipt binds August's exact mains. Later appends must preserve
        # that snapshot, rather than pretend today's index has the old hash.
        historical_raw = subprocess.check_output(
            ["git", "-C", str(ROOT), "show",
             source["mirror"]["reciprocal_receipt_main"] + ":" + source["append_only_receipt_index"]["path"]],
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1"}, timeout=30,
        )
        self.assertEqual(
            git_blob_sha1(historical_raw),
            source["append_only_receipt_index"]["git_blob_sha1"],
        )
        verify_append_only_index(json.loads(index_raw), json.loads(historical_raw))

    def test_append_only_snapshot_rejects_deletion_rewrite_reorder_and_duplicates(self) -> None:
        historical = {"schema": "fixture", "equality_receipts": [
            {"receipt_id": "one", "binding": "exact-one"},
            {"receipt_id": "two", "binding": "exact-two"}]}
        extended = copy.deepcopy(historical)
        extended["equality_receipts"].append({"receipt_id": "three", "binding": "new"})
        verify_append_only_index(extended, historical)
        for mutation in (lambda rows: rows.pop(0), lambda rows: rows.reverse(),
                         lambda rows: rows[0].update(binding="changed"),
                         lambda rows: rows.append(copy.deepcopy(rows[0]))):
            changed = copy.deepcopy(extended)
            mutation(changed["equality_receipts"])
            with self.assertRaises(ValueError):
                verify_append_only_index(changed, historical)

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
