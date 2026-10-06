# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Microsoft Graph ingress adapter of the existing repository REST handler.

Basic notifications are wake-ups, never document delivery or task completion.
Only authenticated, subscription-bound metadata enters the existing private
ingest/replay/audit store. No mail, token, or clientState enters public Git.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import parse_qs, urlsplit

from qikvrt_api_handler import (
    HandlerConfig, run_handler, secure_read_bytes, _strict_json_loads, _assert_safe_target,
)

MAIL_PATH = "/webhooks/microsoft-graph/mail"
LIFECYCLE_PATH = "/webhooks/microsoft-graph/lifecycle"
PATHS = {MAIL_PATH, LIFECYCLE_PATH}
SCOPE = "OPAQUE_GRAPH_MAIL_EVENT_STORAGE_ONLY"
GUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")


class BindingError(ValueError):
    """Private deployment/subscription binding is missing or invalid."""


class NotificationError(ValueError):
    """Untrusted or unbound provider notification."""


def wire(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def read_private(path: Path, limit=262144):
    path = Path(path)
    if not path.is_absolute():
        raise BindingError("absolute private file required")
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
            or info.st_uid != os.geteuid()):
        raise BindingError("owner-only regular private file required")
    return secure_read_bytes(path, max_bytes=limit)


def load_binding(path, *, repository, principal):
    value = _strict_json_loads(read_private(Path(path)))
    required = {"schema", "repository", "responsibility_owner", "state_root",
                "accepted_effect_scope", "notification_url", "lifecycle_url",
                "subscriptions"}
    if not isinstance(value, dict) or set(value) != required:
        raise BindingError("exact webhook binding fields required")
    if (value["schema"] != "qikvrt_graph_mail_webhook_binding_v1"
            or value["repository"] != repository or not principal
            or value["responsibility_owner"] != principal
            or value["accepted_effect_scope"] != SCOPE):
        raise BindingError("owner/repository/effect scope mismatch")
    for key, endpoint in (("notification_url", MAIL_PATH), ("lifecycle_url", LIFECYCLE_PATH)):
        u = urlsplit(value[key])
        if (u.scheme != "https" or not u.hostname or u.username or u.password
                or u.path != endpoint or u.query or u.fragment):
            raise BindingError("exact HTTPS callback required")
    if urlsplit(value["notification_url"]).netloc != urlsplit(value["lifecycle_url"]).netloc:
        raise BindingError("callbacks must share the bound origin")
    root = Path(value["state_root"])
    if not root.is_absolute() or not root.is_dir():
        raise BindingError("provisioned private state directory required")
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
        raise BindingError("owner-only state directory required")
    _assert_safe_target(root / "private-state-probe")
    # Includes no-follow checks of the complete parent chain.
    secure_read_bytes(Path(path), max_bytes=262144)
    rows = value["subscriptions"]
    if not isinstance(rows, list) or len(rows) > 32:
        raise BindingError("bounded subscription bindings required")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "id", "tenant_id", "resource_prefix", "client_state"
        }:
            raise BindingError("exact subscription fields required")
        if (not isinstance(row["id"], str) or not GUID.fullmatch(row["id"])
                or row["id"] in seen or not isinstance(row["tenant_id"], str)
                or not GUID.fullmatch(row["tenant_id"])):
            raise BindingError("distinct provider subscription/tenant IDs required")
        seen.add(row["id"])
        prefix = row["resource_prefix"]
        if (not isinstance(prefix, str) or len(prefix) > 512
                or not re.fullmatch(r"users/[A-Za-z0-9_.@=-]{1,256}/messages/", prefix)):
            raise BindingError("exact provider mailbox resource prefix required")
        secret = row["client_state"]
        if (not isinstance(secret, str) or not 32 <= len(secret) <= 128
                or not secret.isascii() or any(ord(c) <= 32 or ord(c) >= 127 for c in secret)
                or secret == os.environ.get("QIKVRT_API_TOKEN")):
            raise BindingError("distinct private clientState required")
    return value


