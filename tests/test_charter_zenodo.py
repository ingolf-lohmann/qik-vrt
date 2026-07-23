#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

import pathlib
import unittest

from tools import qikvrt_charter_zenodo as charter

ROOT = pathlib.Path(__file__).resolve().parents[1]


class CharterZenodoContractTests(unittest.TestCase):
    def test_fixed_artifact_and_evidence_paths(self) -> None:
        self.assertEqual(
            charter.ARTIFACT.relative_to(ROOT).as_posix(),
            "docs/CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md",
        )
        self.assertEqual(
            charter.EVIDENCE.relative_to(ROOT).as_posix(),
            "release/machine-verifiable-science/zenodo-publication.json",
        )

    def test_metadata_preserves_identity_and_license(self) -> None:
        metadata = charter.metadata()
        self.assertEqual(metadata["title"], "Charta einer maschinenprüfbaren Wissenschaft")
        self.assertEqual(metadata["creators"], [{"name": "Lohmann, Ingolf"}])
        self.assertEqual(metadata["license"], "cc-by-nc-nd-4.0")
        self.assertEqual(metadata["access_right"], "open")
        self.assertTrue(metadata["prereserve_doi"])

    def test_capability_contract_exists(self) -> None:
        self.assertTrue((ROOT / "runtime/capabilities/ZENODO_PUBLICATION_CAPABILITY.json").is_file())
        self.assertTrue((ROOT / ".github/workflows/qikvrt_charter_zenodo_publish.yml").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
