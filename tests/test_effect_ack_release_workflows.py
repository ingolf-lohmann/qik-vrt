#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline structural regression tests for EFFECT_ACK release workflows."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile
import textwrap
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
RESERVE = ROOT / ".github/workflows/qikvrt_zenodo_reserve.yml"
FINALIZE = ROOT / ".github/workflows/qikvrt_effect_ack_finalize.yml"
GENERAL_CI = ROOT / ".github/workflows/qikvrt_ci.yml"
ADAPTIVE_RUNTIME = ROOT / ".github/workflows/qikvrt_adaptive_runtime.yml"
MARKER = ROOT / "release/effect-ack-universality-request.json"
SCHEMA = ROOT / "policy/qikvrt-effect-ack-release-request.schema.json"
MARKER_PATH = "release/effect-ack-universality-request.json"
RESERVE_BRANCH = "automation/effect-ack-universality-reserve-20260722"
FINALIZE_BRANCH = "automation/effect-ack-universality-finalize-20260722"


def run_git(root: pathlib.Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", os.fspath(root), *arguments],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def embedded_python_for_step(workflow: str, step_name: str) -> str:
    start = workflow.index(f"      - name: {step_name}")
    end = workflow.index("\n      - name:", start + 1)
    block = workflow[start:end]
    match = re.search(r"python -B - <<'PY'\n(.*?)\n\s*PY(?:\n|$)", block, re.S)
    if match is None:
        raise AssertionError(f"workflow step has no embedded Python: {step_name}")
    lines = match.group(1).splitlines()
    indentation = min(
        len(line) - len(line.lstrip()) for line in lines if line.strip()
    )
    return "\n".join(
        line[indentation:] if line.strip() else "" for line in lines
    )


class EffectAckReleaseWorkflowTests(unittest.TestCase):
    maxDiff = None

    def test_inert_marker_binds_schema_and_canonical_payload(self) -> None:
        marker = json.loads(MARKER.read_text(encoding="utf-8"))
        json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(marker["state"], "inactive")
        self.assertEqual(marker["confirm"], "NOT_AUTHORIZED")
        self.assertEqual(marker["release"]["expected_source_commit"], "0" * 40)
        self.assertEqual(marker["release"]["expected_source_tree"], "0" * 40)
        self.assertEqual(
            marker["schema_sha256"], hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
        )
        supplied = marker.pop("authorization_payload_sha256")
        canonical = json.dumps(
            marker, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.assertEqual(supplied, hashlib.sha256(canonical).hexdigest())

    def test_exact_branch_filters_and_no_interactive_or_main_trigger(self) -> None:
        reserve = RESERVE.read_text(encoding="utf-8")
        finalize = FINALIZE.read_text(encoding="utf-8")
        self.assertIn(f"      - {RESERVE_BRANCH}\n", reserve)
        self.assertNotIn(FINALIZE_BRANCH, reserve.split("permissions:", 1)[0])
        self.assertIn(f"      - {FINALIZE_BRANCH}\n", finalize)
        self.assertNotIn(RESERVE_BRANCH, finalize.split("permissions:", 1)[0])
        for text in (reserve, finalize):
            trigger = text.split("permissions:", 1)[0]
            self.assertNotRegex(trigger, r"(?m)^\s*- main\s*$")
            self.assertNotIn("workflow_dispatch", text)
            self.assertNotIn("repository_dispatch", text)
            self.assertNotRegex(text, r"(?m)^\s*environment\s*:")

        general_ci = GENERAL_CI.read_text(encoding="utf-8")
        self.assertIn(f"      - {RESERVE_BRANCH}\n", general_ci)
        self.assertIn(f"      - {FINALIZE_BRANCH}\n", general_ci)

    def test_effect_boundaries_and_secret_wiring(self) -> None:
        for path in (RESERVE, FINALIZE):
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            self.assertNotIn("datatracker.ietf.org", lowered)
            self.assertNotIn("gh release", lowered)
            self.assertNotIn("--token", lowered)
            secret_expressions = re.findall(
                r"\$\{\{\s*secrets\.[A-Za-z0-9_]+\s*\}\}", text
            )
            self.assertTrue(secret_expressions)
            self.assertEqual(
                set(secret_expressions), {"${{ secrets.ZENODO_ACCESS_TOKEN }}"}
            )
        reserve = RESERVE.read_text(encoding="utf-8")
        finalize = FINALIZE.read_text(encoding="utf-8")
        self.assertIn('release_path = "/releases/tags/"', finalize)
        self.assertIn('api("GET", release_path, missing_ok=True)', finalize)
        self.assertIn('"github_release_object_absence_verified": True', finalize)
        self.assertNotRegex(
            finalize,
            r'api\("(?:POST|PATCH|PUT|DELETE)",\s*(?:release_path|"/releases)',
        )
        self.assertIn(
            ".qikvrt/release/effect-ack-universality/zenodo-reservation.json",
            reserve,
        )
        self.assertIn(
            ".qikvrt/release/effect-ack-universality/zenodo-finalization.json",
            finalize,
        )
        self.assertIn("tools/qikvrt_build_zenodo_manifest.py", finalize)
        self.assertIn(
            "--manifest .qikvrt/release/effect-ack-universality/zenodo-final-manifest.json",
            finalize,
        )
        self.assertIn("--source-commit \"$SOURCE_COMMIT\"", finalize)
        self.assertIn("--source-tree \"$SOURCE_TREE\"", finalize)
        self.assertNotRegex(reserve, r"runner\.temp[^\n]*zenodo-reservation")
        self.assertNotRegex(finalize, r"runner\.temp[^\n]*zenodo-finalization")

    def test_finalize_binds_reserved_software_doi_before_publication(self) -> None:
        finalize = FINALIZE.read_text(encoding="utf-8")
        build = finalize.index(
            "Build deterministic exact-tree software archive and final manifest"
        )
        bind = finalize.index(
            "Bind reserved software DOI into transient metadata and revalidate"
        )
        publish = finalize.index(
            "Finalize both Zenodo depositions through the hash-bound client"
        )
        self.assertLess(build, bind)
        self.assertLess(bind, publish)
        block = finalize[bind:publish]
        self.assertIn(
            'reserved_doi = manifest.get("reserved_dois", {}).get("software")',
            block,
        )
        self.assertIn(
            'reservation.get("software", {}).get("doi") != reserved_doi',
            block,
        )
        self.assertIn('if metadata.get("doi") is not None:', block)
        self.assertIn('prefix = "Reserved DOI for this software version:"', block)
        self.assertIn("normalized = validate_manifest(manifest, root, final=True)", block)
        self.assertIn("verified = verify_manifest_files(", block)
        self.assertIn("_validate_final_dois(normalized, reservation, verified)", block)
        self.assertNotIn("10.5281/zenodo.", block)

    def test_reserved_software_doi_binding_executes_idempotently_and_fail_closed(
        self,
    ) -> None:
        step = "Bind reserved software DOI into transient metadata and revalidate"
        source = embedded_python_for_step(
            FINALIZE.read_text(encoding="utf-8"), step
        )
        doi = "10.5281/zenodo.12345678"
        sentence = f"Reserved DOI for this software version: {doi}."
        with tempfile.TemporaryDirectory(prefix="qikvrt-doi-binding-") as raw:
            root = pathlib.Path(raw)
            manifest_path = root / "manifest.json"
            reservation_path = root / "reservation.json"
            manifest = {
                "reserved_dois": {"software": doi},
                "software": {"metadata": {"notes": "Bounded release metadata."}},
            }
            reservation = {"software": {"doi": doi}}
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            reservation_path.write_text(json.dumps(reservation), encoding="utf-8")

            def validate(value, repository_root, *, final):
                self.assertIsInstance(repository_root, pathlib.Path)
                self.assertTrue(final)
                return value

            def verify(value, repository_root, token):
                self.assertEqual(value["software"]["metadata"]["notes"].count(sentence), 1)
                self.assertIsInstance(repository_root, pathlib.Path)
                self.assertEqual(token, "qikvrt-no-secret-local-validation-sentinel")
                return {}

            def validate_dois(value, reservation_value, verified):
                self.assertEqual(value["reserved_dois"]["software"], doi)
                self.assertEqual(reservation_value["software"]["doi"], doi)
                self.assertEqual(verified, {})

            environment = {
                "FINAL_MANIFEST": os.fspath(manifest_path),
                "RESERVATION_RESULT": os.fspath(reservation_path),
            }
            with mock.patch.dict(os.environ, environment), mock.patch.multiple(
                "tools.qikvrt_zenodo_actions",
                validate_manifest=validate,
                verify_manifest_files=verify,
                _validate_final_dois=validate_dois,
            ):
                exec(compile(source, f"{FINALIZE}:{step}", "exec"), {})
                exec(compile(source, f"{FINALIZE}:{step}", "exec"), {})

                enriched = json.loads(manifest_path.read_text(encoding="utf-8"))
                self.assertEqual(
                    enriched["software"]["metadata"]["notes"].count(sentence), 1
                )
                enriched["software"]["metadata"]["notes"] = (
                    "Reserved DOI for this software version: 10.5281/zenodo.87654321."
                )
                manifest_path.write_text(json.dumps(enriched), encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "conflicting self-DOI"):
                    exec(compile(source, f"{FINALIZE}:{step}", "exec"), {})

    def test_state_branch_reads_single_ref_and_patches_plural_refs(self) -> None:
        finalize = FINALIZE.read_text(encoding="utf-8")
        self.assertEqual(
            finalize.count('get_ref_path = "/git/ref/" + encoded_ref'), 2
        )
        self.assertEqual(
            finalize.count('update_ref_path = "/git/refs/" + encoded_ref'), 2
        )
        self.assertEqual(
            finalize.count('ref = api("GET", get_ref_path, missing_ok=True)'), 2
        )
        self.assertEqual(
            finalize.count(
                'api("PATCH", update_ref_path, {"sha": commit, "force": False})'
            ),
            2,
        )
        self.assertNotIn('api("PATCH", get_ref_path', finalize)
        self.assertNotIn('api("PATCH", ref_path', finalize)

    def test_workflows_pin_external_actions_by_full_sha(self) -> None:
        for path in (RESERVE, FINALIZE, ADAPTIVE_RUNTIME):
            text = path.read_text(encoding="utf-8")
            uses = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", text)
            self.assertTrue(uses)
            for reference in uses:
                self.assertRegex(reference, r"^[^@]+@[0-9a-f]{40}$")

    def test_adaptive_runtime_exact_renderer_capability_is_fail_closed(self) -> None:
        text = ADAPTIVE_RUNTIME.read_text(encoding="utf-8")
        self.assertEqual(text.count("exact_renderer_optional: false"), 2)
        self.assertEqual(text.count("exact_renderer_optional: true"), 4)
        self.assertEqual(text.count("id: renderer-python"), 2)
        self.assertEqual(
            text.count("continue-on-error: ${{ matrix.exact_renderer_optional }}"),
            2,
        )
        self.assertGreaterEqual(
            text.count("steps.renderer-python.outcome == 'success'"), 12
        )
        self.assertGreaterEqual(
            text.count("steps.renderer-python.outcome == 'failure'"), 8
        )
        self.assertIn(
            "Revalidate exact POSIX renderer before cache publication", text
        )
        self.assertIn(
            "Revalidate exact Windows renderer before cache publication", text
        )
        self.assertIn("qikvrt-runtime-v4-py-3.12.13-success-", text)
        self.assertIn("qikvrt-runtime-v4-py-3.12.13-unavailable-", text)
        self.assertIn("path: .qikvrt/toolchains/gh", text)
        self.assertNotIn("restore-keys:", text)
        self.assertNotIn("enableCrossOsArchive: true", text)
        exact_restore = text[
            text.index("Restore exact renderer and GH cache") :
            text.index("Restore GH-only cache without exact renderer")
        ]
        exact_save = text[
            text.index("Save verified exact renderer and GH cache") :
            text.index("Save verified GH-only cache without exact renderer")
        ]
        for cache_step in (exact_restore, exact_save):
            self.assertIn(
                ".qikvrt/toolchains/xml2rfc/3.34.0/"
                "python-3.12.13/*/wheelhouse",
                cache_step,
            )
            self.assertNotIn("/venv", cache_step)
            self.assertNotIn("\\venv", cache_step)
        self.assertIn(
            'renderer=".qikvrt/toolchains/xml2rfc/3.34.0/'
            'python-3.12.13/$renderer_platform/venv/bin/xml2rfc"',
            text,
        )
        self.assertIn(
            "'.qikvrt\\toolchains\\xml2rfc\\3.34.0\\python-3.12.13\\"
            "windows-amd64\\venv\\Scripts\\xml2rfc.exe'",
            text,
        )
        exact_save = text.index("Save verified exact renderer and GH cache")
        posix_recheck = text.index(
            "Revalidate exact POSIX renderer before cache publication"
        )
        windows_recheck = text.index(
            "Revalidate exact Windows renderer before cache publication"
        )
        self.assertLess(posix_recheck, exact_save)
        self.assertLess(windows_recheck, exact_save)
        posix_bootstrap = (ROOT / "tools/bootstrap-gh.sh").read_text(
            encoding="utf-8"
        )
        windows_bootstrap = (ROOT / "tools/bootstrap-gh.ps1").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("gh version $VERSION (2026-07-02)", posix_bootstrap)
        self.assertNotIn("gh version $Version (2026-07-02)", windows_bootstrap)
        self.assertIn("^gh version 2\\.96\\.0", posix_bootstrap)
        self.assertIn("[regex]::Escape($Version)", windows_bootstrap)
        self.assertNotIn(
            '"gh_${Version}_windows_${Arch}\\bin\\gh.exe"',
            windows_bootstrap,
        )
        self.assertIn("Join-Path $verifyDir 'bin\\gh.exe'", windows_bootstrap)
        self.assertIn("Join-Path $ExtractDir 'bin\\gh.exe'", windows_bootstrap)

    def test_embedded_python_is_syntactically_valid(self) -> None:
        pattern = re.compile(r"python -B - <<'PY'\n(.*?)\n\s*PY(?:\n|$)", re.S)
        for path in (RESERVE, FINALIZE):
            blocks = pattern.findall(path.read_text(encoding="utf-8"))
            self.assertTrue(blocks)
            for index, block in enumerate(blocks, 1):
                lines = block.splitlines()
                indentation = min(
                    len(line) - len(line.lstrip()) for line in lines if line.strip()
                )
                source = "\n".join(
                    line[indentation:] if line.strip() else "" for line in lines
                )
                compile(source, f"{path}:embedded-python-{index}", "exec")

    def test_two_commit_parent_tree_fixture(self) -> None:
        """Prove the selector is parent A, not authorization marker HEAD B."""
        with tempfile.TemporaryDirectory(prefix="qikvrt-release-workflow-") as raw:
            repository = pathlib.Path(raw)
            run_git(repository, "init", "-q")
            run_git(repository, "config", "user.name", "QIK-VRT fixture")
            run_git(repository, "config", "user.email", "fixture@example.invalid")
            marker_path = repository / MARKER_PATH
            marker_path.parent.mkdir(parents=True)
            inert = json.loads(MARKER.read_text(encoding="utf-8"))
            marker_path.write_text(
                json.dumps(inert, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            run_git(repository, "add", MARKER_PATH)
            run_git(repository, "commit", "-q", "-m", "candidate A with inert marker")
            source_commit = run_git(repository, "rev-parse", "HEAD")
            source_tree = run_git(repository, "show", "-s", "--format=%T", "HEAD")

            active = copy.deepcopy(inert)
            active["state"] = "reserve"
            active["confirm"] = "RESERVE_ZENODO_DRAFT_ONLY_NO_PUBLISH"
            active["release"]["expected_source_commit"] = source_commit
            active["release"]["expected_source_tree"] = source_tree
            active["authorization_payload_sha256"] = "0" * 64
            projection = copy.deepcopy(active)
            projection.pop("authorization_payload_sha256")
            active["authorization_payload_sha256"] = hashlib.sha256(
                json.dumps(
                    projection,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            marker_path.write_text(
                json.dumps(active, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            run_git(repository, "add", MARKER_PATH)
            run_git(repository, "commit", "-q", "-m", "marker-only authorization B")

            self.assertEqual(run_git(repository, "rev-parse", "HEAD^"), source_commit)
            self.assertEqual(
                run_git(repository, "show", "-s", "--format=%T", "HEAD^"),
                source_tree,
            )
            self.assertNotEqual(
                run_git(repository, "show", "-s", "--format=%T", "HEAD"),
                source_tree,
            )
            self.assertEqual(
                run_git(
                    repository,
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    "HEAD^",
                    "HEAD",
                ).splitlines(),
                [MARKER_PATH],
            )
            for path in (RESERVE, FINALIZE):
                text = path.read_text(encoding="utf-8")
                self.assertIn('["git", "show", "-s", "--format=%T", "HEAD^"]', text)
                self.assertNotIn('["git", "rev-parse", "HEAD^{tree}"]', text)


class GeneralCITerminalDispositionTests(unittest.TestCase):
    """Execute the real terminal step; a skipped writer is not a failed test."""

    SCOPE = (
        "github.event_name == 'pull_request' && "
        "github.event.pull_request.head.repo.full_name == github.repository"
    )
    STEP = "      - name: Enforce terminal tested-fixpoint disposition\n"

    def run_terminal(self, required: str, full_test: str, fixpoint: str):
        block = GENERAL_CI.read_text(encoding="utf-8").split(self.STEP, 1)[1]
        block = block.split("\n      - name:", 1)[0]
        metadata, script = block.split("        run: |\n", 1)
        values = {
            self.SCOPE: required,
            "steps.full_test.outcome": full_test,
            "steps.fixpoint.outcome": fixpoint,
        }

        def render(text: str) -> str:
            return re.sub(
                r"\$\{\{\s*(.*?)\s*\}\}",
                lambda match: values[match.group(1)],
                text,
            )

        environment = {"PATH": os.environ["PATH"]}
        for name, value in re.findall(
            r"^          ([A-Z_]+): (.+)$", metadata, re.MULTILINE
        ):
            environment[name] = render(value)
        return subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", render(textwrap.dedent(script))],
            env=environment,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    def test_push_dispatch_and_fork_pr_accept_successful_exact_checkout(self):
        # These events all exclude the writer under the scope checked below.
        for event, head_repository in (
            ("push", ""),
            ("workflow_dispatch", ""),
            ("pull_request", "contributor/qik-vrt"),
        ):
            with self.subTest(event=event, head_repository=head_repository):
                required = str(
                    event == "pull_request"
                    and head_repository == "ingolf-lohmann/qik-vrt"
                ).lower()
                self.assertEqual(required, "false")
                result = self.run_terminal(required, "success", "skipped")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("QIKVRT_TERMINAL_DISPOSITION PASS", result.stdout)

    def test_real_make_failure_remains_failure_in_both_paths(self):
        workflow = GENERAL_CI.read_text(encoding="utf-8")

        def script_for(name):
            block = workflow.split("      - name: " + name + "\n", 1)[1]
            block = block.split("\n      - ", 1)[0]
            return textwrap.dedent(block.split("        run: |\n", 1)[1])

        full_script = script_for(
            "Full compile, launcher, protocol, handler, security and TCP/IP tests"
        )
        fixpoint_script = script_for("Same-writer successor re-entry to tested fixpoint")
        with tempfile.TemporaryDirectory(prefix="qikvrt-ci-real-failure-") as raw:
            root = pathlib.Path(raw) / "source"
            root.mkdir()
            remote = pathlib.Path(raw) / "remote.git"
            run_git(pathlib.Path(raw), "init", "--bare", os.fspath(remote))
            run_git(root, "init")
            run_git(root, "config", "user.name", "CI regression")
            run_git(root, "config", "user.email", "ci-regression@example.invalid")
            (root / "Makefile").write_text("test:\n\t@exit 17\n", encoding="utf-8")
            (root / "REPOSITORY_FILE_MANIFEST.json").write_text(
                '{"files": []}\n', encoding="utf-8"
            )
            (root / "tools").mkdir()
            # Successful integrity generation must not hide a real test failure.
            (root / "tools/qikvrt_integrity.py").write_text(
                'MANIFEST_NAME = "REPOSITORY_FILE_MANIFEST.json"\n'
                'def build_outputs():\n'
                '    return None, None, None, {"files": []}\n',
                encoding="utf-8",
            )
            run_git(root, "add", ".")
            run_git(root, "commit", "-m", "test fixture")
            subject = run_git(root, "rev-parse", "HEAD")
            run_git(root, "remote", "add", "origin", os.fspath(remote))
            run_git(root, "push", "origin", "HEAD:refs/heads/fixture")
            environment = dict(
                os.environ, EXPECTED_HEAD=subject, TARGET_REF="fixture", MAX_SUCCESSORS="4",
            )
            full_result = subprocess.run(
                ["bash", "-c", full_script], cwd=root, env=environment,
                text=True, capture_output=True, timeout=20, check=False,
            )
            self.assertEqual(full_result.returncode, 2, full_result.stdout + full_result.stderr)
            self.assertIn("MAKE_TEST_EXIT=2", full_result.stdout)
            fixpoint_result = subprocess.run(
                ["bash", "-c", fixpoint_script], cwd=root, env=environment,
                text=True, capture_output=True, timeout=20, check=False,
            )
            self.assertNotEqual(fixpoint_result.returncode, 0)
            self.assertNotIn("QIKVRT_FIXPOINT_REACHED", fixpoint_result.stdout)
            self.assertEqual(run_git(root, "rev-parse", "HEAD"), subject)
            self.assertEqual(run_git(remote, "rev-parse", "refs/heads/fixture"), subject)
            full_outcome = "success" if full_result.returncode == 0 else "failure"
            fixpoint_outcome = "success" if fixpoint_result.returncode == 0 else "failure"
            for required, outcome in (("false", "skipped"), ("true", fixpoint_outcome)):
                with self.subTest(fixpoint_required=required):
                    terminal = self.run_terminal(required, full_outcome, outcome)
                    self.assertNotEqual(terminal.returncode, 0)
                    self.assertNotIn("QIKVRT_TERMINAL_DISPOSITION PASS", terminal.stdout)

    def test_non_writer_test_failures_cannot_be_hidden_by_continue_on_error(self):
        for outcome in ("failure", "cancelled", "skipped", "", "unknown"):
            with self.subTest(outcome=outcome):
                result = self.run_terminal("false", outcome, "skipped")
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("QIKVRT_TERMINAL_DISPOSITION PASS", result.stdout)

    def test_same_repository_pr_requires_completed_fixpoint(self):
        for outcome in ("failure", "cancelled", "skipped", "", "unknown"):
            with self.subTest(outcome=outcome):
                result = self.run_terminal("true", "success", outcome)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("QIKVRT_TERMINAL_DISPOSITION PASS", result.stdout)

    def test_retested_successor_may_recover_failed_predecessor(self):
        result = self.run_terminal("true", "failure", "success")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("QIKVRT_TERMINAL_DISPOSITION PASS", result.stdout)

    def test_non_writer_rejects_unexpected_writer_execution(self):
        for outcome in ("success", "failure", "cancelled", "", "unknown"):
            with self.subTest(outcome=outcome):
                result = self.run_terminal("false", "success", outcome)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("QIKVRT_TERMINAL_DISPOSITION PASS", result.stdout)

    def test_invalid_scope_is_not_success(self):
        for required in ("", "unknown"):
            with self.subTest(required=required):
                self.assertNotEqual(
                    self.run_terminal(required, "success", "success").returncode, 0
                )

    def test_terminal_gate_uses_the_actual_writer_scope_and_raw_outcomes(self):
        workflow = GENERAL_CI.read_text(encoding="utf-8")
        writer = workflow.split("        id: fixpoint\n", 1)[1].split(
            "        env:\n", 1
        )[0]
        terminal = workflow.split(self.STEP, 1)[1]
        self.assertIn("if: always() && " + self.SCOPE, writer)
        self.assertIn("if: always()", terminal)
        self.assertNotIn("continue-on-error:", terminal)
        self.assertIn("FIXPOINT_REQUIRED: ${{ " + self.SCOPE + " }}", terminal)
        self.assertIn("FULL_TEST_OUTCOME: ${{ steps.full_test.outcome }}", terminal)
        self.assertIn("FIXPOINT_OUTCOME: ${{ steps.fixpoint.outcome }}", terminal)
        self.assertNotIn(".conclusion", terminal)

    def test_native_command_runs_after_success_and_failure_and_preserves_receipt(self):
        workflow = GENERAL_CI.read_text(encoding="utf-8")
        marker = "      - name: Consume repository-native Never stop CI command\n"
        block = workflow.split(marker, 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("if: always()", block)
        self.assertLess(workflow.index(self.STEP), workflow.index(marker))
        self.assertLess(workflow.index(marker), workflow.index("      - name: Upload audit\n"))
        script = textwrap.dedent(block.split("        run: |\n", 1)[1])
        paths = (
            "tools/qikvrt_autonomous_self_heal.py",
            "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json",
            "state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json",
            "tools/qikvrt_mesh_recovery.py",
            "tools/qikvrt_seed_common.py",
            "tools/qikvrt_subprocess.py",
            "tools/qikvrt_workflow_executor.py",
            "policy/QIKVRT_FULL_NODE_RECOVERY_AND_DERIVATION_V1.json",
        )
        for outcome in ("success", "failure", "cancelled", "skipped", "unknown"):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw)
                for path in paths:
                    file = root / path
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes((ROOT / path).read_bytes())
                run_git(root, "init")
                run_git(root, "config", "user.name", "native CI fixture")
                run_git(root, "config", "user.email", "native-ci@example.invalid")
                run_git(root, "add", ".")
                run_git(root, "commit", "-m", "bound native continuation fixture")
                head = run_git(root, "rev-parse", "HEAD")
                tree = run_git(root, "rev-parse", "HEAD^{tree}")
                env = dict(os.environ, CI_TERMINAL_OUTCOME=outcome,
                           GITHUB_REPOSITORY="owner/fixture", GITHUB_EVENT_NAME="push",
                           GITHUB_RUN_ID="101", GITHUB_RUN_ATTEMPT="2")
                result = subprocess.run(["bash", "-c", script], cwd=root, env=env,
                                        text=True, capture_output=True, timeout=10)
                receipt = json.loads((root / ".qikvrt/runtime/ci-diagnostics/CI_CONTINUATION.json").read_text())
                if outcome == "unknown":
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual("BLOCK", receipt["state"])
                    continue
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual("Never stop CI", receipt["owner_command"]["literal"])
                self.assertEqual((head, tree), (receipt["head"], receipt["tree"]))
                self.assertEqual(outcome, receipt["execution"]["terminal_test_outcome"])
                self.assertEqual("EFFECT_ACK_CONTINUE", receipt["state"])
                self.assertFalse(receipt["global_ci_stop"])
                self.assertFalse(receipt["ordinary_release"])
                self.assertFalse(receipt["effect_ack_done"])
                self.assertFalse(receipt["writer_authorization_implied"])
                self.assertFalse(receipt["execution_routing"]["external_trigger_owns_repository_execution"])
                self.assertTrue(receipt["execution_routing"]["all_other_external_dependencies_in_scope"])
                self.assertEqual(hashlib.sha256((root / paths[-1]).read_bytes()).hexdigest(),
                                 receipt["dependency_policy_sha256"])
                self.assertEqual(head, run_git(root, "rev-parse", "HEAD"))

    def test_rehashed_successor_cannot_remove_or_weaken_native_command(self):
        paths = (
            "tools/qikvrt_autonomous_self_heal.py",
            "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json",
            "state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json",
            "tools/qikvrt_mesh_recovery.py",
            "tools/qikvrt_seed_common.py",
            "tools/qikvrt_subprocess.py",
            "tools/qikvrt_workflow_executor.py",
            "policy/QIKVRT_FULL_NODE_RECOVERY_AND_DERIVATION_V1.json",
        )
        for change in ("remove", "stop_on_failure", "dirty_bytes", "stale_head",
                       "external_executor", "chatgpt_only", "policy_missing", "dirty_dependency_policy"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as raw:
                root = pathlib.Path(raw)
                for path in paths:
                    file = root / path
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes((ROOT / path).read_bytes())
                run_git(root, "init")
                run_git(root, "config", "user.name", "negative native fixture")
                run_git(root, "config", "user.email", "negative@example.invalid")
                run_git(root, "add", ".")
                run_git(root, "commit", "-m", "original fixture")
                original = run_git(root, "rev-parse", "HEAD")
                policy = root / paths[1]
                value = json.loads(policy.read_text())
                if change == "remove":
                    del value["continuous_integration"]
                elif change == "stop_on_failure":
                    value["continuous_integration"]["first_failure_terminal"] = True
                elif change == "external_executor":
                    value["execution_routing"]["external_trigger_owns_repository_execution"] = True
                elif change in {"chatgpt_only", "policy_missing", "dirty_dependency_policy"}:
                    dep_path = root / paths[-1]
                    dep_policy = json.loads(dep_path.read_text())
                    if change == "policy_missing":
                        del dep_policy["post_binding_repository_mirroring"]
                    elif change == "chatgpt_only":
                        dep_policy["post_binding_repository_mirroring"]["chatgpt_only"] = True
                    else:
                        dep_policy["post_binding_repository_mirroring"]["owner_statement"] += " changed"
                    dep_path.write_text(json.dumps(dep_policy))
                else:
                    value["contract_id"] += "-successor"
                policy.write_text(json.dumps(value))
                if change not in {"dirty_bytes", "dirty_dependency_policy"}:
                    run_git(root, "add", ".")
                    run_git(root, "commit", "-m", "rebound successor fixture")
                reference = original if change == "stale_head" else run_git(root, "rev-parse", "HEAD")
                result = subprocess.run([
                    "python3", "-B", str(root / paths[0]), "ci-continuation",
                    "--reference", reference, "--test-outcome", "success",
                    "--repository-name", "owner/fixture", "--event", "push",
                    "--run-id", "101", "--run-attempt", "1",
                ], cwd=root, capture_output=True, text=True, timeout=10)
                self.assertNotEqual(0, result.returncode)
                self.assertEqual("BLOCK", json.loads(result.stdout)["state"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
