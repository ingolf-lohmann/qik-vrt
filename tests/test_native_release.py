#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Execute source-bound build, network-free rebuild and package refusal paths."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools import qikvrt_native_release as native

ROOT = Path(__file__).resolve().parents[1]


class NativeReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="qikvrt-native-test-")
        cls.work = Path(cls.temp.name)
        cls.source = cls.work / "repository"
        definition = json.loads((ROOT / native.DEFINITION).read_bytes())
        for name in definition["files"]:
            target = cls.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        def git(*args):
            return subprocess.check_output(["git", "-C", str(cls.source), *args], stderr=subprocess.DEVNULL).decode().strip()
        git("init")
        git("add", ".")
        git("-c", "user.name=QIKVRT fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "source fixture")
        cls.head, cls.tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        cls.package = cls.work / "package"
        cls.result = native.build(cls.source, cls.package, cls.head, cls.tree)
        cls.pin = cls.result["manifest_sha256"]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_executed_source_and_sql_binding(self):
        manifest = native.verify(self.package, self.pin)
        self.assertEqual(manifest["source"]["head"], self.head)
        evaluate = native.sql_function(self.package, self.pin)
        self.assertEqual(evaluate(bytes.fromhex("0000000700000003060201010100")), bytes.fromhex("000000040201"))
        with self.assertRaisesRegex(ValueError, "EXACT_14_BYTE"):
            evaluate(b"short")
        receipt = json.loads((self.package / "EXECUTION.json").read_bytes())
        self.assertEqual(receipt["source"]["tree"], self.tree)
        self.assertEqual(receipt["binary_sha256"], hashlib.sha256((self.package / manifest["cli"]).read_bytes()).hexdigest())
        self.assertFalse(receipt["effect_ack_done"])

    def test_rebuild_without_git_checkout(self):
        self.assertFalse((self.package / ".git").exists())
        rebuilt = self.work / "rebuilt"
        result = native.build(self.package, rebuilt, rebuild_pin=self.pin)
        self.assertEqual(result["source"]["head"], self.head)
        self.assertEqual(result["source"]["rebuilt_from_manifest_sha256"], self.pin)
        native.verify(rebuilt, result["manifest_sha256"])

    def test_wrong_pin_changed_source_and_extra_file_refused(self):
        with self.assertRaisesRegex(ValueError, "PIN_MISMATCH"):
            native.verify(self.package, "0" * 64)
        path = self.package / "source/src/temdd_core.c"
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n")
            with self.assertRaisesRegex(ValueError, "PACKAGE_BYTES"):
                native.verify(self.package, self.pin)
        finally:
            path.write_bytes(original)
        extra = self.package / "unexpected"
        try:
            extra.write_text("unbound")
            with self.assertRaisesRegex(ValueError, "PACKAGE_INVENTORY"):
                native.verify(self.package, self.pin)
        finally:
            extra.unlink()

    def test_source_head_and_dirty_checkout_refused(self):
        with self.assertRaisesRegex(ValueError, "EXACT_SOURCE_MISMATCH"):
            native.build(self.source, self.work / "wrong", "0" * 40, self.tree)
        path = self.source / "src/temdd_core.c"
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"\n")
            with self.assertRaises(subprocess.CalledProcessError):
                native.build(self.source, self.work / "dirty", self.head, self.tree)
        finally:
            path.write_bytes(original)

    def test_catalog_binds_executed_package_and_refuses_source_drift(self):
        artifacts = self.work / "artifact-readback"
        artifacts.mkdir()
        shutil.copyfile(Path(str(self.package) + ".zip"), artifacts / "qikvrt-native.zip")
        (artifacts / "NATIVE_BUILD.json").write_bytes(native.canonical(self.result))
        output = self.work / "publication-candidate"
        result = native.catalog(artifacts, output, self.head, self.tree)
        self.assertEqual(result["variant_count"], 1)
        self.assertFalse(result["zenodo_published"])
        with self.assertRaisesRegex(ValueError, "SOURCE_MISMATCH"):
            native.catalog(artifacts, self.work / "wrong-candidate", "0" * 40, self.tree)


if __name__ == "__main__":
    unittest.main()
