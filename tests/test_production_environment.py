# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fixed Authority SSO handoff; provider and vault doubles prove no live effect."""
import base64
import copy
import hashlib
import io
import json
import os
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from tools import qikvrt_authority_credentials as a


class Vault:
    def __init__(self): self.value = {}
    def read(self): return copy.deepcopy(self.value)
    def write(self, value): self.value = copy.deepcopy(value)


class Auth:
    """Explicit fixture identity; this class cannot attest real SSO."""
    def __init__(self):
        self.store, self.lock, self.binding = Vault(), threading.RLock(), "fixture-oidc-binding"
        self.active, self.live = True, True
    def authenticate(self, token, **_kwargs):
        if token != "fixture-sso-bearer" or not self.active: raise ValueError("FIXTURE_AUTH_DENIED")
    def status(self): return {"live_authentication_observed_this_process": self.live}


class Provider:
    def __init__(self, *_):
        self.calls, self.variables, self.secrets = [], {}, {}
        self.main, self.account, self.admin = "1" * 40, "ingolf-lohmann", True
        self.env_id, self.drift, self.fail_after, self.main_drift = 123, False, None, False
        self.mutations = 0
        self.prefix = "/repos/" + a.PRODUCTION_REPOSITORY
        self.target = self.prefix + "/environments/" + a.PRODUCTION_ENVIRONMENT
    def call(self, method, path, body=None, **kwargs):
        self.calls.append((method, path, copy.deepcopy(body)))
        if method != "GET":
            self.mutations += 1
            if "/variables" in path: self.variables[body["name"]] = body["value"]
            else: self.secrets[path.rsplit("/", 1)[1]] = {"name": path.rsplit("/", 1)[1], "updated_at": "fixture"}
            if self.fail_after == self.mutations: raise URLError("fixture lost response")
            return {}
        if path == "/user": return {"login": self.account, "id": 294949349}
        if path == self.prefix: return {"id": 1273784147, "full_name": a.PRODUCTION_REPOSITORY, "permissions": {"admin": self.admin}}
        if path.endswith("/git/ref/heads/main"):
            return {"ref": "refs/heads/main", "object": {"sha": "2" * 40 if self.main_drift and self.mutations else self.main}}
        if "/git/commits/" in path: return {"sha": self.main, "tree": {"sha": "4" * 40}}
        if path == self.target:
            return {"name": a.PRODUCTION_ENVIRONMENT, "id": self.env_id,
                    "protection_rules": [{"id": 5 if self.drift and len(self.calls) > 10 else 4}],
                    "deployment_branch_policy": {"protected_branches": True}, "can_admins_bypass": False}
        if path.endswith("/secrets/public-key"): return {"key": "fixture-public-key", "key_id": "key-1"}
        name = path.rsplit("/", 1)[-1]
        if "/variables/" in path: return {"name": name, "value": self.variables[name]} if name in self.variables else None
        if "/secrets/" in path: return self.secrets.get(name)
        raise AssertionError((method, path))


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.auth, self.api = Auth(), Provider()
        self.values = {n: "FIXTURE_ONLY_" + n for n in a.PRODUCTION_VARIABLES + a.PRODUCTION_SECRETS}
        self.values[a.PRODUCTION_VARIABLES[1]] = "a" * 64
        self.env = {"QIKVRT_ALLOWED_REPOSITORY": a.PRODUCTION_REPOSITORY,
                    "QIKVRT_API_PRINCIPAL": "ingolf-lohmann", "QIKVRT_GITHUB_ADMIN_TOKEN": "fixture-protected-github-token"}
        self.body = {"schema": a.PRODUCTION_SCHEMA, "request_id": "handoff-1", "expected_main_sha": "1" * 40,
                     "binding_sha256": "a" * 64, "effect_accepted": True}
        self.patches = [mock.patch.object(a, "production_material", return_value=self.values),
                        mock.patch.object(a, "production_source", return_value=True),
                        mock.patch.object(a, "seal_environment_secret", side_effect=lambda key, value: "SEALED-" + hashlib.sha256(value.encode()).hexdigest())]
        for p in self.patches: p.start(); self.addCleanup(p.stop)

    def run_operation(self, *, write=True, request=None):
        value = self.body if request is None else request
        if not write and request is None: value = {k: v for k, v in value.items() if k != "effect_accepted"}
        return a.production_environment(self.auth, "fixture-sso-bearer", value, self.env,
                                        write=write, api_factory=lambda *_: self.api)

    def test_preview_observes_no_write_and_discovers_exact_current_main(self):
        result = self.run_operation(write=False, request={"schema": a.PRODUCTION_SCHEMA, "request_id": "prepare"})
        self.assertEqual(result["expected_main_sha"], self.api.main)
        self.assertEqual(result["binding_sha256"], "a" * 64)
        self.assertTrue(all(m == "GET" for m, _, _ in self.api.calls))
        self.assertEqual(self.auth.store.read(), {})

    def test_all_five_exact_bindings_and_independent_metadata_readback(self):
        result = self.run_operation()
        self.assertEqual(result["state"], "UPLOAD_ACKNOWLEDGED_METADATA_READBACK_VERIFIED")
        mutations = [(m, p, b) for m, p, b in self.api.calls if m != "GET"]
        self.assertEqual([m for m, _, _ in mutations], ["POST", "POST", "PUT", "PUT", "PUT"])
        for method, path, body in mutations[2:]:
            self.assertEqual(set(body), {"encrypted_value", "key_id"})
            self.assertTrue(path.startswith(self.api.target + "/secrets/"))
            self.assertNotIn("FIXTURE_ONLY_", json.dumps(body))
        self.assertTrue(all(v["present"] for v in result["bindings"].values()))
        self.assertFalse(result["effect_ack_done"])
        self.assertFalse(result["secret_values_verified"])
        self.assertFalse(result["job_credential_delivery_verified"])
        self.assertFalse(result["host_identity_verified"])
        self.assertEqual(result["next_required_operation"], "GET /v1.45/info")
        raw = json.dumps([result, self.auth.store.read()])
        for secret in [*self.values.values(), "fixture-sso-bearer", "fixture-protected-github-token"]:
            if secret != "a" * 64: self.assertNotIn(secret, raw)
        self.assertEqual(self.auth.store.read()["github_environment_handoff"]["state"], "COMPLETE")

    def test_readback_without_local_material_observes_remote_state_first(self):
        self.api.variables = {n: "REMOTE_FIXTURE_ONLY" for n in a.PRODUCTION_VARIABLES}
        self.api.secrets = {n: {"name": n} for n in a.PRODUCTION_SECRETS}
        def unavailable(_environment):
            self.assertEqual(self.api.calls[-1][1], self.api.target + "/secrets/" + a.PRODUCTION_SECRETS[-1])
            raise a.ProductionBlock("ORIGINAL_FIVE_PROTECTED_BINDINGS_REQUIRED")
        with mock.patch.object(a, "production_material", side_effect=unavailable):
            result = self.run_operation(write=False, request={"schema": a.PRODUCTION_SCHEMA, "request_id": "metadata-only"})
        self.assertEqual(result["state"], "READBACK_ONLY")
        self.assertFalse(result["protected_material_available"])
        self.assertEqual(result["protected_material_reason"], "ORIGINAL_FIVE_PROTECTED_BINDINGS_REQUIRED")
        self.assertIsNone(result["binding_sha256"])
        self.assertTrue(all(v["present"] for v in result["bindings"].values()))
        for name in a.PRODUCTION_VARIABLES:
            self.assertIsNone(result["bindings"][name]["value_matches"])
        self.assertNotIn("REMOTE_FIXTURE_ONLY", json.dumps(result))
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
        self.assertEqual(self.auth.store.read(), {})
        self.assertFalse(result["secret_values_verified"])
        self.assertFalse(result["job_credential_delivery_verified"])
        self.assertFalse(result["host_identity_verified"])
        self.assertFalse(result["effect_ack_done"])

    def test_unresolved_handoff_readback_preserves_journal_without_material(self):
        journal = {"auth_binding": self.auth.binding, "state": "UNKNOWN_READBACK_REQUIRED", "steps": [{"name": a.PRODUCTION_SECRETS[0], "state": "UNKNOWN_READBACK_REQUIRED"}]}
        self.auth.store.write({"github_environment_handoff": journal})
        before = self.auth.store.read()
        with mock.patch.object(a, "production_material", side_effect=a.ProductionBlock("ORIGINAL_HOST_OR_MTLS_MATERIAL_INVALID")):
            result = self.run_operation(write=False)
        self.assertEqual(result["prior_attempt_state"], "UNKNOWN_READBACK_REQUIRED")
        self.assertFalse(result["protected_material_available"])
        self.assertEqual(self.auth.store.read(), before)
        self.assertEqual(self.api.mutations, 0)

    def test_readback_with_real_missing_material_validation_needs_no_bindings(self):
        self.patches[0].stop()  # Exercise the original material validator, not its double.
        result = self.run_operation(write=False, request={"schema": a.PRODUCTION_SCHEMA, "request_id": "real-validator-empty-input"})
        self.assertFalse(result["protected_material_available"])
        self.assertEqual(result["protected_material_reason"], "ORIGINAL_FIVE_PROTECTED_BINDINGS_REQUIRED")
        self.assertEqual(result["next_required_operation"], "CONNECT_ORIGINAL_PROTECTED_MATERIAL_SOURCE")
        self.assertEqual(self.api.mutations, 0)

    def test_write_without_material_still_stops_before_provider_access(self):
        with mock.patch.object(a, "production_material", side_effect=a.ProductionBlock("ORIGINAL_FIVE_PROTECTED_BINDINGS_REQUIRED")):
            with self.assertRaisesRegex(a.ProductionBlock, "FIVE_PROTECTED_BINDINGS"):
                self.run_operation()
        self.assertEqual(self.api.calls, [])

    def test_failed_optional_material_checker_keeps_remote_readback_unknown(self):
        with mock.patch.object(a, "production_material", side_effect=OSError("PRIVATE_ERROR_MUST_NOT_ESCAPE")):
            result = self.run_operation(write=False, request={"schema": a.PRODUCTION_SCHEMA, "request_id": "checker-unavailable"})
        self.assertFalse(result["protected_material_available"])
        self.assertEqual(result["protected_material_reason"], "ORIGINAL_PROTECTED_MATERIAL_VALIDATION_UNAVAILABLE")
        self.assertIsNone(result["binding_sha256"])
        self.assertNotIn("PRIVATE_ERROR", json.dumps(result))
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))
        self.assertFalse(result["effect_ack_done"])

    def test_matching_variables_are_not_rewritten_and_mismatches_use_patch(self):
        self.api.variables = dict((n, self.values[n]) for n in a.PRODUCTION_VARIABLES)
        self.api.variables[a.PRODUCTION_VARIABLES[0]] = "OLD_FIXTURE"
        result = self.run_operation()
        self.assertEqual(result["mutation_count"], 4)
        self.assertEqual([m for m, _, _ in self.api.calls if m != "GET"], ["PATCH", "PUT", "PUT", "PUT"])

    def test_new_request_id_or_source_timestamp_cannot_replay_completed_input(self):
        self.run_operation(); count = self.api.mutations
        self.body["request_id"] = "renamed-request"
        self.body["expected_main_sha"] = self.api.main = "2" * 40
        self.assertEqual(self.run_operation()["state"], "NOOP")
        self.assertEqual(self.api.mutations, count)

    def test_lost_put_reply_persists_intent_and_never_uploads_again_after_reconnect(self):
        self.api.fail_after = 3
        with self.assertRaisesRegex(a.ProductionBlock, "UNRESOLVED_READBACK_ONLY"): self.run_operation()
        journal = self.auth.store.read()["github_environment_handoff"]
        self.assertEqual(journal["state"], "UNKNOWN_READBACK_REQUIRED")
        self.assertEqual(journal["steps"][-1]["state"], "UNKNOWN_READBACK_REQUIRED")
        self.body["request_id"] = "reconnect"
        self.assertEqual(self.run_operation()["state"], "NOOP")
        self.assertEqual(self.api.mutations, 3)
        self.values[a.PRODUCTION_SECRETS[2]] += "CHANGED"
        self.assertEqual(self.run_operation()["state"], "NOOP")
        self.assertEqual(self.api.mutations, 3)

    def test_source_change_stops_before_the_next_effect(self):
        self.api.main_drift = True
        with self.assertRaises(a.ProductionBlock): self.run_operation()
        self.assertEqual(self.api.mutations, 1)

    def test_environment_protections_never_modified(self):
        self.api.drift = True
        with self.assertRaises(a.ProductionBlock): self.run_operation()
        self.assertEqual(self.api.mutations, 0)
        self.assertFalse(any(p == self.api.target and m != "GET" for m, p, _ in self.api.calls))

    def test_wrong_identity_admin_principal_or_repository_stops_before_write(self):
        environment, body = dict(self.env), dict(self.body)
        for option in ("account", "admin", "principal", "repository", "pin", "main"):
            with self.subTest(option=option):
                self.api, self.env, self.body = Provider(), dict(environment), dict(body)
                if option == "account": self.api.account = "foreign"
                if option == "admin": self.api.admin = False
                if option == "principal": self.env["QIKVRT_API_PRINCIPAL"] = "foreign"
                if option == "repository": self.env["QIKVRT_ALLOWED_REPOSITORY"] = "foreign/repo"
                if option == "pin": self.body["binding_sha256"] = "b" * 64
                if option == "main": self.api.main = "3" * 40
                with self.assertRaises(a.ProductionBlock): self.run_operation()
                self.assertEqual(self.api.mutations, 0)

    def test_expired_revoked_or_unverified_sso_cannot_use_provider(self):
        self.auth.active = False
        with self.assertRaises(ValueError): self.run_operation()
        self.auth.active, self.auth.live = True, False
        with self.assertRaisesRegex(a.ProductionBlock, "LIVE_ORIGINAL_SSO"): self.run_operation()
        self.assertEqual(self.api.calls, [])

    def test_no_caller_or_generic_workflow_credential_fallback(self):
        for token in ("", "fixture-sso-bearer", "fixture-api-token", "bad token"):
            with self.subTest(token=token):
                self.env.update(QIKVRT_GITHUB_ADMIN_TOKEN=token, QIKVRT_API_TOKEN="fixture-api-token", GITHUB_TOKEN="generic")
                with self.assertRaises(a.ProductionBlock): self.run_operation()
                self.assertEqual(self.api.calls, [])

    def test_arbitrary_fields_payload_secrets_or_effect_without_acceptance_rejected(self):
        for change in ({"environment": "other"}, {"url": "https://evil.test"}, {"token": "secret"},
                       {"effect_accepted": False}, {"expected_main_sha": []}, {"binding_sha256": None}):
            with self.subTest(change=change), self.assertRaises(a.ProductionBlock):
                self.run_operation(request=dict(self.body, **change))
        self.assertEqual(self.api.calls, [])

    def test_failed_durable_intent_cannot_send(self):
        with mock.patch.object(self.auth.store, "write", side_effect=OSError("fixture store closed")):
            with self.assertRaises(OSError): self.run_operation()
        self.assertEqual(self.api.mutations, 0)

    def test_uncommitted_or_other_runtime_source_has_readonly_preview_and_no_write(self):
        with mock.patch.object(a, "production_source", return_value=False):
            self.assertFalse(self.run_operation(write=False)["implementation_source_verified"])
            with self.assertRaisesRegex(a.ProductionBlock, "CLEAN_ORIGINAL_MAIN_RUNTIME_SOURCE"):
                self.run_operation()
        self.assertEqual(self.api.mutations, 0)


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.vault, self.now = Vault(), [1000]
        self.api = a.ProductionEnvironmentAPI("FIXTURE_ONLY_TOKEN", self.vault, clock=lambda: self.now[0])
        self.opener = mock.Mock(); self.api.opener = self.opener

    def test_fixed_scope_forbids_env_creation_permission_changes_arbitrary_urls(self):
        for method, path in [("PUT", "/repos/ingolf-lohmann/qik-vrt/environments/qikvrt-production"),
                ("GET", "https://evil.test"), ("DELETE", "/user"),
                ("GET", "/repos/foreign/repo"), ("GET", "/repos/ingolf-lohmann/qik-vrt/actions/secrets")]:
            with self.assertRaises(a.ProductionBlock): self.api.call(method, path)
        self.opener.open.assert_not_called()

    def test_rate_limit_persists_and_suppresses_requests_after_new_process(self):
        self.opener.open.side_effect = HTTPError("https://api.github.com/user", 429, "fixture", {"Retry-After": "180"}, io.BytesIO(b"NEVER_RETURN_THIS"))
        with self.assertRaisesRegex(a.ProductionBlock, "HTTP_429"): self.api.call("GET", "/user")
        self.assertEqual(self.vault.read()["github_environment_not_before"], 1180)
        reopened = a.ProductionEnvironmentAPI("OTHER_FIXTURE_TOKEN", self.vault, clock=lambda: self.now[0])
        reopened.opener = mock.Mock()
        with self.assertRaisesRegex(a.ProductionBlock, "COOLDOWN_NO_REQUEST"): reopened.call("GET", "/user")
        reopened.opener.open.assert_not_called()

    def test_sso_header_is_not_confused_with_scope_or_browser_login(self):
        self.opener.open.side_effect = HTTPError("https://api.github.com/user", 403, "fixture", {"X-GitHub-SSO": "required; url=PRIVATE"}, io.BytesIO(b"PRIVATE_TOKEN"))
        with self.assertRaisesRegex(a.ProductionBlock, "GITHUB_SSO_AUTHORIZATION_REQUIRED") as caught:
            self.api.call("GET", "/user")
        self.assertNotIn("PRIVATE", str(caught.exception))
        self.assertEqual(self.opener.open.call_count, 1)

    def test_response_redirect_or_invalid_json_never_accepted(self):
        response = mock.MagicMock(status=200, headers={})
        response.__enter__.return_value = response
        self.opener.open.return_value = response
        response.geturl.return_value = "https://evil.test"
        with self.assertRaisesRegex(a.ProductionBlock, "REDIRECT_REFUSED"): self.api.call("GET", "/user")
        response.geturl.return_value = "https://api.github.com/user"
        response.read.return_value = b'{"login":"one","login":"two"}'
        with self.assertRaises(ValueError): self.api.call("GET", "/user")


