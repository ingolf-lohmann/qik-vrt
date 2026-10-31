#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Revision-03 wire gate on the original admitted S1 OwnerREST and ledger.

This module owns no listener, credential store or alternate effect executor.
The sole protected effect is the original durable terminal-input observation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
import time
from urllib.parse import urlsplit

try:
    from . import qikvrt_effect_ack as core
    from . import qikvrt_effect_ack_wire as wire
except ImportError:
    import qikvrt_effect_ack as core
    import qikvrt_effect_ack_wire as wire

POLICY = {
    "policy_id": "QIKVRT_ADMITTED_NATIVE_TERMINAL_INPUT_V1", "policy_version": 1,
    "effect": "ORIGINAL_OWNER_REST_DURABLE_TERMINAL_INPUT",
    "semantics": "Bounded text input is an observation; it is never executed as a command.",
    "required_evidence_rule": "Exact admitted subject and authenticated principal's current permission set",
    "authentication": "EXISTING_OWNER_REST_BEARER_AND_QIKVRT_OWNER",
    "freshness": "Latest private ledger record plus original expiring request/principal-bound preparation",
    "replay": "Original native event identity; recover the same independent SQLite receipt without another effect",
    "scope": "LOCAL_NATIVE_INPUT_ACCEPTANCE; NO_REPOSITORY_OR_HOST_OR_DOMAIN_COMPLETION",
}
CAPABILITIES = {"message_type": "effect-ack-capabilities", "supported_versions": [1]}
ROUTE = "/api/eap/effect"


