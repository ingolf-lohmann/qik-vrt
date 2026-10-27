#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# Implementation contribution: Claude (Anthropic).
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Repository-wide pins for JavaScript actions after the GitHub Node 20 removal.

Source contract only: verifies workflow text, not a hosted run. The two target
commits were resolved from the public action repositories on 2026-10-27:
actions/setup-node v7.1.0 and actions/cache v6.1.0 both declare node24.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github/workflows").glob("*.yml"))
SETUP_NODE = "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0"
CACHE_SAVE = "actions/cache/save@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0"
RETIRED = {
    "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020": "node20",
    "actions/cache/save@0057852bfaa89a56745cba8c7296529d2fc39830": "node20",
}
# Exact sites at main 9763b2c8; a new site must be added here deliberately.
EXPECTED_SETUP_NODE = 18
EXPECTED_CACHE_SAVE = 4
CACHED_SETUP_NODE = 5


def steps(text: str, needle: str) -> list[tuple[str, dict[str, str]]]:
    """Return (uses line, with-inputs) for every step whose uses contains needle."""
    lines = text.split("\n")
    found = []
    for index, line in enumerate(lines):
        if needle not in line or "uses:" not in line:
            continue
        indent = len(line) - len(line.lstrip(" -"))
        inputs: dict[str, str] = {}
        cursor = index + 1
        while cursor < len(lines):
            current = lines[cursor]
            if current.strip() and (len(current) - len(current.lstrip()) < indent or current.lstrip().startswith("- ")):
                break
            match = re.match(r"\s+([A-Za-z0-9_-]+):\s*(.*)$", current)
            if match and match.group(1) != "with":
                inputs[match.group(1)] = match.group(2)
            cursor += 1
        found.append((line.strip(), inputs))
    return found


class WorkflowActionRuntimePins(unittest.TestCase):
    def setUp(self) -> None:
        self.texts = {path.name: path.read_text(encoding="utf-8") for path in WORKFLOWS}

    def test_no_active_workflow_uses_a_retired_node20_pin(self) -> None:
        for name, text in self.texts.items():
            for pin, runtime in RETIRED.items():
                with self.subTest(workflow=name, pin=pin):
                    self.assertNotIn(pin, text, f"{runtime} action pin remains")

    def test_every_setup_node_and_cache_save_uses_the_verified_node24_commit(self) -> None:
        node = save = 0
        for name, text in self.texts.items():
            for line in re.findall(r"uses:\s*actions/setup-node@[^\n]*", text):
                node += 1
                self.assertEqual(line.split("uses:", 1)[1].strip(), SETUP_NODE, name)
            for line in re.findall(r"uses:\s*actions/cache/save@[^\n]*", text):
                save += 1
                self.assertEqual(line.split("uses:", 1)[1].strip(), CACHE_SAVE, name)
        self.assertEqual((node, save), (EXPECTED_SETUP_NODE, EXPECTED_CACHE_SAVE))

    def test_existing_caches_are_kept_and_automatic_detection_is_off_elsewhere(self) -> None:
        cached = 0
        for name, text in self.texts.items():
            for _, inputs in steps(text, "actions/setup-node@"):
                with self.subTest(workflow=name, inputs=inputs):
                    self.assertIn("node-version", inputs)
                    if "cache" in inputs:
                        cached += 1
                        self.assertEqual(inputs["cache"], "npm")
                        self.assertIn("cache-dependency-path", inputs)
                        self.assertNotIn("package-manager-cache", inputs)
                    else:
                        self.assertEqual(inputs.get("package-manager-cache"), "false")
                        self.assertNotIn("cache-dependency-path", inputs)
        self.assertEqual(cached, CACHED_SETUP_NODE)

    def test_cache_save_inputs_are_unchanged_path_and_key_only(self) -> None:
        for name, text in self.texts.items():
            for _, inputs in steps(text, "actions/cache/save@"):
                with self.subTest(workflow=name):
                    self.assertEqual(set(inputs), {"path", "key"})

    def test_archived_original_workflows_are_not_rewritten(self) -> None:
        original = ROOT / "runtime/self-host/original-workflows/qikvrt_temdd.yml"
        self.assertIn("actions/setup-node@v6", original.read_text(encoding="utf-8"))

    def test_tool_cache_registry_binds_the_same_action_commits_and_runtime(self) -> None:
        # Register-binding contribution: OpenAI Codex; retain the original tests.
        registry = json.loads((ROOT / "runtime/toolchains/CACHE_REGISTRY.json").read_text(encoding="utf-8"))
        node = registry["components"]["node"]
        for reference in (SETUP_NODE, CACHE_SAVE):
            action, target = reference.split("@", 1)
            commit, version = target.split(" # ", 1)
            with self.subTest(action=action):
                self.assertEqual(node["action_pins"][action], {
                    "commit": commit, "using": "node24", "version": version,
                })
        for name, text in self.texts.items():
            if "uses: actions/setup-node@" in text or "uses: actions/cache/save@" in text:
                self.assertIn(".github/workflows/" + name, node["authority_files"])
        self.assertIn("tests/test_workflow_action_runtime_pins.py", node["authority_files"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