class MaterialTests(unittest.TestCase):
    def test_original_binding_accepts_real_matching_pem_and_rejects_changed_private_key(self):
        try:
            from src.qikvrt_personal_auth import require_crypto_runtime
            require_crypto_runtime()
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.x509.oid import NameOID
        except (ImportError, ValueError):
            self.skipTest("Optional locked Personal cryptography unavailable; no material acceptance inferred")
        from datetime import datetime, timedelta, timezone
        from tests.test_self_host_container import declaration
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "DISPOSABLE_TEST_ONLY")])
        now = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                .serial_number(1).not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
                .sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode())
        raw = json.dumps(declaration())
        values = {a.PRODUCTION_VARIABLES[0]: raw, a.PRODUCTION_VARIABLES[1]: hashlib.sha256(raw.encode()).hexdigest(),
            a.PRODUCTION_SECRETS[0]: cert, a.PRODUCTION_SECRETS[1]: cert,
            a.PRODUCTION_SECRETS[2]: key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()}
        self.assertEqual(a.production_material(values), values)
        wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        values[a.PRODUCTION_SECRETS[2]] = wrong.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
        with self.assertRaisesRegex(a.ProductionBlock, "MTLS_MATERIAL_INVALID"): a.production_material(values)

    def test_runtime_source_checks_actual_head_tree_and_dirty_state(self):
        from src import qikvrt_personal_assistant as personal
        for head, tree, dirty, expected in [("1" * 40, "2" * 40, False, True),
                ("3" * 40, "2" * 40, False, False), ("1" * 40, "3" * 40, False, False),
                ("1" * 40, "2" * 40, True, False), (None, None, False, False)]:
            with self.subTest(head=head, dirty=dirty), mock.patch.object(personal, "subject", return_value={"head":head,"tree":tree,"worktree_dirty":dirty}):
                self.assertIs(a.production_source("1" * 40, "2" * 40), expected)

    def test_missing_material_has_no_generated_or_filesystem_fallback(self):
        with self.assertRaisesRegex(a.ProductionBlock, "FIVE_PROTECTED_BINDINGS"): a.production_material({})

    def test_independent_pin_required_before_crypto_or_http(self):
        values = {n: "FIXTURE_ONLY" for n in a.PRODUCTION_VARIABLES + a.PRODUCTION_SECRETS}
        with self.assertRaisesRegex(a.ProductionBlock, "INDEPENDENT_HOST_BINDING_PIN"): a.production_material(values)

    def test_real_sealed_box_roundtrip_and_wrong_key_version(self):
        try:
            import nacl
            from nacl.public import PrivateKey, SealedBox
        except ImportError:
            self.skipTest("Optional locked PyNaCl unavailable; no encryption/live delivery inferred")
        if nacl.__version__ != "1.6.2": self.skipTest("Optional locked PyNaCl 1.6.2 unavailable")
        key = PrivateKey.generate()
        public = base64.b64encode(bytes(key.public_key)).decode()
        sealed = a.seal_environment_secret(public, "DISPOSABLE_TEST_MATERIAL")
        self.assertEqual(SealedBox(key).decrypt(base64.b64decode(sealed)), b"DISPOSABLE_TEST_MATERIAL")
        self.assertNotIn("DISPOSABLE_TEST_MATERIAL", sealed)
        with self.assertRaises(a.ProductionBlock): a.seal_environment_secret("invalid", "DISPOSABLE")
        with mock.patch.object(nacl, "__version__", "unadmitted-version"):
            with self.assertRaises(a.ProductionBlock): a.seal_environment_secret(public, "DISPOSABLE")


