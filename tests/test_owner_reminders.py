# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import copy
import datetime as dt
import unittest
from pathlib import Path

from tools import qikvrt_owner_reminders as module
from tools.qikvrt_seed_common import read_json

CONFIG = read_json(Path(__file__).resolve().parents[1] / module.CONFIG)
HEAD = "a" * 40


class FakeGitHub:
    def __init__(self, ambiguous=False, claimed=False, delivered=False):
        self.claimed, self.delivered = claimed, delivered
        self.ambiguous = ambiguous
        self.posts = []

    def observe_delivery(self, row, expected):
        return {"id": 42, "url": "https://github.com/ingolf-lohmann/qik-vrt/commit/test#commitcomment-42"} if self.delivered else None

    def request(self, method, suffix, payload=None):
        if method == "GET":
            return {"object": {"sha": HEAD}}
        self.posts.append(suffix)
        if suffix == "git/refs":
            if self.claimed:
                raise OSError("existing create-only claim")
            self.claimed = True
            return {"ref": payload["ref"], "object": {"sha": HEAD}}
        self.delivered = not self.ambiguous
        if self.ambiguous:
            raise OSError("uncertain transport")
        return {"id": 42}


class OwnerReminderTests(unittest.TestCase):
    def run_due(self, api=None, config=None):
        return module.execute(config or CONFIG, module.instant("2026-10-06T06:30:00Z"), api, HEAD)["receipts"][0]

    def test_no_early_notification(self):
        api = FakeGitHub()
        result = module.execute(CONFIG, module.instant("2026-10-06T06:29:59Z"), api, HEAD)
        self.assertEqual(result["receipts"][0]["notification"], "NOT_DUE")
        self.assertFalse(api.posts)

    def test_due_preview_has_no_effect(self):
        self.assertEqual(self.run_due()["notification"], "DUE_NO_EFFECT_PREVIEW")

    def test_single_claim_and_readback_then_dedup(self):
        api = FakeGitHub()
        self.assertEqual(self.run_due(api)["notification"], "READ_BACK")
        self.assertEqual(self.run_due(api)["task_completion"], "NOT_PROVEN")
        self.assertEqual(api.posts, ["git/refs", f"commits/{CONFIG['reminders'][0]['anchor_sha']}/comments"])

    def test_ambiguous_delivery_never_reposts(self):
        api = FakeGitHub(ambiguous=True)
        self.assertEqual(self.run_due(api)["notification"], "HOLD_DELIVERY_NOT_READ_BACK")
        self.assertTrue(self.run_due(api)["notification"].startswith("HOLD"))
        self.assertEqual(sum("comments" in path for path in api.posts), 1)

    def test_existing_claim_without_delivery_is_hold(self):
        api = FakeGitHub(claimed=True)
        self.assertTrue(self.run_due(api)["notification"].startswith("HOLD"))
        self.assertEqual(api.posts, ["git/refs"])

    def test_completed_or_cancelled_is_not_reopened(self):
        for state in ("COMPLETED", "CANCELLED"):
            config = copy.deepcopy(CONFIG)
            config["reminders"][0]["state"] = state
            api = FakeGitHub()
            self.assertEqual(self.run_due(api, config)["notification"], state)
            self.assertFalse(api.posts)

    def test_unknown_fields_wrong_owner_and_due_offset_rejected(self):
        for change in ({"owner": "someone"}, {"command": "ignored"}):
            config = copy.deepcopy(CONFIG)
            config.update(change)
            with self.assertRaises(module.ReminderError):
                module.validate(config)
        config = copy.deepcopy(CONFIG)
        config["reminders"][0]["due"] = "2026-10-06T08:30:00+00:00"
        with self.assertRaises(module.ReminderError):
            module.validate(config)

    def test_version_or_artifact_change_changes_idempotency_identity(self):
        row = copy.deepcopy(CONFIG["reminders"][0])
        before = module.identity(row)
        row["version"] += 1
        self.assertNotEqual(before, module.identity(row))

    def test_public_body_contains_only_neutral_links(self):
        text = module.body(CONFIG["reminders"][0], "b" * 64)
        self.assertIn("@ingolf-lohmann", text)
        self.assertIn("https://chatgpt.com/api/library/files/", text)
        for private_value in ("WHBS", "Burnout", "MEOCLINIC", "3918", "2600449", "IBAN"):
            self.assertNotIn(private_value, text)

    def test_moved_main_blocks_claim_and_delivery(self):
        api = FakeGitHub()
        original = api.request
        api.request = lambda method, suffix, payload=None: (
            {"object": {"sha": "c" * 40}} if suffix == "git/ref/heads/main"
            else original(method, suffix, payload))
        with self.assertRaises(module.ReminderError):
            self.run_due(api)
        self.assertFalse(api.posts)

    def test_remote_comment_requires_exact_body_and_bot_and_anchor(self):
        api = object.__new__(module.GitHub)
        row = CONFIG["reminders"][0]
        expected = module.body(row, module.identity(row))
        item = {"id": 7, "body": expected, "user": {"login": "github-actions[bot]"},
                "commit_id": row["anchor_sha"], "created_at": "2026-10-06T06:30:00Z",
                "html_url": f"https://github.com/{module.REPOSITORY}/commit/{row['anchor_sha']}#commitcomment-7"}
        api.request = lambda method, suffix: [item] if "commits/" in suffix else item
        self.assertEqual(api.observe_delivery(row, expected)["id"], 7)
        item["commit_id"] = HEAD
        with self.assertRaises(module.ReminderError):
            api.observe_delivery(row, expected)

    def test_comment_inventory_overflow_stops_without_ignoring_old_delivery(self):
        api = object.__new__(module.GitHub)
        api.request = lambda method, suffix: [{"body": "unrelated"}] * 100
        with self.assertRaises(module.ReminderError):
            api.observe_delivery(CONFIG["reminders"][0], "expected")


if __name__ == "__main__":
    unittest.main()
