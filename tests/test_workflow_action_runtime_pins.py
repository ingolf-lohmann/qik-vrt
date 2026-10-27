#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# Implementation contribution: Claude (Anthropic).
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Repository-wide pins for JavaScript actions after the GitHub Node 20 removal.

Source contract only: verifies workflow text, not a hosted run. The two target
commits were resolved from the public action repositories on 2026-10-27:
actions/setup-node v7.1.0 and actions/cache v6.1.0 both declare node24.
actions/setup-python v6.3.0 (node24) replaced v5.6.0 (node20) on 2026-10-27 in
every job that can run on the Authority; Goldkelch-only historical release jobs
(and jobs that need one) keep their original pin and are not rewritten.
"""
from __future__ import annotations

import json
import re
import unittest

import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github/workflows").glob("*.yml"))
SETUP_NODE = "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0"
CACHE_SAVE = "actions/cache/save@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0"
RETIRED = {
    "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020": "node20",
    "actions/cache/save@0057852bfaa89a56745cba8c7296529d2fc39830": "node20",
}
SETUP_PYTHON = "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6.3.0"
SETUP_PYTHON_RETIRED = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
EXPECTED_SETUP_PYTHON_ACTIVE = 56
EXPECTED_SETUP_PYTHON_HISTORICAL = 10
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

    def test_setup_python_is_node24_wherever_a_job_can_run_on_the_authority(self) -> None:
        active = historical = 0
        for name, text in self.texts.items():
            jobs = (yaml.safe_load(text) or {}).get("jobs", {})

            def goldkelch_only(job: str, seen: frozenset = frozenset()) -> bool:
                spec = jobs[job]
                condition = str(spec.get("if", ""))
                if "Goldkelch/qik-vrt" in condition and "ingolf-lohmann/qik-vrt" not in condition:
                    return True
                if any(token in condition for token in ("always()", "failure()", "!cancelled()")):
                    return False
                needs = spec.get("needs") or []
                needs = [needs] if isinstance(needs, str) else needs
                return any(n not in seen and goldkelch_only(n, seen | {job}) for n in needs)

            lines = text.split("\n")
            starts = [(i, m.group(1)) for i, line in enumerate(lines)
                      for m in [re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)] if m and m.group(1) in jobs]
            for index, line in enumerate(lines):
                if "actions/setup-python@" not in line:
                    continue
                job = [n for s, n in starts if s <= index][-1]
                pin = line.split("uses:", 1)[1].strip()
                with self.subTest(workflow=name, job=job, line=index + 1):
                    if goldkelch_only(job):
                        historical += 1
                        self.assertTrue(pin.startswith(SETUP_PYTHON_RETIRED), "historical job rewritten")
                    else:
                        active += 1
                        self.assertEqual(pin, SETUP_PYTHON)
        self.assertEqual((active, historical), (EXPECTED_SETUP_PYTHON_ACTIVE, EXPECTED_SETUP_PYTHON_HISTORICAL))

    def test_tool_cache_registry_binds_the_setup_python_commit_and_runtime(self) -> None:
        registry = json.loads((ROOT / "runtime/toolchains/CACHE_REGISTRY.json").read_text(encoding="utf-8"))
        python = registry["components"]["python"]
        commit, version = SETUP_PYTHON.split("@", 1)[1].split(" # ", 1)
        self.assertEqual(python["provider"], "actions/setup-python")
        self.assertEqual(python["action_pins"]["actions/setup-python"],
                         {"commit": commit, "using": "node24", "version": version})
        self.assertIn("tests/test_workflow_action_runtime_pins.py", python["authority_files"])

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