class Service:
    def __init__(self, rest):
        self.rest, self.runtime = rest, rest.runtime

    def _key(self, principal, request_id):
        return "eap-context:" + wire.digest([principal, request_id])[7:]

    def _read(self, key):
        row = self.runtime.ledger.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return wire.parse(row[0].encode("utf-8")) if row else None

    def _evidence(self, grant):
        values = [
            {"schema": "qikvrt_eap_subject_v1", "subject": self.runtime.ensure_subject(), "ledger_id": self.runtime.ledger.epoch},
            {"schema": "qikvrt_eap_authority_v1", "principal": grant["principal"], "permissions": sorted(grant["permissions"])}]
        return {wire.digest(value): value for value in values}

    def _ticket(self, grant, context):
        bound = {"method": "POST", "target": ROUTE, "principal": grant["principal"],
            "protocol_hash": context["chain"][-1]["protocol_hash"], "policy_hash": wire.digest(POLICY),
            "original_preparation_hash": context["original_hash"], "expires_at": context["expires_at"],
            "ledger_id": self.runtime.ledger.epoch}
        return hmac.new(grant["token"].encode("ascii"), wire.canonical(bound), hashlib.sha256).hexdigest()

    def _validate_context(self, context, grant, request_id):
        if not context or context.get("principal") != grant["principal"] or context.get("request_id") != request_id:
            raise ValueError("EAP_PREPARATION_REQUIRED")
        wire.verify_chain(context["chain"])
        original = self.rest.record(grant["principal"], request_id)
        if original is None or original["record_hash"] != context["original_hash"]:
            raise ValueError("EAP_ORIGINAL_PREPARATION_MISMATCH")
        return original

    def prepare(self, grant, value):
        value = self.rest.request(value)
        ledger = self.runtime.ledger
        with ledger.condition:
            ledger._check_writer()
            original = self.rest.prepare(grant, value)
            key = self._key(grant["principal"], value["request_id"])
            old = self._read(key)
            if old:
                self._validate_context(old, grant, value["request_id"])
            evidence = self._evidence(grant)
            request = core.EffectAckRequest(
                protocol_root_id="qikvrt:eap:" + wire.digest([grant["principal"], value["request_id"]])[7:],
                input_id=value["request_id"], payload=wire.canonical(value["input"]), transport_ack=True,
                origin_checked=True, context_checked=True, semantics_reconstructed=True, effect_anticipated=True,
                risk_classified=True, risk_level=core.RiskLevel.LOW, responsibility_assigned=True,
                responsibility_owner=grant["principal"], connection_decision=core.ConnectionDecision.RELEASE,
                policy_allows_release="commit" in grant["permissions"],
                evidence_refs=tuple(evidence), required_evidence_refs=tuple(evidence),
                reasons=("EXACT_AUTHENTICATED_NATIVE_INPUT_POLICY",))
            record = wire.make_record(request, POLICY, previous_chain=old["chain"] if old else None)
            chain = old["chain"] if old and old["chain"][-1]["protocol_hash"] == record["protocol_hash"] else (old["chain"] if old else []) + [record]
            if len(chain) > 128:
                raise ValueError("EAP_CHAIN_CAPACITY_REACHED")
            # A lost response after the original append is reconciled before
            # another event. Preserve its original timestamp and native bytes.
            native_id = "eap:" + record["protocol_hash"][7:]
            row = ledger.db.execute("SELECT seq,binding,body,body_digest FROM events WHERE source=? AND native_id=?",
                                    ("transputer", native_id)).fetchone()
            if row:
                event = ledger._decode(row)
                stored = event["payload"]["record"]
                if wire.projection(stored) != wire.projection(record):
                    raise ValueError("EAP_NATIVE_RECORD_CONFLICT")
                chain = chain[:-1] + [stored]
                record = stored
            else:
                event = self.runtime.append({"schema": self.rest.terminal.NATIVE_SCHEMA, "kind": "CLASSIFY",
                    "subject": value["subject"], "provenance": {"source": "transputer", "native_event_id": native_id},
                    "observed_at": record["created_utc"], "message": "EAP revision-03 native input decision",
                    "payload": {"adapter": "QIKVRT_EFFECT_ACK_HTTP_V1", "record": record, "policy_hash": wire.digest(POLICY)}})
            context = {"principal": grant["principal"], "request_id": value["request_id"], "chain": chain,
                "policy": POLICY, "evidence": evidence, "original_hash": original["record_hash"],
                "expires_at": original["preparation"]["expires_at"], "native_classification_id": event["id"]}
            with ledger.db:
                for name in (key, "eap-record:" + record["protocol_hash"][7:]):
                    ledger.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (name, wire.canonical(context).decode("utf-8")))
            if self._read(key) != context:
                raise ValueError("EAP_NATIVE_CONTEXT_READBACK_MISMATCH")
            response = {"state": record["state"], "record": record,
                "record_url": "/api/eap/records/" + record["protocol_hash"][7:],
                "context_url": "/api/eap/records/" + record["protocol_hash"][7:] + "/context",
                "expires_at": context["expires_at"], "ordinary_release": False,
                "effect_scope": POLICY["effect"], "effect_ack_done": False}
            if record["state"] == "EFFECT_ACK_DONE":
                response["commit_token"] = self._ticket(grant, context)
            return response

    def record(self, grant, digest, context=False):
        self.runtime.ensure_subject()
        with self.runtime.ledger.condition:
            found = self._read("eap-record:" + digest)
            if found is None or found["principal"] != grant["principal"]:
                raise ValueError("EAP_RECORD_NOT_FOUND_FOR_PRINCIPAL")
            self._validate_context(found, grant, found["request_id"])
            if context:
                latest = self._read(self._key(grant["principal"], found["request_id"]))
                return {**{k: found[k] for k in ("chain", "policy", "evidence")},
                        "latest_hash": latest["chain"][-1]["protocol_hash"] if latest else None}
            return found["chain"][-1]

    def commit(self, grant, value, binding):
        value = self.rest.request(value)
        with self.runtime.ledger.condition:
            self.runtime.ensure_subject()
            context = self._read(self._key(grant["principal"], value["request_id"]))
            original = self._validate_context(context, grant, value["request_id"])
            if wire.canonical(value) != wire.canonical(original["request"]):
                raise ValueError("EAP_EXACT_REQUEST_BINDING_MISMATCH")
            record = context["chain"][-1]
            if binding["hash"] != record["protocol_hash"][7:] or not hmac.compare_digest(binding["token"], self._ticket(grant, context)):
                raise ValueError("EAP_COMMIT_BINDING_MISMATCH")
            wire.verify_release(context["chain"], authenticated=True, latest_hash=record["protocol_hash"],
                policy=POLICY, required_evidence=self._evidence(grant), observed_evidence=context["evidence"])
            # Original OwnerREST performs expiry, idempotent append and a cold
            # SQLite readback. The EAP adapter never invokes a second executor.
            receipt = self.rest.commit(grant, value, {"v": 1, "mode": "commit",
                "hash": original["record_hash"], "token": self.rest.ticket(grant, original)})
            return {"state": record["state"], "record": record, "native_receipt": receipt,
                "effect_scope": POLICY["effect"], "ordinary_release": True,
                "independent_readback_verified": receipt["independent_sqlite_readback"], "effect_ack_done": False}


