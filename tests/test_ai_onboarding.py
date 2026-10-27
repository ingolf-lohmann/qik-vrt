#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# Implementation contribution: Claude (Anthropic).
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Structural contract for AI_ONBOARDING.md; documentary consistency only."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONBOARDING = ROOT / "AI_ONBOARDING.md"


class AiOnboardingContract(unittest.TestCase):
    def setUp(self) -> None:
        self.text = ONBOARDING.read_text(encoding="utf-8")

    def test_registered_as_url_readable_adapter_without_changing_authority(self) -> None:
        registry = json.loads((ROOT / "AI_ADAPTERS.json").read_text(encoding="utf-8"))
        entries = [a for a in registry["adapters"] if a["path"] == "AI_ONBOARDING.md"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["mode"], "url-readable")
        self.assertEqual(registry["canonical_entrypoint"], "AI")
        self.assertIn("compatibility shims only", registry["rule"])
        self.assertIn("`AI`, `AI_CONTEXT.json` and `AGENTS.md` remain\nauthoritative", self.text)
        self.assertIn("they win and this file is the defect", self.text)

    def test_every_referenced_repository_path_exists(self) -> None:
        candidates = set(re.findall(r"`((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:md|json|py))(?:#[^`]*)?`", self.text))
        candidates |= {"AI", "AGENTS.md", "AI_CONTEXT.json"}
        missing_by_design = {"policy/PERFECT_OPTIMUM_V1.json"}
        for path in sorted(candidates - missing_by_design):
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file(), path)
        for path in missing_by_design:
            self.assertFalse((ROOT / path).exists(), "snapshot says absent; update section 8 when it is restored")

    def test_read_order_matches_runtime_context(self) -> None:
        context = json.loads((ROOT / "AI_CONTEXT.json").read_text(encoding="utf-8"))
        order = context["required_read_order"]
        self.assertEqual(order[:2], ["AI", "AI_CONTEXT.json"])
        self.assertIn("AGENTS.md", order)
        self.assertIn("required_read_order", self.text)

    def test_evidence_boundaries_are_stated_not_weakened(self) -> None:
        for phrase in ("`TRANSPORT_ACK` is not `EFFECT_ACK`", "never inferred", "Not verified here",
                       "REST_API_ONLY", "Never force", "No automatic merge",
                       'never set `APT::Sandbox::User "root"`'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)
        self.assertNotRegex(self.text, r"(?i)\bEFFECT_ACK_DONE\s*[:=]\s*true")

    def test_snapshot_is_dated_and_bound_to_a_commit(self) -> None:
        section = self.text.split("## 8. Snapshot of open work", 1)[1]
        self.assertRegex(section.splitlines()[0], r"\d{1,2} \w+ 20\d\d")
        self.assertIn("Re-observe before use", section)
        self.assertRegex(section, r"`[0-9a-f]{40}`,\ntree `[0-9a-f]{40}`")

    def test_license_header_and_attribution(self) -> None:
        self.assertTrue(self.text.startswith("<!--\nSPDX-License-Identifier: CC-BY-NC-ND-4.0\n"))
        self.assertIn("Owner: Ingolf Lohmann", self.text)
        self.assertIn("Claude (Anthropic)", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
