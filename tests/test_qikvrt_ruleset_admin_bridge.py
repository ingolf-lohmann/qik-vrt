# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Executable negative controls for the one-shot administrative carrier."""
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import unittest
import tempfile
from unittest.mock import patch

from tools import qikvrt_ruleset_admin_bridge as bridge

HEAD = "1" * 40
TREE = "2" * 40
NOW = 1789550000
REPO = {"id": bridge.REPO_ID, "full_name": bridge.AUTHORITY}


class Reconciler:
    def __init__(self):
        self.current = False
        self.calls = 0
        self.fail_after_put = False

    def load_policy(self):
        return {"repository": bridge.AUTHORITY, "ruleset_id": bridge.RULESET}

    def evaluate(self, snapshot, policy):
        return {"state": "CURRENT" if snapshot["current"] else "DRIFT", "pre_state_sha256": "digest"}

    def reconcile(self, token, policy):
        self.calls += 1
        self.current = True
        if self.fail_after_put:
            raise RuntimeError("unsafe upstream response MUST NOT be printed")
        return {"state": "CURRENT", "mutation": "PUT", "effect_observed": True}


class Api:
    def __init__(self, reconciler):
        self.reconciler = reconciler
        self.calls = []
        self.overrides = {}
        self.carrier_reads = 0
        self.drift_after = None
        self.revoke_fails = False
        self.app = {"id": 7, "client_id": "Iv23fixture"}
        self.installation = {"id": 8, "app_id": 7, "account": {"login": "Goldkelch"},
                             "permissions": {"administration": "write"}, "suspended_at": None}
        self.grant = {"token": "fixture-installation-token", "permissions": {"administration": "write", "metadata": "read"},
                      "repositories": [REPO], "expires_at": datetime.fromtimestamp(NOW + 3600, timezone.utc).isoformat()}

    def __call__(self, method, path, token, payload=None):
        self.calls.append((method, path, token, payload))
        if path in self.overrides:
            return self.overrides[path]
        if path.endswith("/pulls/381"):
            self.carrier_reads += 1
            head = "f" * 40 if self.drift_after and self.carrier_reads >= self.drift_after else HEAD
            return {"state": "open", "head": {"sha": head, "ref": bridge.BRANCH}}
        if path.endswith("/git/ref/heads/" + bridge.BRANCH):
            return {"object": {"sha": HEAD}}
        if path.endswith("/git/commits/" + HEAD):
            return {"parents": [{"sha": bridge.PARENT}], "tree": {"sha": TREE}}
        if path.endswith("/git/ref/heads/main"):
            return {"object": {"sha": bridge.MAIN}}
        if path.endswith("/git/commits/" + bridge.MAIN):
            return {"tree": {"sha": bridge.MAIN_TREE}}
        if path.endswith("/rulesets/19344903"):
            return {"current": self.reconciler.current}
        if path == "/app":
            return self.app
        if path.endswith("/installation"):
            return self.installation
        if method == "POST":
            assert path == "/app/installations/8/access_tokens"
            assert payload == {"repository_ids": [bridge.REPO_ID], "permissions": {"administration": "write"}}
            return self.grant
        if path.startswith("/installation/repositories"):
            return {"total_count": 1, "repositories": [REPO]}
        if method == "DELETE":
            assert path == "/installation/token"
            if self.revoke_fails:
                raise RuntimeError("do not print fixture-installation-token")
            return {}
        raise AssertionError((method, path))


