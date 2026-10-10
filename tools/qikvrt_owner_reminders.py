#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Owner-authorized reminders inside the existing repository executor.

The public configuration contains only neutral labels and authenticated links.
A create-only remote receipt ref admits at most one delivery attempt per exact
reminder version. An interrupted/ambiguous attempt becomes HOLD, never a blind
retry. Notification readback does not prove human receipt or task completion.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

try:
    from tools.qikvrt_seed_common import _NoRedirect, read_json, write_json
except ModuleNotFoundError:
    from qikvrt_seed_common import _NoRedirect, read_json, write_json

REPOSITORY = "ingolf-lohmann/qik-vrt"
OWNER = "ingolf-lohmann"
SHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_BYTES = 1_048_576
CONFIG = "personal/ingolf-lohmann/reminders/OWNER_REMINDERS_V1.json"
MAIL_TASK_SCOPE = "PRIVATE_MAIL_CLASSIFICATION_AND_TASK_PLAN_ONLY"
MAIL_RULES = (
    ("DE_EXPLICIT_REQUEST", re.compile(
        r"\b(?:bitte|kannst du|könntest du|können sie|könnten sie)\b[^.!?\n]{0,100}"
        r"\b(?:prüfen|prüfe|senden|sende|schicken|schicke|antworten|antworte|bestätigen|bestätige|"
        r"unterschreiben|unterschreibe|mitbringen|vereinbaren|bezahlen|überweisen)\b", re.I)),
    ("EN_EXPLICIT_REQUEST", re.compile(
        r"\b(?:please|can you|could you|would you)\b[^.!?\n]{0,100}"
        r"\b(?:review|send|reply|confirm|sign|bring|schedule|pay|transfer)\b", re.I)),
    ("FR_EXPLICIT_REQUEST", re.compile(
        r"\b(?:merci de|pouvez-vous|pourriez-vous|veuillez)\b[^.!?\n]{0,100}"
        r"\b(?:vérifier|envoyer|répondre|confirmer|signer|apporter|payer|virer)\b", re.I)),
)


def mail_address(value):
    if not isinstance(value, str) or not re.fullmatch(r"[^\s@<>]{1,64}@[^\s@<>]{1,190}", value):
        raise ReminderError("bounded private mail address required")
    return value.casefold()


def classify_private_mail(message, *, owner_addresses, human_senders):
    """Bounded rule evidence, never sender authentication or executable content.

    Only selected current uniqueBody text can derive a request. bodyPreview is
    truncated; subjects, quotes, automated senders and importance alone cannot
    invent a task. Unknown senders retain an explicit owner-review disposition.
    """
    owners = {mail_address(a) for a in owner_addresses}
    humans = {mail_address(a) for a in human_senders}
    sender = message.get("from") or {}
    address = sender.get("emailAddress", {}).get("address")
    address = mail_address(address) if address else None
    recipients = message.get("toRecipients")
    complete = (isinstance(recipients, list) and isinstance(message.get("isDraft"), bool)
                and isinstance(message.get("internetMessageHeaders"), list)
                and isinstance(message.get("uniqueBody"), dict))
    direct = bool(complete and any(
        mail_address(r["emailAddress"]["address"]) in owners for r in recipients))
    automated = bool(address and re.search(r"(?:no[-_]?reply|do[-_]?not[-_]?reply|mailer-daemon)",
                                          address.split("@", 1)[0], re.I))
    for header in message.get("internetMessageHeaders", []):
        name, value = header["name"].casefold(), header["value"].strip().casefold()
        if (name == "list-id" or name == "auto-submitted" and value != "no"
                or name == "precedence" and value in {"bulk", "list", "junk"}):
            automated = True
    unique = message.get("uniqueBody") or {}
    text = unique.get("content", "") if unique.get("contentType", "").casefold() == "text" else ""
    lines = []
    for line in text.splitlines():
        if re.match(r"\s*(?:[-_]{2,}\s*(?:original|forwarded)|from:|von:|de :)|.*wrote:$", line, re.I):
            break
        if not line.lstrip().startswith(">"):
            lines.append(line)
    text = "\n".join(lines)
    rule, excerpt = None, None
    for sentence in re.split(r"[.!?\n]", text):
        # Conservative: a negated sentence cannot become an action.
        if re.search(r"\b(?:nicht|kein|keine|don't|do not|not|pas)\b", sentence, re.I):
            continue
        for name, pattern in MAIL_RULES:
            if pattern.search(sentence):
                rule, excerpt = name, sentence.strip()[:512]
                break
        if rule:
            break
    urgency_text = message.get("subject", "") + "\n" + text
    negated = re.search(r"\b(?:nicht dringend|not urgent|pas urgent|sans urgence)\b", urgency_text, re.I)
    urgent = bool(not negated and re.search(r"\b(?:dringend|urgent|urgence|asap)\b", urgency_text, re.I))
    human_request = bool(complete and direct and rule and address in humans and address not in owners
                         and not automated and message["isDraft"] is False)
    important = message.get("importance") == "high" or human_request
    category = ("AUTOMATED_OR_BULK" if automated else "INSUFFICIENT_PROJECTION" if not complete
                else "DIRECT_HUMAN_REQUEST" if human_request
                else "DIRECT_REQUEST_SENDER_UNVERIFIED" if direct and rule and address not in owners
                and message["isDraft"] is False else "URGENT" if urgent
                else "IMPORTANT" if important else "INFORMATION")
    return {"category": category, "urgent": urgent, "important": important,
            "direct_to_owner": direct, "request_rule": rule, "request_excerpt": excerpt,
            "task_derivable": human_request,
            "human_sender_basis": "PRIVATE_CONTACT_CLASSIFICATION_NOT_IDENTITY_ATTESTATION",
            "coverage": "SELECTED_CURRENT_UNIQUE_BODY_RULES_ONLY"}


