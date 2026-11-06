#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed tests of the optional original-user-host systemd adapter."""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
UNIT = ROOT / "runtime/self-host/qikvrt-original-adapter.service.in"
ENFORCED = {
    "QIKVRT_API_HOST": "127.0.0.1",
    "QIKVRT_PRODUCTION_ENVIRONMENT_ENABLED": "1",
    "QIKVRT_PUBLICATION_REST_ENABLED": "0",
}


class OriginalAdapterSystemdTests(unittest.TestCase):
    def test_original_user_host_only_and_final_exec_invariants(self):
        source = UNIT.read_text(encoding="utf-8")
        self.assertEqual(source.count("ExecStart="), 1)
        self.assertIn("EnvironmentFile=@QIKVRT_PRIVATE_ENV_FILE@", source)
        self.assertIn("WorkingDirectory=@QIKVRT_SEALED_PACKAGE_ROOT@", source)
        self.assertIn("NoNewPrivileges=true", source)
        self.assertIn("UMask=0077", source)
        self.assertNotIn("QIKVRT_API_HOST=0.0.0.0", source)
        args = shlex.split(next(line.split("=", 1)[1] for line in source.splitlines()
                                if line.startswith("ExecStart=")))
        self.assertEqual(args[0], "/usr/bin/env")
        self.assertEqual(args[1:4], [f"{name}={value}" for name, value in ENFORCED.items()])
        self.assertEqual(args[4:], ["@QIKVRT_PYTHON@", "-B", "src/qikvrt_github_api_shim.py"])
        self.assertNotIn("railway", source.lower())
        self.assertNotIn("tinyfish", source.lower())

    def test_private_environment_cannot_override_final_exec(self):
        """Simulate a hostile or stale EnvironmentFile without opening a socket."""
        source = UNIT.read_text(encoding="utf-8")
        command = shlex.split(next(line.split("=", 1)[1] for line in source.splitlines()
                                   if line.startswith("ExecStart=")))
        injected = os.environ.copy()
        injected.update({"QIKVRT_API_HOST": "0.0.0.0",
                         "QIKVRT_PRODUCTION_ENVIRONMENT_ENABLED": "0",
                         "QIKVRT_PUBLICATION_REST_ENABLED": "1"})
        reader = "import json,os; print(json.dumps({k: os.environ[k] for k in %r}))" % list(ENFORCED)
        result = subprocess.run([*command[:4], sys.executable, "-c", reader],
                                env=injected, check=False, capture_output=True,
                                text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ENFORCED)

    def test_rendered_unit_has_valid_systemd_syntax(self):
        checker = shutil.which("systemd-analyze")
        if checker is None:
            self.skipTest("systemd-analyze not installed in this test environment")
        with tempfile.TemporaryDirectory(prefix="qikvrt-original-adapter-") as tmp:
            root = Path(tmp)
            env_file = root / "original-private.env"
            env_file.write_text("QIKVRT_API_HOST=0.0.0.0\n", encoding="utf-8")
            os.chmod(env_file, 0o600)
            data = UNIT.read_text(encoding="utf-8")
            data = data.replace("@QIKVRT_SEALED_PACKAGE_ROOT@", str(root))
            data = data.replace("@QIKVRT_PRIVATE_ENV_FILE@", str(env_file))
            data = data.replace("@QIKVRT_PYTHON@", sys.executable)
            target = root / "qikvrt-original-adapter.service"
            target.write_text(data, encoding="utf-8")
            result = subprocess.run([checker, "verify", str(target)], check=False,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
