#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Static safety contract for the public QIK-VRT question entrypoint."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PublicQuestionsEntrypointTest(unittest.TestCase):
    def test_page_discloses_server_and_local_fallback(self):
        page = (ROOT / "docs/fragen/index.html").read_text(encoding="utf-8")
        self.assertIn('id="question-form"', page)
        self.assertIn('id="answer-output"', page)
        self.assertIn('maxlength="2000"', page)
        self.assertIn("festgelegten Bestand lokaler Repository-Quellen", page)
        self.assertIn("Modellanbieter", page)
        self.assertIn("phänomenalen Bewusstseins", page)
        self.assertIn("form-action 'none'", page)
        self.assertNotIn("site123", page.lower())
        self.assertNotIn("api.openai.com", page.lower())

    def test_question_handling_never_claims_unverified_answer(self):
        script = (ROOT / "docs/assets/js/qikvrt-questions.js").read_text(encoding="utf-8")
        self.assertIn("QIKVRTLocalEngine.answerLocal", script)
        self.assertIn("LOCAL_RULE_ANALYSIS", script)
        self.assertIn("keine allgemeine KI-Antwort", script)
        self.assertIn("output.textContent", script)
        self.assertNotIn("innerHTML", script)
        self.assertIn('fetch("/api/ask"', script)
        self.assertIn('credentials: "same-origin"', script)
        self.assertIn("GENERATED_UNVERIFIED", script)
        self.assertNotIn("api.openai.com", script)
        self.assertNotIn("XMLHttpRequest", script)

    def test_homepage_links_to_question_entrypoint(self):
        page = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        self.assertIn('href="fragen/"', page)


if __name__ == "__main__":
    unittest.main()
