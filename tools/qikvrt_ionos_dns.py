#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: Claude (Anthropic); OpenAI Codex (IPv4 cutover, 2026-10-26).
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
- ``apply --disable-apex-aaaa`` explicitly admits the observed single-A,
  single-AAAA IPv4 cutover. It preserves the IPv6 record disabled, verifies
  every step and stops on drift or an unresolved outcome. Default apply
  retains its strict AAAA/CNAME refusal.

The API key is taken from the environment variable IONOS_DNS_API_KEY in the
documented ``<prefix>.<secret>`` form and is never written to any receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
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


def _ipv4_cutover(api: API, zone: str, target: str, before: dict) -> dict:
    """At most two existing-record PUTs; no create, delete or blind resume."""
    records = before["apex_records"]
    active = [r for r in records if not r["disabled"]]
    if any(r["type"] == "CNAME" for r in active):
        raise DNSHold("HOLD_APEX_CNAME_PRESENT")
    ipv6 = [r for r in active if r["type"] == "AAAA"]
    if len(ipv6) > 1:
        raise DNSHold("HOLD_APEX_AAAA_RECORD_NOT_SINGLE")
    if ipv6:
        try:
            ipaddress.IPv6Address(ipv6[0]["content"])
        except ValueError:
            raise DNSHold("HOLD_APEX_AAAA_INVALID") from None
    # Reuse the original single-A planner after the explicitly selected
    # IPv6 policy has been checked. No CNAME or multi-A guard is weakened.
    a_step = plan([r for r in records if r["type"] != "AAAA"], target)
    steps = []
    if a_step["action"] == "UPDATE_A":
        steps.append({"record_id": a_step["record_id"], "type": "A",
                      "content": target, "ttl": a_step["ttl"], "disabled": False})
    for record in ipv6:
        ttl = record["ttl"] if isinstance(record["ttl"], int) and record["ttl"] > 0 else 3600
        steps.append({"record_id": record["id"], "type": "AAAA",
                      "content": record["content"], "ttl": ttl, "disabled": True})
    receipt = {"schema": RECEIPT_SCHEMA, "operation": "apply", "zone": zone,
               "zone_id": before["zone_id"], "target_ipv4": target,
               "before_sha256": before["apex_records_sha256"],
               "disable_apex_aaaa": True,
               "plan": {"action": "IPV4_CUTOVER", "steps": steps},
               "writes": [], "effect": "NONE"}
    expected = [dict(r) for r in records]

    def observe():
        try:
            observed = readback(api, zone)
        except DNSHold as exc:
            receipt.update(state="HOLD_READBACK_UNAVAILABLE", readback_boundary=str(exc))
            return None
        receipt.update(after_records=observed["apex_records"],
                       after_sha256=observed["apex_records_sha256"])
        if observed["zone_id"] != before["zone_id"]:
            receipt["state"] = "HOLD_ROUTING_ZONE_CHANGED"
            return None
        return observed

    for step in steps:
        # A provider-side atomic CAS is not assumed. Reobserve immediately
        # before each scoped PUT and compare the entire bound routing set.
        current = observe()
        if current is None:
            return receipt
        if current["apex_records_sha256"] != digest(expected):
            receipt["state"] = "HOLD_ROUTING_RECORDS_CHANGED"
            return receipt
        body = {key: step[key] for key in ("content", "ttl", "disabled")}
        after_expected = [dict(r) for r in expected]
        for record in after_expected:
            if record["id"] == step["record_id"]:
                record.update(body)
        after_expected.sort(key=lambda r: (r["type"], r["content"], r["id"]))
        write = {"record_id": step["record_id"], "type": step["type"],
                 "before_sha256": current["apex_records_sha256"],
                 "expected_after_sha256": digest(after_expected), "outcome": "PUT_RETURNED"}
        receipt["writes"].append(write)
        path = (f"/zones/{urllib.parse.quote(before['zone_id'], safe='')}/records/"
                f"{urllib.parse.quote(step['record_id'], safe='')}")
        try:
            api.request("PUT", path, body)
        except DNSHold as exc:
            write.update(outcome="PUT_OUTCOME_UNKNOWN", transport_boundary=str(exc))
        receipt["effect"] = ("PUT_OUTCOME_UNKNOWN" if any(
            w["outcome"] == "PUT_OUTCOME_UNKNOWN" for w in receipt["writes"])
            else "PUT_APEX_ROUTING_RECORDS")
        after = observe()
        if after is None:
            return receipt
        write["observed_after_sha256"] = after["apex_records_sha256"]
        if after["apex_records_sha256"] != digest(after_expected):
            receipt["state"] = "HOLD_ROUTING_READBACK_MISMATCH"
            return receipt
        expected = after_expected

    after = observe()
    if after is None:
        return receipt
    active_after = [r for r in after["apex_records"] if not r["disabled"]]
    receipt["state"] = "DONE" if (after["apex_records_sha256"] == digest(expected)
        and len(active_after) == 1 and active_after[0]["type"] == "A"
        and active_after[0]["content"] == target) else "HOLD_ROUTING_READBACK_MISMATCH"
    return receipt


