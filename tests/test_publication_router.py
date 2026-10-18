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
        self.governance = mock.patch.object(self.router, "_main_governance", return_value={"gate_state": "success"}).start()
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
        self.governance.assert_called_once_with(self.root, self.head)
        self.publisher.publish.assert_called_once_with(self.manifest, self.root)
        self.editor.edit_published_metadata.assert_not_called()
        self.assertTrue(result["publisher_invoked"])
        self.assertIsNone(result["external_effect_performed"])
        self.assertFalse(result["effect_ack_done"])

    def test_metadata_mode_never_calls_the_new_record_publisher(self):
        self.request("metadata-edit", execute=True)
        self.editor.edit_published_metadata.assert_called_once_with(self.manifest, self.root)
        self.publisher.publish.assert_not_called()

    def test_direct_publish_and_metadata_effects_cannot_bypass_native_governance(self):
        self.governance.side_effect = ValueError("CODE_OWNER_RULE_NOT_ENFORCED")
        for operation in ("publish", "metadata-edit"):
            with self.subTest(operation=operation), self.assertRaisesRegex(ValueError, "CODE_OWNER_RULE_NOT_ENFORCED"):
                self.request(operation, execute=True)
        self.assert_no_effect()

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

    def test_optional_workflow_route_preserves_generic_capability_contract(self):
        for name in ("ZENODO_PUBLICATION_CAPABILITY.json", "ZENODO_METADATA_EDIT_CAPABILITY.json"):
            capability = json.loads((ROUTER.parent.parent / "runtime/capabilities" / name).read_bytes())
            self.assertTrue(capability["workflow_binding"].startswith("none"))
            self.assertEqual(capability["invocation_routes"][0]["repository"], self.repository)
            self.assertEqual(capability["invocation_routes"][0]["default"], "PREFLIGHT_ONLY; execute=false")

