# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Independent dpkg lifecycle and original installed runtime; no public host."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_debian as packages
from tests import test_self_host as existing
from tests import test_self_host_temdd as native


class LinuxPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse the original real git -> sealed export fixture, without
        # inheriting or duplicating its acceptance cases.
        cls.fixture = type("DistributionSourceFixture", (), {})
        existing.StandaloneTests.setUpClass.__func__(cls.fixture)
        cls.addClassCleanup(existing.StandaloneTests.tearDownClass.__func__, cls.fixture)

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="qikvrt-deb-test-")
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.source = self.work / "source"
        shutil.copytree(self.fixture.export, self.source)
        self.pin = self.fixture.pin

    def build(self, revision="1"):
        output = self.work / ("debs-" + revision)
        receipt = packages.build(self.source, self.pin, output, revision)
        return output, receipt

    def command(self, *args, **kw):
        completed = subprocess.run(args, text=True, capture_output=True, timeout=60, **kw)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return completed.stdout

    def require_dpkg(self):
        # Required on the native Linux CI lane, never a silent skip.
        self.assertIsNotNone(shutil.which("dpkg"), "dpkg lifecycle checker unavailable")
        self.assertIsNotNone(shutil.which("dpkg-deb"), "independent .deb reader unavailable")

    def test_real_deb_readback_disjoint_complete_files_and_exact_dependencies(self):
        self.require_dpkg()
        directory, receipt = self.build()
        seen = set()
        for item in receipt["packages"]:
            deb = directory / item["filename"]
            name = self.command("dpkg-deb", "--field", str(deb), "Package").strip()
            self.assertEqual(name, item["name"])
            depends = self.command("dpkg-deb", "--field", str(deb), "Depends").strip()
            self.assertEqual(depends, ", ".join(item["depends"]))
            destination = self.work / name
            self.command("dpkg-deb", "--extract", str(deb), str(destination))
            files = {str(p.relative_to(destination)) for p in destination.rglob("*") if p.is_file()}
            self.assertFalse(seen & files, "cross-package file overwrite")
            seen |= files
        original_files = set(self.fixture.manifest["files"])
        self.assertEqual(set(receipt["ownership"]), original_files)
        self.assertEqual(receipt["ownership"]["src/qikvrt_effect_ack.py"], "qikvrt-eap")
        self.assertEqual(receipt["ownership"]["src/qikvrt_effect_ack_http_terminal.py"], "qikvrt-terminal")
        self.assertEqual(receipt["ownership"]["src/qikvrt_temdd_event_ledger.py"], "qikvrt-terminal")
        self.assertEqual(receipt["ownership"]["docs/monitor/react-runtime.js"], "qikvrt-web")
        self.assertFalse(receipt["host_admission_verified"])
        self.assertFalse(receipt["effect_ack_done"])
        for item in receipt["packages"]:
            self.assertEqual(hashlib.sha256((directory / item["filename"]).read_bytes()).hexdigest(), item["sha256"])

    def test_two_builds_are_byte_identical(self):
        first, _ = self.build()
        second = self.work / "independent-build"
        packages.build(self.source, self.pin, second)
        self.assertEqual({p.name: p.read_bytes() for p in first.iterdir()},
                         {p.name: p.read_bytes() for p in second.iterdir()})

    def test_existing_deb_verify_entrypoint_reads_original_bytes_and_rejects_corruption(self):
        directory, receipt = self.build()
        alias_directory = self.work / "original-entrypoint"
        built = self.command(sys.executable, "-B", str(packages.ROOT / "tools/qikvrt_self_host.py"),
                             "deb-pack", "--root", str(self.source), "--manifest-sha256", self.pin,
                             "--output", str(alias_directory))
        self.assertEqual(json.loads(built)["bundle_sha256"], receipt["bundle_sha256"])
        observed = packages.verify(directory, receipt["bundle_sha256"])
        self.assertEqual(observed["verified_source_files"], len(self.fixture.manifest["files"]))
        text = self.command(sys.executable, "-B", str(packages.ROOT / "tools/qikvrt_self_host.py"),
                            "deb-verify", "--root", str(directory), "--debian-bundle-sha256", receipt["bundle_sha256"])
        self.assertEqual(json.loads(text)["state"], "DEBIAN_PACKAGES_INDEPENDENTLY_VERIFIED_NOT_INSTALLED")
        index = directory / "SHA256SUMS.txt"
        original = index.read_bytes()
        index.write_bytes(b"wrong index")
        with self.assertRaisesRegex(ValueError, "DEBIAN_BUNDLE_CHECKSUM_INDEX_MISMATCH"):
            packages.verify(directory, receipt["bundle_sha256"])
        index.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "DEBIAN_BUNDLE_PIN_MISMATCH"):
            packages.verify(directory, "0" * 64)
        archive = directory / receipt["packages"][0]["filename"]
        archive.write_bytes(archive.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "DEBIAN_PACKAGE_DIGEST_MISMATCH"):
            packages.verify(directory, receipt["bundle_sha256"])

    def test_wrong_pin_changed_source_or_untracked_file_blocks_before_output(self):
        for kind in ("pin", "bytes", "extra", "symlink"):
            with self.subTest(kind=kind):
                root = self.work / kind
                shutil.copytree(self.source, root)
                pin = self.pin
                if kind == "pin":
                    pin = "0" * 64
                elif kind == "bytes":
                    (root / "src/qikvrt_effect_ack.py").write_bytes(b"changed")
                elif kind == "extra":
                    (root / "private.token").write_bytes(b"synthetic-private-control")
                else:
                    p = root / "LICENSE"
                    p.unlink()
                    p.symlink_to(self.source / "LICENSE")
                output = self.work / (kind + "-output")
                with self.assertRaises(ValueError):
                    packages.build(root, pin, output)
                self.assertFalse(output.exists())

    def test_output_and_revision_guards_preserve_existing_data(self):
        old = self.work / "existing"
        old.mkdir()
        (old / "keep").write_bytes(b"original")
        with self.assertRaises(ValueError):
            packages.build(self.source, self.pin, old)
        self.assertEqual((old / "keep").read_bytes(), b"original")
        for revision in ("-1", "1\nDepends: bad", "../../state"):
            with self.assertRaises(ValueError):
                packages.build(self.source, self.pin, self.work / "invalid", revision)
        link = self.work / "link"
        link.symlink_to(old, target_is_directory=True)
        with self.assertRaises(ValueError):
            packages.build(self.source, self.pin, link / "escape")

    def test_host_seal_idempotent_and_corruption_not_resealed(self):
        destination = self.work / "installed"
        first = packages.configure(self.source, self.pin, destination)
        sealed = Path(first["package_path"])
        verified = packages.original().verify(sealed, first["manifest_sha256"])
        self.assertEqual(verified["distribution_source_manifest_sha256"], self.pin)
        self.assertEqual(packages.configure(self.source, self.pin, destination), first)
        self.assertEqual((self.source / "MANIFEST.json").read_bytes(), (self.fixture.export / "MANIFEST.json").read_bytes())
        (sealed / "src/qikvrt_effect_ack.py").write_bytes(b"corruption")
        with self.assertRaisesRegex(ValueError, "PACKAGE_ARTIFACT_MISMATCH"):
            packages.configure(self.source, self.pin, destination)
        self.assertFalse(first["service_started"])

    def test_incompatible_runtime_or_failed_checker_creates_no_candidate(self):
        destination = self.work / "installed"
        host = packages.original()
        with mock.patch.object(packages, "original", return_value=host):
            with mock.patch.object(host, "runtime", return_value={"version": "v22.0.0", "executable_sha256": "a" * 64}):
                with self.assertRaisesRegex(ValueError, "LINUX_NODE24_PYTHON312_REQUIRED"):
                    packages.configure(self.source, self.pin, destination)
            with mock.patch.object(host, "runtime", side_effect=OSError("checker unavailable")):
                with self.assertRaisesRegex(OSError, "checker unavailable"):
                    packages.configure(self.source, self.pin, destination)
        self.assertFalse(destination.exists())

    def dpkg(self, root, *args):
        # The empty test root models distro dependency metadata; the postinst
        # separately checks the actual host executable bytes and versions.
        database = root / "var/lib/dpkg/status"
        if not database.exists():
            database.parent.mkdir(parents=True, exist_ok=True)
            versions = {"python3.12": "3.12.0", "nodejs": "24.0.0", "systemd": "252", "ca-certificates": "20260101"}
            database.write_text("".join(f"Package: {name}\nStatus: install ok installed\nArchitecture: all\nVersion: {version}\nMaintainer: Fixture <fixture@example.invalid>\nDescription: isolated distro dependency metadata\n\n"
                                        for name, version in versions.items()))
        return self.command("dpkg", "--root=" + str(root), "--force-script-chrootless",
                            "--force-not-root", *args)

    def test_native_dependency_solver_rejects_mixed_component_versions(self):
        self.require_dpkg()
        one, first = self.build()
        two, second = self.build("2")
        root = self.work / "mixed-root"
        self.dpkg(root, "--audit")
        selected = [str((two if p["name"] == "qikvrt-terminal" else one) /
                        (next(v for v in second["packages"] if v["name"] == p["name"])["filename"]
                         if p["name"] == "qikvrt-terminal" else p["filename"])) for p in first["packages"]]
        result = subprocess.run(["dpkg", "--root=" + str(root), "--force-script-chrootless",
                                 "--force-not-root", "--install", *selected], text=True, capture_output=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("depends on qikvrt-eap (= " + second["version"] + ")", result.stderr)
        self.assertFalse((root / "var/lib/qikvrt/distribution").exists())

    def test_real_dpkg_install_upgrade_remove_purge_preserves_config_and_ledger(self):
        self.require_dpkg()
        directory, receipt = self.build()
        root = self.work / "dpkg-root"
        config = root / "etc/qikvrt/config.json"
        ledger = root / "var/lib/qikvrt/node/original-ledger.bin"
        for path, body in ((config, b"private-original-config"), (ledger, b"acknowledged-original-bytes")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        expected = [config.read_bytes(), ledger.read_bytes()]
        debs = lambda folder, r: [str(folder / p["filename"]) for p in r["packages"]]
        self.dpkg(root, "--install", *debs(directory, receipt))
        installed = root / "var/lib/qikvrt/distribution"
        candidates = [p for p in installed.iterdir() if p.is_dir() and not p.name.startswith(".")]
        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        packages.original().verify(candidate, candidate.name)
        # Exercise the actual installed original Terminal/Transputer from the
        # dpkg-root, then a real process restart, with existing fixture helpers.
        case = native.NativeStandaloneTests(methodName="runTest")
        for key in ("head", "tree"):
            setattr(case, key, getattr(self.fixture, key))
        case.export, case.pin = candidate, candidate.name
        try:
            case.setUp()
            # This sandbox permits the original TCP/SQLite profile but denies
            # AF_UNIX. Select its existing optional Unix-ingress=false mode;
            # the separate native S1 lane retains the Unix-socket obligations.
            case.config["unix_ingress"] = False
            case.volume = ledger.parent
            case.volume.chmod(0o700)
            case.config["state_dir"] = str(case.volume)
            case.owner_token = case.work / "owner.token"
            case.owner_token.write_text("synthetic-distribution-test-owner-token-no-real-credential")
            case.owner_token.chmod(0o600)
            case.config["owner_rest_grants"] = [{"principal": "owner:fixture", "token_file": str(case.owner_token),
                                                  "permissions": ["prepare", "commit", "readback"]}]
            case.request = {"schema": "qikvrt_owner_rest_input_v1", "request_id": "distribution:fixture-001",
                            "subject": {"repository": "ingolf-lohmann/qik-vrt", "pr": 457,
                                        "head": case.head, "tree": case.tree},
                            "input": {"schema": "qikvrt_terminal_input_v1", "text": "synthetic packaged EAP observation"}}
            case.save_config()
            case.start()
            status, value = case.get("/api/terminal")
            self.assertEqual(status, 200)
            self.assertEqual(value["state"], "NATIVE_TEMDD_READY")
            rest = native.OwnerRESTMonolithTests.rest.__get__(case)
            status, prepared = rest("prepare")
            self.assertEqual(status, 200, prepared)
            status, committed = rest("commit", prepared=prepared)
            self.assertEqual(status, 200, committed)
            acknowledged = committed["durable_readback"]
            self.assertTrue(committed["independent_sqlite_readback"])
            self.assertFalse(committed["EFFECT_ACK_DONE"])
            rows = case.sql("SELECT seq,body,native_digest FROM events")
            self.assertEqual(len(rows), 1)
            case.stop()
            case.start()
            self.assertEqual(case.get("/api/terminal")[0], 200)
            self.assertEqual(rest("readback")[1]["durable_readback"], acknowledged)
            self.assertEqual(case.sql("SELECT seq,body,native_digest FROM events"), rows)
            case.stop()
        finally:
            case.doCleanups()
        durable = {p.relative_to(ledger.parent).as_posix(): p.read_bytes() for p in ledger.parent.rglob("*") if p.is_file()}
        second, upgrade = self.build("2")
        self.dpkg(root, "--install", *debs(second, upgrade))
        self.assertEqual([p for p in installed.iterdir() if p.is_dir()], [candidate])
        self.dpkg(root, "--remove", *reversed(packages.PACKAGES))
        self.dpkg(root, "--purge", *reversed(packages.PACKAGES))
        self.assertEqual([config.read_bytes(), ledger.read_bytes()], expected)
        self.assertEqual({p.relative_to(ledger.parent).as_posix(): p.read_bytes()
                          for p in ledger.parent.rglob("*") if p.is_file()}, durable)
        packages.original().verify(candidate, candidate.name)
        self.assertFalse(any(p.suffix == ".service" for p in root.rglob("*")))

    def test_sources_keep_licenses_and_server_uses_existing_supervisor(self):
        definition = json.loads((packages.ROOT / "runtime/self-host/PACKAGE.json").read_bytes())
        for name in ("LICENSE", "LICENSES/PolyForm-Noncommercial-1.0.0.txt", "tools/qikvrt_self_host.py",
                     "tools/qikvrt_debian.py", "src/effect_ack_core.c", "include/qikvrt/effect_ack.h"):
            self.assertIn(name, definition["files"])
        doc = (packages.ROOT / "runtime/self-host/LINUX_PACKAGES.md").read_text()
        for marker in ("supervisor", "run-admitted", "raumzeitterminal.de", "Python 3.12", "Node 24"):
            self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