def project_private_mail_plan(mail, tasks, lifecycle, *, owner, timezone, observed_at):
    """Existing reminder/day-plan adapter's event-native, entirely private lane.

    No public registry mutation, library-ID fabrication, scheduler, notification
    send or provider effect. Only source-derived tasks enter the task lane;
    important/urgent messages without an action remain attention items.
    """
    if (not isinstance(owner, str) or not 1 <= len(owner) <= 256
            or not isinstance(mail, dict) or not isinstance(tasks, dict)
            or max(len(mail), len(tasks)) > 10000):
        raise ReminderError("bounded private mail/task input required")
    local_date = instant(observed_at).astimezone(ZoneInfo(timezone)).date().isoformat()
    for key, task in tasks.items():
        if (task.get("id") != key or task.get("kind") != "REVIEW_AND_HANDLE_EXPLICIT_MAIL_REQUEST"
                or task.get("source_message_id") not in mail
                or not task.get("request_excerpt") or task.get("request_rule") not in dict(MAIL_RULES)
                or task.get("due") is not None
                or task.get("state") not in {"OPEN", "COMPLETED", "CANCELLED",
                    "SOURCE_UNAVAILABLE_REVIEW_REQUIRED", "SOURCE_CHANGED_REVIEW_REQUIRED"}):
            raise ReminderError("only evidence-derived private tasks may enter the plan")
    def priority(item):
        return (not item["urgent"], not item["important"], item["id"])
    attention = [{"id": key, "category": item["classification"]["category"],
                  "urgent": item["classification"]["urgent"],
                  "important": item["classification"]["important"],
                  "source_observation_key": item["source_observation_key"],
                  "notification": "PRIVATE_OWNER_REVIEW_PENDING"}
                 for key, item in mail.items() if item["folders"] and (
                     item["classification"]["urgent"] or item["classification"]["important"]
                     or item["classification"]["category"] == "DIRECT_REQUEST_SENDER_UNVERIFIED")]
    active = [dict(t) for t in tasks.values() if t["state"] not in {"COMPLETED", "CANCELLED"}]
    return {"schema": "qikvrt_private_mail_day_plan_v1", "effect_scope": MAIL_TASK_SCOPE,
            "owner": owner, "timezone": timezone, "local_date": local_date,
            "tasks": sorted(active, key=priority), "attention": sorted(attention, key=priority),
            "lifecycle_signals": sorted(set(lifecycle)), "due_times_inferred": False,
            "notification_sent": False, "task_completion_proven": False, "effect_ack_done": False}


class ReminderError(RuntimeError):
    """An admission/readback boundary needs a human or fresh evidence."""


