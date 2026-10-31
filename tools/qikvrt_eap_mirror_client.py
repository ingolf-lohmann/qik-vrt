#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: Claude (Anthropic).
# Integration and negative-control repair: OpenAI Codex.
"""Non-browser EAP client for a Mirror principal (runtime/self-host/EAP_HTTP.md).

Uses only the existing public routes of the S1 listener; it adds no listener,
route, executor or credential store. One run delivers one bounded text
observation to the Authority's original OwnerREST/ledger:

  discovery -> state -> prepare -> record + context readback -> local
  revision-03 verification -> commit -> receipt readback

The bearer credential is read only from the environment variable named by
--token-env (default QIKVRT_EAP_TOKEN). It is never printed or persisted.
Accepted text is an observation, never a command (EAP_HTTP.md). The output is
a delivery receipt; it is not merge, deployment or EFFECT_ACK_DONE.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import qikvrt_effect_ack_http_service as service  # noqa: E402
import qikvrt_effect_ack_wire as wire  # noqa: E402
import qikvrt_temdd_event_ledger as native  # noqa: E402

PERMISSIONS = ("prepare", "commit", "readback")


class Hold(RuntimeError):
    """Delivery stops; the message names the exact step and observation."""


def sf_bytes(raw: bytes) -> str:
    return ":" + base64.b64encode(raw).decode("ascii") + ":"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    handler_order = 100

    def redirect_request(self, request, response, code, message, headers, new_url):
        raise Hold("REDIRECT_FORBIDDEN " + str(code))


def verify_receipt(receipt: dict, value: dict, principal: str, ledger_id: str) -> dict:
    """Check the original native event and digests without opening a local ledger."""
    try:
        event = receipt["durable_readback"]
        if (receipt["principal"] != principal or receipt["request_id"] != value["request_id"]
                or receipt["durable_persisted"] is not True
                or receipt["independent_sqlite_readback"] is not True
                or event["schema"] != "qikvrt_temdd_event_v1" or event["kind"] != "OBSERVE"
                or event["subject"] != value["subject"]
                or not re.fullmatch(re.escape(ledger_id) + r":[1-9][0-9]{0,18}", event["id"])
                or event["payload"] != {"adapter": "QIKVRT_OWNER_REST_TERMINAL_V1",
                    "principal": principal, "request_id": value["request_id"],
                    "terminal_input": value["input"],
                    "input_hash": "sha256:" + native.digest(value["input"]), "effect_ack_done": False}
                or event["payload_digest"] != native.digest(event["payload"])
                or event["ledger_digest"] != native.digest({k: v for k, v in event.items()
                                                           if k not in ("id", "ledger_digest")})):
            raise ValueError("receipt does not bind the submitted observation")
        original = {k: event[k] for k in ("kind", "subject", "provenance", "observed_at", "message", "payload")}
        original["schema"] = native.SCHEMA
        validator = object.__new__(native.Ledger); validator.subject = value["subject"]
        validator._validate(original)
        if (event["provenance"]["source"] != "transputer"
                or not re.fullmatch(r"terminal:[0-9a-f]{48}", event["provenance"]["native_event_id"])):
            raise ValueError("native input provenance does not match")
        return event
    except (KeyError, TypeError, ValueError) as error:
        raise Hold("RECEIPT_BINDING_MISMATCH " + str(error)) from None


class Client:
    def __init__(self, base_url: str, principal: str, token: str, opener=None):
        if not base_url.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
            raise Hold("HTTPS_OR_LOOPBACK_BASE_URL_REQUIRED")
        self.base = base_url.rstrip("/")
        self.principal, self.token = principal, token
        self.opener = opener or urllib.request.build_opener()
        self.opener.add_handler(NoRedirect())
        self.trace: list[dict] = []

    def call(self, path: str, value=None, effect_ack_request: str | None = None, auth: bool = True):
        headers = {}
        if auth:
            headers.update({"Authorization": "Bearer " + self.token, "QIKVRT-Owner": self.principal})
        data = None
        if value is not None:
            data = wire.canonical(value)
            headers.update({"Content-Type": "application/json", "Effect-Ack-Request": effect_ack_request})
        request = urllib.request.Request(self.base + path, data=data, headers=headers,
                                         method="POST" if value is not None else "GET")
        try:
            response = self.opener.open(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        except OSError as error:
            raise Hold(f"TRANSPORT_UNAVAILABLE {path}: {type(error).__name__}") from None
        body = response.read()
        self.trace.append({"method": request.get_method(), "path": path, "status": response.status,
                           "effect_ack": response.headers.get("Effect-Ack"),
                           "body_sha256": hashlib.sha256(body).hexdigest()})
        try:
            parsed = json.loads(body)
        except ValueError:
            raise Hold(f"NON_JSON_RESPONSE {path} {response.status}") from None
        if not isinstance(parsed, dict):
            raise Hold("JSON_OBJECT_REQUIRED " + path)
        if response.status != 200:
            raise Hold(f"HTTP_{response.status} {path}: {parsed.get('reason') or parsed.get('error')}")
        return parsed

    def deliver(self, request_id: str, text: str) -> dict:
        discovery = self.call("/.well-known/effect-ack", auth=False)
        if discovery.get("effect_endpoint") != service.ROUTE or discovery.get("versions") != [1]:
            raise Hold("CAPABILITY_DISCOVERY_MISMATCH")
        if self.call("/api/eap/capabilities", auth=False) != service.CAPABILITIES:
            raise Hold("CORE_CAPABILITY_MISMATCH")
        state = self.call("/api/eap/state", auth=False)
        subject = state.get("subject")
        if state.get("state") != "NATIVE_EAP_HTTP_READY" or not isinstance(subject, dict):
            raise Hold("EAP_NOT_READY")
        value = wire.normalize({"schema": "qikvrt_owner_rest_input_v1", "request_id": request_id, "subject": subject,
                 "input": {"schema": "qikvrt_terminal_input_v1", "text": text, "audio": None, "video": None}})
        prepared = self.call(service.ROUTE, value, "v=1, mode=prepare")
        record = prepared.get("record") or {}
        if prepared.get("state") != "EFFECT_ACK_DONE" or "commit_token" not in prepared:
            raise Hold("PREPARE_NOT_RELEASED " + str(prepared.get("state")))
        digest = record["protocol_hash"][7:]
        if self.call("/api/eap/records/" + digest) != record:
            raise Hold("RECORD_READBACK_MISMATCH")
        context = self.call("/api/eap/records/" + digest + "/context")
        # Required evidence is rebuilt from independently observed values:
        # the anonymous state subject and this client's own principal/grant.
        observed = context.get("evidence", {})
        subject_ev = [v for v in observed.values() if v.get("schema") == "qikvrt_eap_subject_v1"]
        if len(subject_ev) != 1 or subject_ev[0].get("subject") != subject:
            raise Hold("SUBJECT_EVIDENCE_MISMATCH")
        required = [{"schema": "qikvrt_eap_subject_v1", "subject": subject, "ledger_id": subject_ev[0]["ledger_id"]},
                    {"schema": "qikvrt_eap_authority_v1", "principal": self.principal, "permissions": sorted(PERMISSIONS)}]
        try:
            wire.verify_release(context["chain"], authenticated=True, latest_hash=context["latest_hash"],
                                policy=service.POLICY, required_evidence={wire.digest(v): v for v in required},
                                observed_evidence=observed)
        except Exception as error:  # the wire module raises its own error class
            raise Hold("LOCAL_RELEASE_VERIFICATION_FAILED " + str(error)) from None
        if context["latest_hash"] != record["protocol_hash"]:
            raise Hold("STALE_RECORD")
        if record["input_id"] != request_id or record["input_hash"] != wire.digest(value["input"]):
            raise Hold("PREPARED_INPUT_BINDING_MISMATCH")
        commit_field = ("v=1, mode=commit, token=" + sf_bytes(prepared["commit_token"].encode("ascii"))
                        + ", hash=" + sf_bytes(bytes.fromhex(digest)))
        committed = self.call(service.ROUTE, value, commit_field)
        if committed.get("independent_readback_verified") is not True:
            raise Hold("COMMIT_WITHOUT_INDEPENDENT_READBACK")
        receipt = self.call("/api/eap/receipts/" + request_id)
        event = verify_receipt(receipt, value, self.principal, subject_ev[0]["ledger_id"])
        committed_event = verify_receipt(committed["native_receipt"], value, self.principal, subject_ev[0]["ledger_id"])
        if event != committed_event or receipt.get("prepare_hash") != committed["native_receipt"].get("prepare_hash"):
            raise Hold("RECEIPT_READBACK_MISMATCH")
        return {"state": "DELIVERED_TO_AUTHORITY_LEDGER", "target": self.base, "principal": self.principal,
                "request_id": request_id, "subject": subject, "record_hash": record["protocol_hash"],
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "durable_readback": committed["native_receipt"]["durable_readback"],
                "effect_scope": service.POLICY["effect"], "effect_ack_done": False, "trace": self.trace}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True, help="e.g. https://raumzeitterminal.de")
    parser.add_argument("--principal", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--text-file", required=True, type=pathlib.Path)
    parser.add_argument("--token-env", default="QIKVRT_EAP_TOKEN")
    args = parser.parse_args(argv)
    token = os.environ.get(args.token_env, "")
    try:
        if not 32 <= len(token) <= 256:
            raise Hold("EAP_TOKEN_ENV_REQUIRED " + args.token_env)
        text = args.text_file.read_text(encoding="utf-8")
        client = Client(args.base_url, args.principal, token)
        result = client.deliver(args.request_id, text)
    except Hold as hold:
        print(json.dumps({"state": "HOLD", "reason": str(hold)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