class HTTPIntegrationTests(unittest.TestCase):
    """Real loopback request framing and shared SSO handler, provider double only."""
    def setUp(self):
        ProductionTests.setUp(self)
        from http.server import ThreadingHTTPServer
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        import qikvrt_github_api_shim as shim
        from src.qikvrt_personal_assistant import personal_handler
        self.shim = shim
        self.env.update(QIKVRT_PRODUCTION_ENVIRONMENT_ENABLED="1", QIKVRT_RATE_LIMIT_PER_MINUTE="10000")
        p = mock.patch.dict(os.environ, self.env); p.start(); self.addCleanup(p.stop)
        original = a.production_environment
        p = mock.patch.object(a, "production_environment", side_effect=lambda *args, **kwargs: original(*args, **dict(kwargs, api_factory=lambda *_: self.api)))
        p.start(); self.addCleanup(p.stop)
        runtime = SimpleNamespace(personal_auth=self.auth, lock=self.auth.lock, native_terminal=None, auth_receipt=None)
        self.auth.config = {"redirect_uri": "placeholder", "issuer": "https://fixture.test"}
        with shim._RATE_LOCK: shim._RATE_WINDOWS.clear()
        try: self.server = ThreadingHTTPServer(("127.0.0.1", 0), personal_handler(shim.QikvrtGitHubApiShim, runtime, auth_only=True))
        except PermissionError: self.skipTest("Host denies sockets; native CI required, no wire acceptance inferred")
        self.server.authority_sso = runtime
        self.origin = "http://127.0.0.1:" + str(self.server.server_port)
        self.auth.config["redirect_uri"] = self.origin + "/personal/auth/callback"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.addCleanup(self.stop)

    def stop(self): self.server.shutdown(); self.server.server_close(); self.thread.join(3)

    def wire(self, path=None, *, method="POST", body=None, origin=None, bearer="fixture-sso-bearer"):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            c.request(method, path or "/repos/ingolf-lohmann/qik-vrt/qikvrt/production-environment",
                body=json.dumps(self.body if body is None else body) if method == "POST" else None,
                headers={"Content-Type": "application/json", "Origin": origin or self.origin, "Authorization": "Bearer " + bearer})
            result = c.getresponse(); return result.status, json.loads(result.read())
        finally: c.close()

    def test_real_http_route_uses_the_original_provider_controller(self):
        status, result = self.wire()
        self.assertEqual(status, 200, result)
        self.assertEqual(result["mutation_count"], 5)

    def test_foreign_origin_repo_expired_sso_and_plain_api_token_cannot_write(self):
        self.assertEqual(self.wire(origin="https://evil.test")[0], 409)
        self.assertEqual(self.wire(path="/repos/foreign/repo/qikvrt/production-environment")[0], 409)
        self.assertEqual(self.wire(bearer="fixture-api-token")[0], 409)
        self.auth.active = False
        self.assertEqual(self.wire()[0], 409)
        self.assertEqual(self.api.mutations, 0)

    def test_auth_only_has_no_model_key_requirement_or_model_operations(self):
        status, result = self.wire(path="/personal/auth/status", method="GET")
        self.assertEqual(status, 200, result)
        self.assertEqual(self.wire(path="/personal/create")[0], 404)
        self.assertEqual(self.wire(path="/personal/capabilities", method="GET")[0], 404)
        self.assertEqual(self.api.calls, [])

    def test_auth_only_assets_are_same_origin_and_secret_free(self):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            c.request("GET", "/personal/")
            r=c.getresponse(); raw=r.read()
            self.assertEqual(r.status, 200)
            self.assertIn(b"/personal/authority.js", raw)
            self.assertIn("default-src 'none'", r.getheader("Content-Security-Policy"))
            self.assertNotIn(b"fixture-sso-bearer", raw)
        finally: c.close()