class RulesetAdminBridgeTests(unittest.TestCase):
    def setUp(self):
        self.env = {"GITHUB_REPOSITORY": bridge.CARRIER, "GITHUB_EVENT_NAME": "push",
                    "GITHUB_ACTOR": "ingolf-lohmann", "GITHUB_RUN_ATTEMPT": "1",
                    "GITHUB_REF": "refs/heads/" + bridge.BRANCH, "GITHUB_SHA": HEAD,
                    "GITHUB_RUN_ID": "42", "GH_TOKEN": "fixture-read-token",
                    "QIKVRT_RULESET_APP_CLIENT_ID": "Iv23fixture", "QIKVRT_RULESET_APP_ID": "7",
                    "QIKVRT_RULESET_APP_PRIVATE_KEY": "fixture-private-key-NEVER-LOG"}
        self.event = {"before": bridge.PARENT, "after": HEAD, "forced": False, "created": False, "deleted": False}
        self.reconciler = Reconciler()
        self.api = Api(self.reconciler)
        self.signed = 0

    def run_bridge(self):
        def sign(*args):
            self.signed += 1
            return "fixture-jwt-NEVER-LOG"
        result = bridge.execute(self.event, self.env, self.reconciler, self.api, sign, lambda: NOW)
        text = json.dumps(result)
        for secret in ("fixture-private-key-NEVER-LOG", "fixture-jwt-NEVER-LOG", "fixture-installation-token", "fixture-read-token"):
            self.assertNotIn(secret, text)
        self.assertFalse(result["effect_ack_done"])
        self.assertFalse(result["source_promotion"])
        self.assertFalse(result["review_submission"])
        return result

    def test_scoped_success_independent_readback_and_revocation(self):
        result = self.run_bridge()
        self.assertEqual(result["state"], "RULESET_CURRENT")
        self.assertEqual(result["carrier_tree"], TREE)
        self.assertTrue(result["effect_observed"])
        self.assertTrue(result["token_revoked"])
        reads = [c for c in self.api.calls if c[1].endswith("/rulesets/19344903")]
        self.assertEqual(len(reads), 2)
        self.assertTrue(all(c[2] == "fixture-read-token" for c in reads))

    def test_missing_configuration_blocks_before_signing_and_privileged_write(self):
        self.env["QIKVRT_RULESET_APP_PRIVATE_KEY"] = ""
        result = self.run_bridge()
        self.assertEqual(result["first_blocker"], "RULESET_APP_CONFIGURATION_MISSING")
        self.assertEqual(self.signed, 0)
        self.assertEqual(self.reconciler.calls, 0)
        self.assertFalse(any(c[0] != "GET" for c in self.api.calls))

    def test_absent_both_identifiers_is_explicit_hold(self):
        self.env["QIKVRT_RULESET_APP_CLIENT_ID"] = ""
        self.env["QIKVRT_RULESET_APP_ID"] = ""
        self.assertEqual(self.run_bridge()["first_blocker"], "RULESET_APP_CONFIGURATION_MISSING")

    def test_client_id_only_and_documented_app_id_only(self):
        for absent in ("QIKVRT_RULESET_APP_CLIENT_ID", "QIKVRT_RULESET_APP_ID"):
            with self.subTest(absent=absent):
                self.setUp()
                self.env[absent] = ""
                self.assertEqual(self.run_bridge()["state"], "RULESET_CURRENT")

    def test_wrong_app_identity_blocks_before_token_creation(self):
        self.api.app["id"] = 9
        self.assertEqual(self.run_bridge()["first_blocker"], "APP_IDENTITY_MISMATCH")
        self.assertFalse(any(c[0] == "POST" for c in self.api.calls))

    def test_wrong_installation_owner_blocks_before_token_creation(self):
        self.api.installation["account"]["login"] = "ingolf-lohmann"
        self.assertEqual(self.run_bridge()["first_blocker"], "INSTALLATION_OWNER_MISMATCH")
        self.assertFalse(any(c[0] == "POST" for c in self.api.calls))

    def test_missing_installation_admin_permission_blocks_before_mint_and_put(self):
        self.api.installation["permissions"]["administration"] = "read"
        self.assertEqual(self.run_bridge()["first_blocker"], "ADMINISTRATION_WRITE_MISSING")
        self.assertEqual(self.reconciler.calls, 0)
        self.assertFalse(any(c[0] == "POST" for c in self.api.calls))

    def test_invalid_grants_are_revoked_without_calling_reconciler(self):
        cases = [({"permissions": {"administration": "read"}}, "TOKEN_ADMINISTRATION_WRITE_MISSING"),
                 ({"permissions": {"administration": "write", "contents": "write"}}, "TOKEN_EXCESS_PERMISSIONS"),
                 ({"repositories": [{"id": 1, "full_name": bridge.CARRIER}]}, "TOKEN_REPOSITORY_MISMATCH"),
                 ({"repositories": [REPO, REPO]}, "TOKEN_REPOSITORY_SCOPE_INVALID"),
                 ({"expires_at": datetime.fromtimestamp(NOW - 1, timezone.utc).isoformat()}, "TOKEN_NOT_SHORT_LIVED"),
                 ({"expires_at": datetime.fromtimestamp(NOW + 7200, timezone.utc).isoformat()}, "TOKEN_NOT_SHORT_LIVED")]
        for values, code in cases:
            with self.subTest(code=code):
                self.setUp()
                self.api.grant.update(values)
                result = self.run_bridge()
                self.assertEqual(result["first_blocker"], code)
                self.assertTrue(result["token_revoked"])
                self.assertEqual(self.reconciler.calls, 0)

    def test_live_token_scope_is_independently_checked(self):
        self.api.overrides["/installation/repositories?per_page=100"] = {"total_count": 2, "repositories": [REPO, REPO]}
        result = self.run_bridge()
        self.assertEqual(result["first_blocker"], "TOKEN_REPOSITORY_SCOPE_INVALID")
        self.assertEqual(self.reconciler.calls, 0)

    def test_wrong_parent_force_creation_and_rerun_never_sign(self):
        for field, value in (("before", "0" * 40), ("after", "f" * 40), ("forced", True), ("created", True), ("deleted", True)):
            with self.subTest(field=field):
                self.setUp()
                self.event[field] = value
                self.assertEqual(self.run_bridge()["state"], "HOLD_UNVERIFIED")
                self.assertEqual(self.signed, 0)
        self.setUp()
        self.env["GITHUB_RUN_ATTEMPT"] = "2"
        self.assertEqual(self.run_bridge()["first_blocker"], "RERUN_FORBIDDEN")

    def test_pre_effect_carrier_drift_revokes_without_put(self):
        self.api.drift_after = 2
        result = self.run_bridge()
        self.assertEqual(result["first_blocker"], "CARRIER_PR_DRIFT")
        self.assertEqual(result["mutation"], "NONE")
        self.assertTrue(result["token_revoked"])
        self.assertEqual(self.reconciler.calls, 0)

    def test_main_drift_blocks_before_signing(self):
        self.api.overrides["/repos/" + bridge.AUTHORITY + "/git/ref/heads/main"] = {"object": {"sha": "f" * 40}}
        self.assertEqual(self.run_bridge()["first_blocker"], "AUTHORITY_MAIN_DRIFT")
        self.assertEqual(self.signed, 0)

    def test_reconciler_exception_after_possible_put_cannot_claim_no_mutation(self):
        self.reconciler.fail_after_put = True
        result = self.run_bridge()
        self.assertEqual(result["mutation"], "UNKNOWN")
        self.assertEqual(result["state"], "HOLD_UNVERIFIED")
        self.assertTrue(result["token_revoked"])

    def test_transport_success_without_independent_match_is_not_effect(self):
        self.api.overrides["/repos/" + bridge.AUTHORITY + "/rulesets/19344903"] = {"current": False}
        result = self.run_bridge()
        self.assertEqual(result["first_blocker"], "INDEPENDENT_RULESET_READBACK_NOT_CURRENT")
        self.assertFalse(result["effect_observed"])
        self.assertEqual(result["mutation"], "PUT")

    def test_post_effect_head_drift_cannot_validate_successor(self):
        self.api.drift_after = 3
        result = self.run_bridge()
        self.assertEqual(result["state"], "HOLD_UNVERIFIED")
        self.assertFalse(result["effect_observed"])
        self.assertEqual(result["mutation"], "PUT")

    def test_already_current_is_read_twice_without_mint_or_put(self):
        self.reconciler.current = True
        result = self.run_bridge()
        self.assertEqual(result["state"], "RULESET_CURRENT")
        self.assertFalse(result["effect_observed"])
        self.assertEqual(result["mutation"], "NONE")
        self.assertEqual(self.signed, 0)

    def test_revocation_failure_is_explicit_and_not_hidden(self):
        self.api.revoke_fails = True
        result = self.run_bridge()
        self.assertEqual(result["state"], "HOLD_UNVERIFIED")
        self.assertEqual(result["first_blocker"], "TOKEN_REVOCATION_UNCONFIRMED")

    def test_key_signing_error_never_exposes_openssl_stderr(self):
        completed = subprocess.CompletedProcess([], 1, b"", b"fixture-private-key-NEVER-LOG")
        with patch.object(bridge.subprocess, "run", return_value=completed):
            with self.assertRaisesRegex(bridge.Hold, "^APP_KEY_SIGNING_FAILED$"):
                bridge.sign_jwt("7", "fixture-private-key-NEVER-LOG", NOW)

    def test_no_adapter_put_review_merge_or_source_write(self):
        for method, path in (("PUT", "/repos/Goldkelch/qik-vrt/rulesets/19344903"),
                             ("POST", "/repos/Goldkelch/qik-vrt/pulls/1071/reviews"),
                             ("PATCH", "/repos/Goldkelch/qik-vrt/git/refs/heads/main")):
            with self.subTest(path=path):
                with self.assertRaisesRegex(bridge.Hold, "ADAPTER_OPERATION_FORBIDDEN"):
                    bridge.request(method, path, "no-token")


    def test_real_openssl_jwt_roundtrip_without_private_key_file(self):
        generated = subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048"], capture_output=True, timeout=15, check=True)
        key = generated.stdout.decode()
        token = bridge.sign_jwt("Iv23fixture", key, NOW)
        header, claims, signature = token.split(".")
        decode = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
        self.assertEqual(json.loads(decode(header))["alg"], "RS256")
        self.assertEqual(json.loads(decode(claims)), {"iat": NOW - 60, "exp": NOW + 540, "iss": "Iv23fixture"})
        public = subprocess.run(["openssl", "pkey", "-pubout"], input=generated.stdout, capture_output=True, timeout=15, check=True).stdout
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            (p / "public.pem").write_bytes(public)
            (p / "claims").write_text(header + "." + claims)
            (p / "signature").write_bytes(decode(signature))
            verified = subprocess.run(["openssl", "dgst", "-sha256", "-verify", str(p / "public.pem"), "-signature", str(p / "signature"), str(p / "claims")], capture_output=True, timeout=15)
            self.assertEqual(verified.returncode, 0)

    def test_actual_workflow_uses_adapter_not_static_admin_secret(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / ".github/workflows/qikvrt_mesh_authority_edge.yml").read_text()
        administrative = source.split("  reconcile-authorized-ruleset:", 1)[1]
        self.assertNotIn("secrets.QIKVRT_GITHUB_ADMIN_TOKEN", administrative)
        self.assertIn("carrier/tools/qikvrt_ruleset_admin_bridge.py", administrative)
        self.assertIn("make ruleset-admin-bridge-test", administrative)
        self.assertIn("secrets.QIKVRT_RULESET_APP_PRIVATE_KEY", administrative)
        self.assertLess(administrative.index("make ruleset-admin-bridge-test"), administrative.index("secrets.QIKVRT_RULESET_APP_PRIVATE_KEY"))
        self.assertNotIn("continue-on-error", administrative)
        self.assertNotIn("schedule:", source)

    def test_product_pr_drift_is_not_a_ruleset_administration_dependency(self):
        self.api.overrides["/repos/" + bridge.AUTHORITY + "/pulls/1104"] = {
            "state": "open", "head": {"sha": "55e6ff0cc2e527f9ef615deed6d30a21c3f9aee1"},
            "base": {"sha": bridge.MAIN, "ref": "main"}}
        result = self.run_bridge()
        self.assertEqual(result["state"], "RULESET_CURRENT")
        self.assertFalse(any(c[1].endswith("/pulls/1104") for c in self.api.calls))
        self.assertEqual(result["scope"], "APPLY_EXISTING_MAIN_RULESET_POLICY_ONLY")
        self.assertNotIn("product_head", result)

    def test_missing_configuration_keeps_exact_bindings_and_actionable_route(self):
        self.env["QIKVRT_RULESET_APP_PRIVATE_KEY"] = ""
        result = self.run_bridge()
        self.assertEqual(result["state"], "HOLD_UNVERIFIED")
        self.assertEqual(result["carrier_parent"], bridge.PARENT)
        self.assertEqual(result["carrier_tree"], TREE)
        self.assertEqual(result["authority_main_tree"], bridge.MAIN_TREE)
        self.assertEqual(result["pre_ruleset_state"], "DRIFT")
        self.assertEqual(result["next_action"], "BIND_EXISTING_RULESET_APP_CONFIGURATION_IN_CARRIER_ACTIONS")
        self.assertEqual(self.reconciler.calls, 0)

    def test_permanent_regressions_are_admitted_to_normal_make_test(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "Makefile").read_text()
        self.assertIn("test: ruleset-admin-bridge-test", source)
        self.assertIn("test_qikvrt_ruleset_admin_bridge.py", source)

if __name__ == "__main__":
    unittest.main()
