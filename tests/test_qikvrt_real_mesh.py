#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import asyncio
import json
import pathlib
import socket
import tempfile
import unittest
from unittest.mock import patch

from tools import qikvrt_real_mesh as mesh

SOURCE_HEAD = "a" * 40
SOURCE_TREE = "b" * 40


def unused_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class RealMeshPureContractTests(unittest.TestCase):
    def synthetic_topology(self) -> dict[str, object]:
        nodes = []
        for index, (pair_id, role, repository) in enumerate(
            (
                ("pair-a", "AUTHORITY", "Goldkelch/qik-vrt"),
                ("pair-a", "MIRROR", "ingolf-lohmann/qik-vrt"),
                ("pair-b", "AUTHORITY", "Goldkelch/qik-vrt"),
                ("pair-b", "MIRROR", "ingolf-lohmann/qik-vrt"),
            ),
            start=1,
        ):
            nodes.append(
                {
                    "node_id": f"node-{index}",
                    "pair_id": pair_id,
                    "role": role,
                    "repository": repository,
                    "instance_id": f"instance-{index}",
                    "root_tree_sha": ("a" if role == "AUTHORITY" else "b") * 40,
                    "host": "127.0.0.1",
                    "port": 20000 + index,
                }
            )
        return {
            "schema": mesh.TOPOLOGY_SCHEMA,
            "mesh_id": mesh.MESH_ID,
            "network_scope": mesh.NETWORK_SCOPE,
            "nodes": nodes,
            "links": [
                ["node-1", "node-2"],
                ["node-1", "node-3"],
                ["node-2", "node-3"],
                ["node-2", "node-4"],
                ["node-3", "node-4"],
            ],
        }

    def test_real_mesh_requires_two_complete_authority_mirror_pairs(self) -> None:
        topology = self.synthetic_topology()
        for node in topology["nodes"]:
            node["pair_id"] = "only-pair"
        with self.assertRaisesRegex(
            mesh.MeshRuntimeError,
            "REAL_MESH_REQUIRES_AT_LEAST_TWO_AUTHORITY_MIRROR_PAIRS",
        ):
            mesh.normalize_topology(topology)

    def test_real_mesh_requires_connected_cyclic_peer_graph(self) -> None:
        topology = self.synthetic_topology()
        topology["links"] = [
            ["node-1", "node-2"],
            ["node-2", "node-3"],
            ["node-3", "node-4"],
            ["node-1", "node-2"],
        ]
        with self.assertRaises(mesh.MeshRuntimeError):
            mesh.normalize_topology(topology)

    def test_route_must_cross_pairs_and_follow_declared_links(self) -> None:
        topology = mesh.normalize_topology(self.synthetic_topology())
        with self.assertRaises(mesh.MeshRuntimeError):
            mesh.build_message(
                topology,
                ["node-1", "node-2", "node-1", "node-2"],
                message_id="bad-route",
                nonce="BAD-ROUTE",
                source_head=SOURCE_HEAD,
                source_tree=SOURCE_TREE,
            )


