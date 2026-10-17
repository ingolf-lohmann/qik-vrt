#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Exact-subject Digital Twin API using the existing fenced repository broker.

The reference-only mode remains explicitly non-reflexive. Broker mode returns
one canonical API result only after Git bytes and the durable ledger are freshly
read back. HTTP success never grants product acceptance or EFFECT_ACK_DONE.
"""
from __future__ import annotations

import argparse
import base64
import copy
import json
import threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from src.qikvrt_siemens_reference_integration import TwinState, prepare, commit_simulated, reobserve, digest
from src.qikvrt_github_api_shim import GitHubAuthorityProvider
from tools.qikvrt_authority_transition import AuthorityControlPlane, TransitionError, secret_file
from tools.qikvrt_seed_common import canonical_json_bytes, parse_json_bytes


class Store:
    def __init__(self, state, authority_subject, mirror_subject, *, writer=None,
                 writer_capability=None, permit=None, repository_subject=None):
        self.state = state
        self.authority_subject = authority_subject
        self.mirror_subject = mirror_subject
        self.lock = threading.RLock()
        self.last_receipt = None
        self.last_repository_receipt = None
        self.last_effect_id = None
        self.writer = writer
        self.writer_capability = writer_capability
        self.permit = copy.deepcopy(permit)
        self.repository_subject = copy.deepcopy(repository_subject)
        self.unresolved_effect_id = None
        if writer is not None and (not writer_capability or not permit or not repository_subject):
            raise ValueError("COMPLETE_BROKER_CONFIGURATION_REQUIRED")

    def snapshot(self):
        with self.lock:
            body = asdict(self.state)
            return {"schema": "qikvrt_digital_twin_rest_v1", "state": body, "state_sha256": digest(body),
                    "authority_subject": self.authority_subject, "mirror_subject": self.mirror_subject,
                    "repository_subject": self.repository_subject, "last_effect_id": self.last_effect_id,
                    "unresolved_effect_id": self.unresolved_effect_id,
                    "mode": "FENCED_REPOSITORY_BROKER" if self.writer else "LOCAL_REFERENCE_ONLY",
                    "repository_effect_verified": self.last_repository_receipt is not None,
                    "pole_equality_claim": False, "effect_ack_done": False}

    def apply(self, expected_version, target_velocity_mps, binding=None):
        with self.lock:
            if type(expected_version) is not int or expected_version != self.state.version:
                raise ValueError("STALE_EXACT_TWIN_VERSION")
            if type(target_velocity_mps) not in (int, float):
                raise ValueError("INVALID_TARGET_VELOCITY")
            if self.unresolved_effect_id is not None:
                raise ValueError("UNRESOLVED_INTENT_READBACK_ONLY")
            before = self.state
            prepared = prepare(before, target_velocity_mps=target_velocity_mps)
            after, effect = commit_simulated(before, prepared)
            receipt = reobserve(before, after, effect)
            if not receipt["effect_ack"]:
                raise ValueError("POST_EFFECT_READBACK_FAILED")
            response = {"prepared": prepared, "effect": effect, "receipt": receipt, "state": asdict(after)}
            if self.writer is None:
                if binding is not None:
                    raise ValueError("REPOSITORY_BROKER_NOT_CONFIGURED")
                self.state, self.last_receipt = after, receipt
                return {**response, "mode": "LOCAL_REFERENCE_ONLY", "repository_effect_verified": False,
                        "effect_ack_done": False, "effect_state": "EFFECT_ACK_CONTINUE"}
            if not isinstance(binding, dict):
                raise ValueError("EXACT_REPOSITORY_BINDING_REQUIRED")
            for key in ("repository", "pr", "head", "tree"):
                if binding.get(key) != self.repository_subject.get(key):
                    raise ValueError("STALE_REPOSITORY_SUBJECT")
            if binding.get("expected_state_sha256") != digest(asdict(before)):
                raise ValueError("STALE_EXACT_TWIN_STATE")
            if binding.get("expected_predecessor_effect_id") != self.last_effect_id:
                raise ValueError("STALE_TWIN_PREDECESSOR")
            result = {"schema": "qikvrt_reflexive_twin_effect_v1", "binding": copy.deepcopy(binding),
                      "request": {"expected_version": expected_version, "target_velocity_mps": target_velocity_mps,
                                  "binding": copy.deepcopy(binding)},
                      "before_state": asdict(before), "response": response, "effect_ack_done": False}
            # Validate all inputs before entering the canonical writer.
            self.writer._twin_result(result)
            try:
                out = self.writer.execute(self.writer_capability, self.permit,
                    {"operation": "persist_twin_transition", "effect_id": binding["effect_id"], "api_result": result})
                self._accept_readback(out, expected_result=result)
            except (ValueError, TypeError, OSError, RuntimeError):
                # Even an uncertain outcome cannot be rolled back by HTTP code.
                # Recovery is exclusively the existing broker's readback path.
                try:
                    status = self.writer.twin_intent_status(self.writer_capability, self.permit, binding["effect_id"])
                except (ValueError, TypeError, OSError, RuntimeError):
                    status = "UNKNOWN"
                if status not in {None, "REJECTED"}:
                    self.unresolved_effect_id = binding["effect_id"]
                raise
            return out

    def _accept_readback(self, out, *, expected_result=None):
        result = out["api_result"]
        if expected_result is not None and canonical_json_bytes(result) != canonical_json_bytes(expected_result):
            raise ValueError("INITIATOR_REPOSITORY_RESULT_MISMATCH")
        raw = base64.b64decode(out["api_result_bytes_b64"], validate=True)
        if raw != canonical_json_bytes(result) or not out["repository_receipt"].get("fresh_byte_readback"):
            raise ValueError("INITIATOR_REPOSITORY_BYTE_MISMATCH")
        binding, _, after = self.writer._twin_result(result)
        if any(binding[k] != self.repository_subject[k] for k in ("repository", "pr", "head", "tree")):
            raise ValueError("RECOVERY_REPOSITORY_SUBJECT_MISMATCH")
        # Reading an older receipt must not rewind a newer in-memory projection.
        if after["version"] >= self.state.version:
            self.state = TwinState.from_dict(after)
            self.last_receipt = result["response"]["receipt"]
            self.last_repository_receipt = out["repository_receipt"]
            self.last_effect_id = binding["effect_id"]
        self.unresolved_effect_id = None

    def recover(self, effect_id):
        with self.lock:
            if self.writer is None:
                raise ValueError("REPOSITORY_BROKER_NOT_CONFIGURED")
            if self.unresolved_effect_id is not None and effect_id != self.unresolved_effect_id:
                raise ValueError("UNRESOLVED_INTENT_READBACK_ONLY")
            out = self.writer.recover_twin_transition(self.writer_capability, self.permit, effect_id)
            self._accept_readback(out)
            return out

    def receipt(self):
        with self.lock:
            return {"receipt": self.last_receipt, "repository_receipt": self.last_repository_receipt,
                    "effect_ack_done": False}


def handler(store):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def sendj(self, code, obj):
            payload = canonical_json_bytes(obj)
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                # The repository effect is already durable. No retry/rollback.
                return

        def body(self):
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("TRANSFER_ENCODING_UNSUPPORTED")
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise ValueError("INVALID_CONTENT_LENGTH") from None
            if length < 1 or length > 16384:
                raise ValueError("INVALID_BODY_SIZE")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("TRUNCATED_REQUEST")
            value = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_nonfinite)
            if not isinstance(value, dict):
                raise ValueError("OBJECT_REQUIRED")
            return value

        def do_GET(self):
            path = urlsplit(self.path).path
            try:
                if path == "/api/digital-twin/v1":
                    return self.sendj(200, {"schema": "qikvrt_digital_twin_rest_v1",
                        "links": {"state": "/api/digital-twin/v1/state", "receipt": "/api/digital-twin/v1/receipt",
                                  "transition": "/api/digital-twin/v1/transitions"},
                        "mode": "FENCED_REPOSITORY_BROKER" if store.writer else "LOCAL_REFERENCE_ONLY",
                        "effect_ack_done": False})
                if path == "/api/digital-twin/v1/state":
                    return self.sendj(200, store.snapshot())
                if path == "/api/digital-twin/v1/receipt":
                    return self.sendj(200, store.receipt())
                prefix = "/api/digital-twin/v1/receipts/"
                if path.startswith(prefix):
                    return self.sendj(200, store.recover(path[len(prefix):]))
            except (ValueError, TypeError, OSError, RuntimeError) as exc:
                return self.sendj(409, {"state": "HOLD", "reason": _public_reason(exc), "effect_ack_done": False})
            return self.sendj(404, {"state": "HOLD", "reason": "NOT_FOUND", "effect_ack_done": False})

        def do_POST(self):
            if urlsplit(self.path).path != "/api/digital-twin/v1/transitions":
                return self.sendj(404, {"state": "HOLD", "reason": "NOT_FOUND", "effect_ack_done": False})
            try:
                value = self.body()
                expected_keys = {"expected_version", "target_velocity_mps"}
                if store.writer:
                    expected_keys.add("binding")
                if set(value) != expected_keys:
                    raise ValueError("CLOSED_REQUEST_SCHEMA")
                out = store.apply(value["expected_version"], value["target_velocity_mps"], value.get("binding"))
                return self.sendj(200, out)
            except (ValueError, TypeError, OSError, RuntimeError) as exc:
                return self.sendj(409, {"state": "HOLD", "reason": _public_reason(exc), "effect_ack_done": False})

        def log_message(self, *args):
            pass
    return H


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError("NONFINITE_JSON_NUMBER")


def _public_reason(exc):
    # Fixed internal diagnostics only; do not reflect credentials/error bodies.
    if isinstance(exc, TransitionError):
        return "REPOSITORY_EFFECT_HOLD_READBACK_REQUIRED"
    return str(exc) if isinstance(exc, ValueError) else "INVALID_REQUEST_OR_UNAVAILABLE_BROKER"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--authority-subject", required=True)
    ap.add_argument("--mirror-subject", required=True)
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8782)
    ap.add_argument("--control-plane")
    ap.add_argument("--writer-capability-file")
    ap.add_argument("--permit")
    ap.add_argument("--repository-subject")
    ns = ap.parse_args()
    if ns.bind not in {"127.0.0.1", "localhost"}:
        ap.error("privileged reference API requires loopback bind")
    config = [ns.control_plane, ns.writer_capability_file, ns.permit, ns.repository_subject]
    if any(config) and not all(config):
        ap.error("complete existing broker configuration required")
    state = TwinState.from_dict(parse_json_bytes(Path(ns.state).read_bytes(), "initial twin state"))
    kwargs = {}
    if all(config):
        subject = parse_json_bytes(Path(ns.repository_subject).read_bytes(), "repository subject")
        kwargs = {"writer": GitHubAuthorityProvider(AuthorityControlPlane(Path(ns.control_plane)), subject["repository"]),
                  "writer_capability": secret_file(Path(ns.writer_capability_file)),
                  "permit": parse_json_bytes(Path(ns.permit).read_bytes(), "writer permit"), "repository_subject": subject}
    store = Store(state, ns.authority_subject, ns.mirror_subject, **kwargs)
    if store.writer:
        latest = store.writer.latest_twin_effect(store.writer_capability, store.permit, state.twin_id)
        if latest:
            store.recover(latest)
    ThreadingHTTPServer((ns.bind, ns.port), handler(store)).serve_forever()


if __name__ == "__main__":
    main()
