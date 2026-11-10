"""Fail-closed regression for the owner roundtrip diagnostic."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.issue_agent.compile import compile_issue


class OwnerRoundtripDiagnosticTest(unittest.TestCase):
    def test_exact_owner_issue_is_classified_without_effect_ack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue = root / "issue.json"
            context = root / "context.md"
            answer = root / "answer.md"
            issue.write_text(json.dumps({
                "number": 718,
                "title": "Owner directive: repository-native input/output roundtrip as authoritative execution path",
                "body": "Implement a repository-native, authenticated input carrier",
            }), encoding="utf-8")
            context.write_text("bounded context", encoding="utf-8")
            compile_issue(issue, context, answer)
            result = answer.read_text(encoding="utf-8")
            self.assertIn("repository_native_io_roundtrip_diagnostic_v1", result)
            self.assertIn("BLOCKED_WITH_NEXT_ACTION", result)
            self.assertIn("EFFECTING_HANDLER_NOT_ADMITTED", result)
            self.assertNotIn("EFFECT_ACK_DONE=true", result)

    def test_untrusted_variant_is_not_admitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            issue = root / "issue.json"
            context = root / "context.md"
            answer = root / "answer.md"
            issue.write_text(json.dumps({
                "number": 719,
                "title": "Owner directive: repository-native input/output roundtrip as authoritative execution path",
                "body": "Implement a repository-native, authenticated input carrier",
            }), encoding="utf-8")
            context.write_text("bounded context", encoding="utf-8")
            compile_issue(issue, context, answer)
            result = answer.read_text(encoding="utf-8")
            self.assertIn("UNSUPPORTED_DETERMINISTIC_WORK_UNIT", result)
            self.assertNotIn("repository_native_io_roundtrip_diagnostic_v1", result)


if __name__ == "__main__":
    unittest.main()
