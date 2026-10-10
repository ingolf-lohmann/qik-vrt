#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Register/renew one private Graph mail subscription without a client scheduler.

The existing REST shim must already answer the HTTPS validation challenge.
OAuth remains in the host's private credential binding. No token is copied from
a connector and no application or broader permission is created by this tool.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hmac
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qikvrt_graph_webhook import load_binding, read_private, wire, BindingError
from qikvrt_api_handler import atomic_write_bytes
from qikvrt_api_handler import _strict_json_loads
try:
    from tools.qikvrt_seed_common import _NoRedirect
except ModuleNotFoundError:
    from qikvrt_seed_common import _NoRedirect

PENDING = "00000000-0000-0000-0000-000000000000"


class SubscriptionError(RuntimeError):
    pass


class Graph:
    source = "MICROSOFT_GRAPH_HTTPS"

    def __init__(self, token_file):
        self.token = read_private(Path(token_file), limit=16384).decode("ascii").strip()
        if not self.token or any(ord(c) <= 32 or ord(c) >= 127 for c in self.token):
            raise BindingError("private OAuth bearer required")
        self.opener = urllib.request.build_opener(_NoRedirect())

    def request(self, method, suffix, payload=None):
        # No untrusted notification resource becomes a network target.
        allowed = suffix in {"me?$select=id", "subscriptions"} or (
            suffix.startswith("subscriptions/") and len(suffix.split("/")) == 2
            and re.fullmatch(r"[0-9a-fA-F-]{36}", suffix.split("/")[1]))
        if not allowed:
            raise SubscriptionError("fixed Graph control-plane endpoint required")
        return self._request_url(method, "https://graph.microsoft.com/v1.0/" + suffix, payload)

    def mail_get(self, url):
        """Reuse the private transport for read-only, fixed-origin mail reads.

        The consumer additionally binds pagination to the exact folder path.
        Notification URLs and message resources never become request targets.
        """
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.netloc != "graph.microsoft.com"
                or parsed.fragment or any(ord(c) <= 32 or ord(c) >= 127 for c in url)
                or not re.fullmatch(
                    r"/v1\.0/me/(?:mailFolders/[A-Za-z0-9_%=+\-]+(?:/messages/delta)?"
                    r"|messages/[A-Za-z0-9_%=+\-]+)", parsed.path)):
            raise SubscriptionError("fixed Graph mail read endpoint required")
        return self._request_url("GET", url, mail_text=True)

    def _request_url(self, method, url, payload=None, *, mail_text=False):
        request = urllib.request.Request(
            url, method=method,
            data=None if payload is None else wire(payload),
            headers={"Authorization": "Bearer " + self.token,
                     "Content-Type": "application/json", "Accept": "application/json",
                     "Prefer": 'IdType="ImmutableId"' + (', outlook.body-content-type="text"' if mail_text else '')})
        with self.opener.open(request, timeout=20) as response:
            raw = response.read(1048577)
        if len(raw) > 1048576:
            raise SubscriptionError("Graph response exceeds limit")
        self.last_readback = {"url": url, "bytes": len(raw),
                              "sha256": hashlib.sha256(raw).hexdigest(),
                              "read_at_utc": datetime.now(timezone.utc).isoformat()}
        return _strict_json_loads(raw)


