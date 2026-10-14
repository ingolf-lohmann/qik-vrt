# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Negative integrity/admission controls; fixture hosts are not deployments."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
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
        for variant in ('valid', 'changed-ledger', 'failed-readback'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as tmp:
                calls, phase = [], {'restart': False}
                name = 'qikvrt-s1-smoke-' + '1' * 16
                network = name + '-net'
                manifest = json.dumps({'source_head': HEAD, 'source_tree': TREE}).encode()
                client = json.dumps({'state': 'CLIENT_BYTE_READBACK_VERIFIED',
                                     'source_head': HEAD, 'source_tree': TREE, 'effect_ack_done': False}).encode()
                failed = b'{"state":"HOLD_PUBLIC_OR_INDEPENDENT_CLIENT_READBACK","cause":"HOLD_PUBLIC_NODE_HEALTH_CONTRACT","effect_ack_done":false}\n'
                def command(*argv, **kwargs):
                    calls.append(argv)
                    if argv[0] == 'node':
                        if variant == 'failed-readback':
                            raise subprocess.CalledProcessError(20, list(argv), output=failed)
                        return client
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
                     patch.object(c, 'firefox_image_admission'), \
                     patch.object(c.subprocess, 'run', return_value=SimpleNamespace(stdout=b'', stderr=b'')), \
                     patch('builtins.print'):
                    if variant == 'valid':
                        result = c.smoke('fixture-image', tmp)
                        self.assertEqual(result['state'], 'CONTAINER_SMOKE_AND_RESTART_VERIFIED')
                        self.assertTrue(result['ledger_identity_preserved'])
                        self.assertFalse(result['public_production_verified'])
                    elif variant == 'changed-ledger':
                        with self.assertRaisesRegex(ValueError, 'DURABLE_LEDGER_ID_RESTART_MISMATCH'):
                            c.smoke('fixture-image', tmp)
                    else:
                        with self.assertRaises(subprocess.CalledProcessError): c.smoke('fixture-image', tmp)
                        self.assertEqual((Path(tmp)/'smoke-readback-before-restart.stdout').read_bytes(), failed)
                        self.assertFalse(phase['restart'])
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

    def test_no_registry_publication_without_the_current_signed_firefox_job(self):
        text=(Path(__file__).resolve().parents[1]/'.github/workflows/qikvrt_ci.yml').read_text()
        container=text.split('  container:\n',1)[1].split('  container_publish:\n',1)[0]
        publication=text.split('  container_publish:\n',1)[1].split('  container_deploy:\n',1)[0]
        self.assertIn('needs: [test, s1_firefox_extension]',container)
        self.assertIn('needs: [test, container, s1_firefox_extension]',publication)
        self.assertIn("github.ref == 'refs/heads/main'",publication)
        self.assertIn('environment: qikvrt-production',publication)
        self.assertIn('container-production-gate',publication)
        self.assertIn('container-carrier-archive-check',publication)
        self.assertIn('carrier-registry-readback.json',publication)


if __name__ == "__main__":
    unittest.main()

