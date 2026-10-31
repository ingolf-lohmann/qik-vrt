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
import subprocess
import sys
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
SETUP_PYTHON = "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6.3.0"
SETUP_PYTHON_RETIRED = "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
EXPECTED_SETUP_PYTHON_ACTIVE = 57
EXPECTED_SETUP_PYTHON_HISTORICAL = 10
# Exact sites at main 9763b2c8; a new site must be added here deliberately.
EXPECTED_SETUP_NODE = 18
EXPECTED_CACHE_SAVE = 5
CACHED_SETUP_NODE = 5


def job_policies(text: str) -> dict[str, dict[str, str | list[str]]]:
    """Read this repository's job-level if/needs syntax using only the stdlib.

    This is a bounded workflow-text check, like ``steps`` below, not a YAML
    loader. Unsupported job declarations or dependencies fail the check.
    Dependency repair contribution: OpenAI Codex.
    """
    start = re.search(r"^jobs:[^\n]*$", text, re.MULTILINE)
    if start is None:
        return {}
    if not re.fullmatch(r"jobs:\s*(?:#.*)?", start.group()):
        raise ValueError("unsupported jobs declaration")
    body = text[start.end():]
    end = re.search(r"^[A-Za-z_][A-Za-z0-9_-]*:", body, re.MULTILINE)
    if end:
        body = body[:end.start()]
    header = re.compile(r"^  ([A-Za-z0-9_-]+):\s*(?:#.*)?$", re.MULTILINE)
    headers = list(header.finditer(body))
    for line in body.splitlines():
        if re.match(r"^  [^\s#]", line) and not header.fullmatch(line):
            raise ValueError("unsupported job declaration: " + line)

    def scalar(value: str) -> str:
        quote = ""
        cursor = 0
        while cursor < len(value):
            char = value[cursor]
            if quote:
                if quote == '"' and char == "\\":
                    cursor += 2
                    continue
                if char == quote:
                    if quote == "'" and value[cursor:cursor + 2] == "''":
                        cursor += 2
                        continue
                    quote = ""
            elif char in ("'", '"'):
                quote = char
            elif char == "#" and (cursor == 0 or value[cursor - 1].isspace()):
                value = value[:cursor]
                break
            cursor += 1
        if quote:
            raise ValueError("unterminated workflow scalar quote")
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            return json.loads(value)
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1].replace("''", "'")
        return value

    jobs: dict[str, dict[str, str | list[str]]] = {}
    for index, match in enumerate(headers):
        name = match.group(1)
        if name in jobs:
            raise ValueError("duplicate job: " + name)
        stop = headers[index + 1].start() if index + 1 < len(headers) else len(body)
        block = body[match.end():stop]
        policy: dict[str, str | list[str]] = {"if": "", "needs": []}
        seen = set()
        for field in re.finditer(r"^    (if|needs):[ \t]*(.*)$", block, re.MULTILINE):
            key, value = field.group(1), scalar(field.group(2))
            if key in seen:
                raise ValueError("duplicate job policy: " + key)
            seen.add(key)
            children = []
            for line in block[field.end():].splitlines():
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                if not line.startswith("      "):
                    break
                children.append(line.strip())
            if key == "if":
                policy[key] = (
                    " ".join(scalar(line) for line in children)
                    if re.fullmatch(r"[>|][+-]?", value) else value
                )
                continue
            if not value:
                if any(not line.startswith("- ") for line in children):
                    raise ValueError("unsupported needs sequence")
                needs = [scalar(line[2:]) for line in children]
            elif value.startswith("[") and value.endswith("]"):
                needs = [scalar(item.strip()) for item in value[1:-1].split(",") if item.strip()]
            else:
                needs = [value]
            if any(not re.fullmatch(r"[A-Za-z0-9_-]+", job) for job in needs):
                raise ValueError("unsupported needs declaration: " + value)
            policy[key] = needs
        jobs[name] = policy
    return jobs


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
            jobs = job_policies(text)

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


class WorkflowPolicyParsing(unittest.TestCase):
    def test_pin_checks_run_without_site_packages(self) -> None:
        result = subprocess.run(
            [sys.executable, "-S", "-B", "-m", "unittest",
             "tests.test_workflow_action_runtime_pins.WorkflowActionRuntimePins"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_folded_condition_and_dependency_forms(self) -> None:
        jobs = job_policies("\n".join([
            "on:", "  workflow_dispatch:", "jobs:",
            "  gated:", "    if: >-",
            "      github.repository == 'Goldkelch/qik-vrt' &&",
            "      github.event_name == 'workflow_dispatch'",
            "  chain:", "    needs:", "      - gated",
            "  consumer:", "    needs: [gated, 'chain'] # prerequisites",
            "    if: ${{ always() }} # Goldkelch/qik-vrt is only a comment",
        ]))
        self.assertEqual(set(jobs), {"gated", "chain", "consumer"})
        self.assertEqual(jobs["gated"]["if"],
                         "github.repository == 'Goldkelch/qik-vrt' && github.event_name == 'workflow_dispatch'")
        self.assertEqual(jobs["chain"]["needs"], ["gated"])
        self.assertEqual(jobs["consumer"]["needs"], ["gated", "chain"])
        self.assertEqual(jobs["consumer"]["if"], "${{ always() }}")

    def test_unsupported_needs_expression_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported needs"):
            job_policies("jobs:\n  test:\n    needs: ${{ fromJSON(inputs.jobs) }}\n")

    def test_quoted_hash_is_preserved_and_unclosed_quote_rejected(self) -> None:
        jobs = job_policies("jobs:\n  test:\n    if: contains('a # b', 'b') # comment\n")
        self.assertEqual(jobs["test"]["if"], "contains('a # b', 'b')")
        with self.assertRaisesRegex(ValueError, "unterminated"):
            job_policies("jobs:\n  test:\n    if: 'unterminated\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