def normalize(body, binding, *, lifecycle=False):
    if not isinstance(body, dict) or set(body) != {"value"}:
        raise NotificationError("basic notification collection required")
    rows = body["value"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise NotificationError("bounded nonempty notification batch required")
    subscriptions = {row["id"]: row for row in binding["subscriptions"]
                     if row["id"] != "00000000-0000-0000-0000-000000000000"}
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise NotificationError("notification object required")
        known = subscriptions.get(row.get("subscriptionId"))
        secret = row.get("clientState")
        if (known is None or not isinstance(secret, str)
                or not hmac.compare_digest(secret.encode(), known["client_state"].encode())
                or row.get("tenantId") != known["tenant_id"]):
            raise NotificationError("notification origin binding mismatch")
        if "encryptedContent" in row or "validationTokens" in body:
            raise NotificationError("rich notifications are outside the basic contract")
        item = {"schema": "qikvrt_graph_mail_notification_v1",
                "subscription_id": known["id"], "tenant_id": known["tenant_id"]}
        if lifecycle:
            kind = row.get("lifecycleEvent")
            if kind not in {"reauthorizationRequired", "subscriptionRemoved", "missed"}:
                raise NotificationError("supported lifecycle event required")
            item.update(kind="lifecycle." + kind)
        else:
            kind, resource, data = row.get("changeType"), row.get("resource"), row.get("resourceData")
            if kind not in {"created", "updated", "deleted"} or not isinstance(data, dict):
                raise NotificationError("message change notification required")
            prefix = known["resource_prefix"]
            if (not isinstance(resource, str) or not resource.startswith(prefix)
                    or len(resource) > 2048 or data.get("@odata.type") != "#Microsoft.Graph.Message"):
                raise NotificationError("notification mailbox scope mismatch")
            message_id = resource[len(prefix):]
            if (not message_id or len(message_id) > 1024 or "/" in message_id
                    or any(ord(c) <= 32 or ord(c) >= 127 for c in message_id)
                    or data.get("id") != message_id):
                raise NotificationError("exact message resource binding required")
            etag = data.get("@odata.etag", "")
            if not isinstance(etag, str) or len(etag) > 512:
                raise NotificationError("bounded message version required")
            item.update(kind="message." + kind, resource=resource,
                        message_id=message_id, etag=etag)
        notification_id = row.get("id", "")
        if not isinstance(notification_id, str) or len(notification_id) > 512:
            raise NotificationError("bounded notification ID required")
        item["notification_id"] = notification_id
        result.append(item)
    return result


def receive(body, binding, *, lifecycle=False):
    # Validate the entire batch before writing any record. Never persist clientState.
    records = normalize(body, binding, lifecycle=lifecycle)
    accepted = []
    for record in records:
        payload = wire(record)
        key = hashlib.sha256(payload).hexdigest()
        cfg = HandlerConfig(root=Path(binding["state_root"]), operation="ingest",
                            artifact_id="graph-" + key, request_id="graph-" + key,
                            payload_b64=base64.b64encode(payload).decode(), expected_sha256=key,
                            dry_run=False, repository=binding["repository"], run_id="graph-webhook",
                            effect_accepted=True, origin_authenticated=True,
                            responsibility_owner=binding["responsibility_owner"])
        stored = run_handler(cfg)
        if (stored.get("effect_state") != "EFFECT_ACK_DONE"
                or stored.get("effect_scope") != "opaque-byte-storage-only"
                or stored.get("sha256") != key):
            raise OSError("private notification persistence not verified")
        target = Path(binding["state_root"]) / ".qikvrt/api/inbox" / (cfg.artifact_id + ".bin")
        if secure_read_bytes(target, max_bytes=262144) != payload:
            raise OSError("independent notification byte readback mismatch")
        accepted.append(cfg.artifact_id)
    return {"status": "TRANSPORT_ACK", "queued": len(accepted), "event_keys": accepted,
            "effect_scope": SCOPE, "document_received": False, "effect_ack_done": False}


def handle(handler):
    """Return true only for the two explicit Graph callback paths."""
    parsed = urlsplit(handler.path)
    if parsed.path not in PATHS:
        return False
    try:
        path = os.environ.get("QIKVRT_GRAPH_WEBHOOK_BINDING", "")
        if not path:
            raise BindingError("private Graph webhook binding missing")
        binding = load_binding(path, repository=os.environ.get("QIKVRT_ALLOWED_REPOSITORY", ""),
                               principal=os.environ.get("QIKVRT_API_PRINCIPAL", ""))
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
        if query:
            values = query.get("validationToken")
            if set(query) != {"validationToken"} or not values or len(values) != 1:
                raise NotificationError("single opaque validation token required")
            token = values[0]
            if not 1 <= len(token.encode()) <= 4096 or any(ord(c) < 32 for c in token):
                raise NotificationError("bounded validation token required")
            data = token.encode("utf-8")
            handler.send_response(200)
            handler.send_header("Content-Type", "text/plain; charset=utf-8")
            handler.send_header("Content-Length", str(len(data)))
            handler.send_header("Cache-Control", "no-store")
            handler.send_header("X-Content-Type-Options", "nosniff")
            handler.send_header("Connection", "close")
            handler.end_headers()
            handler.wfile.write(data)
            return True
        receipt = receive(handler._read_json(), binding,
                          lifecycle=parsed.path == LIFECYCLE_PATH)
        # The existing host may bind its native worker's Event here. Replays also
        # wake it: basic notifications can lack an event ID/etag, so workers must
        # independently fetch the current message and deduplicate document hashes.
        wake = getattr(handler.server, "graph_mail_wakeup", None)
        if wake is not None:
            wake.set()
        handler._send_json(202, receipt)
    except BindingError:
        handler._send_json(503, {"status": "BLOCK", "reason": "Graph webhook binding unavailable"})
    except NotificationError:
        handler._send_json(401, {"status": "BLOCK", "reason": "Graph notification rejected"})
    except (ValueError, TypeError, KeyError):
        handler._send_json(400, {"status": "BLOCK", "reason": "invalid Graph notification"})
    except (OSError, RuntimeError):
        handler._send_json(503, {"status": "BLOCK", "reason": "Graph notification not durably queued"})
    return True
