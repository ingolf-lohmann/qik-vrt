# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Exact package transport and real builder-shell fault injection; no deployment."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools import qikvrt_self_host_container as c

ROOT = Path(__file__).resolve().parents[1]


class FrozenBuildAPT(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archives = self.root / "archives"
        self.archives.mkdir()
        self.lock = {"schema": "qikvrt-frozen-build-apt/v1", "origins": {
            "debian": "https://deb.debian.org/debian",
            "debian-security": "https://deb.debian.org/debian-security"}, "packages": []}
        self.rows = []
        for i in range(8):
            name = "package" + str(i)
            payload = (name + ":isolated synthetic archive\n").encode()
            filename = name + "_1.0_amd64.deb"
            record = {"name": name, "version": "1.0", "archive": "debian",
                "filename": "pool/main/p/fixture/" + filename,
                "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
            self.lock["packages"].append(record)
            (self.archives / filename).write_bytes(payload)
            self.rows.append("'https://deb.debian.org/debian/" + record["filename"] + "' " +
                filename + " " + str(len(payload)) + " SHA256:" + record["sha256"])
        self.lockfile = self.root / "lock.json"
        self.lockfile.write_text(json.dumps(self.lock))
        self.plan = self.root / "plan"
        self.plan.write_text("APT explanation, not executable input\n" + "\n".join(self.rows) + "\n")

    def check(self, phase, path=None):
        return c.frozen_apt_guard(phase, self.lockfile,
            path if path is not None else self.archives if phase == "archives" else self.plan)

    def test_exact_plan_and_actual_bytes_are_checked_without_execution(self):
        with patch.object(c.subprocess, "check_output") as command:
            for phase in ("plan", "archives"):
                receipt = self.check(phase)
                self.assertEqual(receipt["state"], "EXACT_FROZEN_BUILD_PACKAGES_VERIFIED")
                self.assertEqual(len(receipt["packages"]), 8)
                self.assertFalse(receipt["effect_ack_done"])
            command.assert_not_called()

    def test_missing_extra_and_duplicate_package_plans_cannot_pass(self):
        for rows in (self.rows[:-1], self.rows + [self.rows[0]], self.rows[1:] + [self.rows[1]]):
            with self.subTest(rows=rows):
                self.plan.write_text("\n".join(rows))
                with self.assertRaisesRegex(ValueError, "FROZEN_APT_"): self.check("plan")

    def test_wrong_origin_path_size_and_weak_hash_are_rejected(self):
        original = self.rows[0]
        for changed in (original.replace("https://", "http://"),
                        original.replace("deb.debian.org", "deb.debian.org.evil.invalid"),
                        original.replace("/debian/pool/", "/debian/../pool/"),
                        original.replace(" SHA256:", " MD5Sum:"),
                        original.replace(" " + str(self.lock["packages"][0]["bytes"]) + " SHA256:", " 1 SHA256:"),
                        original.replace("_1.0_amd64.deb'", "_1.1_amd64.deb'")):
            with self.subTest(changed=changed):
                self.plan.write_text("\n".join([changed, *self.rows[1:]]))
                with self.assertRaisesRegex(ValueError, "FROZEN_APT_"): self.check("plan")

    def test_shell_text_is_data_and_never_executed(self):
        marker = self.root / "MUST_NOT_EXECUTE"
        self.plan.write_text(self.plan.read_text().replace("https://deb.debian.org/debian/",
            "https://deb.debian.org/debian/$(touch " + str(marker) + ")/", 1))
        with self.assertRaises(ValueError): self.check("plan")
        self.assertFalse(marker.exists())

    def test_incomplete_corrupt_and_symlinked_downloads_fail_closed(self):
        path = next(self.archives.glob("*.deb"))
        raw = path.read_bytes()
        for change in ("missing", "corrupt", "symlink"):
            with self.subTest(change=change):
                path.unlink()
                if change == "corrupt": path.write_bytes(raw + b"tampered")
                if change == "symlink":
                    target = self.root / "outside"; target.write_bytes(raw); path.symlink_to(target)
                with self.assertRaisesRegex(ValueError, "FROZEN_APT_"): self.check("archives")
                path.unlink(missing_ok=True); path.write_bytes(raw)

    def test_installed_versions_are_read_from_dpkg_and_must_match(self):
        output = "".join(p["name"] + "\t" + p["version"] + "\n" for p in self.lock["packages"]).encode()
        with patch.object(c.subprocess, "check_output", return_value=output) as command:
            self.assertEqual(self.check("installed")["phase"], "installed")
            self.assertEqual(command.call_args.kwargs["timeout"], 15)
        with patch.object(c.subprocess, "check_output", return_value=output.replace(b"1.0", b"0.9", 1)):
            with self.assertRaisesRegex(ValueError, "INSTALLED_VERSION_DRIFT"): self.check("installed")

    def test_versioned_carrier_and_new_image_have_separate_readback_artifacts(self):
        """One unambiguous carrier variant per CI run; no implicit predecessor PASS."""
        workflow = (ROOT / ".github/workflows/qikvrt_ci.yml").read_text()
        successor_path = ROOT / "runtime/self-host/DELIVERY_SUCCESSOR_20261107.json"
        baseline = json.loads((ROOT / "runtime/self-host/CONTAINER_CARRIER.json").read_text())
        if successor_path.is_file():
            successor = json.loads(successor_path.read_text())
            candidate = successor["candidate"]
            self.assertEqual(successor["schema"], "qikvrt-runtime-delivery-successor/v1")
            self.assertNotEqual(candidate["artifact_id"], baseline["artifact_id"])
            self.assertNotEqual(candidate["artifact_sha256"], baseline["archive_sha256"])
            self.assertEqual(candidate["source_head"], baseline["source_head"])
            self.assertEqual(candidate["source_tree"], baseline["source_tree"])
            self.assertIs(type(candidate["attempt"]), int)
            self.assertEqual(candidate["attempt"], 2)
            for field in ("image_config_digest", "oci_manifest_digest", "package_manifest_sha256"):
                self.assertNotEqual(candidate[field], baseline[field])
            self.assertIn("oci-layout://$RUNNER_TEMP/frozen-carrier@" +
                          candidate["oci_manifest_digest"], workflow)
            self.assertTrue(all(type(value) is bool and not value
                                for value in successor["claims"].values()))
            kind, label = "successor", "versioned"
            verify_step = "Verify versioned PR494 dependency carrier successor"
        else:
            kind, label = "original", "original"
            verify_step = "Verify and reuse original PR494 Docker carrier"
        other = "original" if kind == "successor" else "successor"
        preserve_step = "Preserve " + ("versioned" if kind == "successor" else "original") + " frozen carrier separately"
        other_step = "Preserve " + ("original" if kind == "successor" else "versioned") + " frozen carrier separately"
        self.assertEqual(workflow.count("- name: " + preserve_step + "\n"), 1)
        self.assertNotIn("- name: " + other_step + "\n", workflow)
        self.assertEqual(workflow.count("- name: " + verify_step + "\n"), 1)

        carrier = workflow.split("- name: " + preserve_step + "\n", 1)[1].split(
            "\n      - name:", 1)[0]
        result = workflow.split(
            "- name: Preserve exact OCI image and non-secret original evidence\n", 1
        )[1].split("\n  container_publish:", 1)[0]
        publisher = workflow.split("\n  container_publish:", 1)[1].split(
            "\n  container_deploy:", 1)[0]
        artifact_name = "qikvrt-s1-" + kind + "-carrier-"
        carrier_file = "carrier-" + kind + ".oci.tar"
        self.assertIn("if: always()", carrier)
        self.assertIn(artifact_name, carrier)
        self.assertIn("path: ${{ runner.temp }}/container-evidence/" + carrier_file, carrier)
        self.assertIn("!${{ runner.temp }}/container-evidence/" + carrier_file, result)
        self.assertNotIn("!${{ runner.temp }}/container-evidence/image.oci.tar", result)
        self.assertIn("qikvrt-s1-container-", result)
        self.assertIn("include-hidden-files: true", result)
        self.assertIn("name: " + artifact_name + "${{ needs.container.outputs.head }}", publisher)
        self.assertIn("name: " + artifact_name +
                      "${{ github.event.pull_request.head.sha || github.sha }}", result)
        self.assertIn("name: qikvrt-s1-container-${{ github.event.pull_request.head.sha || github.sha }}", result)
        for section in (carrier, result, publisher):
            self.assertNotIn("carrier-" + other + ".oci.tar", section)
            self.assertNotIn("qikvrt-s1-" + other + "-carrier-", section)
        self.assertIn("restore_artifact_package", result)
        self.assertIn("carrier_archive_check", result)
        self.assertIn(carrier_file, result)
        if kind == "successor":
            self.assertIn("--carrier-successor", publisher)
            self.assertIn("carrier_expected(Path('.'), successor=True)", result)
        readback = workflow.split("\n  container_public_readback:", 1)[1]
        self.assertIn("restore_artifact_package", readback)
        for marker in ("PYROUNDTRIP", "PYPACKAGE"):
            body = workflow.split("<<'" + marker + "'\n", 1)[1].split(
                "\n          " + marker, 1)[0]
            compile("\n".join(line[10:] for line in body.splitlines()), marker, "exec")

    def artifact_package(self):
        package = self.root / "package"
        package.mkdir(exist_ok=True)
        files = {}
        for name, raw, mode in ((".github/CODEOWNERS", b"sealed owners\n", "100644"),
                                (".well-known/disclosure.json", b"{}\n", "100644"),
                                ("start.sh", b"#!/bin/sh\nexit 0\n", "100755")):
            path = package / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw); path.chmod(0o644)
            files[name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), mode=mode)
        value = dict(schema="qikvrt-self-host-package/v1", source_head="a"*40, source_tree="b"*40,
                     files=files, effect_ack_done=False)
        raw = (json.dumps(value, sort_keys=True) + "\n").encode()
        (package / "MANIFEST.json").write_bytes(raw)
        return package, hashlib.sha256(raw).hexdigest()

    def test_complete_artifact_package_restores_only_pinned_modes(self):
        package, pin = self.artifact_package()
        result = c.restore_artifact_package(package, pin, "a"*40, "b"*40)
        self.assertEqual(result["files_verified"], 3)
        self.assertEqual((package / "start.sh").stat().st_mode & 0o777, 0o755)
        self.assertEqual(hashlib.sha256((package / "MANIFEST.json").read_bytes()).hexdigest(), pin)
        self.assertFalse(result["effect_ack_done"])

    def test_artifact_faults_fail_before_any_permission_mutation(self):
        for change in ("missing_hidden", "extra", "bytes", "symlink", "head", "tree", "pin"):
            with self.subTest(change=change):
                shutil.rmtree(self.root / "package", ignore_errors=True)
                package, pin = self.artifact_package(); head, tree = "a"*40, "b"*40
                if change == "missing_hidden": (package / ".github/CODEOWNERS").unlink()
                if change == "extra": (package / "extra").write_bytes(b"unexpected")
                if change == "bytes": (package / ".github/CODEOWNERS").write_bytes(b"tampered")
                if change == "symlink":
                    path = package / ".github/CODEOWNERS"; path.unlink(); path.symlink_to(package / "start.sh")
                if change == "head": head = "c"*40
                if change == "tree": tree = "c"*40
                if change == "pin": pin = "c"*64
                with self.assertRaisesRegex(ValueError, "ARTIFACT_PACKAGE_"):
                    c.restore_artifact_package(package, pin, head, tree)
                self.assertEqual((package / "start.sh").stat().st_mode & 0o777, 0o644)

    def test_real_builder_shell_stops_before_install_for_each_failure(self):
        # Exercise the actual Dockerfile RUN body with isolated commands. Only
        # APT/dpkg/git are fixtures; Python executes the original guard source.
        text = (ROOT / "runtime/self-host/Dockerfile").read_text()
        recipe = text.split("FROM ${QIKVRT_PRODUCTION_IMAGE} AS package-builder\n", 1)[1]
        shell = recipe.split("RUN ", 1)[1].split("\nWORKDIR /source", 1)[0]
        self.assertIn('Acquire::Retries "0"', shell)
        self.assertIn('APT::Update::Error-Mode "any"', shell)
        self.assertEqual(shell.count("timeout --signal=TERM --kill-after=10s"), 3)
        self.assertIn("--no-download", shell)
        self.assertNotIn("--allow-unauthenticated", shell)
        self.assertNotIn("trusted=yes", shell)
        for variant in ("valid", "update-failure", "plan-drift", "byte-drift", "installed-drift"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); commands = root / "bin"; commands.mkdir()
                archives = root / "archives"; archives.mkdir()
                (root / "etc/apt/sources.list.d").mkdir(parents=True)
                (root / "etc/apt/apt.conf.d").mkdir()
                shutil.copyfile(c.__file__, root / "guard.py")
                (root / "lock.json").write_text(json.dumps(self.lock))
                fixture = {"rows": self.rows, "packages": self.lock["packages"],
                           "source": str(self.archives), "variant": variant}
                (root / "fixture.json").write_text(json.dumps(fixture))
                program = '''#!/usr/bin/env python3
import json,os,shutil,sys
from pathlib import Path
r=Path(os.environ["APT_FIXTURE_ROOT"]); f=json.loads((r/"fixture.json").read_text()); a=sys.argv[1:]
with (r/"commands.jsonl").open("a") as log: log.write(json.dumps([Path(sys.argv[0]).name,a])+"\\n")
if Path(sys.argv[0]).name=="git":sys.exit(0)
if Path(sys.argv[0]).name=="dpkg-query":
 for p in f["packages"]:print(p["name"]+"\\t"+("0.9" if f["variant"]=="installed-drift" else p["version"]))
 sys.exit(0)
if "update" in a and f["variant"]=="update-failure":sys.exit(100)
if "--print-uris" in a:print("\\n".join(f["rows"][:-1] if f["variant"]=="plan-drift" else f["rows"]))
if "--download-only" in a:
 for p in Path(f["source"]).glob("*.deb"):shutil.copyfile(p,r/"archives"/p.name)
 if f["variant"]=="byte-drift":next((r/"archives").glob("*.deb")).write_bytes(b"corrupt")
'''
                for name in ("apt-get", "dpkg-query", "git"):
                    file = commands / name; file.write_text(program); file.chmod(0o755)
                actual = shell.replace("/tmp/qikvrt-build-apt.py", str(root / "guard.py"))
                actual = actual.replace("/tmp/qikvrt-build-apt.json", str(root / "lock.json"))
                actual = actual.replace("/tmp/qikvrt-build-apt-plan", str(root / "plan"))
                actual = actual.replace("/var/cache/apt/archives", str(archives))
                actual = actual.replace("/etc/apt/", str(root / "etc/apt") + "/")
                actual = actual.replace("/var/lib/apt/", str(root / "var/lib/apt") + "/")
                actual = actual.replace("/var/log/", str(root / "var/log") + "/")
                result = subprocess.run(["bash", "-c", actual], env={**os.environ,
                    "APT_FIXTURE_ROOT": str(root), "PATH": str(commands) + ":" + os.environ["PATH"]},
                    capture_output=True, text=True, timeout=15)
                calls = [json.loads(s) for s in (root / "commands.jsonl").read_text().splitlines()]
                installs = [a for name, a in calls if name == "apt-get" and "--no-download" in a]
                if variant == "valid":
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(len(installs), 1)
                    self.assertIn('"phase": "installed"', result.stdout)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(len(installs), 1 if variant == "installed-drift" else 0)


if __name__ == "__main__":
    unittest.main()
