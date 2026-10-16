from __future__ import annotations
import json
import hashlib
import importlib.util
import os
import subprocess
import sys
import unittest
import tempfile
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs/publications/2026-08-04-pre-spacetime-ontology"
ROUTER = Path(__file__).resolve().parents[1] / "tools/qikvrt_publication_router.py"

class PublicationRouterTests(unittest.TestCase):
    def test_router_is_fail_closed_and_effect_free(self) -> None:
        cp = subprocess.run(
            [sys.executable, "-B", str(ROUTER), str(ROOT), "--json"],
            check=True,
            text=True,
            capture_output=True,
        )
        data = json.loads(cp.stdout)
        self.assertEqual(data["repository"], "CANDIDATE")
        self.assertEqual(data["zenodo"], "STAGED_REQUIRES_EXPLICIT_REQUEST")
        self.assertEqual(data["ietf"], "NO_SUBMISSION_SCOPE_NOTE_ONLY")
        self.assertIs(data["external_effect_performed"], False)

    def test_ietf_disposition_is_non_mutating(self) -> None:
        data = json.loads((ROOT / "IETF_DISPOSITION.json").read_text(encoding="utf-8"))
        self.assertIs(data["protocol_change_required"], False)
        self.assertIs(data["ietf_mutation_authorized"], False)


class RequestedAuthorityPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.manifest = self.root / "publish.json"
        self.manifest.write_bytes(b'{"candidate":"exact"}\n')
        self.raw = self.manifest.read_bytes()
        self.digest = hashlib.sha256(self.raw).hexdigest()
        spec = importlib.util.spec_from_file_location("requested_publication_router", ROUTER)
        self.router = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.router)
        for args in (("init", "-q"), ("add", "publish.json"),
                     ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                      "commit", "-qm", "Exact candidate")):
            self.git(*args)
        self.head = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        self.repository = "ingolf-lohmann/qik-vrt"
        self.env = {"GITHUB_REPOSITORY": self.repository, "GITHUB_REF": "refs/heads/main",
                    "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_SHA": self.head}
        self.normalized = {"schema": "v2", "repository": self.repository,
                           "evidence_path": self.root / "zenodo-publication.json"}
        self.executor = SimpleNamespace(
            load_repository_roles=mock.Mock(return_value={"AUTHORITY": self.repository}),
            _git=lambda root, *args: self.git(*args),
            read_authority_main=mock.Mock(return_value={"repository": self.repository,
                                                        "main_head": self.head, "main_tree": self.tree}))
        self.publisher = SimpleNamespace(
            PRODUCTION_REPOSITORY=self.repository, SCHEMA_V2="v2",
            _safe_relative=lambda root, relative, *args, **kw: root / relative,
            zenodo=SimpleNamespace(read_regular_file=lambda path, limit: path.read_bytes(),
                                   MAX_JSON_BYTES=1024),
            load_manifest=mock.Mock(return_value=self.normalized),
            _validate_repository_source_head=mock.Mock(return_value=self.head),
            _validate_origin_repository=mock.Mock(),
            publish=mock.Mock(return_value={"phase": "public_verified"}))
        self.editor = SimpleNamespace(
            load_manifest=mock.Mock(return_value=self.normalized),
            _validate_repository_heads=mock.Mock(return_value=self.head),
            edit_published_metadata=mock.Mock(return_value={"phase": "public_verified"}))
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(self.router, "_publication_dependencies", return_value=(
            self.executor, self.publisher, self.editor)).start()
        mock.patch.dict(os.environ, self.env).start()

    def git(self, *args) -> str:
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def request(self, operation="publish", execute=False, **changes):
        values = dict(root=self.root, operation=operation, manifest_relative="publish.json",
                      manifest_sha256=self.digest, expected_head=self.head,
                      expected_tree=self.tree, execute=execute)
        values.update(changes)
        return self.router.requested_zenodo(**values)

    def assert_no_effect(self):
        self.publisher.publish.assert_not_called()
        self.editor.edit_published_metadata.assert_not_called()

    def test_preflight_is_read_only_even_with_a_valid_candidate(self):
        result = self.request()
        self.assertEqual(result["manifest_blob_sha1"], self.git("rev-parse", "HEAD:publish.json"))
        self.assertFalse(result["external_effect_performed"])
        self.assertFalse(result["effect_ack_done"])
        self.executor.read_authority_main.assert_called_once_with(self.root)
        self.assert_no_effect()

    def test_explicit_effect_reuses_exact_existing_publisher_once(self):
        result = self.request(execute=True)
        self.publisher.publish.assert_called_once_with(self.manifest, self.root)
        self.editor.edit_published_metadata.assert_not_called()
        self.assertTrue(result["publisher_invoked"])
        self.assertIsNone(result["external_effect_performed"])
        self.assertFalse(result["effect_ack_done"])

    def test_metadata_mode_never_calls_the_new_record_publisher(self):
        self.request("metadata-edit", execute=True)
        self.editor.edit_published_metadata.assert_called_once_with(self.manifest, self.root)
        self.publisher.publish.assert_not_called()

    def test_push_pr_wrong_repository_and_wrong_ref_cannot_execute(self):
        for key, wrong in (("GITHUB_EVENT_NAME", "push"), ("GITHUB_EVENT_NAME", "pull_request"),
                           ("GITHUB_REPOSITORY", "Goldkelch/qik-vrt"),
                           ("GITHUB_REF", "refs/heads/candidate"), ("GITHUB_SHA", "a" * 40)):
            with self.subTest(key=key, wrong=wrong), mock.patch.dict(os.environ, {key: wrong}):
                with self.assertRaises(ValueError):
                    self.request(execute=True)
        self.assert_no_effect()

    def test_missing_exact_identities_cannot_execute(self):
        for key in ("manifest_sha256", "expected_head", "expected_tree"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.request(execute=True, **{key: None})
        self.assert_no_effect()

    def test_wrong_digest_cannot_reach_the_publisher(self):
        with self.assertRaises(ValueError):
            self.request(execute=True, manifest_sha256="0" * 64)
        self.publisher.load_manifest.assert_not_called()
        self.assert_no_effect()

    def test_changed_worktree_bytes_with_matching_request_are_not_committed_bytes(self):
        self.manifest.write_bytes(b'{"candidate":"substituted"}\n')
        with self.assertRaises(ValueError):
            self.request(execute=True, manifest_sha256=hashlib.sha256(self.manifest.read_bytes()).hexdigest())
        self.assert_no_effect()

    def test_live_main_head_or_tree_drift_blocks_after_local_gates(self):
        for field in ("main_head", "main_tree"):
            self.executor.read_authority_main.return_value = {
                "repository": self.repository, "main_head": self.head, "main_tree": self.tree,
                field: "a" * 40}
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.request(execute=True)
        self.assert_no_effect()

    def test_legacy_or_wrong_manifest_repository_cannot_execute(self):
        for key, value in (("schema", "v1"), ("repository", "Goldkelch/qik-vrt")):
            with self.subTest(key=key), mock.patch.dict(self.normalized, {key: value}):
                with self.assertRaises(ValueError):
                    self.request(execute=True)
        self.assert_no_effect()

    def test_existing_machine_proof_or_owner_gate_failure_remains_blocking(self):
        self.publisher.load_manifest.side_effect = ValueError("candidate authorization missing")
        with self.assertRaises(ValueError):
            self.request(execute=True)
        self.executor.read_authority_main.assert_not_called()
        self.assert_no_effect()

    def test_manual_job_keeps_pr_validation_secret_free_and_never_pushes_main(self):
        workflow = (ROUTER.parent.parent / ".github/workflows/qikvrt_publication_router.yml").read_text()
        route, requested = workflow.split("  requested-zenodo:", 1)
        self.assertNotIn("secrets.", route)
        self.assertIn("github.event_name == 'pull_request'", route)
        self.assertIn("github.event_name == 'workflow_dispatch'", requested)
        self.assertIn("github.ref == 'refs/heads/main'", requested)
        self.assertIn("if: inputs.execute", requested)
        self.assertIn("make test", requested)
        self.assertIn("secrets.ZENODO_ACCESS_TOKEN", requested)
        self.assertNotIn("git push", requested)
        self.assertNotIn("--force", requested)

if __name__ == "__main__":
    unittest.main()
