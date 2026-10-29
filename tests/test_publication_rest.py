# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Original REST admission and recovery boundaries, not production acceptance."""
import copy
import http.client
import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from urllib.parse import urlencode

from tests.test_production_environment import Auth
from tools import qikvrt_authority_credentials as authority
from tools import qikvrt_self_host as launcher
from tools import qikvrt_zenodo_publish as publisher
from src import qikvrt_github_api_shim as shim


class PublicationRESTTests(unittest.TestCase):
    def setUp(self):
        self.auth = Auth()
        self.pin, self.head, self.tree = "a" * 64, "1" * 40, "2" * 40
        self.env = {"QIKVRT_ALLOWED_REPOSITORY": authority.PRODUCTION_REPOSITORY,
            "QIKVRT_API_PRINCIPAL": "ingolf-lohmann", "QIKVRT_PUBLICATION_REST_ENABLED": "1",
            "QIKVRT_PUBLICATION_REQUEST": "/private/fixture-only-request.json",
            "QIKVRT_PUBLICATION_REQUEST_SHA256": self.pin}
        original = {"repository": authority.PRODUCTION_REPOSITORY, "execution_head": self.head,
            "execution_tree": self.tree, "manifest_sha256": "b" * 64}
        manifest = {"machine_proof": {"publication_id": "fixture-only-publication"},
            "owner_authorization": {"consumption_key": {"value": "c" * 64}}}
        self.admitted = (original, Path("/fixture-only-checkout"), Path("/fixture-only-manifest"),
            manifest, publisher, Path("/fixture-only-registry"), {})
        self.admission = mock.patch.object(launcher, "publication_request", return_value=self.admitted).start()
        self.source = mock.patch.object(authority, "production_source", return_value=True).start()
        self.invoke = mock.patch.object(launcher, "publication_resume", return_value={"state": "HOLD_PUBLISHER"}).start()
        self.addCleanup(mock.patch.stopall)
        self.read = {"schema": authority.PUBLICATION_REST_SCHEMA, "request_id": "fixture-read"}
        self.write = dict(self.read, request_id="fixture-write", expected_main_sha=self.head,
            request_sha256=self.pin, effect_accepted=True)

    def run_operation(self, *, write=False, request=None):
        return authority.publication_handoff(self.auth, "fixture-sso-bearer",
            request if request is not None else (self.write if write else self.read), self.env, write=write)

    def test_check_calls_original_admission_without_credentials_or_publisher(self):
        result = self.run_operation()
        self.admission.assert_called_once_with(Path(self.env["QIKVRT_PUBLICATION_REQUEST"]), self.pin)
        self.invoke.assert_not_called()
        self.assertEqual(self.auth.store.read(), {})
        self.assertEqual(result["state"], "SOURCE_AND_REFERENCES_ADMITTED")
        self.assertFalse(result["publisher_invoked"])
        self.assertFalse(result["job_credential_delivery_verified"])
        self.assertFalse(result["effect_ack_done"])
        self.assertNotIn("/private/", json.dumps(result))

    def test_real_unavailable_original_source_is_not_invented_or_discovered(self):
        mock.patch.stopall()
        with tempfile.TemporaryDirectory() as directory:
            self.env["QIKVRT_PUBLICATION_REQUEST"] = str(Path(directory) / "absent.json")
            with self.assertRaisesRegex(authority.ProductionBlock, "ORIGINAL_PUBLICATION_ADMISSION_UNAVAILABLE"):
                self.run_operation()
        self.assertEqual(self.auth.store.read(), {})

    def test_missing_server_binding_and_arbitrary_caller_paths_are_refused(self):
        for change in ({"path": "/other"}, {"token": "PRIVATE"}, {"environment": "other"},
                       {"effect_accepted": False}, {"request_sha256": "d" * 64},
                       {"expected_main_sha": "3" * 40}):
            with self.subTest(change=change), self.assertRaises(authority.ProductionBlock):
                self.run_operation(write=True, request=dict(self.write, **change))
        self.invoke.assert_not_called()
        self.env.pop("QIKVRT_PUBLICATION_REQUEST")
        with self.assertRaisesRegex(authority.ProductionBlock, "ORIGINAL_PRIVATE_PUBLICATION_REQUEST_REQUIRED"):
            self.run_operation()

    def test_real_intent_precedes_one_original_launcher_call_and_reconnect_is_noop(self):
        def invoke(*args):
            records = self.auth.store.read()["publication_rest_handoffs"]
            self.assertEqual(next(iter(records.values()))["state"], "UNKNOWN_READBACK_REQUIRED")
            return {"state": "HOLD_PUBLISHER"}
        self.invoke.side_effect = invoke
        first = self.run_operation(write=True)
        again = self.run_operation(write=True, request=dict(self.write, request_id="another-name"))
        self.assertTrue(first["publisher_invoked"])
        self.assertEqual(again["state"], "NOOP_ORIGINAL_ATTEMPT_READBACK_ONLY")
        self.assertEqual(self.invoke.call_count, 1)
        self.assertEqual(self.run_operation()["state"], "ORIGINAL_ATTEMPT_READBACK_ONLY")

    def test_lost_reply_keeps_original_intent_and_never_reinvokes(self):
        self.invoke.side_effect = TimeoutError("PRIVATE_PROVIDER_BODY")
        with self.assertRaisesRegex(authority.ProductionBlock, "PUBLICATION_RESULT_UNKNOWN_ORIGINAL_READBACK_ONLY") as caught:
            self.run_operation(write=True)
        self.assertNotIn("PRIVATE", str(caught.exception))
        self.assertEqual(self.run_operation()["prior_attempt_state"], "UNKNOWN_READBACK_REQUIRED")
        self.run_operation(write=True)
        self.assertEqual(self.invoke.call_count, 1)

    def test_failed_durable_intent_cannot_invoke_and_checker_failure_is_redacted(self):
        with mock.patch.object(self.auth.store, "write", side_effect=OSError("PRIVATE")):
            with self.assertRaises(OSError): self.run_operation(write=True)
        self.invoke.assert_not_called()
        self.admission.side_effect = OSError("PRIVATE_SOURCE_OR_CREDENTIAL")
        with self.assertRaises(authority.ProductionBlock) as caught: self.run_operation()
        self.assertNotIn("PRIVATE_SOURCE", str(caught.exception))

    def test_expired_identity_wrong_owner_and_dirty_source_cannot_invoke(self):
        self.auth.active = False
        with self.assertRaises(ValueError): self.run_operation(write=True)
        self.auth.active, self.auth.live = True, False
        with self.assertRaises(authority.ProductionBlock): self.run_operation(write=True)
        self.auth.live = True
        self.env["QIKVRT_API_PRINCIPAL"] = "foreign"
        with self.assertRaises(authority.ProductionBlock): self.run_operation(write=True)
        self.env["QIKVRT_API_PRINCIPAL"] = "ingolf-lohmann"
        self.source.return_value = False
        self.assertFalse(self.run_operation()["implementation_source_verified"])
        with self.assertRaises(authority.ProductionBlock): self.run_operation(write=True)
        self.invoke.assert_not_called()

    def test_new_source_pin_cannot_bypass_an_unknown_candidate_attempt(self):
        self.invoke.side_effect = TimeoutError()
        with self.assertRaises(authority.ProductionBlock): self.run_operation(write=True)
        self.env["QIKVRT_PUBLICATION_REQUEST_SHA256"] = "e" * 64
        self.admitted[0]["execution_head"] = "f" * 40
        self.run_operation(write=True, request=dict(self.write, request_sha256="e" * 64,
            expected_main_sha="f" * 40, request_id="new-head-and-request"))
        self.assertEqual(self.invoke.call_count, 1)

    def test_checker_failure_and_corrupt_journal_are_not_readiness(self):
        self.source.side_effect = OSError("PRIVATE_CHECKER_BODY")
        with self.assertRaisesRegex(authority.ProductionBlock, "SOURCE_CHECK_UNAVAILABLE") as caught:
            self.run_operation()
        self.assertNotIn("PRIVATE", str(caught.exception))
        self.source.side_effect = None
        self.run_operation(write=True)
        journal = self.auth.store.read()
        journal["publication_rest_handoffs"][next(iter(journal["publication_rest_handoffs"]))] = {}
        self.auth.store.write(journal)
        with self.assertRaisesRegex(authority.ProductionBlock, "JOURNAL_INVALID"):
            self.run_operation(write=True)
        self.assertEqual(self.invoke.call_count, 1)

    def test_same_existing_http_listener_checks_origin_before_invocation(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), shim.QikvrtGitHubApiShim)
        server.authority_sso = SimpleNamespace(personal_auth=self.auth)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        port = server.server_address[1]
        route = "/repos/ingolf-lohmann/qik-vrt/qikvrt/publication"
        with mock.patch.dict(os.environ, self.env):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("GET", route + "?" + urlencode(self.read),
                headers={"Authorization": "Bearer fixture-sso-bearer"})
            response = connection.getresponse(); result = json.loads(response.read())
            self.assertEqual(response.status, 200); self.assertEqual(result["schema"], authority.PUBLICATION_REST_SCHEMA)
            connection.request("POST", route, json.dumps(self.write),
                {"Content-Type": "application/json", "Authorization": "Bearer fixture-sso-bearer", "Origin": "https://foreign.test"})
            response = connection.getresponse(); self.assertEqual(response.status, 409); response.read()
            self.invoke.assert_not_called()
            connection.request("POST", route, json.dumps(self.write),
                {"Content-Type": "application/json", "Authorization": "Bearer fixture-sso-bearer", "Origin": f"http://127.0.0.1:{port}"})
            response = connection.getresponse(); result = json.loads(response.read())
            self.assertEqual(response.status, 200); self.assertTrue(result["publisher_invoked"])
            connection.close()


