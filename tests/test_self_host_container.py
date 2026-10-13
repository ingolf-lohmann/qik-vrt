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

    def test_tls_redirect_not_followed(self):
        with self.assertRaisesRegex(ValueError, "REDIRECT_FORBIDDEN"):
            c.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example")


if __name__ == "__main__":
    unittest.main()