def expiry(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise SubscriptionError("explicit expiry offset required")
    return parsed.astimezone(timezone.utc)


def request_body(binding, row, expires):
    return {"changeType": "created,updated,deleted", "resource": "/me/messages",
            "notificationUrl": binding["notification_url"],
            "lifecycleNotificationUrl": binding["lifecycle_url"],
            "expirationDateTime": expires, "clientState": row["client_state"],
            "includeResourceData": False}


def same_subscription(remote, expected):
    return (remote.get("includeResourceData", False) is False
        and all(remote.get(k) == expected[k] for k in (
        "resource", "notificationUrl", "lifecycleNotificationUrl"))
        and set(str(remote.get("changeType", "")).split(",")) == set(expected["changeType"].split(","))
        and isinstance(remote.get("clientState"), str)
        and hmac.compare_digest(remote["clientState"].encode(), expected["clientState"].encode()))


def observe(api, expected):
    collection = api.request("GET", "subscriptions")
    if collection.get("@odata.nextLink") or not isinstance(collection.get("value"), list):
        raise SubscriptionError("complete bounded subscription inventory required")
    matches = [s for s in collection["value"] if same_subscription(s, expected)]
    if len(matches) > 1:
        raise SubscriptionError("duplicate matching subscription; reconcile before effect")
    return matches[0] if matches else None


def execute(binding, api, *, index=0, renew=False, now=None):
    now = now or datetime.now(timezone.utc)
    row = binding["subscriptions"][index]
    expected = request_body(binding, row, (now.replace(microsecond=0) + timedelta(days=6)).isoformat())
    account = api.request("GET", "me?$select=id")
    if row["resource_prefix"] != "users/" + str(account.get("id", "")) + "/messages/":
        raise SubscriptionError("authenticated Graph mailbox differs from private binding")
    existing = observe(api, expected)
    if renew:
        if existing is None or existing.get("id") != row["id"]:
            raise SubscriptionError("exact existing subscription readback required for renewal")
        try:
            api.request("PATCH", "subscriptions/" + row["id"],
                        {"expirationDateTime": expected["expirationDateTime"]})
        except OSError:
            # An uncertain effect is resolved by readback, never another PATCH.
            pass
        candidate = existing
    elif existing is not None:
        if row["id"] not in {PENDING, existing.get("id")}:
            raise SubscriptionError("existing native subscription identity differs")
        candidate = existing
    else:
        if row["id"] != PENDING:
            raise SubscriptionError("bound subscription missing; explicit recovery required")
        try:
            candidate = api.request("POST", "subscriptions", expected)
        except OSError:
            candidate = observe(api, expected)
            if candidate is None:
                raise SubscriptionError("ambiguous create has no matching readback; no blind retry") from None
    from qikvrt_graph_webhook import GUID
    native_id = candidate.get("id") if isinstance(candidate, dict) else None
    if not isinstance(native_id, str) or not GUID.fullmatch(native_id) or native_id == PENDING:
        raise SubscriptionError("native subscription ID required")
    observed = api.request("GET", "subscriptions/" + native_id)
    if not same_subscription(observed, expected) or observed.get("id") != native_id:
        raise SubscriptionError("subscription effect readback mismatch")
    end = expiry(observed["expirationDateTime"])
    if end <= now or (renew and end < expiry(expected["expirationDateTime"])):
        raise SubscriptionError("subscription lifetime not confirmed")
    row["id"] = native_id
    return {"schema": "qikvrt_graph_subscription_receipt_v1",
            "subscription_id": native_id, "expires_utc": end.isoformat(),
            "state": "SUBSCRIPTION_READ_BACK", "mail_delivery_observed": False,
            "client_scheduler_created": False, "effect_ack_done": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--renew", action="store_true")
    args = parser.parse_args()
    binding = load_binding(args.binding, repository=args.repository, principal=args.principal)
    if not 0 <= args.index < len(binding["subscriptions"]):
        raise BindingError("one existing private subscription binding required")
    if not args.apply:
        print(json.dumps({"state": "PLAN_ONLY", "resource": "/me/messages",
                          "notification_url": binding["notification_url"],
                          "lifecycle_url": binding["lifecycle_url"],
                          "permission": "delegated Mail.Read", "secrets_disclosed": False,
                          "client_scheduler_created": False, "effect_ack_done": False}))
        return 0
    if not args.token_file:
        raise BindingError("private delegated OAuth token file required")
    before = read_private(args.binding)
    receipt = execute(binding, Graph(args.token_file), index=args.index, renew=args.renew)
    if read_private(args.binding) != before:
        raise SubscriptionError("private binding changed concurrently; retain native receipt and reconcile")
    atomic_write_bytes(args.binding, wire(binding) + b"\n")
    read_back = load_binding(args.binding, repository=args.repository, principal=args.principal)
    if read_back != binding:
        raise SubscriptionError("private binding readback mismatch")
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BindingError, SubscriptionError, OSError, ValueError, KeyError, TypeError):
        # Provider errors may contain URLs or credential echoes; never print them.
        print("BLOCK Graph subscription binding or effect not verified", file=sys.stderr)
        raise SystemExit(2)
