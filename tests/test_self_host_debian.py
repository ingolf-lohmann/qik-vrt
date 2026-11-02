#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools import qikvrt_debian as debian


ROOT = Path(__file__).resolve().parents[1]
EAP = ("src/qikvrt_effect_ack.py", "src/qikvrt_effect_ack_http_service.py",
       "src/qikvrt_effect_ack_http_terminal.py", "src/qikvrt_effect_ack_wire.py")


class DebianPackageTest(unittest.TestCase):
    def fixture(self, root: Path):
        files = {}
        for name in (*EAP, "tools/qikvrt_self_host.py", debian.LAYOUT):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = ((ROOT / name).read_bytes() if name == debian.LAYOUT else ("fixture:" + name + "\n").encode())
            target.write_bytes(raw)
            target.chmod(0o755 if name == "tools/qikvrt_self_host.py" else 0o644)
            files[name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                           "mode": "100755" if name == "tools/qikvrt_self_host.py" else "100644"}
        manifest = {"schema": "qikvrt-self-host-package/v1", "package_version": "1.15.0",
                    "source_repository": "ingolf-lohmann/qik-vrt", "source_head": "1" * 40,
                    "source_tree": "2" * 40, "runtime": {"platform": "x86_64"}, "files": files,
                    "effect_ack_done": False}
        raw = debian.raw_json(manifest)
        (root / "MANIFEST.json").write_bytes(raw)
        return manifest, hashlib.sha256(raw).hexdigest()

    def test_deterministic_partition_build_and_independent_readback(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); source = base / "source"; source.mkdir()
            manifest, pin = self.fixture(source)
            def verified(path, expected):
                self.assertEqual(path, source.resolve()); self.assertEqual(expected, pin); return manifest
            first = debian.build(source, pin, base / "one", verified)
            second = debian.build(source, pin, base / "two", verified)
            self.assertEqual(first["state"], "DEBIAN_PACKAGES_BUILT_NOT_INSTALLED")
            self.assertFalse(first["service_auto_started"]); self.assertFalse(first["host_admission_verified"])
            self.assertEqual([item["name"] for item in first["packages"]], ["qikvrt-eap", "qikvrt"])
            for left, right in zip(first["packages"], second["packages"]):
                self.assertEqual((base / "one" / left["file"]).read_bytes(), (base / "two" / right["file"]).read_bytes())
            result = debian.verify(base / "one", first["bundle_sha256"])
            self.assertEqual(result["state"], "DEBIAN_PACKAGES_INDEPENDENTLY_VERIFIED_NOT_INSTALLED")
            self.assertEqual(result["verified_source_files"], len(manifest["files"]))
            self.assertFalse(result["effect_ack_done"])

    @unittest.skipUnless(shutil.which("dpkg-deb"), "distribution dpkg-deb unavailable")
    def test_distribution_tool_accepts_and_extracts_both_packages(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); source = base / "source"; source.mkdir()
            manifest, pin = self.fixture(source)
            result = debian.build(source, pin, base / "bundle", lambda *_: manifest)
            install = base / "install"; install.mkdir()
            for item in result["packages"]:
                archive = base / "bundle" / item["file"]
                subprocess.run(["dpkg-deb", "--info", str(archive)], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                subprocess.run(["dpkg-deb", "--extract", str(archive), str(install)], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            prefix = install / "usr/lib/qikvrt/1.15.0"
            for name in manifest["files"]:
                self.assertEqual((prefix / name).read_bytes(), (source / name).read_bytes())
            self.assertTrue((install / "usr/bin/qikvrt-self-host").stat().st_mode & 0o111)

    def test_changed_archive_and_changed_pin_hold(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); source = base / "source"; source.mkdir()
            manifest, pin = self.fixture(source)
            result = debian.build(source, pin, base / "bundle", lambda *_: manifest)
            with self.assertRaisesRegex(ValueError, "DEBIAN_BUNDLE_PIN_MISMATCH"):
                debian.verify(base / "bundle", "0" * 64)
            archive = base / "bundle" / result["packages"][0]["file"]
            archive.write_bytes(archive.read_bytes() + b"x")
            with self.assertRaisesRegex(ValueError, "DEBIAN_PACKAGE_DIGEST_MISMATCH"):
                debian.verify(base / "bundle", result["bundle_sha256"])


if __name__ == "__main__":
    unittest.main()