def instant(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ReminderError("timestamp must have an explicit UTC offset")
    return parsed.astimezone(dt.timezone.utc)


def validate(config: dict) -> list[dict]:
    if set(config) != {"schema", "repository", "owner", "reminders"}:
        raise ReminderError("unknown or missing configuration field")
    if (config["schema"], config["repository"], config["owner"]) != (
        "qikvrt_owner_reminders_v1", REPOSITORY, OWNER
    ):
        raise ReminderError("owner/repository/schema mismatch")
    rows = config["reminders"]
    if not isinstance(rows, list) or len(rows) > 100:
        raise ReminderError("bounded reminder list required")
    seen = set()
    for row in rows:
        required = {
            "id", "version", "state", "due", "timezone", "anchor_sha",
            "title", "private_artifacts", "acceptance"
        }
        if (not isinstance(row, dict) or not required <= set(row)
                or set(row) - required - {"expires"}):
            raise ReminderError("unknown or missing reminder field")
        if not re.fullmatch(r"[a-z0-9-]{1,80}", row["id"]) or row["id"] in seen:
            raise ReminderError("invalid or duplicate reminder ID")
        seen.add(row["id"])
        if type(row["version"]) is not int or row["version"] < 1:
            raise ReminderError("positive integer version required")
        if row["state"] not in {"OPEN", "COMPLETED", "CANCELLED"}:
            raise ReminderError("invalid reminder state")
        if not SHA.fullmatch(row["anchor_sha"]):
            raise ReminderError("invalid stable comment anchor")
        due = dt.datetime.fromisoformat(row["due"])
        if due.tzinfo is None or due.utcoffset() != due.astimezone(ZoneInfo(row["timezone"])).utcoffset():
            raise ReminderError("due offset disagrees with named timezone")
        if "expires" in row:
            expires = dt.datetime.fromisoformat(row["expires"])
            if (expires.tzinfo is None
                    or expires.utcoffset() != expires.astimezone(ZoneInfo(row["timezone"])).utcoffset()
                    or instant(row["expires"]) <= instant(row["due"])):
                raise ReminderError("expiry must follow due and match named timezone")
        if row["title"] not in {"Vorbereitete Zahlung prüfen und persönlich freigeben", "Persönlichen Tagesplan prüfen"}:
            raise ReminderError("public reminder title must use a neutral approved label")
        if row["acceptance"] != "OWNER_CONFIRMS_TASK_COMPLETION_WITH_EVIDENCE":
            raise ReminderError("task completion requires owner evidence")
        artifacts = row["private_artifacts"]
        if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= 5:
            raise ReminderError("private artifact references required")
        for artifact in artifacts:
            if set(artifact) != {"label", "library_file_id", "version", "sha256"}:
                raise ReminderError("unknown private artifact field")
            if artifact["label"] not in {"Zahlungspaket", "Tagesplan"}:
                raise ReminderError("private artifact label must remain neutral")
            if not re.fullmatch(r"libfile_[0-9a-f]{32}", artifact["library_file_id"]):
                raise ReminderError("invalid private file identity")
            if type(artifact["version"]) is not int or artifact["version"] < 0:
                raise ReminderError("invalid private artifact version")
            if not re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]):
                raise ReminderError("invalid private artifact digest")
    return rows


def identity(row: dict) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def body(row: dict, key: str) -> str:
    links = "\n".join(
        f"- [{a['label']}](https://chatgpt.com/api/library/files/{a['library_file_id']}/download)"
        for a in row["private_artifacts"]
    )
    return (f"<!-- qikvrt-owner-reminder:{key} -->\n"
            f"@{OWNER} **{row['title']}**\n\n"
            f"Fällig: {row['due']} ({row['timezone']}).\n\n{links}\n\n"
            "Bitte zuerst den tatsächlichen Stand prüfen. Eine bereits erledigte Aufgabe "
            "nicht erneut ausführen. Die Erinnerung führt keine Zahlung aus.\n")