class StartupTests(unittest.TestCase):
    def test_original_profile_and_writer_lock_are_reused_without_a_model_key(self):
        from contextlib import ExitStack, contextmanager
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        import qikvrt_github_api_shim as shim
        import qikvrt_personal_auth as native_auth
        from tests.test_qikvrt_personal_auth import CONFIG
        vault, held = Vault(), []
        @contextmanager
        def fence(_state):
            held.append(True)
            try: yield
            finally: held.pop()
        vault.provision_lock = fence
        environment = {"QIKVRT_PRODUCTION_ENVIRONMENT_ENABLED":"1", "QIKVRT_SSO_STATE_DIR":"/private/original-profile",
                       "QIKVRT_SSO_AUTH_CONFIG":"/private/original-oidc", "QIKVRT_SSO_PROFILE":"openai"}
        with mock.patch.dict(os.environ, environment), mock.patch.object(native_auth, "load_config", return_value=CONFIG), \
             mock.patch.object(native_auth, "OSSecretStore", return_value=vault) as create:
            with ExitStack() as stack:
                handler, runtime = shim.authority_sso_handler(stack, "127.0.0.1", 8771)
                self.assertIs(runtime.personal_auth.store, vault)
                self.assertIs(runtime.lock, runtime.personal_auth.lock)
                self.assertEqual(held, [True])
                self.assertFalse(hasattr(runtime, "credential"))
                self.assertTrue(issubclass(handler, shim.QikvrtGitHubApiShim))
                create.assert_called_once_with("/private/original-profile", "openai")
            self.assertEqual(held, [])

    def test_unregistered_or_remote_sso_context_cannot_start(self):
        from contextlib import ExitStack
        import qikvrt_github_api_shim as shim
        for host in ("0.0.0.0", "127.0.0.1"):
            with self.subTest(host=host), mock.patch.dict(os.environ, {"QIKVRT_PRODUCTION_ENVIRONMENT_ENABLED":"1", "QIKVRT_SSO_STATE_DIR":"", "QIKVRT_SSO_AUTH_CONFIG":""}), ExitStack() as stack:
                with self.assertRaises(ValueError): shim.authority_sso_handler(stack, host, 8766)


if __name__ == "__main__": unittest.main()
