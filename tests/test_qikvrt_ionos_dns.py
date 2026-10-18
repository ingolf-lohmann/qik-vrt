# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: Claude (Anthropic).
"""IONOS DNS readback/apply controls against an explicit fake; no live provider."""
from __future__ import annotations

import copy
import io
import json
import unittest
from contextlib import redirect_stdout

from tools import qikvrt_ionos_dns as dns

ZONE = "raumzeitterminal.de"
WEBHOSTING = "217.160.0.52"
ORIGIN = "212.227.147.105"


class FakeAPI(dns.API):
    def __init__(self, records=None, fail_put=False, put_applies=True, change_before_apply=None):
        super().__init__("fixture-prefix.fixture-secret", root="https://fixture.invalid/dns/v1")
        self.records = records if records is not None else [
            {"id": "rec-a", "name": ZONE, "type": "A", "content": WEBHOSTING, "ttl": 3600, "disabled": False},
            {"id": "rec-mx", "name": ZONE, "type": "MX", "content": "mx00.ionos.de", "ttl": 3600, "disabled": False},
            {"id": "rec-www", "name": "www." + ZONE, "type": "CNAME", "content": ZONE, "ttl": 3600, "disabled": False},
        ]
        self.calls = []
        self.fail_put = fail_put
        self.put_applies = put_applies
        self.change_before_apply = change_before_apply

    def request(self, method, path, body=None):
        self.calls.append((method, path, copy.deepcopy(body)))
        if method not in {"GET", "PUT"}:
            raise AssertionError("method outside allowlist")
        if path == "/zones":
            return [{"id": "zone-1", "name": ZONE, "type": "NATIVE"}, {"id": "zone-2", "name": "other.de"}]
        if path.startswith("/zones/zone-1?"):
            if self.change_before_apply and sum(1 for c in self.calls if c[0] == "GET" and "?" in c[1]) == 1:
                self.change_before_apply(self.records)
            return {"id": "zone-1", "name": ZONE, "records": copy.deepcopy(self.records)}
        if method == "PUT" and path.startswith("/zones/zone-1/records/"):
            record_id = path.rsplit("/", 1)[1]
            if self.put_applies:
                for r in self.records:
                    if r["id"] == record_id:
                        r.update(content=body["content"], ttl=body["ttl"], disabled=body["disabled"])
            if self.fail_put:
                raise dns.DNSHold("HOLD_IONOS_DNS_HTTP_504")
            return None
        raise AssertionError("unexpected path " + path)


def puts(api):
    return [c for c in api.calls if c[0] == "PUT"]


class ReadbackTests(unittest.TestCase):
    def test_readback_is_get_only_and_filters_apex_routing_records(self):
        api = FakeAPI()
        receipt = dns.readback(api, ZONE + ".")
        self.assertEqual(receipt["effect"], "NONE")
        self.assertEqual([r["content"] for r in receipt["apex_records"]], [WEBHOSTING])
        self.assertEqual(receipt["apex_records_sha256"], dns.digest(receipt["apex_records"]))
        self.assertEqual(puts(api), [])

    def test_key_never_appears_in_receipt(self):
        api = FakeAPI()
        out = json.dumps(dns.readback(api, ZONE))
        self.assertNotIn("fixture-secret", out)

    def test_missing_or_malformed_key_holds(self):
        for key in ("", "nodot", "has space.x"):
            with self.assertRaises(dns.DNSHold):
                dns.API(key)


