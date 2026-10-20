# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Synthetic controls for automatic problem reports; no productive mail effects."""
import copy
import json
from pathlib import Path
import unittest

from tools.qikvrt_owner_reminders import classify_private_mail
import tests.test_graph_mail_consumer as mail_tests


def failure_message():
    value = mail_tests.request_message()
    value.update(subject="Unzustellbar: Delivery Status Notification (Failure)",
        hasAttachments=False, importance="normal",
        uniqueBody={"contentType": "text", "content":
            "Delivery has failed to these recipients or groups:\n"
            "support@example.test\nYour message wasn't delivered.\n"
            "Remote server returned '554 5.7.1 policy rejected'."},
        internetMessageHeaders=[{"name": "Auto-Submitted", "value": "auto-generated"}],
        **{"from": {"emailAddress": {"address": "mailer-daemon@example.test"}}})
    return value


class MailProblemRules(unittest.TestCase):
    def classify(self, message):
        return classify_private_mail(message, owner_addresses=["owner@example.test"],
                                     human_senders=["sender@example.test"])

    def test_automatic_ndr_is_important_private_attention_without_human_task(self):
        result = self.classify(failure_message())
        self.assertEqual(result["category"], "DELIVERY_FAILURE_REPORTED")
        self.assertTrue(result["important"])
        self.assertFalse(result["task_derivable"])

    def test_cc_problem_report_is_retained_without_deriving_a_direct_request(self):
        value = failure_message()
        value["toRecipients"] = [{"emailAddress": {"address": "other@example.test"}}]
        value["ccRecipients"] = [{"emailAddress": {"address": "owner@example.test"}}]
        result = self.classify(value)
        self.assertEqual(result["category"], "DELIVERY_FAILURE_REPORTED")
        self.assertFalse(result["direct_to_owner"])
        self.assertFalse(result["task_derivable"])

    def test_smtp_status_or_subject_alone_is_insufficient(self):
        for text in ("This is a reference to 5.7.1.", "Delivery has failed.", ""):
            value = failure_message()
            value["uniqueBody"]["content"] = text
            self.assertNotEqual(self.classify(value)["category"], "DELIVERY_FAILURE_REPORTED")

    def test_quoted_or_forwarded_failure_is_not_a_current_problem(self):
        for text in ("> Delivery has failed: 554 5.7.1", "From: someone@example.test\nDelivery has failed: 554 5.7.1"):
            value = failure_message()
            value["uniqueBody"]["content"] = text
            self.assertNotEqual(self.classify(value)["category"], "DELIVERY_FAILURE_REPORTED")

    def test_draft_self_sent_and_unaddressed_failures_do_not_create_attention(self):
        for field in ("draft", "self", "unaddressed"):
            value = failure_message()
            if field == "draft":
                value["isDraft"] = True
            elif field == "self":
                value["from"]["emailAddress"]["address"] = "owner@example.test"
            else:
                value["toRecipients"] = []
                value["ccRecipients"] = []
            self.assertNotEqual(self.classify(value)["category"], "DELIVERY_FAILURE_REPORTED")

    def test_html_or_truncated_preview_does_not_establish_current_report(self):
        value = failure_message()
        value["bodyPreview"] = value["uniqueBody"]["content"]
        value["uniqueBody"] = {"contentType": "html", "content": "<p>Delivery has failed: 554 5.7.1</p>"}
        self.assertNotEqual(self.classify(value)["category"], "DELIVERY_FAILURE_REPORTED")

    def test_reported_portal_requirement_is_attention_not_an_executable_instruction(self):
        value = failure_message()
        value["subject"] = "Support request"
        value["uniqueBody"]["content"] = "We require new support requests through our Support website: https://support.example.test"
        result = self.classify(value)
        self.assertEqual(result["category"], "SUPPORT_CHANNEL_REJECTED_REPORTED")
        self.assertFalse(result["task_derivable"])

    def test_automatic_ci_failure_is_attention(self):
        value = failure_message()
        value["subject"] = "[owner/repository] Run failed: CI - main"
        value["uniqueBody"]["content"] = "CI: All jobs have failed. Failed in 10 seconds."
        self.assertEqual(self.classify(value)["category"], "OPERATIONAL_FAILURE_REPORTED")

    def test_informational_portal_reference_is_not_a_reported_rejection(self):
        value = failure_message()
        value["subject"] = "Support options"
        value["uniqueBody"]["content"] = "We welcome new support requests. Our support website provides more information."
        self.assertNotEqual(self.classify(value)["category"], "SUPPORT_CHANNEL_REJECTED_REPORTED")

    def test_ordinary_bulk_remains_bulk_and_original_message_is_unchanged(self):
        value = failure_message()
        value.update(subject="Monthly newsletter", uniqueBody={"contentType": "text", "content": "Read our news."})
        before = copy.deepcopy(value)
        result = self.classify(value)
        self.assertEqual(result["category"], "AUTOMATED_OR_BULK")
        self.assertFalse(result["important"])
        self.assertEqual(value, before)

    def test_mandate_is_boot_bound_and_no_timer_or_false_acceptance_is_enabled(self):
        root = Path(__file__).resolve().parents[1]
        path = "personal/ingolf-lohmann/reminders/MAIL_PROBLEM_WATCH_V1.json"
        policy = json.loads((root / path).read_text())
        self.assertIn(path, json.loads((root / "AI_CONTEXT.json").read_text())["required_read_order"])
        self.assertFalse(policy["execution"]["client_timers"])
        self.assertFalse(policy["execution"]["resume_rejected_timer"])
        self.assertFalse(policy["outbound_mail"]["sent_copy_proves_recipient_acceptance"])
        self.assertFalse(policy["activation_observed"])


