# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Read-only S1 host identity boundary tests; never a productive admission."""
import json
from pathlib import Path
import unittest

from tools import qikvrt_self_host_container as c

ROOT = Path(__file__).resolve().parents[1]
FAULTS = {
    "PROCESS_CRASH", "NODE_LOSS", "NETWORK_PARTITION", "PROVIDER_LOSS",
    "LOST_EFFECT_ACK", "CONCURRENT_TAKEOVER", "STALE_WRITER", "NODE_REJOIN",
}
INVARIANTS = {
    "same_work_unit_after_failover", "preserve_confirmed_effects",
    "no_duplicate_irreversible_effect", "fence_previous_writer",
    "replicate_before_positive_effect_ack", "fresh_authenticated_readback",
    "retain_unavailable_inventory_members", "preserve_original_event_bytes",
    "measure_user_visible_interruption", "hold_writes_without_safe_quorum",
}


class OnlyGetEngine:
    def __init__(self, result=None, error=None):
        self.calls = []
        self.result = result
        self.error = error

    def call(self, method, path, *, binary=False):
        self.calls.append((method, path, binary))
        if method != "GET" or path != "/v1.45/info" or binary is not True:
            raise AssertionError("UNEXPECTED_HOST_OPERATION")
        if self.error is not None:
            raise self.error
        return self.result


def binding():
    return {
        "daemon_id": "fixture-daemon-id",
        "source_head": "a" * 40,
        "source_tree": "b" * 40,
        "image_digest": "sha256:" + "c" * 64,
        "manifest_sha256": "d" * 64,
    }


class VirtualHostNativeBoundaryTests(unittest.TestCase):
    def test_live_mesh_contract_cannot_be_weakened(self):
        source = ROOT / "runtime/self-host/MESH_ACTIVATION.json"
        runtime = json.loads(source.read_bytes())["required_node_runtime"]
        self.assertEqual(set(runtime["required_fault_cases"]), FAULTS)
        self.assertTrue(all(runtime["invariants"].get(i) is True for i in INVARIANTS))
        limits = runtime["acceptance_limits"]
        self.assertEqual(limits["acknowledged_effect_loss"], 0)
        self.assertEqual(limits["duplicate_irreversible_effects"], 0)
        self.assertEqual(limits["concurrent_writers_per_effect"], 1)
        self.assertEqual(limits["quorum_loss_behavior"], "HOLD_WRITES_PRESERVE_CONFIRMED_READS")
        self.assertIsNone(limits["rto_ms"])
        self.assertFalse(runtime["all_node_runtime_verified"])
        self.assertFalse(runtime["native_effect_replication_verified"])
        self.assertFalse(runtime["write_failover_verified"])
        self.assertFalse(runtime["effect_ack_done"])

    def test_native_identity_is_one_get_not_deployment(self):
        host = OnlyGetEngine(b'{"OSType":"linux","ID":"fixture-daemon-id"}')
        outcome = c.host_identity(binding(), "e" * 64, host)
        self.assertEqual(host.calls, [("GET", "/v1.45/info", True)])
        self.assertEqual(outcome["scope"], "HOST_IDENTITY_ONLY")
        self.assertTrue(outcome["host_identity_verified"])
        self.assertFalse(outcome["host_package_verified"])
        self.assertFalse(outcome["public_production_verified"])

    def test_native_identity_rejects_wrong_os_and_daemon(self):
        for response in (
            b'{"OSType":"windows","ID":"fixture-daemon-id"}',
            b'{"OSType":"linux","ID":"other-daemon"}',
            b'{"OSType":"linux"}',
            b'not-json',
        ):
            with self.subTest(response=response):
                host = OnlyGetEngine(response)
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    c.host_identity(binding(), "e" * 64, host)
                self.assertEqual(host.calls, [("GET", "/v1.45/info", True)])

    def test_native_identity_tls_failure_cannot_become_success(self):
        host = OnlyGetEngine(error=OSError("fixture TLS handshake failure"))
        with self.assertRaises(OSError):
            c.host_identity(binding(), "e" * 64, host)
        self.assertEqual(host.calls, [("GET", "/v1.45/info", True)])

    def test_native_boundary_does_not_touch_origin_or_storage(self):
        host = OnlyGetEngine(b'{"OSType":"linux","ID":"fixture-daemon-id"}')
        result = c.host_identity(binding(), "e" * 64, host)
        self.assertNotIn("effect_ack_done", result)
        self.assertNotIn("node_deployed", result)
        self.assertNotIn("container_started", result)
        self.assertEqual(len(host.calls), 1)


if __name__ == "__main__":
    unittest.main()
