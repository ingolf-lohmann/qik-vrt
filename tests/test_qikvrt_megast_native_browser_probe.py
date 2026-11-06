#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Synthetic tests: never impersonate live Atari, IONOS, EAP or OAuth effects."""
import json
import unittest

from tools.qikvrt_megast_native_browser_probe import (
    PATH_BROWSER, PATH_CAPABILITY, PATH_HEALTH, PATH_SUBJECT,
    admissible_origin, evaluate,
)

HEAD = "a" * 40
TREE = "b" * 40
REPO = "ingolf-lohmann/qik-vrt"
PR = 693
ORIGIN = "https://raumzeitterminal.de"


def fixture():
    return {
        PATH_HEALTH: (200, "application/json", json.dumps({
            "schema": "qikvrt_cloud_transputer_mesh_health_v1",
            "state": "READY", "commit": HEAD, "tree": TREE,
            "roles": {"terminal": "READY", "gateway": "READY",
                      "m68k": "READY", "live_sse": "READY"},
            "effect_ack": "NOT_IMPLIED",
        }).encode()),
        PATH_SUBJECT: (200, "application/json", json.dumps({
            "subject": {"repository": REPO, "pr": PR, "head": HEAD, "tree": TREE},
            "dod": False, "state": "HOLD_UNVERIFIED",
        }).encode()),
        PATH_BROWSER: (403, "text/html", b"Access denied"),
        PATH_CAPABILITY: (200, "application/json", b"{}"),
    }


def query(data, origin=ORIGIN, **kw):
    return evaluate(lambda host, path: data[path], origin, HEAD, TREE, REPO, PR, **kw)


class NativeCutoverProbeTests(unittest.TestCase):
    def test_gateway_source_never_forwards_anonymous_novnc(self):
        # Static negative control runs even without nginx on portable CI.
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1]
                  / "deploy/universal-terminal/nginx.conf").read_text(encoding="utf-8")
        marker = "location ^~ /qik-vrt/mesh/v1/terminal/ {"
        self.assertEqual(source.count(marker), 1)
        block = source.split(marker, 1)[1].split("}", 1)[0]
        self.assertIn("return 403;", block)
        self.assertNotIn("proxy_pass", block)

    def test_valid_shape_is_still_not_productive_cutover(self):
        r = query(fixture())
        self.assertEqual(r["classification"], "PUBLIC_TRANSPORT_OBSERVED_ONLY")
        self.assertIs(r["browser_cutover"], False)
        self.assertIs(r["effect_ack_done"], False)

    def test_not_proven_vm_origin_is_blocked(self):
        self.assertFalse(admissible_origin("https://unrelated.example"))
        self.assertEqual(query(fixture(), "https://unrelated.example")["reason"],
                         "EXACT_ORIGIN_NOT_ALLOWED")

    def test_origin_credentials_rejected(self):
        self.assertFalse(admissible_origin("https://user:pass@raumzeitterminal.de"))

    def test_origin_query_rejected(self):
        self.assertFalse(admissible_origin("https://raumzeitterminal.de/?token=hidden"))

    def test_http_remote_rejected(self):
        self.assertFalse(admissible_origin("http://raumzeitterminal.de"))

    def test_loopback_explicit_only(self):
        self.assertFalse(admissible_origin("http://127.0.0.1:8080"))
        self.assertTrue(admissible_origin("http://127.0.0.1:8080",
                                          allow_loopback=True))

    def test_wrong_head_is_blocked(self):
        d = fixture()
        h = json.loads(d[PATH_HEALTH][2])
        h["commit"] = "c" * 40
        d[PATH_HEALTH] = (200, "application/json", json.dumps(h).encode())
        self.assertEqual(query(d)["reason"], "MESH_EXACT_HEAD_TREE_MISMATCH")

    def test_missing_transputer_role_is_blocked(self):
        d = fixture()
        h = json.loads(d[PATH_HEALTH][2])
        h["roles"]["m68k"] = "UNKNOWN"
        d[PATH_HEALTH] = (200, "application/json", json.dumps(h).encode())
        self.assertEqual(query(d)["reason"], "REQUIRED_MESH_ROLE_NOT_READY")

    def test_terminal_pr_mismatch_blocked(self):
        d = fixture()
        d[PATH_SUBJECT] = (200, "application/json",
                           json.dumps({"subject": {"repository": REPO, "pr": 2,
                               "head": HEAD, "tree": TREE}, "dod": False}).encode())
        self.assertEqual(query(d)["reason"], "TERMINAL_EXACT_SUBJECT_MISMATCH")

    def test_anonymous_browser_access_blocks_cutover(self):
        d = fixture()
        d[PATH_BROWSER] = (200, "text/html", b"<html>noVNC</html>")
        self.assertEqual(query(d)["reason"], "ANONYMOUS_BROWSER_EXPOSURE")

    def test_browser_redirect_blocks_cutover(self):
        d = fixture()
        d[PATH_BROWSER] = (302, "text/html", b"redirect")
        self.assertEqual(query(d)["reason"], "BROWSER_REDIRECT_FORBIDDEN")

    def test_http_525_remains_transport_error(self):
        d = fixture()
        d[PATH_HEALTH] = (525, "text/html", b"TLS handshake failed")
        self.assertEqual(query(d)["reason"], "MESH_HEALTH_NOT_AVAILABLE")

    def test_without_eap_endpoint_blocks(self):
        d = fixture()
        d[PATH_CAPABILITY] = (404, "text/plain", b"not found")
        self.assertEqual(query(d)["reason"], "EAP_CAPABILITY_NOT_AVAILABLE")

    def test_no_positive_or_retry_from_network_exception(self):
        def interrupted(host, path):
            raise TimeoutError("timeout")
        r = evaluate(interrupted, ORIGIN, HEAD, TREE, REPO, PR)
        self.assertEqual(r["classification"], "BLOCKED")
        self.assertFalse(r["browser_cutover"])
        self.assertFalse(r["effect_ack_done"])

    def test_unpinned_authority_rejected(self):
        r = evaluate(lambda *_: self.fail("must not connect"), ORIGIN,
                     "bad", TREE, REPO, PR)
        self.assertEqual(r["reason"], "EXACT_AUTHORITY_SUBJECT_INVALID")


if __name__ == "__main__":
    unittest.main()
