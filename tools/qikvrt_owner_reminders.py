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
