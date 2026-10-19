#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: Claude (Anthropic).
"""Bounded IONOS DNS readback and exact-state-bound apex address update.

Purpose: close the configuration gap behind the observed HTTP 525 on the
product host. The apex A record of the product zone currently points at the
IONOS shared-webhosting address, not at an owned TLS-terminating origin.

Effect boundary:
- ``readback`` is GET-only and emits a receipt with a canonical digest of the
  apex record set.
- ``apply`` changes exactly one apex A record to one public IPv4 address. It
  requires the digest of an independent prior readback and refuses when the
  live record set differs (no blind write, no lost update), when more than one
  A record exists, or when AAAA/CNAME records at the apex would keep routing
  traffic elsewhere. It never deletes, never creates zones and never touches
  any other record name.
- Every apply ends with a fresh readback; only a matching readback is DONE.

The API key is taken from the environment variable IONOS_DNS_API_KEY in the
documented ``<prefix>.<secret>`` form and is never written to any receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_ROOT = "https://api.hosting.ionos.com/dns/v1"
KEY_ENV = "IONOS_DNS_API_KEY"
RECEIPT_SCHEMA = "qikvrt-ionos-dns-receipt/v1"
MAX_RESPONSE = 2 * 1024 * 1024
ROUTING_TYPES = ("A", "AAAA", "CNAME")


class DNSHold(RuntimeError):
    """A fail-closed boundary; the message is a stable HOLD_* code."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401 - urllib hook
        return None


