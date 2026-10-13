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


def archive(path, *, head=HEAD, tree=TREE, tamper=False, user="10001:10001"):
    blobs = {}
    def add(value):
        raw = json.dumps(value, sort_keys=True).encode()
        digest = c.sha(raw)
        blobs["blobs/sha256/" + digest] = raw
        return {"digest": "sha256:" + digest, "size": len(raw)}
    config = add({"architecture": "amd64", "os": "linux", "config": {"User": user,
        "Labels": {"org.opencontainers.image.revision": head, "de.qikvrt.source-tree": tree}}})
    layer = add({"test-layer": True})
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
