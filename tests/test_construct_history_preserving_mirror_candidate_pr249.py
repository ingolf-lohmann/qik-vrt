#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import json
import pathlib
import tempfile
import unittest

from tools import qikvrt_construct_history_preserving_mirror_candidate_pr249 as m


class HistoryPreservingMirrorCandidatePr249Tests(unittest.TestCase):
    def test_exact_request_is_accepted(self) -> None:
        value = m.load_and_validate_request()
        self.assertEqual(value["authority"]["main"], m.AUTHORITY_MAIN)
        self.assertEqual(value["authority"]["source_pr"], 249)
        self.assertEqual(value["authority"]["accepted_exact_head"], m.ACCEPTED_EXACT_HEAD)
        self.assertEqual(value["mirror"]["parent_main"], m.MIRROR_PARENT)
        self.assertEqual(value["owner_decision"]["decision"], "ACCEPT")

    def test_truth_boundary_inflation_is_rejected(self) -> None:
        value = json.loads(m.REQUEST_PATH.read_text(encoding="utf-8"))
        for key in (
            "mirror_promoted",
            "reciprocal_equality_receipt_materialized",
            "zenodo_mutation_authorized",
            "proof_corpus_published_on_zenodo",
            "pass",
            "final_pass",
            "effect_ack_done",
        ):
            changed = copy.deepcopy(value)
            changed["truth_boundary"][key] = True
            with tempfile.TemporaryDirectory() as directory:
                path = pathlib.Path(directory) / "request.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(m.ConstructionError, msg=key):
                    m.load_and_validate_request(path)

    def test_authority_or_parent_retarget_is_rejected(self) -> None:
        value = json.loads(m.REQUEST_PATH.read_text(encoding="utf-8"))
        for section, key in (("authority", "main"), ("mirror", "parent_main")):
            changed = copy.deepcopy(value)
            changed[section][key] = "0" * 40
            with tempfile.TemporaryDirectory() as directory:
                path = pathlib.Path(directory) / "request.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(m.ConstructionError):
                    m.load_and_validate_request(path)

    def test_manifest_bindings_are_immutable(self) -> None:
        value = json.loads(m.REQUEST_PATH.read_text(encoding="utf-8"))
        for key in (
            "repository_manifest_git_blob_sha1",
            "repository_manifest_sha256",
            "repository_content_tree_sha256",
        ):
            changed = copy.deepcopy(value)
            changed["authority"][key] = "0" * 40 if key.endswith("sha1") else "0" * 64
            with tempfile.TemporaryDirectory() as directory:
                path = pathlib.Path(directory) / "request.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(m.ConstructionError, msg=key):
                    m.load_and_validate_request(path)

    def test_candidate_contract_requires_one_parent_and_tree_equality(self) -> None:
        value = json.loads(m.REQUEST_PATH.read_text(encoding="utf-8"))
        for key in ("sole_parent_required", "authority_tree_equality_required"):
            changed = copy.deepcopy(value)
            changed["candidate_contract"][key] = False
            with tempfile.TemporaryDirectory() as directory:
                path = pathlib.Path(directory) / "request.json"
                path.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(m.ConstructionError):
                    m.load_and_validate_request(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
