# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Byte transport over Morse; native OwnerREST/ledger adapter, not an executor.

QIKM1 is a binary frame, not a JSON canonicalization profile. No Unicode,
case or line-ending normalization occurs. SHA-256 detects corruption; it
does not authenticate a sender. Existing OwnerREST admission supplies that
separate local boundary. The original ledger owns all persistent writes.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

MAGIC = b"QIKM\x01"
HEADER = 45  # magic/version (5), unsigned big-endian length (8), digest (32)
MAX_BYTES = 16384
MAX_WIRE = (HEADER + MAX_BYTES) * 12
MAX_REQUEST = MAX_WIRE + 4096
CODES = ("-----", ".----", "..---", "...--", "....-", ".....", "-....", "--...",
         "---..", "----.", ".-", "-...", "-.-.", "-..", ".", "..-.")
ENCODE = dict(zip("0123456789ABCDEF", CODES))
DECODE = {value: key for key, value in ENCODE.items()}


class MorseError(ValueError):
    """An explicit rejected frame; no silently discarded symbols."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(raw: bytes) -> str:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise MorseError("MORSE_BYTE_LIMIT_OR_TYPE")
    header = MAGIC + len(raw).to_bytes(8, "big")
    wire = header + hashlib.sha256(header + raw).digest() + raw
    return " ".join(ENCODE[c] for c in wire.hex().upper())


def decode(text: str) -> bytes:
    if not isinstance(text, str) or not text or len(text) > MAX_WIRE:
        raise MorseError("MORSE_FRAME_REQUIRED_OR_TOO_LARGE")
    tokens = text.split(" ")
    if len(tokens) % 2:
        raise MorseError("MORSE_INCOMPLETE_BYTE")
    try:
        wire = bytes.fromhex("".join(DECODE[token] for token in tokens))
    except (KeyError, ValueError) as exc:
        raise MorseError("MORSE_UNKNOWN_TOKEN_OR_NONCANONICAL_SPACING") from exc
    if len(wire) < HEADER or wire[:5] != MAGIC:
        raise MorseError("MORSE_VERSION_OR_HEADER")
    length, raw = int.from_bytes(wire[5:13], "big"), wire[HEADER:]
    if length != len(raw) or length > MAX_BYTES:
        raise MorseError("MORSE_LENGTH_MISMATCH")
    if not hmac.compare_digest(wire[13:HEADER], hashlib.sha256(wire[:13] + raw).digest()):
        raise MorseError("MORSE_INTEGRITY_MISMATCH")
    return raw


def unbase64(value: str) -> bytes:
    if not isinstance(value, str) or len(value) > ((MAX_BYTES + 2) // 3) * 4:
        raise MorseError("MORSE_BOUNDED_BASE64_REQUIRED")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise MorseError("MORSE_INVALID_BASE64") from exc
    if base64.b64encode(raw).decode("ascii") != value or len(raw) > MAX_BYTES:
        raise MorseError("MORSE_NONCANONICAL_BASE64")
    return raw


class Transfer:
    """Pure transcode plus original durable events; replay-safe local results.

    Input uses the existing bounded Terminal page-context contract. Result
    bytes live in the original EFFECT event, avoiding a second artifact DB.
    A stopped/restarted original writer retains its original epoch/fencing.
    """
    def __init__(self, runtime, terminal, owner_rest):
        self.runtime, self.terminal, self.rest = runtime, terminal, owner_rest

    def request(self, value):
        if (not isinstance(value, dict)
                or set(value) != {"schema", "request_id", "subject", "operation", "data"}
                or value["schema"] != "qikvrt-morse-request/v1"
                or value["operation"] not in ("encode", "decode")):
            raise MorseError("MORSE_REQUEST_REQUIRED")
        raw = unbase64(value["data"]) if value["operation"] == "encode" else decode(value["data"])
        frame = encode(raw)
        descriptor = {"schema": "qikvrt-morse-result/v1", "operation": value["operation"],
                      "payload_b64": base64.b64encode(raw).decode("ascii"),
                      "byte_length": len(raw), "payload_sha256": sha(raw),
                      "morse_sha256": sha(frame.encode("ascii"))}
        original = {"schema": "qikvrt_owner_rest_input_v1", "request_id": value["request_id"],
                    "subject": value["subject"], "input": {"schema": "qikvrt_terminal_input_v1",
                    "text": "Byte-exact Morse transport: " + value["operation"],
                    "page": {"url": "/morse/", "morse": descriptor}}}
        return self.rest.request(original)

    def prepare(self, grant, value):
        return self.rest.prepare(grant, self.request(value))

    def event(self, record):
        page = record["request"]["input"].get("page")
        if not isinstance(page, dict) or set(page) != {"url", "morse"} or page["url"] != "/morse/":
            raise MorseError("MORSE_RECEIPT_REQUIRED")
        descriptor = page["morse"]
        # Recompute all derived fields from the exact persisted bytes.
        checked = self.request({"schema": "qikvrt-morse-request/v1",
            "request_id": record["request"]["request_id"], "subject": record["request"]["subject"],
            "operation": "encode", "data": descriptor["payload_b64"]})["input"]["page"]["morse"]
        if descriptor.get("operation") not in ("encode", "decode"):
            raise MorseError("MORSE_RESULT_OPERATION")
        checked["operation"] = descriptor["operation"]
        if checked != descriptor:
            raise MorseError("MORSE_RESULT_READBACK_MISMATCH")
        plan = record["plan"]
        identity = sha(self.terminal.canonical_json([plan["principal"], plan["request_id"]]))
        return {"schema": self.terminal.NATIVE_SCHEMA, "kind": "EFFECT", "subject": plan["subject"],
                "provenance": {"source": "transputer", "native_event_id": "morse-result:" + identity},
                "observed_at": plan["event"]["observed_at"],
                "message": "Local byte transcode persisted; public/peer acceptance remains separate",
                "payload": {"result": descriptor, "input_native_sha256": sha(self.terminal.canonical_json(plan["event"])),
                            "scope": "LOCAL_BYTE_TRANSCODE", "effect_ack_done": False}}

    def commit(self, grant, value, binding):
        original = self.request(value)
        with self.runtime.ledger.condition:
            self.rest.commit(grant, original, binding)
            record = self.rest.record(grant["principal"], original["request_id"])
            event = self.event(record)
            persisted = self.runtime.append(event)
            epoch, observed = self.terminal._durable_read(self.rest.state_dir, event)
            if epoch != self.runtime.ledger.epoch or persisted != observed:
                raise MorseError("MORSE_AMBIGUOUS_RESULT_USE_READBACK")
            return self.readback(grant, original["request_id"])

    def readback(self, grant, request_id):
        with self.runtime.ledger.condition:
            original = self.rest.readback(grant, request_id, self.runtime.ensure_subject())
            record = self.rest.record(grant["principal"], request_id)
            epoch, event = self.terminal._durable_read(self.rest.state_dir, self.event(record))
            if epoch != self.runtime.ledger.epoch or event is None:
                raise MorseError("MORSE_RESULT_NOT_OBSERVED_USE_READBACK")
            return {"schema": "qikvrt-morse-receipt/v1", "state": "RESULT_PERSISTED",
                    "request_id": request_id, "subject": record["plan"]["subject"],
                    "prepare_hash": original["prepare_hash"], "input_receipt": original,
                    "execution": event, "independent_sqlite_readback": True,
                    "scope": "LOCAL_BYTE_TRANSCODE_AND_DURABLE_READBACK",
                    "ordinary_release": False, "EFFECT_ACK_DONE": False}

    def download(self, grant, request_id, kind):
        receipt = self.readback(grant, request_id)
        raw = unbase64(receipt["execution"]["payload"]["result"]["payload_b64"])
        if kind == "data": return raw, "application/octet-stream", "qikvrt-result.bin"
        if kind == "morse": return encode(raw).encode("ascii"), "text/plain; charset=us-ascii", "qikvrt-result.morse"
        if kind == "receipt": return self.terminal.canonical_json(receipt) + b"\n", "application/json", "qikvrt-receipt.json"
        raise MorseError("MORSE_DOWNLOAD_KIND")


def serve_get(handler, transport, package):
    """Extend the existing S1 listener and its existing owner guard."""
    path = urlsplit(handler.path)
    assets = {"/morse/": ("index.html", "text/html; charset=utf-8"),
              "/morse/codec.js": ("codec.js", "text/javascript; charset=utf-8"),
              "/morse/ui.js": ("ui.js", "text/javascript; charset=utf-8"),
              "/morse/style.css": ("style.css", "text/css; charset=utf-8")}
    if path.path in assets:
        host = handler.headers.get("Host", "")
        if (path.query or path.fragment or len(handler.headers.get_all("Host", [])) != 1
                or host not in {f"127.0.0.1:{handler.server.server_port}", f"localhost:{handler.server.server_port}"}):
            handler._hold("MORSE_EXACT_LOCAL_ROUTE_REQUIRED", 403); return True
        name, media = assets[path.path]
        try:
            transport.runtime.ensure_subject()
            body = (Path(package) / "docs/terminal/morse" / name).read_bytes()
        except (ValueError, OSError):
            handler._hold("MORSE_BOUND_SOURCE_UNAVAILABLE", 503); return True
        filename = None
    elif path.path.startswith("/api/owner/morse/"):
        grant = handler.owner_guard("readback")
        if grant is None: return True
        try:
            if (path.query or path.fragment or len(handler.headers.get_all("QIKVRT-Subject", [])) != 1
                    or json.loads(handler.headers["QIKVRT-Subject"]) != transport.runtime.ensure_subject()):
                raise MorseError("MORSE_EXACT_SUBJECT_REQUIRED")
            match = re.fullmatch(r"/api/owner/morse/(receipts|download)/([A-Za-z0-9_.:-]{1,100})(?:/(data|morse|receipt))?", path.path)
            if match is None: raise MorseError("MORSE_EXACT_READBACK_ROUTE_REQUIRED")
            mode, request_id, kind = match.groups()
            if mode == "receipts" and kind is None:
                handler._json(200, transport.readback(grant, request_id)); return True
            if mode != "download" or kind is None: raise MorseError("MORSE_DOWNLOAD_KIND_REQUIRED")
            body, media, filename = transport.download(grant, request_id, kind)
        except (ValueError, KeyError, TypeError, RecursionError) as exc:
            handler._hold(str(exc), 409); return True
        except (OSError, sqlite3.Error):
            handler._hold("MORSE_DURABLE_READBACK_UNAVAILABLE", 503); return True
    else:
        return False
    handler.send_response(200)
    handler.send_header("Content-Type", media)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
    handler.send_header("Content-Digest", "sha-256=:" + base64.b64encode(hashlib.sha256(body).digest()).decode("ascii") + ":")
    if filename: handler.send_header("Content-Disposition", 'attachment; filename="' + filename + '"')
    handler.end_headers(); handler.wfile.write(body)
    return True


def main():
    """Portable file codec; durable native receipts require the original S1 API."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("encode", "decode"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, help="new file; existing files are never overwritten")
    args = parser.parse_args()
    try:
        limit = MAX_BYTES if args.operation == "encode" else MAX_WIRE
        with args.input.open("rb") as source:
            raw = source.read(limit + 1)
        if len(raw) > limit: raise MorseError("MORSE_INPUT_TOO_LARGE")
        result = encode(raw).encode("ascii") if args.operation == "encode" else decode(raw.decode("ascii"))
        with args.output.open("xb") as output: output.write(result)
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