class FreshAuthorityTests(unittest.TestCase):
    def test_actual_launcher_refuses_remote_main_or_tree_drift_before_child(self):
        request = {"repository": authority.PRODUCTION_REPOSITORY, "execution_head": "1" * 40,
            "execution_tree": "2" * 40, "manifest": "fixture-only-manifest"}
        ref = {"ref": "refs/heads/main", "object": {"sha": request["execution_head"]}}
        commit = {"sha": request["execution_head"], "tree": {"sha": request["execution_tree"]}}
        for values in ([dict(ref, object={"sha": "3" * 40})], [ref, dict(commit, tree={"sha": "4" * 40})],
                       [ref, commit, dict(ref, object={"sha": "5" * 40})]):
            with mock.patch.object(publisher, "_github_api_request", side_effect=[(200, value) for value in values]), \
                    mock.patch.object(launcher.subprocess, "run") as child:
                with self.assertRaisesRegex(ValueError, "PUBLICATION_LIVE_AUTHORITY"):
                    launcher.publication_invoke(Path("/fixture-only-checkout"), request, {"GITHUB_TOKEN": "FIXTURE_ONLY_TOKEN"})
                child.assert_not_called()
        with mock.patch.object(publisher, "_github_api_request", side_effect=[(200, ref), (200, commit), (200, ref)]) as rest, \
                mock.patch.object(launcher.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as child:
            launcher.publication_invoke(Path("/fixture-only-checkout"), request, {"GITHUB_TOKEN": "FIXTURE_ONLY_TOKEN"})
            self.assertEqual([call.args[0] for call in rest.call_args_list], ["GET", "GET", "GET"])
            child.assert_called_once()
