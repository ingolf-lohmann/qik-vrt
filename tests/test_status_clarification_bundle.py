#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed checks for the official QIK-VRT status clarification bundle."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "docs/publications/2026-07-22-qik-vrt-status-clarification"
REQUIRED = {
    "STATUSERKLAERUNG_DE.md",
    "WHATSAPP_RELEASE_KOMMENTAR_DE.md",
    "RELEASE_NOTES_WHATSAPP_DE.md",
    "EVIDENCE_BOUNDARY.md",
    "EVIDENCE_INDEX.json",
    "BUILD_PROVENANCE.json",
    "PATENT_DISCLOSURE_BOUNDARY.md",
    "LICENSE_NOTICE.md",
    "README.md",
    "CITATION.cff",
    "QIK-VRT_EFFECT_ACK_Statusklaerung_2026-07-22.pdf",
    "ZENODO_FILESET.md",
    "ZENODO_PUBLIC_INVENTORY.md",
}
PROTECTED_ZENODO_IDS = {"21498772", "21498773", "21498774", "21488115"}


class StatusClarificationBundleTests(unittest.TestCase):
    def test_required_files_and_no_private_media(self) -> None:
        names = {item.name for item in BUNDLE.iterdir() if item.is_file()}
        self.assertTrue(REQUIRED <= names)
        self.assertFalse(
            any(
                name.lower().endswith(
                    (".m4a", ".mp3", ".wav", ".ogg", ".mp4", ".webm")
                )
                or "transcript" in name.lower()
                for name in names
            )
        )

    def test_claim_boundaries_are_explicit(self) -> None:
        statement = (BUNDLE / "STATUSERKLAERUNG_DE.md").read_text("utf-8")
        evidence = (BUNDLE / "EVIDENCE_BOUNDARY.md").read_text("utf-8")
        combined = statement + "\n" + evidence
        for required in (
            "PASS_WITH_EXPLICIT_BOUNDARIES",
            "CONTINUE_DRAFT01_WIRE_IMPLEMENTATION",
            "CONCEPTUAL_ONLY / NOT_IMPLEMENTED",
            "keine positive Totalisierungs",
            "Gleichsetzung eines Modelluniversums mit",
            "keine Quantenschaltung",
            "Weder diese\nErklärung noch ein DOI",
            "Patentanmeldung",
        ):
            self.assertIn(required, combined)
        self.assertRegex(
            combined,
            re.compile(
                r"(vollständige|vollständigen)\s+Rekonstruktion\s+"
                r"(?:der\s+)?Informatik,\s+Mathematik,\s+Physik\s+oder\s+"
                r"(?:des\s+)?bekannten\s+Universums",
                re.IGNORECASE,
            ),
        )

    def test_license_layers_and_non_retroactivity(self) -> None:
        notice = (BUNDLE / "LICENSE_NOTICE.md").read_text("utf-8")
        for required in (
            "Apache-2.0 bleibt",
            "PolyForm Noncommercial 1.0.0",
            "CC BY-NC-ND 4.0",
            "Formalisierungspaket | MIT",
            "Drittsoftware",
            "tatsächlich Berechtigten",
        ):
            self.assertIn(required, notice)

    def test_evidence_index_hashes_every_source(self) -> None:
        index = json.loads((BUNDLE / "EVIDENCE_INDEX.json").read_text("utf-8"))
        self.assertEqual(index["schema_version"], 1)
        self.assertEqual(index["status"], "PASS_WITH_EXPLICIT_BOUNDARIES")
        self.assertGreaterEqual(len(index["evidence"]), 10)
        for entry in index["evidence"]:
            path = ROOT / entry["path"]
            self.assertTrue(path.is_file(), entry["path"])
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                entry["sha256"],
                entry["path"],
            )

    def test_public_inventory_and_release_notes_are_truthful(self) -> None:
        inventory = (BUNDLE / "ZENODO_PUBLIC_INVENTORY.md").read_text("utf-8")
        release_notes = (BUNDLE / "RELEASE_NOTES_WHATSAPP_DE.md").read_text("utf-8")
        self.assertIn("14 Versionsrecords in fünf", inventory)
        for concept in ("20712300", "21244411", "21482022", "21488115", "21498772"):
            self.assertIn(concept, inventory)
        for required in (
            "14 versionierte Datensätze in fünf Konzeptlinien",
            "alles Wissen fertig reverse engineered",
            "CONCEPTUAL_ONLY / NOT_IMPLEMENTED",
            "jenseits eines Ereignishorizonts",
            "unterhalb der Planck-Skala",
            "metaphysische oder spirituelle Wahrheit",
        ):
            self.assertIn(required, release_notes)

    def test_build_provenance_binds_the_rendered_pdf(self) -> None:
        receipt = json.loads((BUNDLE / "BUILD_PROVENANCE.json").read_text("utf-8"))
        for section in ("source", "output"):
            path = ROOT / receipt[section]["path"]
            data = path.read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), receipt[section]["sha256"])
            if section == "output":
                self.assertEqual(len(data), receipt[section]["bytes"])
        self.assertEqual(receipt["output"]["pages"], 4)
        self.assertEqual(receipt["visual_qa"]["result"], "PASS")

    def test_pdf_is_a_nontrivial_static_document(self) -> None:
        data = (
            BUNDLE / "QIK-VRT_EFFECT_ACK_Statusklaerung_2026-07-22.pdf"
        ).read_bytes()
        self.assertGreater(len(data), 20_000)
        self.assertTrue(data.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", data[-1024:])
        self.assertNotIn(b"/JavaScript", data)
        self.assertNotIn(b"/EmbeddedFile", data)

    def test_citation_is_a_dataset_with_a_report_citation_and_no_old_doi(self) -> None:
        citation = (BUNDLE / "CITATION.cff").read_text("utf-8")
        self.assertIn("\ntype: dataset\n", citation)
        self.assertIn("preferred-citation:\n  type: report\n", citation)
        for identifier in PROTECTED_ZENODO_IDS:
            self.assertNotIn(f"10.5281/zenodo.{identifier}", citation)


if __name__ == "__main__":
    unittest.main()
