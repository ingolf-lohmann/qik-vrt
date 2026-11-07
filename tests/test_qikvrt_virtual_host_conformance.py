# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Hermetic virtual-host admission regression tests: no VPS, Docker or secrets."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "runtime" / "self-host" / "host-prepare.sh"


class VirtualHostFirewallAdmission(unittest.TestCase):
    def run_dry(self, *args: str, fake_ufw: bool = True):
        """Only invoke the reviewed shell --dry-run path, in an isolated directory."""
        with tempfile.TemporaryDirectory(prefix="qikvrt-virtual-host-") as directory:
            root = Path(directory)
            tools = root / "bin"
            tools.mkdir()
            tls = root / "tls"
            env = os.environ.copy()
            env["QIKVRT_HOST_TLS_DIR"] = str(tls)
            if fake_ufw:
                ufw = tools / "ufw"
                ufw.write_text("#!/bin/sh\nexit 95\n")
                ufw.chmod(0o755)
                env["PATH"] = str(tools) + os.pathsep + env.get("PATH", "")
            else:
                awk = shutil.which("awk")
                assert awk is not None, "POSIX awk required"
                (tools / "awk").symlink_to(awk)
                env["PATH"] = str(tools)
            result = subprocess.run(
                ["/bin/sh", str(SCRIPT), "--dry-run", "--public-ip", "192.0.2.10", *args],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            # A dry-run must never create private TLS material.
            self.assertFalse(tls.exists())
            return result

    def assert_early_hold(self, result, code: str):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("HOLD_" + code, result.stderr)
        self.assertNotIn("DRY-RUN:", result.stdout)
        self.assertNotIn("QIKVRT_HOST_PREPARE=READY", result.stdout)

    def test_missing_cidr_holds_before_effects(self):
        self.assert_early_hold(self.run_dry(), "ADMIN_CIDR_REQUIRED")

    def test_broad_invalid_or_injected_cidr_is_rejected(self):
        for cidr in (
            "0.0.0.0/0", "198.51.100.2/1", "198.51.100.2/23",
            "198.51.100.2/33", "198.51.100.2", "999.0.0.1/32",
            "198.51.100.2/abc", "198.51.100.2/32;true",
            "198.51.100.2/32\n", "198.51.100.2//32",
        ):
            with self.subTest(cidr=repr(cidr)):
                self.assert_early_hold(
                    self.run_dry("--admin-cidr", cidr), "ADMIN_CIDR_INVALID"
                )

    def test_missing_ufw_holds_before_install_or_restart(self):
        self.assert_early_hold(
            self.run_dry("--admin-cidr", "198.51.100.7/32", fake_ufw=False),
            "FIREWALL_REQUIRED_FOR_REMOTE_DOCKER_API",
        )

    def test_valid_narrow_source_is_dry_only(self):
        for prefix in (24, 30, 32):
            with self.subTest(prefix=prefix):
                cidr = f"198.51.100.7/{prefix}"
                result = self.run_dry("--admin-cidr", cidr)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(
                    "DRY-RUN: ufw allow from " + cidr + " to any port 2376 proto tcp",
                    result.stdout,
                )
                self.assertNotIn("DRY-RUN: ufw allow 2376/tcp", result.stdout)

    def test_certificate_only_requires_no_remote_firewall(self):
        result = self.run_dry("--certs-only", fake_ufw=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("ufw allow", result.stdout)

    def test_negative_public_ip_holds(self):
        for address in ("999.0.2.10", "192.0.2.999", "192.0.2", "abc"):
            with self.subTest(address=address):
                result = self.run_dry("--admin-cidr", "198.51.100.7/32",
                                      "--public-ip", address)
                self.assert_early_hold(result, "PUBLIC_IPV4_REQUIRED")

    def test_listener_follows_firewall_and_no_global_fallback(self):
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertLess(script.index("run ufw --force enable"),
                        script.index("run systemctl restart docker"))
        self.assertNotIn('run ufw allow "$API_PORT/tcp"', script)
        self.assertIn('command -v ufw >/dev/null 2>&1 || die "FIREWALL_REQUIRED_FOR_REMOTE_DOCKER_API"', script)


if __name__ == "__main__":
    unittest.main()
