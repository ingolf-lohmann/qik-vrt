# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Simulated OIDC/Secret Service lifecycle; real optional RSA negative controls.

No test provisions a real credential, signs in a person or attests Firefox.
"""
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from src import qikvrt_personal_auth as a
from src import qikvrt_personal_assistant as p
from src import qikvrt_effect_ack_http_terminal as terminal

CONFIG = {"issuer": "https://identity.example.test", "client_id": "registered-test-client", "subject": "bound-test-owner",
          "authorization_endpoint": "https://identity.example.test/authorize", "token_endpoint": "https://identity.example.test/token",
          "jwks_uri": "https://identity.example.test/keys", "revocation_endpoint": "https://identity.example.test/revoke",
          "redirect_uri": "http://127.0.0.1:8771/personal/auth/callback", "refresh_protection": "rotation"}


class VaultDouble:
    evidence_class = "SIMULATED_OS_VAULT_NOT_NATIVE"
    profile = "test-profile-only"

    def __init__(self):
        self.value = {"schema": "qikvrt_protected_personal_v1", "profile": self.profile}
        self.writes = []

    def read(self):
        return copy.deepcopy(self.value)

    def write(self, value):
        self.value = copy.deepcopy(value)
        self.writes.append(copy.deepcopy(value))


class IdPDouble:
    evidence_class = "SIMULATED_OIDC_NOT_AUTHENTICATED_PRODUCT"

    def __init__(self):
        self.calls, self.n = [], 0
        self.fail, self.same_refresh = None, False

    def request(self, url, fields=None):
        self.calls.append((url, copy.deepcopy(fields)))
        if self.fail and url.endswith(self.fail[0]):
            raise a.AuthBlock(self.fail[1])
        if url.endswith("openid-configuration"):
            return {**CONFIG, "code_challenge_methods_supported": ["S256"], "response_modes_supported": ["form_post"],
                    "id_token_signing_alg_values_supported": ["RS256"], "token_endpoint_auth_methods_supported": ["none"]}
        if url.endswith("keys"):
            return {"keys": []}
        if url.endswith("revoke"):
            return {}
        self.n += 1
        result = {"access_token": "SIMULATED_ACCESS_" + str(self.n), "refresh_token": "SIMULATED_REFRESH_" + str(self.n),
                  "expires_in": 120, "token_type": "Bearer", "scope": "openid offline_access"}
        if fields["grant_type"] == "authorization_code":
            result["id_token"] = "SIMULATED_VALIDATED_SEPARATELY"
        elif self.same_refresh:
            result["refresh_token"] = fields["refresh_token"]
        return result


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.vault, self.idp, self.now = VaultDouble(), IdPDouble(), [1000]
        self.auth = a.PersonalAuth(self.vault, CONFIG, transport=self.idp, clock=lambda: self.now[0])
        self.verify = patch.object(a, "verify_id_token", return_value={"sub": CONFIG["subject"]})
        self.verify.start()
        self.crypto = patch.object(a, "require_crypto_runtime", return_value=None)
        self.crypto.start()

    def tearDown(self):
        self.verify.stop()
        self.crypto.stop()

    def login(self):
        begin = self.auth.begin()
        token = self.auth.complete({"state": begin["state"], "code": "test-code-one-use"})
        return token

    def test_pkce_nonce_state_form_post_and_no_token_in_authorization_url(self):
        begin = self.auth.begin()
        fields = parse_qs(urlsplit(begin["authorization_url"]).query)
        self.assertEqual(fields["response_mode"], ["form_post"])
        self.assertEqual(fields["code_challenge_method"], ["S256"])
        self.assertEqual(fields["code_challenge"], [a.b64(a.hashlib.sha256(self.auth.pending["verifier"].encode()).digest())])
        for secret in ("access_token", "refresh_token", "id_token", "code_verifier"):
            self.assertNotIn(secret, fields)
        self.assertEqual(fields["scope"], ["openid offline_access"])
        self.assertGreaterEqual(len(fields["nonce"][0]), 32)

    def test_wrong_state_no_network_and_replay_no_second_exchange(self):
        begin = self.auth.begin(); count = len(self.idp.calls)
        with self.assertRaises(a.AuthBlock):
            self.auth.complete({"state": "wrong", "code": "code"})
        self.assertEqual(len(self.idp.calls), count)
        self.auth.complete({"state": begin["state"], "code": "code"})
        count = len(self.idp.calls)
        with self.assertRaises(a.AuthBlock):
            self.auth.complete({"state": begin["state"], "code": "code"})
        self.assertEqual(len(self.idp.calls), count)

    def test_expired_authorization_and_duplicate_start(self):
        begin = self.auth.begin()
        with self.assertRaises(a.AuthBlock): self.auth.begin()
        self.now[0] += 301
        with self.assertRaises(a.AuthBlock): self.auth.complete({"state": begin["state"], "code": "code"})
        self.auth.begin()

    def test_cancelled_or_rejected_login_allows_new_authentication(self):
        begin = self.auth.begin()
        with self.assertRaises(a.AuthBlock): self.auth.complete({"state": begin["state"], "error": "access_denied", "error_description": "DO_NOT_REFLECT"})
        self.login()

    def test_invalid_token_can_be_followed_by_fresh_sign_in(self):
        begin = self.auth.begin()
        with patch.object(a, "verify_id_token", side_effect=a.AuthBlock("OIDC_ID_TOKEN_REJECTED")):
            with self.assertRaises(a.AuthBlock): self.auth.complete({"state": begin["state"], "code": "code"})
        self.assertEqual(self.auth.status()["state"], "REAUTH_REQUIRED")
        self.login()

    def test_restart_preserves_protected_tokens_but_requires_current_refresh(self):
        local = self.login()
        saved = self.vault.read()["auth"]["refresh_token"]
        self.auth = a.PersonalAuth(self.vault, CONFIG, transport=self.idp, clock=lambda: self.now[0])
        self.assertFalse(self.auth.observed)
        self.auth.authenticate(local)
        self.assertNotEqual(saved, self.vault.read()["auth"]["refresh_token"])
        self.assertTrue(any(v["auth"]["state"] == "REFRESH_PENDING" for v in self.vault.writes))
        self.assertFalse(self.auth.status()["live_authentication_observed_this_process"])

    def test_expired_access_refreshes_once_and_rotates(self):
        local = self.login(); self.now[0] += 121
        self.auth.authenticate(local)
        self.assertEqual(self.vault.read()["auth"]["refresh_token"], "SIMULATED_REFRESH_2")
        count = len(self.idp.calls)
        self.auth.authenticate(local)
        self.assertEqual(count, len(self.idp.calls))

    def test_expired_local_session_requires_oidc_and_retires_old_grant(self):
        local = self.login(); self.now[0] += 43201
        with self.assertRaises(a.AuthBlock): self.auth.authenticate(local)
        new = self.login()
        self.assertNotEqual(local, new)
        self.assertTrue(any(url.endswith("revoke") for url, _ in self.idp.calls))
        with self.assertRaises(a.AuthBlock): self.auth.authenticate(local)
        self.auth.authenticate(new)

    def test_refresh_rejection_requires_login(self):
        local = self.login(); self.now[0] += 121
        self.idp.fail = ("token", "OIDC_AUTHENTICATION_REJECTED")
        with self.assertRaises(a.AuthBlock): self.auth.authenticate(local)
        self.assertEqual(self.auth.status()["state"], "REAUTH_REQUIRED")
        self.idp.fail = None
        self.login()

    def test_timeout_and_restart_never_retry_old_refresh(self):
        local = self.login(); self.now[0] += 121
        self.idp.fail = ("token", "OIDC_RESULT_UNRESOLVED_NO_RETRY")
        with self.assertRaises(a.AuthBlock): self.auth.authenticate(local)
        self.assertEqual(self.auth.status()["state"], "REFRESH_PENDING")
        count = len(self.idp.calls)
        restarted = a.PersonalAuth(self.vault, CONFIG, transport=self.idp, clock=lambda: self.now[0])
        with self.assertRaises(a.AuthBlock): restarted.authenticate(local)
        with self.assertRaises(a.AuthBlock): restarted.begin()
        self.assertEqual(count, len(self.idp.calls))

    def test_nonrotating_refresh_fails_closed(self):
        local = self.login(); self.idp.same_refresh = True
        with self.assertRaises(a.AuthBlock): self.auth.authenticate(local, renew=True)
        self.assertEqual(self.auth.status()["state"], "REFRESH_PENDING")

    def test_refresh_serializes_concurrent_requests(self):
        local = self.login(); self.now[0] += 121
        errors = []
        def run():
            try: self.auth.authenticate(local)
            except Exception as exc: errors.append(type(exc).__name__)
        workers = [threading.Thread(target=run) for _ in range(8)]
        for worker in workers: worker.start()
        for worker in workers: worker.join()
        self.assertEqual(errors, [])
        self.assertEqual(len([f for _, f in self.idp.calls if f and f.get("grant_type") == "refresh_token"]), 1)

    def test_logout_invalidates_local_before_revocation_and_allows_relogin(self):
        local = self.login()
        result = self.auth.logout()
        self.assertTrue(result["local_logout"])
        self.assertEqual(self.auth.status()["state"], "SIGNED_OUT")
        pending = [v["auth"] for v in self.vault.writes if v["auth"]["state"] == "REVOCATION_PENDING"]
        self.assertTrue(pending and all(v["local_token"] == "" for v in pending))
        with self.assertRaises(a.AuthBlock): self.auth.authenticate(local)
        self.assertNotEqual(local, self.login())

    def test_failed_revocation_stays_pending_without_automatic_retry(self):
        local = self.login(); self.idp.fail = ("revoke", "OIDC_RESULT_UNRESOLVED_NO_RETRY")
        self.assertEqual(self.auth.logout()["remote_revocation"], "UNRESOLVED_NO_RETRY")
        count = len(self.idp.calls)
        with self.assertRaises(a.AuthBlock): self.auth.authenticate(local)
        with self.assertRaises(a.AuthBlock): self.auth.begin()
        with self.assertRaises(a.AuthBlock): self.auth.logout()
        self.assertEqual(len(self.idp.calls), count)

    def test_missing_revocation_endpoint_is_explicit_not_claimed(self):
        config = dict(CONFIG); config.pop("revocation_endpoint")
        self.auth = a.PersonalAuth(self.vault, config, transport=self.idp, clock=lambda: self.now[0])
        self.login()
        self.assertEqual(self.auth.logout()["remote_revocation"], "UNSUPPORTED")

    def test_profile_binding_change_and_discovery_mismatch_rejected(self):
        self.login()
        with self.assertRaises(a.AuthBlock): a.PersonalAuth(self.vault, dict(CONFIG, subject="other-owner"), transport=self.idp)
        other = a.PersonalAuth(VaultDouble(), dict(CONFIG, client_id="other"), transport=self.idp)
        with patch.object(self.idp, "request", return_value=dict(CONFIG, issuer="https://wrong.test")):
            with self.assertRaises(a.AuthBlock): other.begin()

    def test_public_status_never_attests_test_double_as_native(self):
        self.login()
        text = json.dumps(self.auth.status())
        self.assertNotIn("SIMULATED_ACCESS", text)
        self.assertNotIn("SIMULATED_REFRESH", text)
        self.assertFalse(self.auth.status()["live_authentication_observed_this_process"])
        self.assertEqual(self.auth.status()["biometric_verification"], "DELEGATED_TO_IDP_NOT_ATTESTED")

    def test_no_oidc_secrets_in_existing_sqlite_or_public_capabilities(self):
        self.login()
        with tempfile.TemporaryDirectory() as tmp:
            runtime = p.PersonalRuntime(Path(tmp) / "private", "explicit-test", "test-model-key", "x" * 48, transport=object())
            runtime.personal_auth = self.auth
            try:
                for secret in self.auth.sensitive_values():
                    with self.assertRaises(p.CapabilityBlock): runtime._nonsecret({"text": secret})
                raw = json.dumps(runtime.capabilities()).encode()
                for secret in self.auth.sensitive_values():
                    self.assertNotIn(secret.encode(), raw)
                    for file in runtime.root.iterdir():
                        self.assertNotIn(secret.encode(), file.read_bytes())
            finally: runtime.close()

    def test_http_callback_form_post_origin_replay_and_no_logging(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = p.PersonalRuntime(Path(tmp) / "private", "explicit-test", "test-model-key", "x" * 48, transport=object())
            server = ThreadingHTTPServer(("127.0.0.1", 0), p.personal_handler(terminal.Handler, runtime))
            origin = f"http://127.0.0.1:{server.server_port}"
            config = dict(CONFIG, redirect_uri=origin + "/personal/auth/callback")
            runtime.personal_auth = a.PersonalAuth(self.vault, config, transport=self.idp, clock=lambda: self.now[0])
            worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
            def post(path, fields, form=False, from_origin=origin):
                data = urlencode(fields).encode() if form else a.encoded(fields)
                return urlopen(Request(origin + path, data=data, headers={"Content-Type": "application/x-www-form-urlencoded" if form else "application/json", "Origin": from_origin}), timeout=3)
            try:
                with patch("sys.stderr", new_callable=io.StringIO) as logged:
                    with self.assertRaises(HTTPError): post("/personal/auth/start", {"confirmed": True}, from_origin="https://evil.test")
                    with post("/personal/auth/start", {"confirmed": True}) as response: begin = json.load(response)
                    with self.assertRaises(HTTPError): urlopen(origin + "/personal/auth/callback?code=DO_NOT_LOG&state=" + begin["state"])
                    with post("/personal/auth/callback", {"state": begin["state"], "code": "DO_NOT_LOG"}, True, CONFIG["issuer"]) as response:
                        html = response.read().decode()
                        self.assertIn("postMessage", html)
                        self.assertIn("nonce-", response.headers["Content-Security-Policy"])
                        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
                        self.assertNotIn("Set-Cookie", response.headers)
                        self.assertNotIn("DO_NOT_LOG", html)
                    with self.assertRaises(HTTPError): post("/personal/auth/callback", {"state": begin["state"], "code": "REPLAY"}, True)
                    self.assertEqual(logged.getvalue(), "")
            finally:
                server.shutdown(); server.server_close(); worker.join(); runtime.close()


class ProtectedStoreAndConfigTests(unittest.TestCase):
    def test_provisioning_reuses_runtime_writer_lock(self):
        if sys.platform != "linux": self.skipTest("Linux Secret Service path only")
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "private"
            runtime = p.PersonalRuntime(state, "test", "fixture-model-key", "x" * 48, transport=object())
            store = object.__new__(a.OSSecretStore)
            try:
                with self.assertRaisesRegex(a.AuthBlock, "PROFILE_IN_USE"):
                    with store.provision_lock(state): self.fail("competing credential writer admitted")
            finally: runtime.close()
            with store.provision_lock(state):
                with self.assertRaises(a.AuthBlock):
                    with store.provision_lock(state): self.fail("second writer admitted")

    def test_unavailable_crypto_stops_before_identity_provider_request(self):
        transport = IdPDouble();auth = a.PersonalAuth(VaultDouble(), CONFIG, transport=transport)
        with patch.object(a, "require_crypto_runtime", side_effect=a.AuthBlock("OIDC_CRYPTOGRAPHY_RUNTIME_BINDING_UNAVAILABLE")):
            with self.assertRaises(a.AuthBlock): auth.begin()
        self.assertEqual(transport.calls, [])

    def test_standard_cli_starts_without_personal_credentials_or_optional_runtime(self):
        env = {k:v for k,v in os.environ.items() if k not in {"OPENAI_API_KEY", "GEMINI_API_KEY", "QIKVRT_PERSONAL_LOCAL_TOKEN"}}
        child = subprocess.Popen([sys.executable, "-B", "src/qikvrt_effect_ack_http_terminal.py", "--port", "0"], cwd=a.ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            value = json.loads(child.stdout.readline())
            self.assertEqual(value["state"], "READY")
            self.assertFalse(value["personal_adapter_enabled"])
        finally:
            child.kill(); child.wait(timeout=5); child.stdout.close(); child.stderr.close()

    def test_json_escaped_credentials_cannot_enter_transcripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = p.PersonalRuntime(Path(tmp) / "private", "test", 'fixture-quoted-"-key', "x" * 48, transport=object())
            try:
                with self.assertRaises(p.CapabilityBlock): runtime._nonsecret({"text": 'fixture-quoted-"-key'})
            finally: runtime.close()

    def test_actual_process_restart_of_simulated_vault_recovery_logic(self):
        # This file contains invented fixture strings only. It is deliberately
        # NOT a secure store or a production backend; the directory is removed.
        script = r'''
import json,sys,time
from pathlib import Path
from unittest.mock import patch
from tests.test_qikvrt_personal_auth import VaultDouble,IdPDouble,CONFIG
from src import qikvrt_personal_auth as a
class FileFixture(VaultDouble):
 def read(self):
  return json.loads(Path(sys.argv[1]).read_text()) if Path(sys.argv[1]).exists() else super().read()
 def write(self,value):
  Path(sys.argv[1]).write_text(json.dumps(value))
v=FileFixture(); transport=IdPDouble()
auth=a.PersonalAuth(v,CONFIG,transport=transport,clock=lambda:1000)
with patch.object(a,'verify_id_token',return_value={'sub':CONFIG['subject']}),patch.object(a,'require_crypto_runtime',return_value=None):
 if sys.argv[2]=='first':
  begin=auth.begin();local=auth.complete({'state':begin['state'],'code':'fixture-code'})
  print(json.dumps({'local':local}),flush=True)
  time.sleep(30)
 else:
  local=v.read()['auth']['local_token'];transport.n=10
  auth.authenticate(local)
  print(json.dumps({'state':auth.status()['state'],'fresh_refresh':v.read()['auth']['refresh_token']=='SIMULATED_REFRESH_11','native':auth.status()['live_authentication_observed_this_process']}),flush=True)
'''
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "SIMULATED_ONLY.json")
            child = subprocess.Popen([sys.executable, "-B", "-c", script, path, "first"], cwd=a.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertTrue(json.loads(child.stdout.readline())["local"])
                child.kill(); child.wait(timeout=5)
                result = subprocess.run([sys.executable, "-B", "-c", script, path, "second"], cwd=a.ROOT, capture_output=True, text=True, timeout=5, check=True)
                self.assertEqual(json.loads(result.stdout), {"state": "AUTHENTICATED", "fresh_refresh": True, "native": False})
            finally:
                if child.poll() is None: child.kill(); child.wait(timeout=5)
                child.stdout.close(); child.stderr.close()

    def test_missing_native_secret_store_never_creates_file_fallback(self):
        with patch.object(Path, "stat", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(a.AuthBlock, "UNAVAILABLE_NO_FALLBACK"):
                a.OSSecretStore("/tmp/private-test-only", "openai")

    def test_store_uses_stdin_fixed_arguments_and_verified_readback(self):
        store = object.__new__(a.OSSecretStore)
        store.command, store.attributes, store.profile = Path("/usr/bin/secret-tool"), ["profile", "test"], "test"
        value = {"schema": "qikvrt_protected_personal_v1", "profile": "test", "key": "TEST_DO_NOT_PRINT_SECRET"}
        with patch.object(a.subprocess, "run", side_effect=[subprocess.CompletedProcess([], 0, b"", b""), subprocess.CompletedProcess([], 0, a.encoded(value), b"")]) as run:
            store.write(value)
            self.assertEqual(run.call_args_list[0].kwargs["input"], a.encoded(value))
            self.assertNotIn(value["key"], " ".join(run.call_args_list[0].args[0]))
            self.assertNotIn("OPENAI_API_KEY", run.call_args_list[0].kwargs["env"])
        with patch.object(a.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, b"", b"SECRET_IN_FAILURE")):
            with self.assertRaises(a.AuthBlock) as exc: store.read()
            self.assertNotIn("SECRET_IN_FAILURE", str(exc.exception))

    def test_unsafe_or_unbound_config_and_duplicate_json_rejected(self):
        origin = "http://127.0.0.1:8771"
        a.validate_config(CONFIG, origin)
        for update in ({"issuer": "http://evil.test"}, {"subject": "<unknown>"}, {"redirect_uri": "https://evil.test/callback"}, {"refresh_protection": "none"}):
            with self.subTest(update=update), self.assertRaises(a.AuthBlock): a.validate_config(dict(CONFIG, **update), origin)
        with self.assertRaises(a.AuthBlock): a.object_json('{"a":1,"a":2}')
        with self.assertRaises(a.AuthBlock): a.object_json('{"a":NaN}')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"; path.write_bytes(a.encoded(CONFIG)); path.chmod(0o600)
            self.assertEqual(a.load_config(path, origin), CONFIG)
            path.chmod(0o644)
            with self.assertRaises(a.AuthBlock): a.load_config(path, origin)
        with self.assertRaises(a.AuthBlock): a.load_config(a.ROOT / "config.json", origin)


try:
    import cryptography
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import hashes
    CRYPTO = cryptography.__version__ == "50.0.2"
except ImportError:
    CRYPTO = False


@unittest.skipUnless(CRYPTO, "Optional Personal RSA runtime cryptography 50.0.2 unavailable; no signature/live-SSO acceptance inferred")
class RealRSAVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pub = cls.key.public_key().public_numbers()
        integer = lambda n: a.b64(n.to_bytes((n.bit_length() + 7) // 8, "big"))
        cls.jwks = {"keys": [{"kid": "test-key", "kty": "RSA", "n": integer(pub.n), "e": integer(pub.e)}]}

    def token(self, update=None, header=None):
        claims = {"iss": CONFIG["issuer"], "sub": CONFIG["subject"], "aud": CONFIG["client_id"], "iat": 1000, "exp": 1200, "nonce": "bound-nonce"}
        claims.update(update or {})
        head = a.b64(a.encoded(header or {"kid": "test-key", "alg": "RS256"}))
        body = a.b64(a.encoded(claims)); data = (head + "." + body).encode()
        return data.decode() + "." + a.b64(self.key.sign(data, padding.PKCS1v15(), hashes.SHA256()))

    def test_actual_signature_issuer_owner_audience_nonce_and_expiry(self):
        claims = a.verify_id_token(self.token(), CONFIG, self.jwks, "bound-nonce", "access", 1000)
        self.assertEqual(claims["sub"], CONFIG["subject"])
        for update in ({"iss": "https://wrong.test"}, {"sub": "attacker"}, {"aud": "other"}, {"aud": [CONFIG["client_id"], "other"]},
                       {"azp": "other"}, {"exp": 999}, {"iat": 2000}, {"nonce": "wrong"}, {"nbf": 2000}, {"at_hash": "wrong"}, {"exp": True}):
            with self.subTest(update=update), self.assertRaises(a.AuthBlock):
                a.verify_id_token(self.token(update), CONFIG, self.jwks, "bound-nonce", "access", 1000)

    def test_algorithm_key_substitution_and_signature_tamper_rejected(self):
        for header in ({"alg": "none", "kid": "test-key"}, {"alg": "HS256", "kid": "test-key"},
                       {"alg": "RS256", "kid": "missing"}, {"alg": "RS256", "kid": "test-key", "jku": "https://evil.test"}):
            with self.subTest(header=header), self.assertRaises(a.AuthBlock):
                a.verify_id_token(self.token(header=header), CONFIG, self.jwks, "bound-nonce", "access", 1000)
        token = self.token().split("."); token[-1] = a.b64(b"wrong-signature")
        with self.assertRaises(a.AuthBlock): a.verify_id_token(".".join(token), CONFIG, self.jwks, "bound-nonce", "access", 1000)
        with self.assertRaises(a.AuthBlock): a.verify_id_token(self.token(), CONFIG, {"keys": self.jwks["keys"] * 2}, "bound-nonce", "access", 1000)

    def test_nonce_is_optional_only_for_a_refresh_id_token(self):
        token = self.token({"nonce": None})
        with self.assertRaises(a.AuthBlock): a.verify_id_token(token, CONFIG, self.jwks, "bound-nonce", "access", 1000)
        # OIDC Core 12.2 permits omission, not substitution, on refresh.
        head, body, _ = self.token().split(".")
        claims = json.loads(a.unb64(body));claims.pop("nonce")
        body = a.b64(a.encoded(claims));data = (head + "." + body).encode()
        token = data.decode() + "." + a.b64(self.key.sign(data, padding.PKCS1v15(), hashes.SHA256()))
        a.verify_id_token(token, CONFIG, self.jwks, "bound-nonce", "access", 1000, nonce_optional=True)
        with self.assertRaises(a.AuthBlock): a.verify_id_token(self.token({"nonce":"wrong"}), CONFIG, self.jwks, "bound-nonce", "access", 1000, nonce_optional=True)


if __name__ == "__main__":
    unittest.main()