class EditorialContinuationTests(unittest.TestCase):
    """Real v2 proof/author controls; only remote effects use invented transports."""

    def setUp(self):
        from tests import test_zenodo_machine_proof_policy as fixtures
        from tools import qikvrt_publication_router as router
        from tools import qikvrt_verify_zenodo_public_manifest as verifier
        self.f, self.router, self.verifier = fixtures, router, verifier
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle, self.manifest = fixtures.MachineProofBeforeZenodoTests().fixture(self.root)
        self.source, self.head = fixtures.materialize_git_history(self.root, self.manifest)
        self.executor, self.publisher, _ = router._publication_dependencies()
        self.request_path = self.root / router.EDITORIAL_QUEUE / "fixture.json"
        self.request_path.parent.mkdir(parents=True)
        package = self.root / "runtime/self-host/PACKAGE.json"
        package.parent.mkdir(parents=True, exist_ok=True)
        package.write_bytes(router._json_bytes({"schema": "qikvrt-self-host-definition/v1",
                                               "files": ["runtime/self-host/PACKAGE.json"]}))
        self.request = {"schema": router.EDITORIAL_SCHEMA, "publication_id": fixtures.FIXTURE_PUBLICATION_ID,
                        "manifest_path": self.manifest.relative_to(self.root).as_posix(),
                        "manifest_sha256": hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
                        "manuscript_paths": ["docs/candidate.md"],
                        "website": {"origin": router.PUBLIC_ORIGIN,
                                    "path": "/publications/" + fixtures.FIXTURE_PUBLICATION_ID + "/"}}
        self.save_request()
        self.f.run_git(self.root, "add", "--all")
        self.f.run_git(self.root, "commit", "-qm", "reviewed editorial request")
        self.head = self.f.run_git(self.root, "rev-parse", "HEAD")
        self.tree = self.f.run_git(self.root, "rev-parse", "HEAD^{tree}")
        self.addCleanup(mock.patch.stopall)
        mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": router.AUTHORITY, "GITHUB_SHA": self.head,
                                    "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "push",
                                    "GH_TOKEN": fixtures.TEST_GITHUB_TOKEN}).start()
        self.live = mock.patch.object(self.executor, "read_authority_main", return_value={
            "repository": router.AUTHORITY, "main_head": self.head, "main_tree": self.tree}).start()
        mock.patch.object(self.executor, "load_repository_roles", return_value={"AUTHORITY": router.AUTHORITY}).start()

    def save_request(self):
        self.request_path.write_bytes(self.router._json_bytes(self.request))

    def intake(self, committed=False):
        return self.router.editorial_intake(self.root, self.request_path.relative_to(self.root).as_posix(),
                                            committed_head=self.head if committed else None)

    def published_fixture(self):
        manifest = self.publisher.load_manifest(self.manifest, self.root)
        metadata = dict(manifest["metadata"])
        metadata["resource_type"] = {"type": metadata.pop("upload_type"), "subtype": metadata.pop("publication_type")}
        record = {"id": 123, "doi": "10.5281/zenodo.123", "conceptdoi": "10.5281/zenodo.122",
                  "links": {"html": "https://zenodo.org/records/123"}, "metadata": metadata,
                  "files": [{"key": f["name"], "size": f["size"], "checksum": "md5:" + f["md5"],
                             "links": {"self": "https://zenodo.org/records/123/files/" + f["name"]}}
                            for f in manifest["files"]]}
        remote = {"remote": "github_git_data_api", "api_origin": self.publisher.GITHUB_API_BASE,
                  "repository": self.router.AUTHORITY, "ref": manifest["owner_authorization"]["remote_consumption_ref"],
                  "tag_object": "d" * 40, "object_type": "tag", "execution_head": self.head,
                  "acquisition": "GITHUB_GIT_DATA_REST_CREATE_ONLY", "recovery_mode": "NEWLY_CREATED_REF"}
        evidence = self.publisher._phase_evidence(self.manifest, self.root, manifest, self.head,
                      remote, "public_verified", record_id=123, doi=record["doi"], published=record)
        manifest["evidence_path"].write_bytes(self.router._json_bytes(evidence))
        by_name = {f["name"]: f for f in manifest["files"]}
        mock.patch.object(self.verifier, "_get_json", return_value=record).start()
        download = mock.patch.object(self.verifier, "_download", side_effect=lambda url, name:
            (by_name[name]["size"], by_name[name]["md5"], by_name[name]["sha256"])).start()
        return manifest, record, download

    def test_real_proof_and_exact_individual_author_allow_read_only_intake(self):
        result = self.intake(committed=True)
        self.assertEqual(result["state"], "READY_EXACT_AUTHOR_AUTHORIZED")
        self.assertEqual(result["author"]["name"], "Ingolf Lohmann")
        self.assertFalse(result["external_effect_performed"])

    def test_missing_author_grant_remains_an_intake_hold(self):
        (self.root / "release/fixture/OWNER_ZENODO_AUTHORIZATION.json").unlink()
        self.assertEqual(self.intake()["state"], "HOLD_PROOF_OR_INDIVIDUAL_AUTHOR_AUTHORIZATION")

    def test_one_principals_grant_cannot_substitute_for_a_coauthors_grant(self):
        value = json.loads(self.manifest.read_bytes())
        value["metadata"]["creators"].append({"name": "Fixture Coauthor"})
        self.manifest.write_bytes(self.router._json_bytes(value))
        self.f.rebind_fixture(self.root, self.manifest)
        self.request["manifest_sha256"] = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.save_request()
        self.assertEqual(self.intake()["state"], "HOLD_INDIVIDUAL_COAUTHOR_APPROVAL_PROTOCOL")

    def test_changed_manuscript_is_not_authorized_by_predecessor_bytes(self):
        (self.root / "docs/candidate.md").write_text("Changed manuscript")
        with self.assertRaises(self.publisher.zenodo.ZenodoError):
            self.intake()

    def test_changed_manifest_digest_is_blocked_before_author_load(self):
        self.request["manifest_sha256"] = "0" * 64
        self.save_request()
        with self.assertRaisesRegex(ValueError, "manifest digest"):
            self.intake()

    def test_nonreturned_source_and_untrusted_origin_or_path_are_rejected(self):
        for field, bad in (("origin", "https://example.invalid"), ("path", "/publications/../x/")):
            with self.subTest(field=field):
                old = self.request["website"][field]
                self.request["website"][field] = bad
                self.save_request()
                with self.assertRaises(ValueError): self.intake()
                self.request["website"][field] = old
        self.request["manuscript_paths"] = ["proof/SOURCE.txt"]
        self.save_request()
        with self.assertRaisesRegex(ValueError, "not returned"):
            self.intake()

    def test_dirty_request_cannot_enter_automatic_dispatch(self):
        self.request["manuscript_paths"] = ["docs/candidate.md", "docs/candidate.md"]
        self.save_request()
        with self.assertRaisesRegex(ValueError, "committed bytes"):
            self.intake(committed=True)

    def test_invalid_text_and_unsupported_manuscripts_are_not_rewritten(self):
        for path, raw in (("a.txt", b"\0"), ("a.md", b" \n"), ("a.docx", b"data")):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.router._manuscript_format(Path(path), raw)

    def test_real_locked_pdf_parser_is_required_and_rejects_malformed_pdf(self):
        # Uses the actual installed parser; no fake version or parser PASS.
        with self.assertRaises(Exception):
            self.router._manuscript_format(Path("a.pdf"), b"%PDF-1.7\ninvalid")

    def test_pdf_text_and_encryption_with_the_actual_locked_runtime(self):
        import importlib.metadata
        try:
            version = importlib.metadata.version("pypdf")
        except importlib.metadata.PackageNotFoundError:
            version = None
        if version != "6.15.0":
            with self.assertRaisesRegex(ValueError, "locked PDF"):
                self.router._manuscript_format(Path("a.pdf"), b"pdf")
            return  # Local hold verified; native pinned job exercises the real parser below.
        import io
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=300, height=300)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 250 Td (Exact manuscript) Tj ET")
        page[NameObject("/Contents")] = stream
        raw = io.BytesIO()
        writer.write(raw)
        self.assertTrue(self.router._manuscript_format(Path("a.pdf"), raw.getvalue())["extractable_text"])
        writer.encrypt("fixture-password")
        encrypted = io.BytesIO()
        writer.write(encrypted)
        with self.assertRaises(ValueError):
            self.router._manuscript_format(Path("a.pdf"), encrypted.getvalue())

    def test_absent_pdf_package_is_an_explicit_hold_instead_of_a_test_environment_error(self):
        import importlib.metadata
        with mock.patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError("pypdf")):
            with self.assertRaisesRegex(ValueError, "locked PDF inspection runtime unavailable"):
                self.router._manuscript_format(Path("a.pdf"), b"%PDF-1.7\nnot accepted")

    def test_durable_dispatch_reservation_suppresses_unchanged_rerun(self):
        ref = "refs/tags/qikvrt-editorial-dispatch/" + self.intake()["authorization_consumption_key"]
        with mock.patch.object(self.publisher, "_github_api_request", return_value=(200, {"ref": ref, "object": {"type": "commit", "sha": self.head}})), \
             mock.patch.object(self.router, "_rest") as rest:
            result = self.router.dispatch_editorial_queue(self.root)
        rest.assert_not_called()
        self.assertIn("NOOP_EXISTING_DISPATCH", result["requests"][0]["state"])

    def test_missing_native_governance_cannot_reserve_or_dispatch(self):
        with mock.patch.object(self.publisher, "_github_api_request", return_value=(404, {})), \
             mock.patch.object(self.router, "_main_governance", side_effect=ValueError("CODE_OWNER_RULE_NOT_ENFORCED")), \
             mock.patch.object(self.router, "_rest") as rest:
            with self.assertRaisesRegex(ValueError, "CODE_OWNER_RULE_NOT_ENFORCED"):
                self.router.dispatch_editorial_queue(self.root)
        rest.assert_not_called()

    def test_main_drift_blocks_dispatch_before_any_mutation(self):
        self.live.return_value["main_head"] = "a" * 40
        with mock.patch.object(self.publisher, "_github_api_request", return_value=(404, {})), \
             mock.patch.object(self.router, "_main_governance"), mock.patch.object(self.router, "_rest") as rest:
            with self.assertRaisesRegex(ValueError, "Main drifted"):
                self.router.dispatch_editorial_queue(self.root)
        rest.assert_not_called()

    def test_exact_main_auto_request_dispatches_existing_lane_once(self):
        calls = []
        def rest(method, endpoint, data=None):
            calls.append((method, endpoint, data))
            if method == "GET":
                return {"ref": calls[0][2]["ref"], "object": {"sha": self.head}}
        with mock.patch.object(self.publisher, "_github_api_request", return_value=(404, {"message": "Not Found"})), \
             mock.patch.object(self.router, "_main_governance"), mock.patch.object(self.router, "_rest", side_effect=rest):
            result = self.router.dispatch_editorial_queue(self.root)
        self.assertEqual(len(calls), 3)
        inputs = calls[-1][2]["inputs"]
        self.assertEqual(inputs["expected_main_head"], self.head)
        self.assertEqual(inputs["expected_main_tree"], self.tree)
        self.assertEqual(inputs["execute"], "true")
        self.assertEqual(inputs["manifest_sha256"], self.request["manifest_sha256"])
        self.assertFalse(result["effect_ack_done"])

    def test_ambiguous_dispatch_is_never_retried(self):
        count = 0
        def rest(method, endpoint, data=None):
            nonlocal count
            if method == "GET":
                return {"ref": ref, "object": {"sha": self.head}}
            if endpoint.endswith("/dispatches"):
                count += 1
                raise ValueError("transport uncertain")
        ref = "refs/tags/qikvrt-editorial-dispatch/" + self.intake()["authorization_consumption_key"]
        with mock.patch.object(self.publisher, "_github_api_request", return_value=(404, {})), \
             mock.patch.object(self.router, "_main_governance"), mock.patch.object(self.router, "_rest", side_effect=rest):
            with self.assertRaises(ValueError): self.router.dispatch_editorial_queue(self.root)
        self.assertEqual(count, 1)

    def test_pr_event_cannot_enter_automatic_effect_lane(self):
        with mock.patch.dict(os.environ, {"GITHUB_EVENT_NAME": "pull_request"}), mock.patch.object(self.router, "_rest") as rest:
            with self.assertRaises(ValueError): self.router.dispatch_editorial_queue(self.root)
        rest.assert_not_called()

    def test_independent_public_verifier_downloads_every_exact_upload(self):
        manifest, _, download = self.published_fixture()
        result = self.verifier.verify_generic(self.manifest, self.root)
        self.assertEqual(download.call_count, len(manifest["files"]))
        self.assertFalse(result["authenticated_transport_used"])
        self.assertEqual(result["doi"], "10.5281/zenodo.123")

    def test_extra_public_file_and_wrong_public_bytes_are_rejected(self):
        _, record, download = self.published_fixture()
        record["files"].append(dict(record["files"][0], key="extra.txt"))
        with self.assertRaisesRegex(ValueError, "upload set"):
            self.verifier.verify_generic(self.manifest, self.root)
        record["files"].pop()
        download.side_effect = lambda *a: (1, "0" * 32, "0" * 64)
        with self.assertRaisesRegex(ValueError, "file bytes"):
            self.verifier.verify_generic(self.manifest, self.root)

    def test_publisher_receipt_alone_cannot_promote_wrong_public_metadata(self):
        _, record, _ = self.published_fixture()
        record["metadata"]["title"] = "different"
        with self.assertRaisesRegex(ValueError, "metadata differs"):
            self.verifier.verify_generic(self.manifest, self.root)

    def test_doi_and_safe_site_assets_follow_independent_verification(self):
        self.published_fixture()
        result = self.router.complete_editorial(self.root, self.request_path.relative_to(self.root).as_posix(),
                                                ".qikvrt/evidence/publication-request/site")
        self.assertEqual(result["doi"], "10.5281/zenodo.123")
        self.assertFalse(result["effect_ack_done"])
        stage = self.root / result["website_stage"]
        self.assertTrue(all((stage / a["path"]).is_file() for a in result["website_assets"]))
        self.assertFalse(any("AUTHORIZATION" in a["path"] for a in result["website_assets"]))
        serialized = (stage / self.request["website"]["path"].lstrip("/") / "publication.json").read_text()
        self.assertNotIn("nonce", serialized)
        self.assertIn("10.5281/zenodo.123", serialized)

    def test_public_website_failure_is_separate_from_zenodo_publication(self):
        self.published_fixture()
        self.router.complete_editorial(self.root, self.request_path.relative_to(self.root).as_posix(),
                                       ".qikvrt/evidence/publication-request/site")
        with mock.patch("urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = OSError("unavailable")
            result = self.router.verify_editorial_delivery(self.root, ".qikvrt/evidence/publication-request/completion.json")
        self.assertEqual(result["state"], "HOLD_PUBLIC_WEBSITE_READBACK")
        self.assertEqual(result["doi"], "10.5281/zenodo.123")
        self.assertEqual(opener.return_value.open.call_count, 1)
        self.assertFalse(result["effect_ack_done"])

    def test_complete_public_website_byte_readback_uses_no_credentials_and_rejects_redirect(self):
        self.published_fixture()
        completion = self.router.complete_editorial(self.root, self.request_path.relative_to(self.root).as_posix(),
                                       ".qikvrt/evidence/publication-request/site")
        raw_by_url = {self.router.PUBLIC_ORIGIN + "/" + a["path"]:
                      (self.root / completion["website_stage"] / a["path"]).read_bytes()
                      for a in completion["website_assets"]}
        def response(request, **kw):
            self.assertFalse(request.has_header("Authorization"))
            raw = raw_by_url[request.full_url]
            value = mock.MagicMock()
            value.__enter__.return_value = SimpleNamespace(status=200, geturl=lambda: request.full_url,
                                                          read=lambda count: raw[:count])
            return value
        with mock.patch("urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = response
            result = self.router.verify_editorial_delivery(self.root, ".qikvrt/evidence/publication-request/completion.json")
        self.assertTrue(all(f["byte_exact_public_readback"] for f in result["files"]))
        self.assertEqual(len(result["files"]), len(raw_by_url))
        self.assertFalse(result["effect_ack_done"])
        with mock.patch("urllib.request.build_opener") as opener:
            bad = mock.MagicMock()
            bad.__enter__.return_value = SimpleNamespace(status=200, geturl=lambda: "https://example.invalid/",
                                                         read=lambda count: b"same-looking")
            opener.return_value.open.return_value = bad
            held = self.router.verify_editorial_delivery(self.root, ".qikvrt/evidence/publication-request/completion.json")
        self.assertTrue(held["state"].startswith("HOLD"))

    def _publish_through_existing_editorial_lane(self):
        """One isolated chain; GitHub, Zenodo and public HTTP are invented transports."""
        calls = []
        def queue_api(method, endpoint, data=None):
            calls.append((method, endpoint, data))
            if method == "GET":
                return {"ref": calls[0][2]["ref"], "object": {"sha": self.head}}
        with mock.patch.object(self.publisher, "_github_api_request", return_value=(404, {})), \
             mock.patch.object(self.router, "_main_governance"), \
             mock.patch.object(self.router, "_rest", side_effect=queue_api):
            admitted = self.router.dispatch_editorial_queue(self.root)
        self.assertEqual(admitted["requests"][0]["state"], "DISPATCH_ACK_REQUIRES_NATIVE_RUN_READBACK")
        self.assertEqual(sum(c[1].endswith("/dispatches") for c in calls), 1)
        inputs = calls[-1][2]["inputs"]
        manifest, public, _ = self.published_fixture()
        manifest["evidence_path"].unlink()
        github = self.f.FakeGitHubGitData()
        draft = {"id": 123, "metadata": {"prereserve_doi": {"doi": public["doi"]}}}
        with mock.patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_dispatch",
                 "GITHUB_TOKEN": self.f.TEST_GITHUB_TOKEN, "ZENODO_ACCESS_TOKEN": "z" * 32}), \
             mock.patch.object(self.router, "_main_governance"), \
             mock.patch.object(self.publisher, "_github_api_request", side_effect=github), \
             mock.patch.object(self.publisher, "_list_all_owned_depositions", return_value=[]), \
             mock.patch.object(self.publisher.zenodo, "ZenodoClient") as client_type:
            client = client_type.return_value
            client.create_paper.return_value = draft
            client.prepare_draft.return_value = "draft"
            client.publish_and_poll.return_value = public
            arguments = (self.root, inputs["operation"], inputs["manifest_path"], inputs["manifest_sha256"],
                         inputs["expected_main_head"], inputs["expected_main_tree"])
            preflight = self.router.requested_zenodo(*arguments, editorial_relative=inputs["editorial_request_path"])
            self.assertFalse(preflight["external_effect_performed"])
            client.create_paper.assert_not_called()
            result = self.router.requested_zenodo(*arguments, execute=True, editorial_relative=inputs["editorial_request_path"])
        self.assertTrue(result["publisher_invoked"])
        client.create_paper.assert_called_once()
        client.publish_and_poll.assert_called_once()
        final = self.router.complete_editorial(self.root, self.request_path.relative_to(self.root).as_posix(),
                                               ".qikvrt/evidence/publication-request/site")
        return result, final

    def test_full_exact_dispatch_uses_real_existing_publisher_then_anonymous_completion(self):
        result, final = self._publish_through_existing_editorial_lane()
        self.assertTrue(result["publisher_invoked"])
        self.assertEqual(final["doi"], "10.5281/zenodo.123")
        self.assertTrue(final["public_zenodo_verification"]["public_record_verified"])
        self.assertFalse(final["effect_ack_done"])

    def test_website_asset_omission_must_not_turn_into_public_integrity_success(self):
        self.published_fixture()
        self.router.complete_editorial(self.root, self.request_path.relative_to(self.root).as_posix(),
                                       ".qikvrt/evidence/publication-request/site")
        path = self.root / ".qikvrt/evidence/publication-request/completion.json"
        value = json.loads(path.read_bytes())
        value["website_assets"] = value["website_assets"][:1]
        path.write_bytes(self.router._json_bytes(value))
        with self.assertRaises(ValueError):
            self.router.verify_editorial_delivery(self.root, path.relative_to(self.root).as_posix())

    def test_rest_wrapper_rejects_permission_changes_and_other_repositories(self):
        for method, endpoint in (("POST", "repos/other/repo/git/refs"),
                                 ("POST", "repos/" + self.router.AUTHORITY + "/rulesets"),
                                 ("PATCH", "repos/" + self.router.AUTHORITY + "/git/refs/heads/main")):
            with self.subTest(endpoint=endpoint), mock.patch.object(subprocess, "run") as run:
                with self.assertRaises(ValueError): self.router._rest(method, endpoint)
                run.assert_not_called()

    def test_native_review_gate_requires_current_merged_carrier_and_exact_approval(self):
        from tools import qikvrt_required_review_gate as review
        rule = {"type": "pull_request", "parameters": {"required_approving_review_count": 1,
                "require_code_owner_review": True, "dismiss_stale_reviews_on_push": True,
                "require_last_push_approval": True}}
        pr = {"number": 1, "merged_at": "2026-10-16T10:00:00Z", "merge_commit_sha": self.head,
              "head": {"sha": self.source}, "user": {"login": "contributor"},
              "base": {"ref": "main", "repo": {"full_name": self.router.AUTHORITY}}, "draft": False}
        approval = {"id": 1, "commit_id": self.source, "state": "APPROVED", "submitted_at": "2026-10-16T09:00:00Z",
                    "user": {"login": "ingolf-lohmann", "type": "User"}}
        def pages(endpoint):
            return [rule] if "/rules/" in endpoint else [pr] if "/commits/" in endpoint else [approval]
        with mock.patch.object(self.router, "_pages", side_effect=pages), \
             mock.patch.object(review, "resolve_required_code_owner", return_value="ingolf-lohmann"):
            self.assertEqual(self.router._main_governance(self.root, self.head)["gate_state"], "success")
            approval["commit_id"] = "f" * 40
            with self.assertRaisesRegex(ValueError, "EXACT_MAIN_MERGE_REVIEW_NOT_VERIFIED"):
                self.router._main_governance(self.root, self.head)

    def test_unrelated_package_definition_change_cannot_enter_publication_carrier(self):
        _, completion = self._publish_through_existing_editorial_lane()
        path = self.root / "runtime/self-host/PACKAGE.json"
        definition = json.loads(path.read_bytes())
        definition["files"].append("unrelated-private-control.json")
        path.write_bytes(self.router._json_bytes(definition))
        api = mock.Mock(side_effect=AssertionError("no GitHub mutation"))
        with mock.patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_dispatch"}):
            with self.assertRaisesRegex(ValueError, "unrelated website package definition changes"):
                self.router.persist_editorial(self.root, ".qikvrt/evidence/publication-request/completion.json", api=api)
        api.assert_not_called()

    def test_receipt_and_website_persistence_use_one_create_only_draft_carrier(self):
        import base64
        from tools import qikvrt_integrity as integrity
        from tools import qikvrt_publication_overview as overview
        from tools import qikvrt_self_heal_pr_materializer as materializer
        from tests.test_qikvrt_publication_overview import PublicationOverviewTests
        PublicationOverviewTests().fixture(str(self.root))
        # Run the real index and integrity generators, not successful substitutes.
        for relative in ("tools/qikvrt_integrity.py", "LEGACY_INTEGRITY_INVENTORIES.md"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROUTER.parent.parent / relative).read_bytes())
        _, completion = self._publish_through_existing_editorial_lane()
        calls, refs, commits, prs = [], {}, {}, []
        def api(method, endpoint, data=None):
            calls.append((method, endpoint, data))
            if "/git/ref/heads/" in endpoint:
                branch = endpoint.split("/git/ref/heads/", 1)[1]
                if branch not in refs: raise materializer.ApiFailure(404)
                return {"ref": "refs/heads/" + branch, "object": {"type": "commit", "sha": refs[branch]}}
            if endpoint.endswith("/git/blobs"):
                raw = base64.b64decode(data["content"])
                return {"sha": self.publisher._git_blob_sha(raw)}
            if endpoint.endswith("/git/trees"):
                return {"sha": self.f.run_git(self.root, "write-tree")}
            if endpoint.endswith("/git/commits"):
                head = "e" * 40
                commits[head] = {"sha": head, "tree": {"sha": data["tree"]},
                                 "parents": [{"sha": p} for p in data["parents"]]}
                return {"sha": head}
            if "/git/commits/" in endpoint: return commits[endpoint.rsplit("/", 1)[1]]
            if endpoint.endswith("/git/refs"):
                refs[data["ref"].removeprefix("refs/heads/")] = data["sha"]
                raise materializer.ApiFailure(None)  # Applied but ACK lost; readback must resolve it.
            if method == "GET" and "/pulls?" in endpoint: return prs
            if method == "POST" and endpoint.endswith("/pulls"):
                prs.append({"number": 42, "state": "open", "head": {"sha": "e" * 40}, "base": {"ref": "main"}})
                return prs[0]
            raise AssertionError(endpoint)
        with mock.patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_dispatch"}):
            result = self.router.persist_editorial(self.root, ".qikvrt/evidence/publication-request/completion.json", api=api)
        self.assertEqual(result["pull_request"], 42)
        self.assertFalse(result["main_merge_verified"])
        self.assertFalse(result["website_delivery_verified"])
        posts = [c for c in calls if c[0] == "POST"]
        self.assertEqual(sum(c[1].endswith("/git/refs") for c in posts), 1)
        self.assertEqual(sum(c[1].endswith("/pulls") for c in posts), 1)
        self.assertTrue(next(c[2] for c in posts if c[1].endswith("/pulls"))["draft"])
        self.assertFalse(any(c[2].get("ref") == "refs/heads/main" for c in posts))
        index = json.loads((self.root / overview.MACHINE_INDEX).read_bytes())
        record = next((r for r in index["zenodo_records"] if r["doi"] == "10.5281/zenodo.123"), None)
        self.assertIsNotNone(record, "A verified publication must enter the DOI catalog")
        self.assertFalse(record["website_delivery_verified"])
        self.assertIn("10.5281/zenodo.123", (self.root / overview.HUMAN_INDEX).read_text())
        self.assertEqual(overview.execute(self.root, materialize=False)["state"], "CURRENT")
        self.assertTrue(integrity.verify(self.root).ok)
        package_files = json.loads((self.root / "runtime/self-host/PACKAGE.json").read_bytes())["files"]
        self.assertEqual(set(package_files), {"runtime/self-host/PACKAGE.json"} |
                         {"docs/" + a["path"] for a in completion["website_assets"]})
        self.assertNotIn(self.manifest.relative_to(self.root).as_posix(), package_files)
        # The same staged originals must also pass the final anonymous website check.
        by_url = {self.router.PUBLIC_ORIGIN + "/" + a["path"]:
                  (self.root / "docs" / a["path"]).read_bytes() for a in completion["website_assets"]}
        def response(request, **kw):
            self.assertFalse(request.has_header("Authorization"))
            raw = by_url[request.full_url]
            value = mock.MagicMock()
            value.__enter__.return_value = SimpleNamespace(status=200, geturl=lambda: request.full_url,
                                                          read=lambda count: raw[:count])
            return value
        with mock.patch("urllib.request.build_opener") as opener:
            opener.return_value.open.side_effect = response
            delivered = self.router.verify_editorial_delivery(self.root, record["editorial_completion_path"], persisted=True)
        self.assertEqual(len(delivered["files"]), len(by_url))
        self.assertTrue(all(f["byte_exact_public_readback"] for f in delivered["files"]))
        self.assertFalse(delivered["effect_ack_done"])
        before = (self.root / overview.MACHINE_INDEX).read_bytes()
        path = self.root / record["editorial_readback_path"]
        saved = json.loads(path.read_bytes())
        saved["status"] = "FAIL"
        path.write_bytes(self.router._json_bytes(saved))
        with self.assertRaises(overview.PublicationOverviewBlock):
            overview.execute(self.root, materialize=True)
        self.assertEqual((self.root / overview.MACHINE_INDEX).read_bytes(), before)

    def test_completion_cannot_promote_a_tampered_public_receipt(self):
        import copy
        self.published_fixture()
        self.router.complete_editorial(self.root, self.request_path.relative_to(self.root).as_posix(),
                                       ".qikvrt/evidence/publication-request/site")
        path = self.root / ".qikvrt/evidence/publication-request/completion.json"
        original = json.loads(path.read_bytes())
        bad_values = []
        for key, value in (("status", "FAIL"), ("authenticated_transport_used", True),
                           ("public_record_verified", 1), ("file_count", 0)):
            changed = copy.deepcopy(original)
            changed["public_zenodo_verification"][key] = value
            bad_values.append(changed)
        changed = copy.deepcopy(original)
        changed["public_zenodo_verification"]["files"][0]["sha256"] = "0" * 64
        bad_values.append(changed)
        changed = copy.deepcopy(original)
        changed["doi"] = "10.5281/zenodo.999"
        bad_values.append(changed)
        for value in bad_values:
            with self.subTest(value=value["doi"]):
                path.write_bytes(self.router._json_bytes(value))
                with self.assertRaises(ValueError):
                    self.router._validated_editorial_completion(self.root, path.relative_to(self.root).as_posix())

    def test_successful_workflow_with_skipped_deployment_never_probes_public_assets(self):
        run = {"head_sha": self.head, "head_branch": "main", "repository": {"full_name": self.router.AUTHORITY},
               "head_repository": {"full_name": self.router.AUTHORITY}, "event": "push",
               "path": ".github/workflows/qikvrt_effect_ack_http_terminal.yml", "status": "completed", "conclusion": "success"}
        jobs = {"total_count": 2, "jobs": [{"name": n, "status": "completed", "conclusion": "skipped"}
                for n in ("deploy-existing-linux-host", "independent-product-http-readback")]}
        with mock.patch.object(self.router, "_rest", side_effect=[run, jobs]), \
             mock.patch.object(self.router, "verify_editorial_delivery") as readback:
            result = self.router.verify_after_existing_deployment(self.root, "123")
        self.assertEqual(result["state"], "NOOP_EXISTING_DEPLOYMENT_NOT_EXECUTED")
        readback.assert_not_called()

    def test_fork_or_other_head_completion_cannot_supply_the_deployment_event(self):
        with mock.patch.object(self.router, "_rest", return_value={"head_sha": "f" * 40}):
            with self.assertRaises(ValueError): self.router.verify_after_existing_deployment(self.root, "123")
        with mock.patch.object(self.router, "_pages", return_value=[]):
            with self.assertRaisesRegex(ValueError, "EXACT_MAIN_MERGE_REVIEW_NOT_VERIFIED"):
                self.router._main_governance(self.root, self.head)

    def test_merged_principal_review_uses_shared_gate_without_an_independent_review(self):
        from tests.test_qikvrt_required_review_gate import PrincipalReviewGateTests
        fixture = PrincipalReviewGateTests()
        pr = fixture.pr()
        pr.update(merged_at="2026-10-18T04:30:00Z", merge_commit_sha=self.head, draft=False)
        def pages(endpoint):
            return [] if "/rules/" in endpoint else [pr] if "/commits/" in endpoint else [fixture.review()]
        with mock.patch.object(self.router, "_pages", side_effect=pages):
            gate = self.router._main_governance(self.root, self.head)
        self.assertEqual(gate["review_basis"], "OWNER_PRINCIPAL_REVIEW")
        self.assertFalse(gate["independent_native_approval"])


if __name__ == "__main__":
    unittest.main()