class ApplyTests(unittest.TestCase):
    def bound(self, api):
        return dns.readback(api, ZONE)["apex_records_sha256"]

    def test_update_single_apex_a_and_verify_by_readback(self):
        api = FakeAPI()
        receipt = dns.apply(api, ZONE, ORIGIN, self.bound(api))
        self.assertEqual(receipt["state"], "DONE")
        self.assertEqual(receipt["effect"], "PUT_ONE_APEX_A_RECORD")
        self.assertEqual(len(puts(api)), 1)
        self.assertEqual(puts(api)[0][1], "/zones/zone-1/records/rec-a")
        self.assertEqual(puts(api)[0][2], {"content": ORIGIN, "ttl": 3600, "disabled": False})
        untouched = {r["id"]: r["content"] for r in api.records}
        self.assertEqual(untouched["rec-mx"], "mx00.ionos.de")
        self.assertEqual(untouched["rec-www"], ZONE)

    def test_already_target_is_noop_without_write(self):
        api = FakeAPI()
        api.records[0]["content"] = ORIGIN
        receipt = dns.apply(api, ZONE, ORIGIN, self.bound(api))
        self.assertEqual((receipt["state"], receipt["effect"]), ("DONE", "NONE"))
        self.assertEqual(puts(api), [])

    def test_stale_expected_digest_refuses_without_write(self):
        api = FakeAPI()
        with self.assertRaisesRegex(dns.DNSHold, "HOLD_APEX_RECORDS_CHANGED_SINCE_READBACK"):
            dns.apply(api, ZONE, ORIGIN, "0" * 64)
        self.assertEqual(puts(api), [])

    def test_concurrent_change_between_readback_and_apply_refuses(self):
        api = FakeAPI()
        expected = self.bound(api)
        api.records[0]["content"] = "203.0.113.9"
        with self.assertRaisesRegex(dns.DNSHold, "CHANGED_SINCE_READBACK"):
            dns.apply(api, ZONE, ORIGIN, expected)
        self.assertEqual(puts(api), [])

    def test_aaaa_or_cname_at_apex_holds(self):
        for extra in ({"id": "rec-6", "name": ZONE, "type": "AAAA", "content": "2001:db8::1", "ttl": 3600},
                      {"id": "rec-c", "name": ZONE, "type": "CNAME", "content": "x.example", "ttl": 3600}):
            api = FakeAPI()
            api.records.append(dict(extra, disabled=False))
            with self.assertRaisesRegex(dns.DNSHold, "HOLD_APEX_AAAA_OR_CNAME_PRESENT"):
                dns.apply(api, ZONE, ORIGIN, self.bound(api))
            self.assertEqual(puts(api), [])

    def test_multiple_or_missing_a_records_hold(self):
        api = FakeAPI()
        api.records.append({"id": "rec-a2", "name": ZONE, "type": "A", "content": "198.51.100.7", "ttl": 3600, "disabled": False})
        with self.assertRaisesRegex(dns.DNSHold, "HOLD_APEX_A_RECORD_NOT_SINGLE"):
            dns.apply(api, ZONE, ORIGIN, self.bound(api))
        api = FakeAPI(records=[])
        with self.assertRaisesRegex(dns.DNSHold, "HOLD_APEX_A_RECORD_NOT_SINGLE"):
            dns.apply(api, ZONE, ORIGIN, self.bound(api))

    def test_non_public_target_refused(self):
        api = FakeAPI()
        for target in ("10.0.0.1", "127.0.0.1", "192.168.1.1", "0.0.0.0", "not-an-ip", "::1"):
            with self.assertRaises(dns.DNSHold):
                dns.apply(api, ZONE, target, self.bound(api))
        self.assertEqual(puts(api), [])

    def test_uncertain_put_is_decided_only_by_readback(self):
        api = FakeAPI(fail_put=True, put_applies=True)
        receipt = dns.apply(api, ZONE, ORIGIN, self.bound(api))
        self.assertEqual(receipt["effect"], "PUT_OUTCOME_UNKNOWN")
        self.assertEqual(receipt["state"], "DONE")
        api = FakeAPI(fail_put=True, put_applies=False)
        receipt = dns.apply(api, ZONE, ORIGIN, self.bound(api))
        self.assertEqual(receipt["state"], "HOLD_READBACK_MISMATCH")
        self.assertEqual(len(puts(api)), 1, "no retry of an uncertain write")

    def test_cli_exit_codes(self):
        with redirect_stdout(io.StringIO()) as out:
            code = dns.main(["readback", "--zone", ZONE], env={})
        self.assertEqual(code, 2)
        self.assertIn("HOLD_IONOS_DNS_API_KEY_REQUIRED", out.getvalue())


if __name__ == "__main__":
    unittest.main()