class API:
    """Minimal IONOS DNS v1 transport with a fixed origin and no redirects."""

    def __init__(self, key: str, root: str = API_ROOT):
        if not key or "." not in key or any(c.isspace() for c in key):
            raise DNSHold("HOLD_IONOS_DNS_API_KEY_REQUIRED")
        self._key = key
        self.root = root
        self._opener = urllib.request.build_opener(NoRedirect())

    def request(self, method: str, path: str, body=None):
        if method not in {"GET", "PUT"}:
            raise DNSHold("HOLD_IONOS_DNS_METHOD_NOT_ALLOWED")
        url = self.root + path
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
        headers = {"X-API-Key": self._key, "Accept": "application/json", "Cache-Control": "no-cache"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with self._opener.open(req, timeout=20) as response:
                if response.geturl() != url:
                    raise DNSHold("HOLD_IONOS_DNS_REDIRECT_REFUSED")
                raw = response.read(MAX_RESPONSE + 1)
        except urllib.error.HTTPError as exc:
            raise DNSHold(f"HOLD_IONOS_DNS_HTTP_{exc.code}") from None
        except (urllib.error.URLError, OSError):
            raise DNSHold("HOLD_IONOS_DNS_TRANSPORT") from None
        if len(raw) > MAX_RESPONSE:
            raise DNSHold("HOLD_IONOS_DNS_RESPONSE_TOO_LARGE")
        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            raise DNSHold("HOLD_IONOS_DNS_RESPONSE_NOT_JSON") from None


def _zone_name(value: str) -> str:
    name = value.strip().rstrip(".").lower()
    labels = name.split(".")
    if len(labels) < 2 or any(not l or len(l) > 63 or not all(c.isalnum() or c == "-" for c in l) for l in labels):
        raise DNSHold("HOLD_ZONE_NAME_INVALID")
    return name


def public_ipv4(value: str) -> str:
    try:
        address = ipaddress.IPv4Address(value)
    except ValueError:
        raise DNSHold("HOLD_TARGET_IPV4_INVALID") from None
    if not address.is_global:
        raise DNSHold("HOLD_TARGET_IPV4_NOT_PUBLIC")
    return str(address)


def find_zone(api: API, zone: str) -> str:
    zones = api.request("GET", "/zones")
    if not isinstance(zones, list):
        raise DNSHold("HOLD_IONOS_DNS_ZONE_LIST_INVALID")
    matches = [z for z in zones if isinstance(z, dict) and str(z.get("name", "")).rstrip(".").lower() == zone]
    if len(matches) != 1 or not isinstance(matches[0].get("id"), str):
        raise DNSHold("HOLD_IONOS_DNS_ZONE_NOT_UNIQUE")
    return matches[0]["id"]


def apex_records(api: API, zone: str, zone_id: str) -> list[dict]:
    query = urllib.parse.urlencode({"recordName": zone})
    detail = api.request("GET", f"/zones/{urllib.parse.quote(zone_id, safe='')}?{query}")
    if not isinstance(detail, dict) or not isinstance(detail.get("records"), list):
        raise DNSHold("HOLD_IONOS_DNS_ZONE_DETAIL_INVALID")
    records = []
    for r in detail["records"]:
        if not isinstance(r, dict) or str(r.get("name", "")).rstrip(".").lower() != zone:
            continue
        if r.get("type") not in ROUTING_TYPES:
            continue
        records.append({"id": str(r.get("id")), "type": r["type"], "content": str(r.get("content")),
                        "ttl": r.get("ttl"), "disabled": bool(r.get("disabled", False))})
    return sorted(records, key=lambda r: (r["type"], r["content"], r["id"]))


def digest(records: list[dict]) -> str:
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def plan(records: list[dict], target: str) -> dict:
    active = [r for r in records if not r["disabled"]]
    a = [r for r in active if r["type"] == "A"]
    others = [r for r in active if r["type"] != "A"]
    if others:
        raise DNSHold("HOLD_APEX_AAAA_OR_CNAME_PRESENT")
    if len(a) != 1:
        raise DNSHold("HOLD_APEX_A_RECORD_NOT_SINGLE")
    if a[0]["content"] == target:
        return {"action": "NOOP", "record_id": a[0]["id"], "from": target, "to": target}
    return {"action": "UPDATE_A", "record_id": a[0]["id"], "from": a[0]["content"], "to": target,
            "ttl": a[0]["ttl"] if isinstance(a[0]["ttl"], int) and a[0]["ttl"] > 0 else 3600}


def readback(api: API, zone: str) -> dict:
    zone = _zone_name(zone)
    zone_id = find_zone(api, zone)
    records = apex_records(api, zone, zone_id)
    return {"schema": RECEIPT_SCHEMA, "operation": "readback", "zone": zone, "zone_id": zone_id,
            "apex_records": records, "apex_records_sha256": digest(records), "effect": "NONE"}


def apply(api: API, zone: str, target: str, expected_sha256: str) -> dict:
    zone = _zone_name(zone)
    target = public_ipv4(target)
    if not (isinstance(expected_sha256, str) and len(expected_sha256) == 64
            and all(c in "0123456789abcdef" for c in expected_sha256)):
        raise DNSHold("HOLD_EXPECTED_RECORDS_SHA256_REQUIRED")
    before = readback(api, zone)
    if before["apex_records_sha256"] != expected_sha256:
        raise DNSHold("HOLD_APEX_RECORDS_CHANGED_SINCE_READBACK")
    step = plan(before["apex_records"], target)
    receipt = {"schema": RECEIPT_SCHEMA, "operation": "apply", "zone": zone, "zone_id": before["zone_id"],
               "target_ipv4": target, "before_sha256": before["apex_records_sha256"], "plan": step}
    if step["action"] == "UPDATE_A":
        path = f"/zones/{urllib.parse.quote(before['zone_id'], safe='')}/records/{urllib.parse.quote(step['record_id'], safe='')}"
        try:
            api.request("PUT", path, {"content": target, "ttl": step["ttl"], "disabled": False})
            receipt["effect"] = "PUT_ONE_APEX_A_RECORD"
        except DNSHold as exc:
            # The request may have reached the provider; only readback decides.
            receipt["effect"] = "PUT_OUTCOME_UNKNOWN"
            receipt["transport_boundary"] = str(exc)
    else:
        receipt["effect"] = "NONE"
    try:
        after = readback(api, zone)
    except DNSHold as exc:
        receipt["state"] = "HOLD_READBACK_UNAVAILABLE"
        receipt["readback_boundary"] = str(exc)
        return receipt
    receipt["after_records"] = after["apex_records"]
    receipt["after_sha256"] = after["apex_records_sha256"]
    active_a = [r["content"] for r in after["apex_records"] if r["type"] == "A" and not r["disabled"]]
    receipt["state"] = "DONE" if active_a == [target] and len(after["apex_records"]) == 1 else "HOLD_READBACK_MISMATCH"
    return receipt


def main(argv=None, env=None) -> int:
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("readback")
    r.add_argument("--zone", required=True)
    a = sub.add_parser("apply")
    a.add_argument("--zone", required=True)
    a.add_argument("--target-ipv4", required=True)
    a.add_argument("--expected-records-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        api = API(env.get(KEY_ENV, ""))
        result = readback(api, args.zone) if args.command == "readback" else apply(
            api, args.zone, args.target_ipv4, args.expected_records_sha256)
    except DNSHold as exc:
        result = {"schema": RECEIPT_SCHEMA, "operation": args.command, "state": str(exc), "effect": "NONE"}
    result.setdefault("state", "READ" if args.command == "readback" else "HOLD")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["state"] in {"READ", "DONE"} else 2


if __name__ == "__main__":
    sys.exit(main())