class GitHub:
    def __init__(self, token: str):
        if not token:
            raise ReminderError("repository execution token missing")
        self.token = token
        self.opener = urllib.request.build_opener(_NoRedirect())

    def request(self, method: str, suffix: str, payload=None):
        request = urllib.request.Request(
            f"https://api.github.com/repos/{REPOSITORY}/{suffix}",
            data=None if payload is None else json.dumps(payload).encode(), method=method,
            headers={"Authorization": f"Bearer {self.token}",
                     "Accept": "application/vnd.github+json", "Content-Type": "application/json",
                     "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "qikvrt-owner-reminders"},
        )
        with self.opener.open(request, timeout=20) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ReminderError("GitHub response exceeds bounded read")
        return json.loads(raw)

    def observe_delivery(self, row, expected):
        matches = []
        for page in range(1, 11):
            comments = self.request("GET", f"commits/{row['anchor_sha']}/comments?per_page=100&page={page}")
            if not isinstance(comments, list):
                raise ReminderError("invalid comment collection")
            matches.extend(c for c in comments if c.get("body") == expected
                           and c.get("user", {}).get("login") == "github-actions[bot]")
            if len(comments) < 100:
                break
        else:
            raise ReminderError("comment inventory bound exceeded")
        if len(matches) > 1:
            raise ReminderError("duplicate notification detected")
        if not matches:
            return None
        item = self.request("GET", f"comments/{matches[0]['id']}")
        if (item.get("body") != expected or item.get("commit_id") != row["anchor_sha"]
                or item.get("user", {}).get("login") != "github-actions[bot]"
                or not item.get("html_url", "").startswith(f"https://github.com/{REPOSITORY}/commit/")):
            raise ReminderError("notification readback mismatch")
        return {"id": item["id"], "url": item["html_url"], "created_at": item["created_at"]}


def execute(config, now, api=None, head=None):
    rows = validate(config)
    receipts = []
    for row in rows:
        key = identity(row)
        receipt = {"id": row["id"], "version": row["version"], "content_sha256": key,
                   "task_completion": "NOT_PROVEN", "head_sha": head}
        receipts.append(receipt)
        if row["state"] != "OPEN" or now < instant(row["due"]):
            receipt["notification"] = "NOT_DUE" if row["state"] == "OPEN" else row["state"]
            continue
        if "expires" in row and now >= instant(row["expires"]):
            receipt["notification"] = "EXPIRED_NO_EFFECT"
            continue
        if api is None:
            receipt["notification"] = "DUE_NO_EFFECT_PREVIEW"
            continue
        expected = body(row, key)
        existing = api.observe_delivery(row, expected)
        if existing:
            receipt.update(notification="READ_BACK", delivery=existing)
            continue
        if api.request("GET", "git/ref/heads/main")["object"]["sha"] != head:
            raise ReminderError("main moved; reobserve successor before delivery")
        claim = f"refs/heads/receipts/owner-reminders/{key}"
        try:
            created = api.request("POST", "git/refs", {"ref": claim, "sha": head})
        except (OSError, ValueError, ReminderError):
            existing = api.observe_delivery(row, expected)
            if existing:
                receipt.update(notification="READ_BACK", delivery=existing)
                continue
            receipt["notification"] = "HOLD_CREATE_ONLY_CLAIM_UNAVAILABLE_OR_ALREADY_EXISTS"
            continue
        if created.get("ref") != claim or created.get("object", {}).get("sha") != head:
            raise ReminderError("create-only delivery claim mismatch")
        observed = api.request("GET", f"git/ref/{claim.removeprefix('refs/')}")
        if observed.get("object", {}).get("sha") != head:
            raise ReminderError("delivery claim readback mismatch")
        receipt["claim_ref"] = claim
        # Even an ambiguous POST cannot cause another attempt: the claim is durable.
        try:
            api.request("POST", f"commits/{row['anchor_sha']}/comments", {"body": expected})
        except (OSError, ValueError, ReminderError):
            pass
        delivered = api.observe_delivery(row, expected)
        if delivered:
            receipt.update(notification="READ_BACK", delivery=delivered)
        else:
            receipt["notification"] = "HOLD_DELIVERY_NOT_READ_BACK"
    return {"schema": "qikvrt_owner_reminder_receipt_v1", "observed_at": now.isoformat(),
            "repository": REPOSITORY, "receipts": receipts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deliver", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = read_json(root / CONFIG)
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    api = None
    if args.deliver:
        if (os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
                or os.environ.get("GITHUB_REF") != "refs/heads/main"
                or os.environ.get("GITHUB_SHA") != head
                or os.environ.get("GITHUB_EVENT_NAME") not in {"push", "schedule", "workflow_dispatch"}):
            raise ReminderError("delivery requires exact repository/main event checkout")
        api = GitHub(os.environ.get("GH_TOKEN", ""))
    result = execute(config, dt.datetime.now(dt.timezone.utc), api, head)
    if args.output:
        write_json(args.output, result)
        write_json(args.output.parent / "AI_PROGRESS.json", result)
        (args.output.parent / "AI_STATUS.md").write_text(
            "# Owner reminder execution\n\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if any(r["notification"].startswith("HOLD") for r in result["receipts"]) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReminderError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"BLOCK owner reminder: {type(exc).__name__}: {exc}")
        raise SystemExit(2)
