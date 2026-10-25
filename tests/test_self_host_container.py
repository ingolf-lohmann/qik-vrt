# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Negative integrity/admission controls; fixture hosts are not deployments."""
import hashlib
import ast
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from tools import qikvrt_self_host_container as c

HEAD, TREE = "a" * 40, "b" * 40


def declaration():
    return {"schema": "qikvrt-s1-linux-host-binding/v1", "repository": c.REPOSITORY,
        "origin": c.ORIGIN, "docker_api": "https://existing-owner-host.example:2376",
        "daemon_id": "exact-daemon-id", "container_name": "qikvrt-s1",
        "state_volume": "qikvrt-state", "config_directory": "/etc/qikvrt/s1",
        "config_sha256": "c" * 64, "node_id": "owner:s1", "manifest_sha256": "d" * 64,
        "loopback_port": 8080, "source_head": HEAD, "source_tree": TREE,
        "image_digest": "sha256:" + "e" * 64}


def archive(path, *, head=HEAD, tree=TREE, tamper=False, user="10001:10001", layer_data=True):
    blobs = {}
    def add(value):
        raw = json.dumps(value, sort_keys=True).encode()
        digest = c.sha(raw)
        blobs["blobs/sha256/" + digest] = raw
        return {"digest": "sha256:" + digest, "size": len(raw)}
    config = add({"architecture": "amd64", "os": "linux", "config": {"User": user,
        "Labels": {"org.opencontainers.image.revision": head, "de.qikvrt.source-tree": tree}}})
    layer = add({"test-layer": layer_data})
    manifest = add({"config": config, "layers": [layer]})
    blobs["oci-layout"] = b'{"imageLayoutVersion":"1.0.0"}'
    blobs["index.json"] = json.dumps({"manifests": [manifest]}).encode()
    if tamper:
        blobs["blobs/sha256/" + layer["digest"][7:]] = b"corruption"
    with tarfile.open(path, "w") as output:
        for name, raw in blobs.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(raw)
            output.addfile(entry, io.BytesIO(raw))


