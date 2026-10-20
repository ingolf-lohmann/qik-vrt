# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import base64
from email.message import EmailMessage
from email import policy
from pathlib import Path
import stat
import tempfile
import unittest

from tools import qikvrt_interaction_archive as archive


FAKE_AGE = r'''#!/usr/bin/env python3
import pathlib
import sys
args = sys.argv[1:]
if '--encrypt' in args:
    output = pathlib.Path(args[args.index('--output') + 1])
    source = pathlib.Path(args[-1])
    output.write_bytes(b'AGE-TEST\0' + source.read_bytes()[::-1])
    raise SystemExit(0)
if '--decrypt' in args:
    source = pathlib.Path(args[-1])
    raw = source.read_bytes()
    if not raw.startswith(b'AGE-TEST\0'):
        raise SystemExit(7)
    sys.stdout.buffer.write(raw[len(b'AGE-TEST\0'):][::-1])
    raise SystemExit(0)
raise SystemExit(9)
'''


class InteractionArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.archive_root = self.root / "private-repository" / "interaction-archive"
        self.fake_age = self.root / "age"
        self.fake_age.write_text(FAKE_AGE, encoding="utf-8")
        self.fake_age.chmod(self.fake_age.stat().st_mode | stat.S_IXUSR)
        self.identity = self.root / "identity.txt"
        self.identity.write_text("test identity\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def append_args(self, content: Path, role: str, event_id: str):
        return type("Args", (), {
            "confirm": archive.CONFIRM_APPEND,
            "role": role,
            "consent_id": "consent-2026-07-25",
            "purpose": "scientific_interaction_continuity",
            "content_file": str(content),
            "max_bytes": 1024,
            "archive_root": str(self.archive_root),
            "event_id": event_id,
            "conversation_id": "conversation-opaque-001",
            "created_at": "2026-07-25T08:00:00+02:00",
            "recipient": "age1example",
            "age_binary": str(self.fake_age),
            "retention_until": "2027-07-25T00:00:00Z",
            "media_type": "text/plain; charset=utf-8",
        })()

    def test_append_verify_and_export_round_trip(self) -> None:
        user = self.root / "user.txt"
        assistant = self.root / "assistant.txt"
        user.write_text("What is the scientific consequence?", encoding="utf-8")
        assistant.write_text("The answer remains linked to its evidence.", encoding="utf-8")

        first = archive.append(self.append_args(user, "user", "event-user-0001"))
        second = archive.append(self.append_args(assistant, "assistant", "event-assistant-0002"))
        self.assertEqual(first["state"], "PERSISTED_ENCRYPTED")
        self.assertEqual(second["state"], "PERSISTED_ENCRYPTED")
        verified = archive.verify(self.archive_root)
        self.assertEqual(verified["event_count"], 2)

        exported = self.root / "export.json"
        args = type("Args", (), {
            "confirm": archive.CONFIRM_EXPORT,
            "archive_root": str(self.archive_root),
            "identity_file": str(self.identity),
            "age_binary": str(self.fake_age),
            "output": str(exported),
            "request_id": "export-request-001",
            "conversation_id": "conversation-opaque-001",
            "overwrite": False,
        })()
        result = archive.export(args)
        self.assertEqual(result["state"], "EXPORTED")
        value = json.loads(exported.read_text(encoding="utf-8"))
        self.assertEqual(value["event_count"], 2)
        self.assertEqual(value["events"][0]["payload"]["content_utf8"], user.read_text(encoding="utf-8"))
        self.assertFalse(value["events"][0]["privacy"]["plaintext_in_repository"])

    def test_append_requires_exact_consent_and_never_writes_plaintext(self) -> None:
        content = self.root / "secret.txt"
        content.write_text("private input", encoding="utf-8")
        args = self.append_args(content, "user", "event-user-0003")
        args.confirm = "YES"
        with self.assertRaises(archive.ArchiveError):
            archive.append(args)
        args.confirm = archive.CONFIRM_APPEND
        archive.append(args)
        all_repository_bytes = b"".join(path.read_bytes() for path in self.archive_root.rglob("*") if path.is_file())
        self.assertNotIn(b"private input", all_repository_bytes)

    def test_tamper_breaks_verification(self) -> None:
        content = self.root / "input.txt"
        content.write_text("tamper target", encoding="utf-8")
        archive.append(self.append_args(content, "user", "event-user-0004"))
        blob = next((self.archive_root / "blobs").glob("*.age"))
        blob.write_bytes(blob.read_bytes() + b"x")
        with self.assertRaises(archive.ArchiveError):
            archive.verify(self.archive_root)

    def test_tombstone_is_append_only(self) -> None:
        content = self.root / "input.txt"
        content.write_text("retention target", encoding="utf-8")
        archive.append(self.append_args(content, "user", "event-user-0005"))
        args = type("Args", (), {
            "confirm": archive.CONFIRM_TOMBSTONE,
            "archive_root": str(self.archive_root),
            "event_id": "event-user-0005",
            "authorization_id": "retention-request-001",
            "created_at": "2026-07-25T09:00:00+02:00",
        })()
        result = archive.tombstone(args)
        self.assertEqual(result["state"], "TOMBSTONE_RECORDED")
        self.assertEqual(archive.verify(self.archive_root)["event_count"], 2)


class MailSourceReceiptTests(unittest.TestCase):
    """Synthetic messages only; fake age tests transport, never cryptography."""
    setUp = InteractionArchiveTests.setUp
    tearDown = InteractionArchiveTests.tearDown
    append_args = InteractionArchiveTests.append_args
    def original(self, *, nested=False):
        message = EmailMessage()
        message["Message-ID"] = "<original-001@example.test>"
        message["Date"] = "Sat, 17 Oct 2026 10:53:54 +0000"
        message["From"] = "Author <author@example.test>"
        message["To"] = "Reviewer <reviewer@example.test>"
        message["Cc"] = "Owner <owner@example.test>"
        message["Subject"] = "Scientific correspondence"
        message.set_content("Please assess this manuscript.")
        message.add_attachment(b"exact PDF source bytes", maintype="application", subtype="pdf", filename="Manuscript.pdf")
        if nested:
            outer = EmailMessage()
            for key in ("Date", "From", "To", "Cc"):
                outer[key] = str(message[key])
            outer["Message-ID"] = "<forward-001@example.test>"
            outer["In-Reply-To"] = str(message["Message-ID"])
            outer.set_content("Original attached.")
            outer.add_attachment(message)
            message = outer
        return message.as_bytes(policy=policy.SMTP)

    def receipt(self, raw=None):
        return archive.build_mail_receipt(raw or self.original(), account="author@example.test",
            provider_message_id="provider-001", observed_at="2026-10-20T14:00:00Z",
            evidence=[("provider.json", b'{"labels":["SENT"],"status":202}')])

    def test_exact_original_and_cc_are_reconstructible(self):
        raw = self.original()
        value = self.receipt(raw)
        self.assertEqual(base64.b64decode(value["original"]["base64"]), raw)
        self.assertEqual(value["identity"]["cc"][0]["address"], "owner@example.test")
        self.assertEqual(value["identity"]["attachments"][0]["decoded_sha256"], archive.sha256(b"exact PDF source bytes"))
        self.assertEqual(archive.verify_mail_receipt(value)["state"], "VERIFIED_MAIL_SOURCE_FIXITY")

    def test_sent_label_202_cc_and_headers_do_not_promote_delivery(self):
        value = self.receipt()
        self.assertEqual(set(value["evidence_states"].values()), {"NOT_ASSESSED"})
        self.assertEqual(value["identity"]["envelope_recipients"], "UNKNOWN")
        self.assertFalse(value["global_effect_ack_done"])
        self.assertFalse(value["resend_performed"])

    def test_forward_preserves_outer_inner_identity_and_pdf_bytes(self):
        value = self.receipt(self.original(nested=True))
        self.assertEqual(value["identity"]["message_id"], "<forward-001@example.test>")
        self.assertEqual(value["identity"]["enclosed_message_ids"][0]["message_id"], "<original-001@example.test>")
        self.assertEqual(value["identity"]["attachments"][0]["decoded_sha256"], archive.sha256(b"exact PDF source bytes"))

    def test_changed_raw_evidence_identity_and_inflated_claim_fail(self):
        for field in ("original", "source_snapshots", "identity", "evidence_states"):
            with self.subTest(field=field):
                value = self.receipt()
                if field == "original": value[field]["base64"] = base64.b64encode(self.original()+b"changed").decode()
                elif field == "source_snapshots": value[field][0]["base64"] = base64.b64encode(b"changed").decode()
                elif field == "identity": value[field]["cc"] = []
                else: value[field]["recipient_delivery"] = "DELIVERED"
                # Even rehashing the changed receipt cannot bless inconsistent derivation.
                value["receipt_sha256"] = archive.sha256(archive.canonical({k:v for k,v in value.items() if k != "receipt_sha256"}))
                with self.assertRaises(archive.ArchiveError): archive.verify_mail_receipt(value)

    def test_missing_duplicate_identity_or_timezone_fail(self):
        raw = self.original()
        for altered in [raw.replace(b"Message-ID:", b"X-Message-ID:", 1),
                        b"Message-ID: <duplicate@example.test>\r\n"+raw,
                        raw.replace(b" +0000", b" -0000", 1)]:
            with self.assertRaises((archive.ArchiveError, ValueError)):
                self.receipt(altered)

    def test_receipt_is_create_only_and_independently_read_back(self):
        source = self.root/"original.eml"; source.write_bytes(self.original())
        output = self.root/"private-mail"/"receipt.json"
        args = type("Args", (), {"source_file":str(source), "output":str(output), "account":"author@example.test",
            "provider_message_id":"provider-001", "observed_at":"2026-10-20T14:00:00Z", "evidence_file":[]})()
        first = archive.mail_receipt(args)
        self.assertEqual(archive.mail_receipt(args), first)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        before = output.read_bytes()
        args.provider_message_id = "other-provider-record"
        with self.assertRaises(archive.ArchiveError): archive.mail_receipt(args)
        self.assertEqual(output.read_bytes(), before)

    def test_plaintext_source_repository_and_symlink_output_rejected(self):
        raw = self.original()
        source = self.root/"original.eml"; source.write_bytes(raw)
        repo = self.root/"source-repo"; repo.mkdir(); (repo/".git").write_text("gitdir: anywhere")
        link = self.root/"link.json"; link.symlink_to(source)
        for target in (repo/"receipt.json", link):
            args = type("Args", (), {"source_file":str(source), "output":str(target), "account":"a@example.test",
                "provider_message_id":"provider-001", "observed_at":"2026-10-20T14:00:00Z", "evidence_file":[]})()
            with self.assertRaises(archive.ArchiveError): archive.mail_receipt(args)
        self.assertEqual(source.read_bytes(), raw)

    def test_existing_encrypted_append_validates_mail_before_encrypting(self):
        content = self.root/"receipt.json"; value = self.receipt()
        content.write_bytes(archive.canonical(value))
        args = self.append_args(content, "tool", "mail-event-0001")
        args.media_type = archive.MAIL_MEDIA_TYPE; args.max_bytes = 100000
        archive.append(args)
        self.assertNotIn(b"author@example.test", b"".join(p.read_bytes() for p in self.archive_root.rglob("*") if p.is_file()))
        value["evidence_states"]["mailbox_ingress"] = "CONFIRMED"
        content.write_bytes(archive.canonical(value)); args.event_id = "mail-event-0002"
        with self.assertRaises(archive.ArchiveError): archive.append(args)
        self.assertEqual(archive.verify(self.archive_root)["event_count"], 1)


if __name__ == "__main__":
    unittest.main()
