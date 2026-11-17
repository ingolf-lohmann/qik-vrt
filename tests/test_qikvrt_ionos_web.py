# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Whole-zone apex/www cutover with preserved mail and service side effects."""
import copy
import unittest
from tools import qikvrt_ionos_dns as dns
from tests.test_qikvrt_ionos_dns import FakeAPI as ApexFakeAPI, ZONE, ORIGIN, WEBHOSTING, puts


class FakeAPI(ApexFakeAPI):
    def request(self, method, path, body=None):
        if method == "GET" and path == "/zones/zone-1":
            self.calls.append((method, path, body))
            return {"records": copy.deepcopy(self.records)}
        return super().request(method, path, body)


class WebCutoverTests(unittest.TestCase):
    def apply(self, api, ipv6=False):
        before = dns.web_readback(api, ZONE)
        return dns.web_apply(api, ZONE, ORIGIN, before["web_records_sha256"],
                             disable_web_aaaa=ipv6)

    def test_full_snapshot_includes_www_mail_and_redirect_txt(self):
        api = FakeAPI()
        api.records.append({"id": "redirect", "name": "_redirect." + ZONE,
                            "type": "TXT", "content": "fixture-old-forwarding",
                            "ttl": 3600, "disabled": False})
        result = dns.web_readback(api, ZONE)
        self.assertEqual(len(result["web_records"]), 4)
        self.assertEqual(puts(api), [])

    def test_existing_www_alias_is_preserved_and_only_apex_changes(self):
        api = FakeAPI()
        before = copy.deepcopy(api.records[1:])
        result = self.apply(api)
        self.assertEqual(result["state"], "DNS_ROUTING_VERIFIED")
        self.assertEqual(api.records[1:], before)
        self.assertEqual(len(puts(api)), 1)
        self.assertFalse(result["hosting_setting_removed"])
        self.assertFalse(result["public_https_verified"])

    def test_www_a_record_is_cut_over_too(self):
        api = FakeAPI()
        api.records[2].update(type="A", content=WEBHOSTING)
        result = self.apply(api)
        self.assertEqual(result["state"], "DNS_ROUTING_VERIFIED")
        self.assertEqual(api.records[2]["content"], ORIGIN)
        self.assertEqual(len(puts(api)), 2)

    def test_www_alias_to_another_site_changes_to_apex(self):
        api = FakeAPI()
        api.records[2]["content"] = "old-site.invalid"
        self.assertEqual(self.apply(api)["state"], "DNS_ROUTING_VERIFIED")
        self.assertEqual(api.records[2]["content"], ZONE)

    def test_all_ipv6_routes_need_explicit_opt_in_before_any_write(self):
        api = FakeAPI()
        api.records.append({"id": "v6", "name": ZONE, "type": "AAAA",
                            "content": "2001:db8::1", "ttl": 3600, "disabled": False})
        with self.assertRaisesRegex(dns.DNSHold, "EXPLICIT_CUTOVER"):
            self.apply(api)
        self.assertEqual(puts(api), [])
        self.assertEqual(self.apply(api, ipv6=True)["state"], "DNS_ROUTING_VERIFIED")
        self.assertTrue(api.records[-1]["disabled"])

    def test_concurrent_mail_change_invalidates_whole_zone_pin(self):
        api = FakeAPI()
        before = dns.web_readback(api, ZONE)
        api.records[1]["content"] = "new-mail.invalid"
        with self.assertRaisesRegex(dns.DNSHold, "ZONE_CHANGED"):
            dns.web_apply(api, ZONE, ORIGIN, before["web_records_sha256"])
        self.assertEqual(puts(api), [])

    def test_documented_service_side_effect_stops_further_writes(self):
        class ServiceAPI(FakeAPI):
            def request(self, method, path, body=None):
                result = super().request(method, path, body)
                if method == "PUT":
                    self.records[1]["disabled"] = True
                return result
        api = ServiceAPI()
        api.records[2].update(type="A", content=WEBHOSTING)
        result = self.apply(api)
        self.assertEqual(result["state"], "HOLD_WEB_ZONE_UNEXPECTED_CHANGE")
        self.assertEqual(len(puts(api)), 1)
        self.assertTrue(next(r for r in result["after_records"] if r["id"] == "rec-mx")["disabled"])

    def test_uncertain_put_uses_readback_and_never_resends(self):
        api = FakeAPI(fail_put=True)
        result = self.apply(api)
        self.assertEqual(result["state"], "DNS_ROUTING_VERIFIED")
        self.assertEqual(result["writes"][0]["outcome"], "PUT_OUTCOME_UNKNOWN")
        self.assertEqual(len(puts(api)), 1)

    def test_missing_or_conflicting_www_refuses_without_write(self):
        for records in (FakeAPI().records[:2], FakeAPI().records + [
                {"id": "www-a", "name": "www." + ZONE, "type": "A", "content": WEBHOSTING,
                 "ttl": 3600, "disabled": False}]):
            api = FakeAPI(records=records)
            with self.assertRaises(dns.DNSHold):
                self.apply(api)
            self.assertEqual(puts(api), [])

    def test_unavailable_readback_preserves_unknown_effect_without_retry(self):
        class Unavailable(FakeAPI):
            def request(self, method, path, body=None):
                if method == "GET" and any(c[0] == "PUT" for c in self.calls):
                    raise dns.DNSHold("HOLD_FIXTURE_OBSERVER_UNAVAILABLE")
                return super().request(method, path, body)
        api = Unavailable()
        result = self.apply(api)
        self.assertEqual(result["state"], "HOLD_WEB_READBACK_UNAVAILABLE")
        self.assertEqual(len(puts(api)), 1)


if __name__ == "__main__":
    unittest.main()