class RealMeshNetworkTests(unittest.TestCase):
    def test_four_process_two_pair_mesh_executes_two_routes_and_restart_replay(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qikvrt-real-mesh-test-") as directory:
            receipt = mesh.run_demo(
                pathlib.Path(directory),
                source_head=SOURCE_HEAD,
                source_tree=SOURCE_TREE,
            )
        self.assertEqual(receipt["schema"], mesh.EXECUTION_RECEIPT_SCHEMA)
        self.assertEqual(receipt["pair_count"], 2)
        self.assertEqual(receipt["node_process_count"], 4)
        self.assertEqual(receipt["transport"], "TCP")
        self.assertEqual(receipt["network_scope"], mesh.NETWORK_SCOPE)
        self.assertTrue(receipt["redundant_path_observed"])
        self.assertTrue(receipt["restart_replay"]["observed"])
        self.assertTrue(receipt["restart_replay"]["same_terminal_receipt"])
        self.assertTrue(receipt["restart_replay"]["ledger_record_count_unchanged"])
        self.assertEqual(len(receipt["routes"]), 2)
        for route in receipt["routes"]:
            with self.subTest(path=route["observation"]["path"]):
                self.assertTrue(route["observation"]["complete_route_reobserved"])
                self.assertEqual(len(route["observation"]["node_observations"]), 4)
                self.assertEqual(route["bounded_effect_ack"]["state"], "EFFECT_ACK_DONE")
                self.assertTrue(route["bounded_effect_ack"]["ordinary_release"])
        claims = receipt["completion_claims"]
        self.assertTrue(claims["real_multi_pair_mesh_runtime_executed"])
        self.assertTrue(claims["independent_tcp_node_processes_observed"])
        self.assertTrue(claims["bounded_loopback_effect_ack_done"])
        for false_claim in (
            "general_effect_ack_done",
            "general_internet_reachability",
            "production_deployment",
            "physical_hardware_execution",
            "authority_mirror_synchronization",
            "authority_mirror_equality_claimed",
            "merge",
            "PASS",
            "FINAL_PASS",
        ):
            self.assertFalse(claims[false_claim])
        self.assertEqual(receipt["effect_ack_scope"], mesh.EFFECT_ACK_SCOPE)
        self.assertEqual(receipt["external_effect"], "NONE")
        self.assertTrue(all(pair["state"] == "DIVERGED" for pair in receipt["pair_states"]))
        projection = dict(receipt)
        stored_hash = projection.pop("receipt_sha256")
        self.assertEqual(stored_hash, mesh.canonical_sha256(projection))

    def test_tamper_rebinding_and_partition_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qikvrt-real-mesh-negative-") as directory:
            with mesh.MeshHarness(pathlib.Path(directory), SOURCE_TREE) as harness:
                assert harness.topology is not None
                route = [
                    "pair-a-authority",
                    "pair-a-mirror",
                    "pair-b-mirror",
                    "pair-b-authority",
                ]
                message = mesh.build_message(
                    harness.topology,
                    route,
                    message_id="negative-route-0001",
                    nonce="NEGATIVE-NONCE-0001",
                    source_head=SOURCE_HEAD,
                    source_tree=SOURCE_TREE,
                )
                first = mesh.node_by_id(harness.topology, route[0])

                tampered = copy.deepcopy(message)
                tampered["payload"]["nonce"] = "TAMPERED"
                tamper_response = mesh.send_message(first["host"], first["port"], tampered)
                self.assertEqual(tamper_response["effect_state"], "EFFECT_ACK_BLOCK")
                self.assertIn("payload_sha256 mismatch", tamper_response["reason"])

                terminal = harness.route_message(message)
                self.assertEqual(terminal["schema"], mesh.TERMINAL_RECEIPT_SCHEMA)
                rebound = mesh.build_message(
                    harness.topology,
                    route,
                    message_id=message["message_id"],
                    nonce="DIFFERENT-BYTES",
                    source_head=SOURCE_HEAD,
                    source_tree=SOURCE_TREE,
                )
                rebound_response = mesh.send_message(first["host"], first["port"], rebound)
                self.assertEqual(rebound_response["effect_state"], "EFFECT_ACK_BLOCK")
                self.assertEqual(
                    rebound_response["reason"],
                    "MESSAGE_ID_REBOUND_TO_DIFFERENT_BYTES",
                )

                partitioned_topology = copy.deepcopy(harness.topology)
                for node in partitioned_topology["nodes"]:
                    if node["node_id"] == route[1]:
                        node["port"] = unused_loopback_port()
                partitioned_topology = mesh.normalize_topology(partitioned_topology)
                partitioned = mesh.build_message(
                    partitioned_topology,
                    route,
                    message_id="partition-route-0001",
                    nonce="PARTITION-NONCE-0001",
                    source_head=SOURCE_HEAD,
                    source_tree=SOURCE_TREE,
                )
                partition_response = mesh.send_message(first["host"], first["port"], partitioned)
                self.assertEqual(partition_response["effect_state"], "EFFECT_ACK_CONTINUE")
                self.assertFalse(partition_response["ordinary_release"])
                self.assertTrue(partition_response["retryable"])
                self.assertIn("NEXT_HOP_UNREACHABLE", partition_response["reason"])


class RealMeshMultitaskingTests(unittest.IsolatedAsyncioTestCase):
    """Exercise the actual event-driven nodes with a controlled blocked hop."""

    def network(self, directory):
        topology = mesh.normalize_topology(RealMeshPureContractTests().synthetic_topology())
        runtimes = {}
        for node in topology["nodes"]:
            fields = {k: node[k] for k in ("node_id", "pair_id", "role", "repository", "instance_id", "root_tree_sha")}
            identity = mesh.NodeIdentity.from_json(fields)
            runtimes[node["port"]] = mesh.NodeRuntime(identity, mesh.AppendOnlyNodeLedger(
                pathlib.Path(directory) / (node["node_id"] + ".jsonl"), node["node_id"]))
        return topology, runtimes

    def message(self, topology, key, route=None, nonce=None):
        return mesh.build_message(topology, route or ["node-1", "node-2", "node-4", "node-3"],
                                  message_id=key, nonce=nonce or key,
                                  source_head=SOURCE_HEAD, source_tree=SOURCE_TREE)

    async def test_crossing_authority_mirror_routes_do_not_deadlock(self):
        with tempfile.TemporaryDirectory() as directory:
            topology, runtimes = self.network(directory)
            both_entered, count = asyncio.Event(), 0
            async def relay(host, port, message, **kwargs):
                nonlocal count
                if message["hop_index"] == 1:
                    count += 1
                    if count == 2:
                        both_entered.set()
                    await both_entered.wait()
                return await runtimes[port].handle(message)
            a = self.message(topology, "a")
            b = self.message(topology, "b", ["node-2", "node-1", "node-3", "node-4"])
            with patch.object(mesh, "send_message_async", side_effect=relay):
                replies = await asyncio.wait_for(asyncio.gather(runtimes[20001].handle(a), runtimes[20002].handle(b)), 1)
            self.assertTrue(all(r["schema"] == mesh.TERMINAL_RECEIPT_SCHEMA for r in replies))
            for runtime in runtimes.values():
                self.assertEqual(set(runtime.ledger.completed), {"a", "b"})
                self.assertEqual(runtime._message_locks, {})

    async def test_cancelled_waiter_duplicate_and_rebound_preserve_one_effect(self):
        with tempfile.TemporaryDirectory() as directory:
            topology, runtimes = self.network(directory)
            entered, release = asyncio.Event(), asyncio.Event()
            async def relay(host, port, message, **kwargs):
                if message["hop_index"] == 1:
                    entered.set()
                    await release.wait()
                return await runtimes[port].handle(message)
            runtime = runtimes[20001]
            original = self.message(topology, "same")
            with patch.object(mesh, "send_message_async", side_effect=relay):
                first = asyncio.create_task(runtime.handle(original))
                try:
                    await asyncio.wait_for(entered.wait(), 1)
                    waiter = asyncio.create_task(runtime.handle(original))
                    await asyncio.sleep(0)
                    waiter.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await waiter
                    replay = asyncio.create_task(runtime.handle(original))
                    rebound = asyncio.create_task(runtime.handle(self.message(topology, "same", nonce="conflict")))
                    await asyncio.sleep(0)
                    self.assertFalse(replay.done())
                    release.set()
                    a, b, conflict = await asyncio.wait_for(asyncio.gather(first, replay, rebound), 1)
                    self.assertEqual(a, b)
                    self.assertEqual(conflict["reason"], "MESSAGE_ID_REBOUND_TO_DIFFERENT_BYTES")
                finally:
                    release.set()
                    await first
            self.assertEqual(runtime._message_locks, {})
            for node in runtimes.values():
                reconstructed = mesh.AppendOnlyNodeLedger(node.ledger.path, node.identity.node_id)
                self.assertEqual(reconstructed.sequence, 2)
                self.assertEqual(set(reconstructed.completed), {"same"})

    async def test_failed_hop_is_retained_without_failing_independent_task(self):
        with tempfile.TemporaryDirectory() as directory:
            topology, runtimes = self.network(directory)
            async def relay(host, port, message, **kwargs):
                if message["message_id"] == "failure":
                    raise mesh.MeshTransportError("controlled unreachable hop")
                return await runtimes[port].handle(message)
            runtime = runtimes[20001]
            with patch.object(mesh, "send_message_async", side_effect=relay):
                failure, success = await asyncio.gather(runtime.handle(self.message(topology, "failure")),
                                                        runtime.handle(self.message(topology, "success")))
            self.assertEqual(failure["schema"], mesh.HOLD_SCHEMA)
            self.assertFalse(failure["ordinary_release"])
            self.assertEqual(success["schema"], mesh.TERMINAL_RECEIPT_SCHEMA)
            loaded = mesh.AppendOnlyNodeLedger(runtime.ledger.path, runtime.identity.node_id)
            self.assertEqual(set(loaded.accepted), {"failure", "success"})
            self.assertEqual(set(loaded.completed), {"success"})
            self.assertIn('"event":"HELD"', runtime.ledger.path.read_text())
            self.assertEqual(runtime._message_locks, {})

    async def test_blocked_message_does_not_block_unrelated_message_on_either_role(self):
        for origin, route in (("node-1", ["node-1", "node-2", "node-4", "node-3"]),
                              ("node-2", ["node-2", "node-1", "node-3", "node-4"])):
            with self.subTest(origin=origin), tempfile.TemporaryDirectory() as directory:
                topology = mesh.normalize_topology(RealMeshPureContractTests().synthetic_topology())
                runtimes = {}
                for node in topology["nodes"]:
                    fields = {k: node[k] for k in ("node_id", "pair_id", "role", "repository", "instance_id", "root_tree_sha")}
                    identity = mesh.NodeIdentity.from_json(fields)
                    runtimes[node["port"]] = mesh.NodeRuntime(identity, mesh.AppendOnlyNodeLedger(
                        pathlib.Path(directory) / (node["node_id"] + ".jsonl"), node["node_id"]))
                entered, release = asyncio.Event(), asyncio.Event()

                async def relay(host, port, message, **kwargs):
                    if message["message_id"] == "blocked" and message["hop_index"] == 1:
                        entered.set()
                        await release.wait()
                    return await runtimes[port].handle(message)

                def message(key):
                    return mesh.build_message(topology, route, message_id=key, nonce=key,
                                              source_head=SOURCE_HEAD, source_tree=SOURCE_TREE)

                runtime = runtimes[mesh.node_by_id(topology, origin)["port"]]
                with patch.object(mesh, "send_message_async", side_effect=relay):
                    blocked = asyncio.create_task(runtime.handle(message("blocked")))
                    try:
                        await asyncio.wait_for(entered.wait(), 1)
                        ready = await asyncio.wait_for(runtime.handle(message("ready")), 0.2)
                        self.assertEqual(ready["schema"], mesh.TERMINAL_RECEIPT_SCHEMA)
                        self.assertFalse(blocked.done())
                        self.assertIn("ready", runtime.ledger.completed)
                        self.assertNotIn("blocked", runtime.ledger.completed)
                    finally:
                        release.set()
                        await asyncio.wait_for(blocked, 1)
                loaded = mesh.AppendOnlyNodeLedger(runtime.ledger.path, origin)
                self.assertEqual(set(loaded.completed), {"blocked", "ready"})


class RealMeshRepositoryContractTests(unittest.TestCase):
    def test_committed_contract_and_workflow_preserve_runtime_boundaries(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        contract = json.loads(
            (root / "state" / "mesh" / "QIKVRT_REAL_MESH_V1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["mesh_id"], mesh.MESH_ID)
        self.assertEqual(contract["minimum_topology"]["pair_count"], 2)
        self.assertEqual(contract["minimum_topology"]["node_process_count"], 4)
        self.assertEqual(contract["transport"]["network_scope"], mesh.NETWORK_SCOPE)
        self.assertFalse(contract["effect_boundary"]["general_effect_ack_done"])
        self.assertFalse(contract["effect_boundary"]["authority_mirror_synchronization"])
        workflow = (
            root / ".github" / "workflows" / "qikvrt_real_mesh.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("schedule:", workflow)
        self.assertIn("QIKVRT real multi-pair Mesh runtime", workflow)
        self.assertIn("tools/qikvrt_real_mesh.py demo", workflow)
        self.assertIn("127.0.0.1", (root / "docs" / "architecture" / "QIKVRT_REAL_MESH_V1.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
