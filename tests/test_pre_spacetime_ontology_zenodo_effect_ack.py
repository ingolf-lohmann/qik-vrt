#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import hashlib
import json
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


class PreSpacetimeOntologyZenodoEffectAckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = json.loads(RECEIPT.read_text(encoding="utf-8"))
        source = cls.value["source_binding"]
        # This receipt records the 2026-08-05 snapshot, not every later append.
        # The existing scoped workflow fetches full history. Missing history
        # fails closed; verification must not fetch evidence over the network.
        cls.index_snapshot_raw = subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "show",
                f'{source["mirror"]["reciprocal_receipt_main"]}:'
                f'{source["append_only_receipt_index"]["path"]}',
            ],
            cwd=ROOT,
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
            check=True,
            capture_output=True,
            timeout=20,
        ).stdout

    def assert_receipt_index_extension(
        self, snapshot_raw: bytes, current_raw: bytes
    ) -> None:
        self.assertEqual(
            git_blob_sha1(snapshot_raw),
            self.value["source_binding"]["append_only_receipt_index"][
                "git_blob_sha1"
            ],
        )
        snapshot = json.loads(snapshot_raw)
        current = json.loads(current_raw)
        # Appends may advance updated_at, but must preserve the index contract
        # and every historically bound row, including order and exact values.
        mutable = {"equality_receipts", "updated_at"}
        self.assertEqual(
            {key: value for key, value in current.items() if key not in mutable},
            {key: value for key, value in snapshot.items() if key not in mutable},
        )
        rows = snapshot["equality_receipts"]
        self.assertEqual(current["equality_receipts"][:len(rows)], rows)

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

    def test_bound_repository_receipts_preserve_publication_snapshot(self) -> None:
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
        self.assert_receipt_index_extension(self.index_snapshot_raw, index_raw)

    def test_receipt_index_accepts_snapshot_and_later_appends(self) -> None:
        self.assert_receipt_index_extension(
            self.index_snapshot_raw, self.index_snapshot_raw
        )
        current = json.loads(RECEIPT_INDEX.read_bytes())
        current["equality_receipts"].append({"receipt_id": "later-scoped-receipt"})
        current["updated_at"] = "2026-10-07T00:00:00Z"
        self.assert_receipt_index_extension(
            self.index_snapshot_raw, json.dumps(current).encode("utf-8")
        )

    def test_receipt_index_rejects_rewritten_deleted_or_reordered_history(self) -> None:
        snapshot = json.loads(self.index_snapshot_raw)
        mutated = copy.deepcopy(snapshot)
        mutated["equality_receipts"][0]["state"] = "REWRITTEN"
        deleted = copy.deepcopy(snapshot)
        deleted["equality_receipts"].pop()
        reordered = copy.deepcopy(snapshot)
        reordered["equality_receipts"].reverse()
        for name, current in (
            ("rewritten", mutated), ("deleted", deleted), ("reordered", reordered)
        ):
            with self.subTest(change=name), self.assertRaises(AssertionError):
                self.assert_receipt_index_extension(
                    self.index_snapshot_raw, json.dumps(current).encode("utf-8")
                )

    def test_receipt_index_rejects_snapshot_byte_drift(self) -> None:
        with self.assertRaises(AssertionError):
            self.assert_receipt_index_extension(
                self.index_snapshot_raw + b" ", RECEIPT_INDEX.read_bytes()
            )

    def test_receipt_index_rejects_contract_drift(self) -> None:
        current = json.loads(RECEIPT_INDEX.read_bytes())
        current["schema"] = "UNBOUND_SCHEMA"
        with self.assertRaises(AssertionError):
            self.assert_receipt_index_extension(
                self.index_snapshot_raw, json.dumps(current).encode("utf-8")
            )

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
