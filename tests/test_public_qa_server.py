# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Bounded public Q&A API contract tests; no external provider calls."""
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from runtime.public_qa import server


class PublicQAContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for path, _, _ in server.SOURCE_FILES:
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                "QIK-VRT repository evidence and authority. EFFECT_ACK requires observed effect.\n",
                encoding="utf-8")
        (self.root / "docs/fragen").mkdir(parents=True, exist_ok=True)
        (self.root / "docs/fragen/index.html").write_text("TEST_PAGE", encoding="utf-8")
        for static in ("runtime/public_qa/index.html", "docs/news/index.html", "docs/publications/index.html"):
            p = self.root / static
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("STATIC_PAGE_" + static, encoding="utf-8")
        self.root_patch = patch.object(server, "ROOT", self.root)
        self.root_patch.start()
        self.rate_patch = patch.dict(server.REQUEST_TIMES, {}, clear=True)
        self.rate_patch.start()
        self.httpd = server.LimitedHTTPServer(("127.0.0.1", 0), server.QAHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.httpd.server_address[1])

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        self.rate_patch.stop()
        self.root_patch.stop()
        self.tmp.cleanup()

    def post(self, payload, origin="http://localhost:8080", content_type="application/json"):
        req = Request(
            self.url + "/api/ask", data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": content_type, "Origin": origin}, method="POST")
        try:
            with urlopen(req, timeout=2) as res:
                return res.status, json.load(res), res.headers
        except HTTPError as exc:
            return exc.code, json.load(exc), exc.headers

    def test_health_does_not_claim_effect_ack(self):
        with urlopen(self.url + "/api/health") as res:
            data = json.load(res)
        self.assertEqual(data["status"], "up")
        self.assertFalse(data["publication_effect"])
        self.assertFalse(data["source_revision_verified"])

    def test_publisher_and_newsroom_routes_are_read_only(self):
        for route in ("/", "/news/", "/publications/", "/fragen/"):
            with urlopen(self.url + route) as res:
                self.assertEqual(res.status, 200)
                self.assertEqual(res.headers["Cache-Control"], "no-store")

    def test_retrieval_has_hash_and_citation(self):
        with patch.dict(os.environ, {"QIKVRT_QA_PROVIDER": "none"}, clear=False):
            code, data, headers = self.post({"question": "Wie funktioniert QIK-VRT authority?"})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "EVIDENCE_ONLY")
        self.assertTrue(data["sources"])
        self.assertEqual(len(data["sources"][0]["sha256"]), 64)
        self.assertIn(data["sources"][0]["revision_kind"], ("MUTABLE_MAIN", "DECLARED_COMMIT_NOT_ATTESTED"))
        self.assertFalse(data["effect_ack_done"])
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_short_qikvrt_question_finds_sources(self):
        self.assertIn("qikvrt", server.tokens("Was ist QIK-VRT?"))
        self.assertIn("qikvrt", server.tokens("Was ist QIK VRT?"))
        code, data, _ = self.post({"question": "Was ist QIK-VRT?"})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "EVIDENCE_ONLY")
        self.assertTrue(data["sources"])
        self.assertFalse(data["independently_verified"])

    def test_unrelated_question_abstains(self):
        code, data, _ = self.post({"question": "Was ist der Durchmesser von Jupiter?"})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "NOT_ENOUGH_EVIDENCE")

    def test_origin_rejected(self):
        code, data, _ = self.post({"question": "QIK-VRT"}, origin="https://attacker.example")
        self.assertEqual(code, 403)
        self.assertEqual(data["status"], "ORIGIN_NOT_AUTHORIZED")

    def test_invalid_question_rejected(self):
        code, data, _ = self.post({"question": "x" * 2001})
        self.assertEqual(code, 422)
        self.assertEqual(data["status"], "INVALID_QUESTION")

    def test_rate_limit(self):
        for _ in range(6):
            self.assertEqual(self.post({"question": "QIK-VRT"})[0], 200)
        self.assertEqual(self.post({"question": "QIK-VRT"})[0], 429)

    def test_no_inference_without_explicit_enablement_and_pin(self):
        with patch.dict(os.environ, {
            "QIKVRT_QA_PROVIDER": "anthropic", "QIKVRT_QA_MODEL": "test",
            "QIKVRT_ANTHROPIC_API_KEY": "fake", "QIKVRT_QA_ENABLED": "false"
        }):
            self.assertFalse(server.inference_ready())

    def test_provider_failure_does_not_leak_secret(self):
        with patch.dict(os.environ, {
            "QIKVRT_QA_PROVIDER": "anthropic", "QIKVRT_QA_MODEL": "test",
            "QIKVRT_ANTHROPIC_API_KEY": "secret-not-to-disclose",
            "QIKVRT_QA_ENABLED": "true"
        }), patch.object(server, "SOURCE_COMMIT", "a" * 40), patch.object(
            server, "generate_draft", side_effect=RuntimeError("secret-not-to-disclose")
        ):
            code, data, _ = self.post({"question": "QIK-VRT authority"})
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "CONTINUE_PROVIDER_UNAVAILABLE")
        self.assertNotIn("secret-not-to-disclose", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
