#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import json
import pathlib
import tempfile
import unittest

from tools import qikvrt_construct_history_preserving_mirror_candidate_pr240 as m


class HistoryPreservingMirrorCandidatePr240Tests(unittest.TestCase):
    def test_exact_request_is_accepted(self) -> None:
        value = m.load_and_validate_request()
        self.assertEqual(value["authority"]["main"], m.AUTHORITY_MAIN)
        self.assertEqual(value["authority"]["source_pr"], 240)
        self.assertEqual(value["mirror"]["parent_main"], m.MIRROR_PARENT)
        self.assertEqual(value["owner_decision"]["decision"], "ACCEPT")

    def test_truth_boundary_inflation_is_rejected(self) -> None:
        value = json.loads(m.REQUEST_PATH.read_text(encoding="utf-8"))
        value = copy.deepcopy(value)
        value["truth_boundary"]["pass"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "request.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(m.ConstructionError):
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