def make_handler(base, rest):
    service = Service(rest)
    class Handler(base):
        def do_GET(self):
            route = urlsplit(self.path)
            if route.path not in ("/.well-known/effect-ack", "/api/eap/capabilities", "/api/eap/state") and not route.path.startswith("/api/eap/"):
                return super().do_GET()
            if route.query or self.path != route.path:
                return self._hold("EAP_EXACT_ROUTE_REQUIRED", 400)
            if route.path == "/.well-known/effect-ack":
                return self._json(200, {"core": CAPABILITIES, "versions": [1], "modes": ["prepare", "commit"],
                    "specification": wire.SPECIFICATION, "effect_scope": POLICY["effect"],
                    "effect_endpoint": ROUTE, "record_template": "/api/eap/records/{sha256}",
                    "authentication": POLICY["authentication"], "ordinary_release": False})
            if route.path == "/api/eap/capabilities":
                return self._json(200, CAPABILITIES)
            if route.path == "/api/eap/state":
                try:
                    return self._json(200, {"schema": "qikvrt_eap_http_status_v1", "state": "NATIVE_EAP_HTTP_READY",
                        "subject": rest.runtime.ensure_subject(), "specification": wire.SPECIFICATION,
                        "effect_scope": POLICY["effect"], "ordinary_release": False, "effect_ack_done": False})
                except (ValueError, OSError, sqlite3.Error):
                    return self._hold("EAP_NATIVE_READBACK_UNAVAILABLE", 503)
            grant = self.owner_guard("readback")
            if grant is None:
                return
            try:
                match = re.fullmatch(r"/api/eap/records/([0-9a-f]{64})(/context)?", route.path)
                if match:
                    return self._json(200, service.record(grant, match[1], bool(match[2])))
                match = re.fullmatch(r"/api/eap/receipts/([A-Za-z0-9_.:-]{1,100})", route.path)
                if match:
                    return self._json(200, rest.readback(grant, match[1], rest.runtime.ensure_subject()))
                return self._hold("EAP_ROUTE_NOT_FOUND", 404)
            except (ValueError, KeyError, TypeError, RecursionError):
                return self._hold("EAP_RECORD_READBACK_UNAVAILABLE", 409)
            except (OSError, sqlite3.Error):
                return self._hold("EAP_NATIVE_STORE_UNAVAILABLE", 503)

        def do_POST(self):
            if urlsplit(self.path).path.startswith("/api/owner/"):
                return self._hold("EAP_PROFILE_REQUIRES_GATED_EFFECT_ROUTE", 405)
            if urlsplit(self.path).path != ROUTE:
                return super().do_POST()
            try:
                if self.path != ROUTE or self.headers.get("Transfer-Encoding") is not None or any(
                        len(self.headers.get_all(name, [])) != 1 for name in ("Content-Length", "Content-Type", "Effect-Ack-Request")):
                    raise ValueError("BOUNDED_EAP_HEADERS_REQUIRED")
                binding = rest.terminal.parse_effect_ack_request(self.headers["Effect-Ack-Request"])
                grant = self.owner_guard(binding["mode"])
                if grant is None:
                    return
                length = int(self.headers["Content-Length"])
                if not 1 <= length <= 32768 or self.headers["Content-Type"].split(";", 1)[0].strip() != "application/json":
                    raise ValueError("BOUNDED_JSON_REQUIRED")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("COMPLETE_BODY_REQUIRED")
                value = wire.parse(raw)
                result = service.prepare(grant, value) if binding["mode"] == "prepare" else service.commit(grant, value, binding)
                record = result["record"]
                return self._json(200, result, state=record["state"], record_hash=record["protocol_hash"][7:], commit_token=result.get("commit_token"))
            except (ValueError, KeyError, TypeError, RecursionError):
                return self._hold("EAP_BINDING_OR_POLICY_VALIDATION_FAILED", 409)
            except (OSError, sqlite3.Error):
                return self._hold("EAP_NATIVE_PERSISTENCE_UNAVAILABLE_READBACK_BEFORE_RETRY", 503)
    return Handler
