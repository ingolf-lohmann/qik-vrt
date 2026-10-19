from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "release/observer-relative-retrocausality-current-synthesis-zenodo-v2"
    / "finalize_authorized_controls.py"
)
WORKFLOW = (
    ROOT
    / ".github/workflows/qikvrt_observer_relative_retrocausality_zenodo_publish.yml"
)
SPEC = importlib.util.spec_from_file_location("orr_zenodo_finalizer", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
controls = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = controls
SPEC.loader.exec_module(controls)


class ObserverRelativeRetrocausalityZenodoFinalizerTests(unittest.TestCase):
    @staticmethod
    def run_command(
        arguments: list[str],
        *,
        cwd: Path,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            arguments,
            cwd=cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

    def action(self) -> dict[str, object]:
        state = controls.release_state()
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        source_head = completed.stdout.strip()
        authorization_id = "qikvrt-orr-zenodo-v2-test-20260814-001"
        statement = controls.publish._canonical_authorization_statement(
            authorization_id,
            controls.PUBLICATION_ID,
            state["receipt_identity"]["sha256"],
            state["metadata_sha256"],
            state["bundle_identity"]["sha256"],
        )
        return {
            "authorization_id": authorization_id,
            "nonce": "a" * 64,
            "source_head": source_head,
            "authorized_at": dt.datetime.now(dt.timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "exact_statement": statement,
        }

    def action_input(self, action: dict[str, object]) -> dict[str, object]:
        return {
            "schema": controls.INPUT_SCHEMA,
            "principal": controls.PRINCIPAL,
            **action,
        }

    def test_builds_exact_controls_without_writing(self) -> None:
        state = controls.release_state()
        action = self.action()
        authorization_raw, manifest_raw = controls.build_controls(action, state)
        authorization = json.loads(authorization_raw)
        manifest = json.loads(manifest_raw)
        self.assertEqual(authorization["source_head"], action["source_head"])
        self.assertEqual(authorization["authorization_event"]["exact_statement"], action["exact_statement"])
        self.assertEqual(authorization["principal"], controls.PRINCIPAL)
        self.assertEqual(len(authorization["uploads"]), 21)
        self.assertEqual(manifest["schema"], controls.publish.SCHEMA_V2)
        self.assertEqual(manifest["source_head"], action["source_head"])
        self.assertEqual(len(manifest["files"]), 21)

    def test_rejects_tampered_authorization_statement_before_writing(self) -> None:
        state = controls.release_state()
        action = self.action()
        action["exact_statement"] = "AUTHORIZE_EXACT_UPLOAD altered"
        with tempfile.TemporaryDirectory() as temporary:
            input_path = Path(temporary) / "authorization.json"
            input_path.write_text(
                json.dumps(self.action_input(action)), encoding="utf-8"
            )
            with self.assertRaisesRegex(SystemExit, "exact statement differs"):
                controls.load_action(input_path, state)

    def test_accepts_canonical_external_authorization_input(self) -> None:
        state = controls.release_state()
        action = self.action()
        with tempfile.TemporaryDirectory() as temporary:
            input_path = Path(temporary) / "authorization.json"
            input_path.write_text(
                json.dumps(self.action_input(action)), encoding="utf-8"
            )
            parsed = controls.load_action(input_path, state)
        self.assertEqual(parsed, action)

    def test_rejects_authorization_before_the_selected_source_commit(self) -> None:
        state = controls.release_state()
        action = self.action()
        source_time = controls.source_commit_time(action["source_head"])
        returned_time = controls.parse_time(
            state["returned_at"], "prepublication return timestamp"
        )
        self.assertGreater(source_time, returned_time)
        action["authorized_at"] = (
            returned_time + (source_time - returned_time) / 2
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        with tempfile.TemporaryDirectory() as temporary:
            input_path = Path(temporary) / "authorization.json"
            input_path.write_text(
                json.dumps(self.action_input(action)), encoding="utf-8"
            )
            with self.assertRaisesRegex(SystemExit, "predates the selected source commit"):
                controls.load_action(input_path, state)

    def test_rejects_future_dated_authorization(self) -> None:
        state = controls.release_state()
        action = self.action()
        action["authorized_at"] = (
            dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        with tempfile.TemporaryDirectory() as temporary:
            input_path = Path(temporary) / "authorization.json"
            input_path.write_text(
                json.dumps(self.action_input(action)), encoding="utf-8"
            )
            with self.assertRaisesRegex(SystemExit, "future-dated"):
                controls.load_action(input_path, state)

    def test_release_state_has_exact_proof_bearing_files(self) -> None:
        state = controls.release_state()
        self.assertEqual(len(state["files"]), 21)
        self.assertEqual(len(state["authorization_uploads"]), 21)
        self.assertEqual(state["metadata"]["creators"], [{"name": "Lohmann, Ingolf"}])
        self.assertGreaterEqual(state["returned_at"], "2026-08-14T09:25:59Z")

    def test_workflow_requires_the_confirmed_goldkelch_execution_account(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.actor == 'Goldkelch'", workflow)
        self.assertIn("github.triggering_actor == 'Goldkelch'", workflow)
        self.assertIn('test "$GITHUB_ACTOR" = \'Goldkelch\'', workflow)
        self.assertIn('test "$GITHUB_TRIGGERING_ACTOR" = \'Goldkelch\'', workflow)
        self.assertNotIn("github.actor == 'ingolf-lohmann'", workflow)
        self.assertNotIn("github.triggering_actor == 'ingolf-lohmann'", workflow)

    def test_write_then_committed_descendant_check_is_local_only(self) -> None:
        """Exercise real source/descendant commits without historical Git objects."""
        state = controls.release_state()
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            isolated = temporary_root / "isolated"
            isolated.mkdir()
            # Copy the exact frozen candidate and its active validators. Historical
            # publication controls belong to their original source, not this fixture.
            paths = {entry["path"] for entry in state["files"]}
            receipt = controls.load_json(state["receipt_identity"]["path"])
            paths.update(entry["path"] for entry in receipt["original_files"])
            paths.update(controls.machine_proof.publication_contract_blobs(ROOT, v3=False))
            paths.update(
                {
                    SCRIPT.relative_to(ROOT).as_posix(),
                    f"{controls.RELEASE_RELATIVE}/PUBLISH_REQUEST_DRAFT.json",
                    f"{controls.RELEASE_RELATIVE}/ZENODO_METADATA_DRAFT.json",
                    "tools/qikvrt_zenodo_actions.py",
                    "tools/qikvrt_zenodo_machine_proof.py",
                    "tools/qikvrt_zenodo_publish.py",
                }
            )
            for relative in sorted(paths):
                target = isolated / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            self.run_command(
                ["git", "init", "--initial-branch=main"], cwd=isolated
            )
            for key, value in (
                ("user.name", "Zenodo Finalizer Test"),
                ("user.email", "zenodo-finalizer-test@example.invalid"),
                ("commit.gpgsign", "false"),
                ("core.autocrlf", "false"),
                ("core.hooksPath", str(temporary_root / "empty-hooks")),
            ):
                self.run_command(["git", "config", "--local", key, value], cwd=isolated)
            self.run_command(["git", "add", "."], cwd=isolated)
            self.run_command(
                ["git", "commit", "-m", "test: freeze exact local candidate"], cwd=isolated
            )
            # No fetch, skip or HEAD substitution for the archived source occurs.
            # The two newly materialized controls must still pass the real gate.
            isolated_script = (
                isolated
                / "release/observer-relative-retrocausality-current-synthesis-zenodo-v2"
                / "finalize_authorized_controls.py"
            )
            self.assertTrue(isolated_script.is_file())
            source_head = self.run_command(
                ["git", "rev-parse", "HEAD"], cwd=isolated
            ).stdout.strip()
            self.assertEqual(
                self.run_command(
                    ["git", "rev-list", "--count", "HEAD"], cwd=isolated
                ).stdout.strip(),
                "1",
            )
            action = self.action()
            action["source_head"] = source_head
            action["nonce"] = "b" * 64
            input_path = temporary_root / "authorization.json"
            input_path.write_text(
                json.dumps(self.action_input(action)), encoding="utf-8"
            )
            environment = dict(os.environ)
            environment.pop("GITHUB_REPOSITORY", None)
            environment.pop("GITHUB_SHA", None)
            environment.pop("PYTHONPATH", None)
            written = self.run_command(
                [
                    sys.executable,
                    "-B",
                    str(isolated_script),
                    "--write",
                    "--authorization-input",
                    str(input_path),
                ],
                cwd=isolated,
                environment=environment,
            )
            self.assertIn("PASS materialized final controls uploads=21", written.stdout)
            self.assertTrue((isolated / controls.AUTHORIZATION_PATH.relative_to(ROOT)).is_file())
            self.assertTrue((isolated / controls.MANIFEST_PATH.relative_to(ROOT)).is_file())
            with self.assertRaises(subprocess.CalledProcessError) as uncommitted:
                self.run_command(
                    [sys.executable, "-B", str(isolated_script), "--check"],
                    cwd=isolated,
                    environment=environment,
                )
            self.assertIn("repository worktree must be clean", uncommitted.exception.stderr)
            self.run_command(
                [
                    "git",
                    "add",
                    controls.AUTHORIZATION_PATH.relative_to(ROOT).as_posix(),
                    controls.MANIFEST_PATH.relative_to(ROOT).as_posix(),
                ],
                cwd=isolated,
            )
            self.run_command(
                [
                    "git",
                    "commit",
                    "-m",
                    "test: materialize final Zenodo controls",
                ],
                cwd=isolated,
            )
            self.assertEqual(
                self.run_command(
                    ["git", "rev-parse", "HEAD^"], cwd=isolated
                ).stdout.strip(),
                source_head,
            )
            checked = self.run_command(
                [sys.executable, "-B", str(isolated_script), "--check"],
                cwd=isolated,
                environment=environment,
            )
            self.assertIn("PASS verified final controls uploads=21", checked.stdout)


if __name__ == "__main__":
    unittest.main()