def apply(api: API, zone: str, target: str, expected_sha256: str, *, disable_apex_aaaa: bool = False) -> dict:
    zone = _zone_name(zone)
    target = public_ipv4(target)
    if not (isinstance(expected_sha256, str) and len(expected_sha256) == 64
            and all(c in "0123456789abcdef" for c in expected_sha256)):
        raise DNSHold("HOLD_EXPECTED_RECORDS_SHA256_REQUIRED")
    before = readback(api, zone)
    if before["apex_records_sha256"] != expected_sha256:
        raise DNSHold("HOLD_APEX_RECORDS_CHANGED_SINCE_READBACK")
    if not isinstance(disable_apex_aaaa, bool):
        raise DNSHold("HOLD_DISABLE_APEX_AAAA_MUST_BE_BOOLEAN")
    if disable_apex_aaaa:
        return _ipv4_cutover(api, zone, target, before)
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


def web_readback(api: API, zone: str) -> dict:
    """Bind the whole zone so service side effects cannot disappear in a filter."""
    zone = _zone_name(zone)
    zone_id = find_zone(api, zone)
    detail = api.request("GET", "/zones/" + urllib.parse.quote(zone_id, safe=""))
    if not isinstance(detail, dict) or not isinstance(detail.get("records"), list):
        raise DNSHold("HOLD_IONOS_DNS_ZONE_DETAIL_INVALID")
    records, seen = [], set()
    for source in detail["records"]:
        if not isinstance(source, dict) or not isinstance(source.get("id"), str):
            raise DNSHold("HOLD_WEB_RECORD_SHAPE")
        name = str(source.get("name", "")).lower().rstrip(".")
        if name != zone and not name.endswith("." + zone):
            raise DNSHold("HOLD_WEB_RECORD_OUTSIDE_ZONE")
        if source["id"] in seen:
            raise DNSHold("HOLD_WEB_RECORD_ID_DUPLICATED")
        seen.add(source["id"])
        record = {k: source.get(k) for k in ("id", "type", "content", "ttl")}
        record.update(name=name, disabled=bool(source.get("disabled", False)))
        if "prio" in source:
            record["prio"] = source["prio"]
        records.append(record)
    records.sort(key=lambda r: r["id"])
    return {"schema": RECEIPT_SCHEMA, "operation": "web-readback", "zone": zone,
            "zone_id": zone_id, "web_records": records,
            "web_records_sha256": digest(records), "effect": "NONE"}


def web_plan(records, zone, target, disable_web_aaaa=False):
    """Change only existing apex/www routes; preserve all other DNS records."""
    if type(disable_web_aaaa) is not bool:
        raise DNSHold("HOLD_DISABLE_WEB_AAAA_MUST_BE_BOOLEAN")
    steps = []
    for name in (zone, "www." + zone):
        active = [r for r in records if r["name"] == name and not r["disabled"]
                  and r["type"] in ROUTING_TYPES]
        aliases = [r for r in active if r["type"] == "CNAME"]
        if aliases:
            if name == zone or len(active) != 1:
                raise DNSHold("HOLD_WEB_CNAME_OR_ROUTING_CONFLICT")
            record = aliases[0]
            if str(record["content"]).rstrip(".").lower() != zone:
                steps.append(dict(record, content=zone))
            continue
        a = [r for r in active if r["type"] == "A"]
        ipv6 = [r for r in active if r["type"] == "AAAA"]
        if len(a) != 1:
            raise DNSHold("HOLD_WEB_A_RECORD_NOT_SINGLE")
        if ipv6 and not disable_web_aaaa:
            raise DNSHold("HOLD_WEB_AAAA_REQUIRES_EXPLICIT_CUTOVER")
        if len(ipv6) > 1:
            raise DNSHold("HOLD_WEB_AAAA_RECORD_NOT_SINGLE")
        if a[0]["content"] != target:
            # Reuse the original single-A validator, including its TTL policy.
            planned = plan([a[0]], target)
            steps.append(dict(a[0], content=target, ttl=planned["ttl"]))
        for record in ipv6:
            try:
                ipaddress.IPv6Address(record["content"])
            except (ValueError, TypeError):
                raise DNSHold("HOLD_WEB_AAAA_INVALID") from None
            steps.append(dict(record, disabled=True))
    return steps