class ExistingContainerRecovery(unittest.TestCase):
    """Engine fixtures establish recovery logic, never a live host/session."""

    class Host:
        def __init__(self, *, running=False, lost_ack=False, start_effect=True):
            self.value = declaration()
            self.config = {key: self.value[key] for key in ('source_head', 'source_tree', 'node_id')}
            self.config.update(source_repository=c.REPOSITORY, host='0.0.0.0', port=8080,
                               state_dir='/var/lib/qikvrt/node', adapter='none', terminal_profile='firefox')
            self.config_raw = json.dumps(self.config).encode()
            self.manifest = b'{"fixture":"exact-admitted-package"}'
            self.value.update(config_sha256=c.sha(self.config_raw), manifest_sha256=c.sha(self.manifest))
            self.image = c.IMAGE + '@' + self.value['image_digest']
            self.identifier = 'f' * 64
            self.live = {'Id': self.identifier,
                'Config': {'Image': self.image, 'User': '10001:10001',
                    'Cmd': ['--config', '/run/qikvrt/config.json', '--manifest-sha256', self.value['manifest_sha256']],
                    'Labels': {'de.qikvrt.repository': c.REPOSITORY,
                               'de.qikvrt.binding-sha256': c.sha(json.dumps(self.value, sort_keys=True).encode())}},
                'State': {'Running': running, 'Status': 'running' if running else 'exited',
                          'Health': {'Status': 'healthy'}},
                'HostConfig': {'ReadonlyRootfs': True, 'CapDrop': ['ALL'],
                    'SecurityOpt': ['no-new-privileges:true'], 'Init': True,
                    'RestartPolicy': {'Name': 'unless-stopped', 'MaximumRetryCount': 0},
                    'ShmSize': 256 * 1024**2, 'Tmpfs': {'/tmp': 'rw,noexec,nosuid,size=768m,mode=1777'},
                    'PortBindings': {'8080/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]}},
                'Mounts': [{'Type': 'volume', 'Name': self.value['state_volume'],
                            'Destination': '/var/lib/qikvrt/node', 'RW': True},
                           {'Type': 'bind', 'Source': self.value['config_directory'],
                            'Destination': '/run/qikvrt', 'RW': False}]}
            self.image_metadata = {'RepoDigests': [self.image], 'Config': {'Labels': {
                'org.opencontainers.image.revision': HEAD, 'de.qikvrt.source-tree': TREE}}}
            self.calls, self.inspect_count = [], 0
            self.lost_ack, self.start_effect, self.drift = lost_ack, start_effect, False
            self.existing, self.concurrent_start = True, False
            self.profile = b'private-profile-fixture-preserved'

        def archive(self, name, raw, mode):
            output = io.BytesIO()
            with tarfile.open(fileobj=output, mode='w') as tar:
                entry = tarfile.TarInfo(name); entry.uid = entry.gid = 10001
                entry.mode, entry.size = mode, len(raw)
                tar.addfile(entry, io.BytesIO(raw))
            return output.getvalue()

        def call(self, method, path, value=None, *, binary=False):
            self.calls.append((method, path))
            if path.endswith('/info'): return {'OSType': 'linux', 'ID': self.value['daemon_id']}
            if '/volumes/' in path:
                return {'Driver': 'local', 'Scope': 'local', 'Labels': {'de.qikvrt.repository': c.REPOSITORY}}
            if '/containers/json?' in path: return [{'Id': self.identifier}] if self.existing else []
            if path.startswith('/v1.45/images/create?') and method == 'POST': return b''
            if path.startswith('/v1.45/containers/create?') and method == 'POST':
                self.created_request = value
                self.existing = True
                return {'Id': self.identifier}
            if '/images/' in path and method == 'GET': return self.image_metadata
            if path.endswith('/archive?path=/run/qikvrt/config.json'):
                return self.archive('config.json', self.config_raw, 0o600)
            if path.endswith('/archive?path=/opt/qikvrt/MANIFEST.json'):
                return self.archive('MANIFEST.json', self.manifest, 0o444)
            if path == '/v1.45/containers/' + self.identifier + '/json':
                self.inspect_count += 1
                if self.drift and self.inspect_count > 1:
                    self.live['Mounts'][0]['Name'] = 'different-state'
                if self.concurrent_start and self.inspect_count > 1:
                    self.live['State'].update(Running=True, Status='running')
                return self.live
            if path == '/v1.45/containers/' + self.identifier + '/start' and method == 'POST':
                if self.start_effect: self.live['State'].update(Running=True, Status='running')
                if self.lost_ack: raise OSError('ambiguous transport fixture')
                return None
            raise AssertionError('Unexpected Engine operation: ' + method + ' ' + path)

    def test_stopped_exact_container_is_started_once_without_recreation_or_profile_access(self):
        host = self.Host()
        result = c.deploy(host.value, host.image, host)
        self.assertEqual(result['state'], 'EXACT_EXISTING_CONTAINER_RESUMED_PENDING_PUBLIC_ACCEPTANCE')
        self.assertEqual(result['container_id'], host.identifier)
        self.assertEqual([x for x in host.calls if x[0] != 'GET'],
                         [('POST', '/v1.45/containers/' + host.identifier + '/start')])
        self.assertEqual(host.profile, b'private-profile-fixture-preserved')
        self.assertFalse(any('profile' in path or 'exec' in path for _, path in host.calls))

    def test_existing_running_exact_container_is_noop(self):
        host = self.Host(running=True)
        self.assertEqual(c.deploy(host.value, host.image, host)['state'], 'EXACT_EXISTING_CONTAINER_NOOP')
        self.assertTrue(all(method == 'GET' for method, _ in host.calls))

    def test_native_image_requires_the_same_explicit_profile_in_pinned_private_config(self):
        for image_profile, config_profile in (("temdd", "temdd"), ("temdd", "firefox"),
                                               ("firefox", "temdd"), ("reference", "temdd")):
            with self.subTest(image=image_profile, config=config_profile):
                host = self.Host()
                host.image_metadata['Config']['Labels']['de.qikvrt.terminal-profile'] = image_profile
                host.config['terminal_profile'] = config_profile
                host.config_raw = json.dumps(host.config).encode()
                host.value['config_sha256'] = c.sha(host.config_raw)
                host.live['Config']['Labels']['de.qikvrt.binding-sha256'] = c.sha(
                    json.dumps(host.value, sort_keys=True).encode())
                if image_profile == config_profile == 'temdd':
                    result = c.deploy(host.value, host.image, host)
                    self.assertEqual(result['terminal_profile'], 'temdd')
                    self.assertEqual([method for method, _ in host.calls if method != 'GET'], ['POST'])
                else:
                    with self.assertRaises(ValueError): c.deploy(host.value, host.image, host)
                    self.assertTrue(all(method == 'GET' for method, _ in host.calls))

    def test_concurrent_start_becomes_noop_before_second_effect(self):
        host = self.Host(); host.concurrent_start = True
        self.assertEqual(c.deploy(host.value, host.image, host)['state'], 'EXACT_EXISTING_CONTAINER_NOOP')
        self.assertTrue(all(method == 'GET' for method, _ in host.calls))

    def test_initial_creation_still_uses_the_original_admitted_specification(self):
        host = self.Host(); host.existing = False
        self.assertEqual(c.deploy(host.value, host.image, host)['state'], 'CONTAINER_STARTED_PENDING_PUBLIC_ACCEPTANCE')
        effects = [path for method, path in host.calls if method == 'POST']
        self.assertEqual(len(effects), 3)
        self.assertTrue(effects[0].startswith('/v1.45/images/create?'))
        self.assertTrue(effects[1].startswith('/v1.45/containers/create?'))
        self.assertTrue(effects[2].endswith('/start'))
        self.assertEqual(host.created_request['User'], '10001:10001')
        self.assertEqual(host.created_request['Cmd'], ['--config', '/run/qikvrt/config.json',
                                                      '--manifest-sha256', host.value['manifest_sha256']])
        config = host.created_request['HostConfig']
        self.assertEqual(config['RestartPolicy'], {'Name': 'unless-stopped'})
        self.assertEqual(config['Mounts'], [
            {'Type': 'volume', 'Source': 'qikvrt-state', 'Target': '/var/lib/qikvrt/node'},
            {'Type': 'bind', 'Source': '/etc/qikvrt/s1', 'Target': '/run/qikvrt', 'ReadOnly': True}])
        self.assertTrue(config['ReadonlyRootfs'])
        self.assertEqual(config['PortBindings'], {'8080/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]})

    def test_resume_lost_ack_uses_running_readback_without_second_start(self):
        host = self.Host(lost_ack=True)
        self.assertIn('RESUMED', c.deploy(host.value, host.image, host)['state'])
        self.assertEqual(sum(method == 'POST' for method, _ in host.calls), 1)

    def test_resume_without_running_effect_never_retries(self):
        host = self.Host(lost_ack=True, start_effect=False)
        with self.assertRaisesRegex(ValueError, 'CONTAINER_START_NOT_OBSERVED'):
            c.deploy(host.value, host.image, host)
        self.assertEqual(sum(method == 'POST' for method, _ in host.calls), 1)

    def test_resume_rejects_storage_routing_or_restart_drift_before_any_write(self):
        for variant in ('volume', 'config-mount', 'writable-config', 'extra-mount', 'public-port',
                        'restart', 'user', 'cmd', 'privileged', 'writable-root', 'paused', 'dead', 'restarting'):
            with self.subTest(variant=variant):
                host = self.Host()
                if variant == 'volume': host.live['Mounts'][0]['Name'] = 'unrelated-state'
                if variant == 'config-mount': host.live['Mounts'][1]['Source'] = '/etc/qikvrt/other'
                if variant == 'writable-config': host.live['Mounts'][1]['RW'] = True
                if variant == 'extra-mount': host.live['Mounts'].append({'Destination': '/extra'})
                if variant == 'public-port': host.live['HostConfig']['PortBindings']['8080/tcp'][0]['HostIp'] = '0.0.0.0'
                if variant == 'restart': host.live['HostConfig']['RestartPolicy']['Name'] = 'no'
                if variant == 'user': host.live['Config']['User'] = '0'
                if variant == 'cmd': host.live['Config']['Cmd'] = ['other-program']
                if variant == 'privileged': host.live['HostConfig']['Privileged'] = True
                if variant == 'writable-root': host.live['HostConfig']['ReadonlyRootfs'] = False
                if variant in ('paused', 'dead', 'restarting'): host.live['State'][variant.capitalize()] = True
                with self.assertRaises(ValueError): c.deploy(host.value, host.image, host)
                self.assertTrue(all(method == 'GET' for method, _ in host.calls))

    def test_resume_rejects_changed_pinned_bytes_and_image_before_any_write(self):
        for variant in ('config', 'manifest', 'digest', 'source'):
            with self.subTest(variant=variant):
                host = self.Host()
                if variant == 'config': host.config_raw += b' '
                if variant == 'manifest': host.manifest += b' '
                if variant == 'digest': host.image_metadata['RepoDigests'] = []
                if variant == 'source': host.image_metadata['Config']['Labels']['de.qikvrt.source-tree'] = '0' * 40
                with self.assertRaises(ValueError): c.deploy(host.value, host.image, host)
                self.assertTrue(all(method == 'GET' for method, _ in host.calls))

    def test_resume_reobserves_mounts_before_start(self):
        host = self.Host(); host.drift = True
        with self.assertRaises(ValueError): c.deploy(host.value, host.image, host)
        self.assertGreater(host.inspect_count, 1)
        self.assertTrue(all(method == 'GET' for method, _ in host.calls))


class ContainerControls(unittest.TestCase):
    def test_original_archive_oci_is_deterministic_and_recovers_exact_pinned_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "original.zip"; original.write_bytes(b"exact-original-archive-fixture")
            expected = {"schema": "qikvrt-s1-frozen-container-carrier/v1", "repository": c.REPOSITORY,
                "source_head": HEAD, "source_tree": TREE, "artifact_id": 11521962723,
                "archive_bytes": original.stat().st_size, "archive_sha256": c.sha(original.read_bytes())}
            outputs = [Path(tmp) / "first.tar", Path(tmp) / "second.tar"]
            results = [c.carrier_archive(expected, original, output) for output in outputs]
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
            self.assertEqual(results[0], c.carrier_archive_check(expected, outputs[1]))
            self.assertEqual(results[0]["archive_sha256"], c.sha(original.read_bytes()))
            self.assertFalse(results[0]["public_production_verified"])
            self.assertFalse(results[0]["durable_ci_source_activated"])
            self.assertFalse(results[0]["predecessor_acceptance_transferred"])
            with self.assertRaisesRegex(ValueError, "CREATE_ONLY_CARRIER_ARCHIVE"):
                c.carrier_archive(expected, original, outputs[0])
            original.write_bytes(b"changed-original-archive-bytes")
            with self.assertRaisesRegex(ValueError, "ORIGINAL_CARRIER_ZIP_INTEGRITY_MISMATCH"):
                c.carrier_archive(expected, original, Path(tmp) / "refused.tar")
            self.assertFalse((Path(tmp) / "refused.tar").exists())

    def test_original_archive_readback_rejects_corruption_and_rehashed_forged_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            original, output = Path(tmp) / "original.zip", Path(tmp) / "wrapper.tar"
            original.write_bytes(b"pinned-original-archive")
            expected = {"schema": "qikvrt-s1-frozen-container-carrier/v1", "repository": c.REPOSITORY,
                "source_head": HEAD, "source_tree": TREE, "artifact_id": 11521962723,
                "archive_bytes": original.stat().st_size, "archive_sha256": c.sha(original.read_bytes())}
            c.carrier_archive(expected, original, output)
            with tarfile.open(output) as archive:
                blobs = {entry.name: archive.extractfile(entry).read() for entry in archive.getmembers()}
            descriptor = json.loads(blobs["index.json"])["manifests"][0]
            manifest_name = "blobs/sha256/" + descriptor["digest"][7:]
            manifest = json.loads(blobs[manifest_name])
            layer_name = "blobs/sha256/" + manifest["layers"][0]["digest"][7:]
            changed_layer = blobs[layer_name].replace(b"pinned-original-archive", b"forged-original-archive")
            def save(values, path):
                with tarfile.open(path, "w") as archive:
                    for name, raw in values.items():
                        entry = tarfile.TarInfo(name); entry.size = len(raw); entry.mode = 0o444
                        archive.addfile(entry, io.BytesIO(raw))
            corrupted = Path(tmp) / "corrupt.tar"
            save({**blobs, layer_name: changed_layer}, corrupted)
            with self.assertRaisesRegex(ValueError, "ARCHIVE_OCI_BLOB_INTEGRITY_MISMATCH"):
                c.carrier_archive_check(expected, corrupted)
            def encode(value):return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
            # Rehash every descriptor and keep the pinned original source labels.
            # Internally coherent transport still cannot replace the original ZIP.
            layer_digest = "sha256:" + c.sha(changed_layer)
            config = encode(c.carrier_archive_config(expected, layer_digest))
            manifest["config"]["digest"], manifest["config"]["size"] = "sha256:" + c.sha(config), len(config)
            manifest["layers"][0]["digest"], manifest["layers"][0]["size"] = layer_digest, len(changed_layer)
            raw_manifest = encode(manifest)
            descriptor["digest"], descriptor["size"] = "sha256:" + c.sha(raw_manifest), len(raw_manifest)
            forged = Path(tmp) / "forged.tar"
            save({"oci-layout": blobs["oci-layout"], "index.json": encode({"schemaVersion": 2, "manifests": [descriptor]}),
                "blobs/sha256/" + c.sha(config): config, "blobs/sha256/" + c.sha(raw_manifest): raw_manifest,
                "blobs/sha256/" + c.sha(changed_layer): changed_layer}, forged)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_CARRIER_ZIP_INTEGRITY_MISMATCH"):
                c.carrier_archive_check(expected, forged)

    def test_smoke_keeps_unprivileged_start_and_requires_independent_persistent_restart(self):
        # Exercise the launcher contract; actual Docker/Firefox remains required
        # by the existing native CI lane, never inferred from these fixtures.
        for profile, variant in ((p, v) for p in ('firefox', 'temdd')
                                 for v in ('valid', 'changed-ledger', 'failed-readback')):
            with self.subTest(profile=profile, variant=variant), tempfile.TemporaryDirectory() as tmp:
                calls, phase = [], {'restart': False}
                name = 'qikvrt-s1-smoke-' + '1' * 16
                network = name + '-net'
                manifest = json.dumps({'source_head': HEAD, 'source_tree': TREE,
                                       'native_terminal_daemon_included': True}).encode()
                client = json.dumps({'state': 'CLIENT_BYTE_READBACK_VERIFIED',
                                     'source_head': HEAD, 'source_tree': TREE, 'effect_ack_done': False}).encode()
                failed = b'{"state":"HOLD_PUBLIC_OR_INDEPENDENT_CLIENT_READBACK","cause":"HOLD_PUBLIC_NODE_HEALTH_CONTRACT","effect_ack_done":false}\n'
                def command(*argv, **kwargs):
                    calls.append(argv)
                    if argv[0] == 'node':
                        if variant == 'failed-readback':
                            raise subprocess.CalledProcessError(20, list(argv), output=failed)
                        return client
                    if argv[:3] == ('docker', 'image', 'inspect'):
                        return json.dumps({'de.qikvrt.terminal-profile': 'temdd'}).encode()
                    if argv[1] == 'inspect':
                        return json.dumps([{'State': {'Running': True}, 'HostConfig': {'NetworkMode': network},
                            'NetworkSettings': {'Ports': {}, 'Networks': {network: {'IPAddress': '172.20.0.2'}}}}]).encode()
                    if argv[1] == 'restart': phase['restart'] = True
                    if 'cat' in argv: return manifest
                    return b''
                def get(url):
                    if url.endswith('/AI/'): return b'<main data-qikvrt-source="node">'
                    if url.endswith('/api/activity'): return json.dumps({'replication': {'source_head': HEAD, 'source_tree': TREE}}).encode()
                    ledger = 'b' * 32 if variant == 'changed-ledger' and phase['restart'] else 'a' * 32
                    return json.dumps({'state': 'NATIVE_TEMDD_READY', 'ledger_id': ledger}).encode()
                with patch.object(c, 'command', side_effect=command), patch.object(c, 'get', side_effect=get), \
                     patch.object(c.uuid, 'uuid4', return_value=SimpleNamespace(hex='1' * 32)), \
                     patch.object(c, 'firefox_image_admission') as firefox, \
                     patch.object(c.subprocess, 'run', return_value=SimpleNamespace(stdout=b'', stderr=b'')), \
                     patch('builtins.print'):
                    if variant == 'valid':
                        result = c.smoke('fixture-image', tmp, profile)
                        self.assertEqual(result['state'], 'CONTAINER_SMOKE_AND_RESTART_VERIFIED')
                        self.assertTrue(result['ledger_identity_preserved'])
                        self.assertFalse(result['public_production_verified'])
                        self.assertEqual(result['terminal_profile'], profile)
                        self.assertEqual(result['firefox_acceptance_in_scope'], profile == 'firefox')
                    elif variant == 'changed-ledger':
                        with self.assertRaisesRegex(ValueError, 'DURABLE_LEDGER_ID_RESTART_MISMATCH'):
                            c.smoke('fixture-image', tmp, profile)
                    else:
                        with self.assertRaises(subprocess.CalledProcessError): c.smoke('fixture-image', tmp, profile)
                        self.assertEqual((Path(tmp)/'smoke-readback-before-restart.stdout').read_bytes(), failed)
                        self.assertFalse(phase['restart'])
                    self.assertEqual(firefox.call_count, int(profile == 'firefox'))
                setup = next(argv[-1] for argv in calls if '-c' in argv)
                self.assertEqual('browser.password' in setup, profile == 'firefox')
                start = next(argv for argv in calls if argv[:3] == ('docker', 'run', '-d'))
                self.assertEqual(start[start.index('--user') + 1], '10001:10001')
                self.assertIn('--read-only', start)
                self.assertEqual(start[start.index('--cap-drop') + 1], 'ALL')
                self.assertEqual(start[start.index('--security-opt') + 1], 'no-new-privileges:true')
                self.assertIn('type=volume,source=' + name + '-state,target=/var/lib/qikvrt/node', start)
                if variant != 'failed-readback':
                    self.assertIn(('docker', 'restart', name), calls)
                    self.assertEqual((Path(tmp)/'smoke-readback-before-restart.stdout').read_bytes(), client)
                    self.assertEqual((Path(tmp)/'smoke-readback-after-restart.stdout').read_bytes(), client)

    def test_isolated_smoke_uses_exact_running_private_bridge_without_port_publication(self):
        network="disposable-ci-net"
        def metadata(address="172.20.0.2", running=True, mode=network):
            return {"State":{"Running":running}, "HostConfig":{"NetworkMode":mode},
                    "NetworkSettings":{"Ports":{}, "Networks":{network:{"IPAddress":address}}}}
        self.assertEqual(c.smoke_origin(metadata(), network), "http://172.20.0.2:8080")
        for value in (metadata(running=False), metadata(mode="host"), metadata(address="8.8.8.8"),
                      metadata(address="127.0.0.1"), metadata(address=""), metadata(address="169.254.1.1")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                c.smoke_origin(value, network)

    def test_oci_checks_all_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "image.tar"
            archive(path)
            self.assertEqual(c.oci(path, HEAD, TREE)["state"], "OCI_BYTES_VERIFIED")
            archive(path, tamper=True)
            with self.assertRaisesRegex(ValueError, "OCI_BLOB_INTEGRITY_MISMATCH"):
                c.oci(path, HEAD, TREE)

    def test_wrong_source_and_privileged_image_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "image.tar"
            archive(path, head="0" * 40)
            with self.assertRaisesRegex(ValueError, "SOURCE_BINDING"):
                c.oci(path, HEAD, TREE)
            archive(path, user="0:0")
            with self.assertRaisesRegex(ValueError, "UNPRIVILEGED"):
                c.oci(path, HEAD, TREE)

    def test_reproducible_oci_descriptor(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.tar", Path(tmp) / "b.tar"
            archive(a); archive(b)
            self.assertEqual(c.oci(a, HEAD, TREE)["image_digest"], c.oci(b, HEAD, TREE)["image_digest"])

    def test_failed_rebuild_retains_original_descriptor_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, receipt = Path(tmp) / "a.tar", Path(tmp) / "b.tar", Path(tmp) / "receipt.json"
            archive(a); archive(b, layer_data="changed")
            args = SimpleNamespace(operation="container-oci-check", oci_archive=a,
                second_oci_archive=b, expected_head=HEAD, expected_tree=TREE, receipt=receipt)
            with self.assertRaisesRegex(ValueError, "INDEPENDENT_OCI_REBUILD_DIGEST_MISMATCH"):
                c.execute(args)
            result = json.loads(receipt.read_bytes())
            self.assertFalse(result["independent_rebuild_digest_equal"])
            self.assertFalse(result["effect_ack_done"])
            self.assertNotEqual(result["layers"], result["independent_rebuild"]["layers"])
            self.assertEqual(result["image_digest"], c.oci(a, HEAD, TREE)["image_digest"])

    def test_carrier_archive_pin_checked_before_unpack_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, output = Path(tmp) / "original.zip", Path(tmp) / "output"
            path.write_bytes(b"unverified predecessor")
            expected = {"schema":"qikvrt-s1-frozen-container-carrier/v1", "repository":c.REPOSITORY,
                        "archive_bytes":path.stat().st_size, "archive_sha256":"0" * 64}
            with self.assertRaisesRegex(ValueError, "ORIGINAL_CARRIER_ZIP_INTEGRITY_MISMATCH"):
                c.carrier_import(expected, path, output)
            self.assertFalse(output.exists())

    def test_expired_carrier_metadata_never_requests_archive(self):
        expected = {"repository":c.REPOSITORY, "artifact_id":11521962723, "archive_bytes":42,
                    "archive_sha256":"0" * 64, "run_id":37710500668, "source_head":HEAD}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,
                {"GITHUB_REPOSITORY":c.REPOSITORY, "GITHUB_TOKEN":"fixture-only"}), \
                patch.object(c, "get", return_value=b'{"expired":true}') as metadata, \
                patch.object(c.urllib.request, "build_opener") as opener:
            path = Path(tmp) / "archive.zip"
            with self.assertRaisesRegex(ValueError, "ARTIFACT_BINDING_MISMATCH_OR_EXPIRED"):
                c.carrier_download(expected, path)
            opener.assert_not_called()
            self.assertFalse(path.exists())
            self.assertEqual(metadata.call_count, 1)


    def test_docker_archive_load_preserves_original_oci_binding(self):
        from textwrap import dedent
        code = (Path(__file__).resolve().parents[1] / ".github/workflows/qikvrt_ci.yml").read_text().split("<<'PYLOAD'\n", 1)[1].split("\n          PYLOAD", 1)[0]
        compiled = compile(dedent(code), "<workflow-PYLOAD>", "exec")
        for variant in ("valid", "config", "layers", "source", "archive"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "container-evidence"; p.mkdir()
                raw = b"TECHNICAL_TEST_ONLY_OCI_PLACEHOLDER"
                (p / "image.oci.tar").write_bytes(raw)
                o = {"independent_rebuild_digest_equal": True, "source_head": HEAD,
                     "source_tree": TREE, "oci_archive_sha256": c.sha(raw),
                     "image_digest": "sha256:" + "e" * 64,
                     "image_config_digest": "sha256:" + "c" * 64,
                     "diff_ids": ["sha256:" + "d" * 64]}
                (p / "oci.json").write_text(json.dumps(o))
                loaded = {"Id": o["image_config_digest"], "RootFS": {"Layers": o["diff_ids"]},
                          "Config": {"Labels": {"org.opencontainers.image.revision": HEAD, "de.qikvrt.source-tree": TREE}}}
                if variant == "config": loaded["Id"] = "sha256:" + "0" * 64
                if variant == "layers": loaded["RootFS"]["Layers"] = ["sha256:" + "0" * 64]
                if variant == "source": loaded["Config"]["Labels"]["de.qikvrt.source-tree"] = "0" * 40
                if variant == "archive": (p / "image.oci.tar").write_bytes(b"CHANGED")
                with patch.dict(os.environ, {"RUNNER_TEMP": tmp}), patch.object(subprocess, "check_output", return_value=json.dumps([loaded])) as inspect, patch("builtins.print"):
                    if variant == "valid":
                        exec(compiled, {})
                        result = json.loads((p / "load.json").read_bytes())
                        self.assertEqual(result["docker_image_id"], o["image_config_digest"])
                        self.assertEqual(result["original_oci_image_digest"], o["image_digest"])
                        self.assertFalse(result["public_production_verified"])
                        self.assertFalse(result["effect_ack_done"])
                    else:
                        with self.assertRaises(AssertionError): exec(compiled, {})
                        self.assertFalse((p / "load.json").exists())
                    if variant == "archive": inspect.assert_not_called()


    def test_context_excludes_git_auth_and_untracked_private_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"; root.mkdir()
            def git(*args):
                return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL)
            git("init"); git("config", "user.name", "Fixture"); git("config", "user.email", "fixture@example.test")
            (root / "source.txt").write_bytes(b"original\n")
            git("add", "source.txt"); git("commit", "-m", "fixture")
            git("config", "http.https://github.com/.extraheader", "DO_NOT_EXPORT_AUTH")
            (root / "private.token").write_text("DO_NOT_EXPORT_PRIVATE_STATE")
            output = Path(tmp) / "context"
            result = c.context(root, output)
            self.assertFalse((output / "private.token").exists())
            self.assertNotIn("DO_NOT_EXPORT_AUTH", (output / ".git/config").read_text())
            self.assertEqual(result["source_head"], git("rev-parse", "HEAD").decode().strip())
            self.assertFalse(result["credential_material_included"])

    def test_binding_rejects_wrong_origin_credentials_or_unconfirmed_fields(self):
        for key, bad in [("origin", "https://another.example"), ("docker_api", "http://host:2375"),
                         ("docker_api", "https://user:password@host:2376"),
                         ("config_directory", "/etc/qikvrt/../secret"), ("loopback_port", True)]:
            value = declaration(); value[key] = bad
            raw = json.dumps(value).encode()
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                c.binding(raw, c.sha(raw), c.IMAGE + "@" + value["image_digest"])
        value = declaration(); value["domain_purchase"] = True
        raw = json.dumps(value).encode()
        with self.assertRaises(ValueError):
            c.binding(raw, c.sha(raw), c.IMAGE + "@" + value["image_digest"])

    def test_independent_pin_and_exact_digest_required(self):
        value = declaration(); raw = json.dumps(value).encode()
        with self.assertRaisesRegex(ValueError, "PIN_REQUIRED"):
            c.binding(raw, "0" * 64, c.IMAGE + "@" + value["image_digest"])
        with self.assertRaisesRegex(ValueError, "VERSIONED_IMAGE"):
            c.binding(raw, c.sha(raw), c.IMAGE + ":latest")

    def test_untrusted_branch_never_reads_production_credentials(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "fixture", "GITHUB_REPOSITORY": c.REPOSITORY,
                                    "GITHUB_REF": "refs/heads/unreviewed"}), patch.object(c, "get") as get:
            with self.assertRaisesRegex(ValueError, "TRUSTED_MAIN"):
                c.production_gate(HEAD)
            get.assert_not_called()

    def test_wrong_host_causes_no_mutation(self):
        class Host:
            def __init__(self): self.calls = []
            def call(self, method, path, value=None):
                self.calls.append(method)
                return {"OSType": "linux", "ID": "unrelated-host"}
        host = Host(); value = declaration()
        with self.assertRaisesRegex(ValueError, "HOST_MISMATCH"):
            c.deploy(value, c.IMAGE + "@" + value["image_digest"], host)
        self.assertEqual(host.calls, ["GET"])

    def test_foreign_or_ephemeral_volume_causes_no_mutation(self):
        class Host:
            def __init__(self): self.calls = []
            def call(self, method, path, value=None):
                self.calls.append(method)
                if path.endswith("info"): return {"OSType": "linux", "ID": "exact-daemon-id"}
                return {"Driver": "local", "Scope": "local", "Labels": {"de.qikvrt.repository": c.REPOSITORY},
                        "Options": {"type": "tmpfs"}}
        host = Host(); value = declaration()
        with self.assertRaisesRegex(ValueError, "PERSISTENT_OWNER_VOLUME"):
            c.deploy(value, c.IMAGE + "@" + value["image_digest"], host)
        self.assertEqual(host.calls, ["GET", "GET"])

    def test_existing_different_writer_not_stopped_or_replaced(self):
        class Host:
            def __init__(self): self.calls = []
            def call(self, method, path, value=None):
                self.calls.append(method)
                if path.endswith("info"): return {"OSType": "linux", "ID": "exact-daemon-id"}
                if "/volumes/" in path: return {"Driver": "local", "Scope": "local", "Labels": {"de.qikvrt.repository": c.REPOSITORY}}
                if "containers/json" in path: return [{"Id": "f" * 64}]
                return {"Config": {"Image": "old-image"}, "State": {"Running": True}}
        host = Host(); value = declaration()
        with self.assertRaisesRegex(ValueError, "REQUIRES_S1_MIGRATION"):
            c.deploy(value, c.IMAGE + "@" + value["image_digest"], host)
        self.assertTrue(all(method == "GET" for method in host.calls))

    def test_unconfirmed_public_origin_refused_before_network(self):
        value = declaration(); value["origin"] = "https://unrelated.example"
        with patch.object(c, "get") as get:
            with self.assertRaisesRegex(ValueError, "EXACT_PRODUCT_ORIGIN"):
                c.public_readback(value, "/unused")
            get.assert_not_called()

    def test_public_reader_binds_the_delivered_profile_without_claiming_firefox_for_temdd(self):
        for profile, observed_profile in (("temdd", "temdd"), ("firefox", "firefox"),
                                          ("temdd", "firefox")):
            with self.subTest(profile=profile, observed=observed_profile):
                value = dict(declaration(), terminal_profile=profile)
                def read(url):
                    if url.endswith('/api/runtime'):
                        runtime = {k: value[k] for k in ('source_head', 'source_tree',
                                   'manifest_sha256', 'config_sha256', 'node_id')}
                        return json.dumps(dict(runtime, terminal_profile=observed_profile)).encode()
                    if url.endswith('/api/terminal'):
                        return json.dumps({'state': 'NATIVE_TEMDD_READY',
                                           'manifest_sha256': value['manifest_sha256']}).encode()
                    return b'public-response-fixture'
                with patch.object(c, 'get', side_effect=read), \
                     patch.object(c, 'command', return_value=b'independent-reader-fixture') as reader:
                    if profile == observed_profile:
                        result = c.public_readback(value, '/fixture')
                        self.assertEqual(result['terminal_profile'], profile)
                        self.assertEqual(result['firefox_acceptance_in_scope'], profile == 'firefox')
                        self.assertFalse(result['native_multi_node_acceptance'])
                        reader.assert_called_once()
                    else:
                        with self.assertRaisesRegex(ValueError, 'PUBLIC_TERMINAL_PROFILE_MISMATCH'):
                            c.public_readback(value, '/fixture')
                        reader.assert_not_called()

    def test_independent_reader_reports_only_typed_guard_codes(self):
        script = """
import {verifyClient, readbackFailure} from './tools/qikvrt_mesh_monitor_readback.mjs';
let guarded;
try { await verifyClient({public_url:'http://fixture.invalid',standalone:true},
  async () => ({status:503})); } catch(error) { guarded = readbackFailure(error); }
console.log(JSON.stringify({guarded,
  arbitrary:readbackFailure(new Error('private-token-and-response-body')),
  forged:readbackFailure(new Error('HOLD_PUBLIC_HTTP'))}));
"""
        raw = subprocess.check_output(["node", "--input-type=module", "-e", script],
                                      cwd=Path(__file__).resolve().parents[1], timeout=30)
        result = json.loads(raw)
        self.assertEqual(result["guarded"]["cause"], "HOLD_PUBLIC_HTTP")
        for key in ("arbitrary", "forged"):
            self.assertEqual(result[key]["cause"], "READBACK_UNCLASSIFIED_ERROR")
        self.assertNotIn(b"private-token", raw)
        self.assertTrue(all(value["effect_ack_done"] is False for value in result.values()))

    def test_tls_redirect_not_followed(self):
        with self.assertRaisesRegex(ValueError, "REDIRECT_FORBIDDEN"):
            c.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example")

    def test_final_image_requires_signed_default_policy_in_both_restart_phases(self):
        # These are negative receipt fixtures, not a native browser witness.
        import copy
        xpi=b'exact-signed-xpi-fixture'
        phase={"minimum_satisfied":True,"policy_active":True,"background_registered":True,
            "temporary_installation_used":False,"signatures_required":True,"mozilla_signed":True,
            "addon":{"isCompatible":True,"isActive":True,"appDisabled":False,
                "userDisabled":False,"temporarilyInstalled":False}}
        good={"state":"EXTENSION_ACTIVATION_AND_RESTART_VERIFIED","strict_min_version":"158.0",
            "firefox_version_output":"Mozilla Firefox 158.0","signed_production_package_verified":True,
            "extension_activation_verified":True,"xpi_sha256":c.sha(xpi),
            "profiles":{"default_signing_policy":[phase,copy.deepcopy(phase)]}}
        for variant in ('valid','old-firefox','unsigned','disabled-after-restart','temporary',
                        'signatures-disabled','missing-restart','changed-xpi'):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as tmp:
                receipt=copy.deepcopy(good);calls=[]
                if variant=='old-firefox':receipt['firefox_version_output']='Mozilla Firefox 157.0'
                if variant=='unsigned':receipt['signed_production_package_verified']=False
                if variant=='disabled-after-restart':receipt['profiles']['default_signing_policy'][1]['addon']['isActive']=False
                if variant=='temporary':receipt['profiles']['default_signing_policy'][0]['temporary_installation_used']=True
                if variant=='signatures-disabled':receipt['profiles']['default_signing_policy'][0]['signatures_required']=False
                if variant=='missing-restart':receipt['profiles']['default_signing_policy'].pop()
                if variant=='changed-xpi':receipt['xpi_sha256']='0'*64
                def command(*args,**kwargs):
                    calls.append(args)
                    if 'python3' in args:
                        (Path(tmp)/'firefox-extension/extension-installation.json').write_text(json.dumps(receipt))
                        return b''
                    return xpi
                with patch.object(c,'command',side_effect=command):
                    if variant=='valid':self.assertEqual(c.firefox_image_admission('exact-image',tmp),receipt)
                    else:
                        with self.assertRaises(ValueError):c.firefox_image_admission('exact-image',tmp)
                invocation=calls[0]
                self.assertEqual(invocation[invocation.index('--network')+1],'none')
                self.assertEqual(invocation[invocation.index('--user')+1],'10001:10001')
                self.assertIn('--read-only',invocation)
                self.assertEqual(invocation[invocation.index('--firefox-package')+1],'firefox')

    def test_native_production_is_independent_of_firefox_but_keeps_host_and_public_gates(self):
        text=(Path(__file__).resolve().parents[1]/'.github/workflows/qikvrt_ci.yml').read_text()
        container=text.split('  container:\n',1)[1].split('  container_publish:\n',1)[0]
        publication=text.split('  container_publish:\n',1)[1].split('  container_deploy:\n',1)[0]
        self.assertIn('needs: test',container)
        self.assertNotIn('s1_firefox_extension',container+publication)
        self.assertIn('--target production-terminal',container)
        self.assertIn('QIKVRT_TERMINAL_PROFILE=temdd',container)
        self.assertIn('--terminal-profile temdd',container)
        self.assertNotIn('qikvrt-signed-extension',container)
        self.assertIn('needs: [test, container]',publication)
        self.assertIn("github.ref == 'refs/heads/main'",publication)
        self.assertIn('environment: qikvrt-production',publication)
        self.assertIn('container-production-gate',publication)
        self.assertIn('container-carrier-archive-check',publication)
        self.assertIn('carrier-registry-readback.json',publication)
        deployment=text.split('  container_deploy:\n',1)[1].split('  container_public_readback:\n',1)[0]
        self.assertIn('needs: [container, container_publish]',deployment)
        self.assertIn('secrets.QIKVRT_LINUX_HOST_KEY',deployment)
        self.assertIn('container-deploy',deployment)
        self.assertIn('container-readback',text.split('  container_public_readback:\n',1)[1])

    def test_native_scope_cannot_silently_fall_back_to_an_unsigned_browser_image(self):
        for variant in ('browser-package', 'missing-native', 'wrong-label'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as tmp:
                manifest = {'native_terminal_daemon_included': variant != 'missing-native'}
                if variant == 'browser-package': manifest['browser_runtime'] = {}
                def command(*args):
                    if args[:3] == ('docker', 'image', 'inspect'):
                        return json.dumps({'de.qikvrt.terminal-profile':
                                           'firefox' if variant == 'wrong-label' else 'temdd'}).encode()
                    self.assertIn('cat', args)
                    return json.dumps(manifest).encode()
                with patch.object(c, 'command', side_effect=command), \
                     patch.object(c, 'firefox_image_admission') as firefox:
                    with self.assertRaisesRegex(ValueError, 'EXACT_NATIVE_ONLY_IMAGE_REQUIRED'):
                        c.smoke('fixture-image', tmp, 'temdd')
                    firefox.assert_not_called()
        with patch.object(c, 'command') as command:
            with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
                c.smoke('fixture-image', tmp, 'reference')
            command.assert_not_called()

    def firefox_gate_selected(self, profile, *, event='pull_request', sign=False,
                              readback=False, signed_binding=''):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_ci.yml').read_text()
        job = workflow.split('  s1_firefox_extension:\n', 1)[1].split('\n  container:', 1)[0]
        expression = next(x.strip()[4:] for x in job.splitlines() if x.strip().startswith('if: '))
        expression = expression.removeprefix('${{').removesuffix('}}').strip()
        expression = expression.replace('always()', 'True').replace('&&', ' and ').replace('||', ' or ')
        parsed = ast.parse(expression, mode='eval')
        allowed = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.Compare, ast.Eq,
                   ast.NotEq, ast.Attribute, ast.Name, ast.Load, ast.Constant)
        self.assertTrue(all(isinstance(x, allowed) for x in ast.walk(parsed)))
        self.assertTrue(all(not x.attr.startswith('_') for x in ast.walk(parsed)
                            if isinstance(x, ast.Attribute)))
        scope = {'needs': SimpleNamespace(container=SimpleNamespace(outputs=SimpleNamespace(
                    terminal_profile=profile)), amo_unlisted=SimpleNamespace(
                    outputs=SimpleNamespace(signed_binding=signed_binding))),
                 'github': SimpleNamespace(event_name=event),
                 'inputs': SimpleNamespace(amo_sign_unlisted=sign, amo_readback_only=readback)}
        return eval(compile(parsed, '<existing-firefox-job-scope>', 'eval'),
                    {'__builtins__': {}}, scope)

    def test_native_only_ci_does_not_require_deferred_firefox_admission(self):
        for event in ('push', 'pull_request', 'workflow_dispatch'):
            with self.subTest(event=event):
                self.assertFalse(self.firefox_gate_selected('temdd', event=event))
        self.assertFalse(self.firefox_gate_selected('temdd', event='push', sign=True))

    def test_browser_and_existing_explicit_signing_paths_keep_firefox_admission(self):
        self.assertTrue(self.firefox_gate_selected('firefox'))
        self.assertTrue(self.firefox_gate_selected('temdd', event='workflow_dispatch', sign=True))
        self.assertTrue(self.firefox_gate_selected('temdd', event='workflow_dispatch', readback=True))
        self.assertTrue(self.firefox_gate_selected('temdd', signed_binding='original-bound-package'))

    def image_receipt(self, smoke, output, *, expect_failure=False):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_ci.yml').read_text()
        step = workflow.split('      - name: Bind exact image/package and CI execution identities\n', 1)[1]
        code = textwrap.dedent(step.split("<<'PY'\n", 1)[1].split('\n          PY', 1)[0])
        oci = {'source_head': HEAD, 'source_tree': TREE, 'independent_rebuild_digest_equal': True,
               'image_digest': 'sha256:' + 'c' * 64}
        (output / 'oci.json').write_text(json.dumps(oci))
        (output / 'smoke.json').write_text(json.dumps(smoke))
        result = output / 'github-output'
        def git(command, **_kwargs):
            return HEAD if command[1] == 'rev-parse' else ''
        with patch.dict(os.environ, {'EVIDENCE': str(output), 'GITHUB_OUTPUT': str(result),
                'GITHUB_REPOSITORY': c.REPOSITORY, 'GITHUB_RUN_ID': '1', 'GITHUB_RUN_ATTEMPT': '1'}), \
             patch.object(subprocess, 'check_output', side_effect=git), \
             patch('sys.stdout', new=io.StringIO()):
            if expect_failure:
                with self.assertRaises(AssertionError): exec(code, {})
                self.assertFalse(result.exists())
                return
            exec(code, {})
        return json.loads((output / 'ci.json').read_bytes()), dict(
            line.split('=', 1) for line in result.read_text().splitlines())

    def test_ci_receipt_exports_verified_smoke_profile(self):
        for profile in ('temdd', 'firefox'):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as temporary:
                smoke = {'source_head': HEAD, 'source_tree': TREE, 'manifest_sha256': 'd' * 64,
                         'state': 'CONTAINER_SMOKE_AND_RESTART_VERIFIED', 'terminal_profile': profile,
                         'firefox_acceptance_in_scope': profile == 'firefox'}
                receipt, outputs = self.image_receipt(smoke, Path(temporary))
                self.assertEqual(receipt['terminal_profile'], profile)
                self.assertEqual(outputs.get('terminal_profile'), profile)
                self.assertFalse(receipt['public_production_verified'])

    def test_ci_profile_export_requires_accepted_typed_smoke_scope(self):
        for variant in ('unknown-profile', 'mismatched-scope', 'untyped-scope', 'unaccepted-smoke'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                smoke = {'source_head': HEAD, 'source_tree': TREE, 'manifest_sha256': 'd' * 64,
                         'state': 'CONTAINER_SMOKE_AND_RESTART_VERIFIED', 'terminal_profile': 'temdd',
                         'firefox_acceptance_in_scope': False}
                if variant == 'unknown-profile': smoke['terminal_profile'] = 'reference'
                if variant == 'mismatched-scope': smoke['firefox_acceptance_in_scope'] = True
                if variant == 'untyped-scope': smoke['firefox_acceptance_in_scope'] = 'false'
                if variant == 'unaccepted-smoke': smoke['state'] = 'STARTING'
                self.image_receipt(smoke, Path(temporary), expect_failure=True)

    def test_firefox_scope_reads_the_required_container_output(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_ci.yml').read_text()
        job = workflow.split('  s1_firefox_extension:\n', 1)[1].split('\n  container:', 1)[0]
        self.assertIn('needs: [amo_unlisted, container]', job)
        container = workflow.split('  container:\n', 1)[1].split('\n  container_publish:', 1)[0]
        self.assertIn('terminal_profile: ${{ steps.receipt.outputs.terminal_profile }}', container)


class ArtifactTransportControls(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.archive = self.root / "image.docker.tar.gz"
        self.archive.write_bytes(b"exact-original-image-bytes")
        self.pin = c.sha(self.archive.read_bytes())
        self.parts = self.root / "parts"

    def split(self):
        return c.artifact_split(self.archive, self.parts, self.pin, part_bytes=8)

    def manifest(self, value=None):
        path = self.parts / "PARTS.json"
        if value is not None:
            path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
        return json.loads(path.read_bytes()), c.sha(path.read_bytes())

    def test_original_image_survives_separate_part_delivery_with_both_pins(self):
        first = self.split()
        delivered = self.root / "delivered"; delivered.mkdir()
        for path in self.parts.iterdir():
            (delivered / path.name).write_bytes(path.read_bytes())
        output = self.root / "restored.tar.gz"
        result = c.artifact_join(delivered, output, first["parts_manifest_sha256"], self.pin)
        self.assertEqual(output.read_bytes(), self.archive.read_bytes())
        self.assertEqual(result["archive_sha256"], self.pin)
        self.assertEqual(result["state"], "ORIGINAL_ARTIFACT_REASSEMBLED_VERIFIED")
        self.assertFalse(result["image_imported"])
        self.assertFalse(result["extension_activation_verified"])
        self.assertFalse(result["public_production_verified"])
        self.assertLess(c.ARTIFACT_PART_BYTES + 1024 * 1024, 536870912)

    def test_existing_cli_dispatch_restores_exact_bytes_and_preserves_admission_boundaries(self):
        launcher = Path(__file__).resolve().parents[1] / 'tools/qikvrt_self_host.py'
        first = json.loads(subprocess.check_output([sys.executable, '-B', str(launcher),
            'container-artifact-split', '--carrier-archive', str(self.archive),
            '--transport-sha256', self.pin, '--output', str(self.parts),
            '--receipt', str(self.root / 'split.json')]))
        output = self.root / 'restored.tar.gz'
        second = json.loads(subprocess.check_output([sys.executable, '-B', str(launcher),
            'container-artifact-join', '--root', str(self.parts), '--output', str(output),
            '--transport-sha256', self.pin, '--manifest-sha256', first['parts_manifest_sha256'],
            '--receipt', str(self.root / 'restore.json')]))
        self.assertEqual(output.read_bytes(), self.archive.read_bytes())
        self.assertFalse(second['effect_ack_done'])
        self.assertFalse(second['ordinary_release'])
        workflow = (launcher.parents[1] / '.github/workflows/qikvrt_ci.yml').read_text()
        reuse = workflow.split('      - name: Reuse the already verified Firefox-158 dependency bytes\n', 1)[1]
        self.assertIn("steps.effect-admission.outputs.probe_required == 'true' || steps.transport-admission.outputs.reuse != 'true'", reuse.splitlines()[0])
        self.assertIn("assert r.get('current_probe_executed',True) is True", workflow)
        self.assertIn("assert r['signed_production_package_verified'] is True", workflow)

    def delivery_cache(self):
        original = {'source_head': 'a' * 40, 'source_tree': 'b' * 40, 'image_id': 'sha256:' + 'c' * 64,
                    'archive_bytes': 572793479, 'archive_sha256': 'd' * 64}
        delivery = {'schema': 'qikvrt-container-artifact-delivery/v1', 'repository': c.REPOSITORY,
            'run_id': 11, 'exporter_head': 'a' * 40, 'exporter_tree': 'b' * 40,
            'original_image': original, 'parts_manifest_sha256': c.sha(b'part-manifest-fixture'),
            'independent_download_back_verified': True, 'original_archive_restored_verified': True,
            'image_imported': False, 'extension_activation_verified': False,
            'public_production_verified': False, 'effect_ack_done': False,
            'parts': [{'index': 0, 'artifact_id': 12, 'artifact_name': 'fixture-part-000', 'zip_sha256': 'f' * 64}]}
        raw = (json.dumps(delivery, sort_keys=True, indent=2) + '\n').encode()
        return {'schema': 'qikvrt-runtime-transport-cache/v1', 'delivery': delivery,
            'metadata_artifact': {'id': 13, 'name': 'fixture-transport', 'bytes': 1000, 'sha256': 'f' * 64},
            'delivery_json_sha256': c.sha(raw), 'transport_module_blob': 'e' * 40}

    def workflow_code(self, marker):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_ci.yml').read_text()
        return textwrap.dedent(workflow.split("<<'" + marker + "'\n", 1)[1].split('\n          ' + marker, 1)[0])

    def test_workflow_cache_reuses_exact_delivery_and_invalidates_only_changed_inputs(self):
        for variant in ('same', 'no-cache', 'new-image', 'new-helper', 'no-runtime-reuse', 'unverified', 'bad-id'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); cache = self.delivery_cache()
                artifact = dict(cache['delivery']['original_image'])
                if variant == 'new-image': artifact['archive_sha256'] = '0' * 64
                if variant == 'unverified': cache['delivery']['independent_download_back_verified'] = False
                if variant == 'bad-id': cache['metadata_artifact']['id'] = True
                upgrade = {'runtime_artifact': artifact, 'bounded_transport_repair_20261017':
                           {'delivery_cache': None if variant == 'no-cache' else cache}}
                work = root / 'state/work_units/QIKVRT_MAIN_CONVERGENCE_20261014_V1.json'
                work.parent.mkdir(parents=True); work.write_text(json.dumps({'firefox158_s1_upgrade': upgrade}))
                code = self.workflow_code('PYTRANSFER'); output = root / 'output'
                before = Path.cwd()
                try:
                    os.chdir(root)
                    with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output),
                            'RUNTIME_REUSE': 'false' if variant == 'no-runtime-reuse' else 'true'}), \
                            patch.object(subprocess, 'check_output', return_value=('0' if variant == 'new-helper' else 'e') * 40):
                        if variant in ('unverified', 'bad-id'):
                            with self.assertRaises(AssertionError): exec(code, {})
                            self.assertFalse(output.exists())
                        else:
                            exec(code, {})
                            self.assertEqual(output.read_text().splitlines()[0], 'reuse=' + str(variant == 'same').lower())
                finally:
                    os.chdir(before)

    def test_workflow_cached_metadata_is_read_only_and_rejects_expiry_drift_and_provider_denial(self):
        import urllib.request
        import urllib.error
        for variant in ('same', 'expired', 'digest', 'source', 'oversize', 'denied'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); cache = self.delivery_cache(); delivery = cache['delivery']
                work = root / 'state/work_units/QIKVRT_MAIN_CONVERGENCE_20261014_V1.json'
                work.parent.mkdir(parents=True); work.write_text(json.dumps({'firefox158_s1_upgrade':
                    {'bounded_transport_repair_20261017': {'delivery_cache': cache}}}))
                folder = root / 's1-firefox158-existing-transport'; folder.mkdir()
                (folder / 'DELIVERY.json').write_text(json.dumps(delivery, sort_keys=True, indent=2) + '\n')
                (folder / 'PARTS.json').write_bytes(b'part-manifest-fixture')
                (root / 's1-extension-evidence').mkdir()
                requests = []
                class Response:
                    status = 200
                    def __init__(self, value): self.raw = json.dumps(value).encode()
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                    def read(self, limit): return self.raw[:limit]
                def opened(request, timeout):
                    requests.append(request)
                    identity = int(request.full_url.rsplit('/', 1)[1])
                    if variant == 'denied':
                        raise urllib.error.HTTPError(request.full_url, 403, 'private-provider-body', {}, None)
                    value = {'id': identity, 'name': 'fixture-transport' if identity == 13 else 'fixture-part-000',
                        'digest': 'sha256:' + ('0' if variant == 'digest' else 'f') * 64,
                        'expired': variant == 'expired', 'size_in_bytes': 536870912 if variant == 'oversize' else 1000,
                        'workflow_run': {'id': 11, 'head_sha': ('0' if variant == 'source' else 'a') * 40}}
                    return Response(value)
                opener = SimpleNamespace(open=opened); code = self.workflow_code('PYEXISTING')
                before = Path.cwd()
                try:
                    os.chdir(root)
                    with patch.dict(os.environ, {'RUNNER_TEMP': str(root), 'GH_TOKEN': 'synthetic-token'}), \
                            patch.object(urllib.request, 'build_opener', return_value=opener):
                        if variant == 'same':
                            exec(code, {})
                            receipt = json.loads((root / 's1-extension-evidence/transport-cache-readback.json').read_bytes())
                            self.assertFalse(receipt['large_archive_downloaded'])
                            self.assertFalse(receipt['parts_republished'])
                            self.assertFalse(receipt['effect_ack_done'])
                        elif variant == 'denied':
                            with self.assertRaisesRegex(ValueError, '^HOLD_PINNED_RUNTIME_TRANSPORT_HTTP_403$'): exec(code, {})
                        else:
                            with self.assertRaises(AssertionError): exec(code, {})
                finally:
                    os.chdir(before)
                self.assertTrue(requests)
                self.assertTrue(all(q.get_method() == 'GET' and '/actions/artifacts/' in q.full_url for q in requests))

    def test_failed_source_pin_does_not_leave_an_export_or_touch_an_existing_one(self):
        with self.assertRaisesRegex(ValueError, "ORIGINAL_ARTIFACT_SHA256_MISMATCH"):
            c.artifact_split(self.archive, self.parts, "0" * 64, part_bytes=8)
        self.assertFalse(self.parts.exists())
        self.split()
        before = {p.name: p.read_bytes() for p in self.parts.iterdir()}
        with self.assertRaisesRegex(ValueError, "CREATE_ONLY_ARTIFACT_PARTS"):
            self.split()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.parts.iterdir()})

    def test_missing_truncated_corrupted_and_symlinked_part_never_publish(self):
        first = self.split()
        path = self.parts / "artifact.part-001"; original = path.read_bytes()
        output = self.root / "restored.tar.gz"
        for variant in ("missing", "truncated", "corrupt", "symlink"):
            with self.subTest(variant=variant):
                path.unlink(missing_ok=True)
                if variant == "truncated": path.write_bytes(original[:-1])
                elif variant == "corrupt": path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
                elif variant == "symlink": path.symlink_to(self.archive)
                with self.assertRaises((ValueError, OSError)):
                    c.artifact_join(self.parts, output, first["parts_manifest_sha256"], self.pin)
                self.assertFalse(output.exists())
                self.assertFalse(list(self.root.glob(".qikvrt-artifact-*")))

    def test_manifest_path_order_duplicate_and_size_claims_are_rejected_even_when_rehashed(self):
        self.split(); original, _ = self.manifest()
        output = self.root / "restored.tar.gz"
        for variant in ("path", "order", "index", "size", "oversize", "archive-pin", "bool-size"):
            with self.subTest(variant=variant):
                value = json.loads(json.dumps(original))
                if variant == "path": value["parts"][0]["name"] = "../image.docker.tar.gz"
                elif variant == "order": value["parts"].reverse()
                elif variant == "index": value["parts"][1]["index"] = 0
                elif variant == "size": value["parts"][0]["bytes"] += 1
                elif variant == "oversize": value["archive_bytes"] = c.ARTIFACT_MAX_BYTES + 1
                elif variant == "archive-pin": value["archive_sha256"] = "0" * 64
                elif variant == "bool-size": value["part_bytes"] = True
                _, pin = self.manifest(value)
                with self.assertRaises(ValueError):
                    c.artifact_join(self.parts, output, pin, self.pin)
                self.assertFalse(output.exists())

    def test_unknown_manifest_pin_and_duplicate_json_members_are_not_trusted(self):
        first = self.split(); output = self.root / "restored.tar.gz"
        with self.assertRaisesRegex(ValueError, "ARTIFACT_PART_MANIFEST_MISMATCH"):
            c.artifact_join(self.parts, output, "0" * 64, self.pin)
        path = self.parts / "PARTS.json"
        path.write_bytes(path.read_bytes().replace(b'{', b'{"schema":"forged",', 1))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ARTIFACT_MANIFEST_MEMBER"):
            c.artifact_join(self.parts, output, c.sha(path.read_bytes()), self.pin)
        self.assertFalse(output.exists())

    def test_existing_restored_image_and_racing_creation_are_never_overwritten(self):
        first = self.split(); output = self.root / "restored.tar.gz"
        output.write_bytes(b"existing")
        with self.assertRaisesRegex(ValueError, "CREATE_ONLY_ARTIFACT"):
            c.artifact_join(self.parts, output, first["parts_manifest_sha256"], self.pin)
        self.assertEqual(output.read_bytes(), b"existing")
        output.unlink(); real_link = os.link
        def raced(source, destination, **keywords):
            output.write_bytes(b"racing-writer")
            return real_link(source, destination, **keywords)
        with patch.object(c.os, "link", side_effect=raced):
            with self.assertRaises(FileExistsError):
                c.artifact_join(self.parts, output, first["parts_manifest_sha256"], self.pin)
        self.assertEqual(output.read_bytes(), b"racing-writer")
        self.assertFalse(list(self.root.glob(".qikvrt-artifact-*")))

    def test_empty_oversized_and_nonregular_inputs_are_bounded_without_export(self):
        self.archive.write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "BOUNDED_ARTIFACT_ARCHIVE"):
            self.split()
        with self.archive.open("wb") as output:
            output.truncate(c.ARTIFACT_MAX_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "BOUNDED_ARTIFACT_ARCHIVE"):
            self.split()
        link = self.root / "link"; link.symlink_to(self.archive)
        with self.assertRaises(OSError):
            c.artifact_split(link, self.parts, self.pin)
        fifo = self.root / "fifo"; os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, "OWNER_REGULAR_ARTIFACT"):
            c.artifact_split(fifo, self.parts, self.pin)
        self.assertFalse(self.parts.exists())


if __name__ == "__main__":
    unittest.main()