class NativeProblemTests(unittest.TestCase):
    setUp = mail_tests.MailTaskTests.setUp
    private = mail_tests.ConsumerTests.private
    native_server = mail_tests.ConsumerTests.native_server
    event = mail_tests.ConsumerTests.event
    observe = mail_tests.ConsumerTests.observe
    current_tasks = mail_tests.MailTaskTests.current_tasks

    def test_native_startup_stores_attention_and_proves_no_send_or_human_task(self):
        self.api.messages = {"message-1": failure_message()}
        server = self.native_server()
        packet = self.current_tasks()
        self.assertEqual(packet["day_plan"]["tasks"], [])
        self.assertEqual(len(packet["day_plan"]["attention"]), 1)
        self.assertEqual(packet["day_plan"]["attention"][0]["category"], "DELIVERY_FAILURE_REPORTED")
        self.assertFalse(packet["day_plan"]["notification_sent"])
        self.assertNotIn("support@example.test", json.dumps(server.graph_mail_status))

    def test_replay_and_restart_preserve_one_private_problem(self):
        self.api.messages = {"message-1": failure_message()}
        server = self.native_server()
        original = self.current_tasks()["day_plan"]["attention"][0]["id"]
        server.graph_mail_wakeup.set()
        server.service_actions()
        self.assertEqual(len(self.current_tasks()["day_plan"]["attention"]), 1)
        self.assertEqual(self.current_tasks()["day_plan"]["attention"][0]["id"], original)
        server.server_close()
        self.native_server()
        self.assertEqual(self.current_tasks()["day_plan"]["attention"][0]["id"], original)

    def test_changed_predecessor_classification_holds_without_rewriting_original_state(self):
        self.api.messages = {"message-1": failure_message()}
        with mail_tests.patch("tools.qikvrt_owner_reminders.reported_mail_problem", return_value=None):
            self.native_server()
            self.assertEqual(self.current_tasks()["day_plan"]["attention"], [])
        pointer = self.state / ".qikvrt/api/out/graph-mail-tasks-current.json"
        original = pointer.read_bytes()
        with self.assertRaises(mail_tests.consumer.ConsumerError):
            self.current_tasks()
        self.assertEqual(pointer.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