def web_apply(api, zone, target, expected_sha256, *, disable_web_aaaa=False):
    zone, target = _zone_name(zone), public_ipv4(target)
    if not re.fullmatch(r"[0-9a-f]{64}", str(expected_sha256)):
        raise DNSHold("HOLD_EXPECTED_RECORDS_SHA256_REQUIRED")
    before = web_readback(api, zone)
    if before["web_records_sha256"] != expected_sha256:
        raise DNSHold("HOLD_WEB_ZONE_CHANGED_SINCE_READBACK")
    steps = web_plan(before["web_records"], zone, target, disable_web_aaaa)
    receipt = {"schema": RECEIPT_SCHEMA, "operation": "web-apply", "zone": zone,
               "target_ipv4": target, "before_sha256": expected_sha256,
               "writes": [], "state": "HOLD", "effect": "NONE",
               "hosting_setting_removed": False, "public_https_verified": False}
    expected = [dict(r) for r in before["web_records"]]

    def observe():
        try:
            current = web_readback(api, zone)
        except DNSHold:
            receipt["state"] = "HOLD_WEB_READBACK_UNAVAILABLE"
            return None
        receipt.update(after_records=current["web_records"],
                       after_sha256=current["web_records_sha256"])
        if current["zone_id"] != before["zone_id"]:
            receipt["state"] = "HOLD_WEB_ZONE_ID_CHANGED"
            return None
        return current

    for step in steps:
        current = observe()
        if current is None:
            return receipt
        if current["web_records_sha256"] != digest(expected):
            receipt["state"] = "HOLD_WEB_ZONE_CHANGED"
            return receipt
        body = {k: step[k] for k in ("content", "ttl", "disabled")}
        if "prio" in step:
            body["prio"] = step["prio"]
        after_expected = [dict(r, **body) if r["id"] == step["id"] else dict(r)
                          for r in expected]
        write = {"record_id": step["id"], "name": step["name"], "outcome": "PUT_RETURNED"}
        receipt["writes"].append(write)
        path = "/zones/" + urllib.parse.quote(before["zone_id"], safe="")
        path += "/records/" + urllib.parse.quote(step["id"], safe="")
        try:
            api.request("PUT", path, body)
        except DNSHold:
            write["outcome"] = "PUT_OUTCOME_UNKNOWN"
        receipt["effect"] = "EXISTING_WEB_ROUTE_PUT"
        after = observe()
        if after is None:
            return receipt
        if after["web_records_sha256"] != digest(after_expected):
            # The IONOS API documents possible deactivation of conflicting
            # service records. Preserve it as a measured partial result, never
            # silently approve it or continue writing against an invented set.
            receipt["state"] = "HOLD_WEB_ZONE_UNEXPECTED_CHANGE"
            return receipt
        expected = after_expected
    after = observe()
    if after and after["web_records_sha256"] == digest(expected):
        receipt["state"] = "DNS_ROUTING_VERIFIED"
    return receipt


def main(argv=None, env=None) -> int:
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("readback")
    r.add_argument("--zone", required=True)
    w = sub.add_parser("web-readback")
    w.add_argument("--zone", required=True)
    w = sub.add_parser("web-apply")
    w.add_argument("--zone", required=True)
    w.add_argument("--target-ipv4", required=True)
    w.add_argument("--expected-records-sha256", required=True)
    w.add_argument("--disable-web-aaaa", action="store_true")
    a = sub.add_parser("apply")
    a.add_argument("--zone", required=True)
    a.add_argument("--target-ipv4", required=True)
    a.add_argument("--expected-records-sha256", required=True)
    a.add_argument("--disable-apex-aaaa", action="store_true",
                   help="Explicitly disable the single bound apex AAAA during a verified IPv4 cutover")
    args = parser.parse_args(argv)
    try:
        api = API(env.get(KEY_ENV, ""))
        if args.command == "web-readback":
            result = web_readback(api, args.zone)
        elif args.command == "web-apply":
            result = web_apply(api, args.zone, args.target_ipv4, args.expected_records_sha256,
                               disable_web_aaaa=args.disable_web_aaaa)
        else:
            result = readback(api, args.zone) if args.command == "readback" else apply(
                api, args.zone, args.target_ipv4, args.expected_records_sha256,
                disable_apex_aaaa=args.disable_apex_aaaa)
    except DNSHold as exc:
        result = {"schema": RECEIPT_SCHEMA, "operation": args.command, "state": str(exc), "effect": "NONE"}
    result.setdefault("state", "READ" if args.command in {"readback", "web-readback"} else "HOLD")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["state"] in {"READ", "DONE", "DNS_ROUTING_VERIFIED"} else 2


if __name__ == "__main__":
    sys.exit(main())
