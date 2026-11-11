# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Writer inventory must never claim a permission or ruleset guarantee."""
import tempfile
import unittest
from pathlib import Path
from tools.qikvrt_writer_authority_inventory import inventory


class WriterInventoryTests(unittest.TestCase):
    def test_empty_workflows_still_hold(self):
        with tempfile.TemporaryDirectory() as d:
            receipt = inventory(Path(d))
            self.assertEqual(receipt["state"], "HOLD")
            self.assertFalse(receipt["universal_writer_enforcement_proven"])

    def test_write_permission_and_git_push_are_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.yml").write_text(
                "name: Writer\npermissions:\n  contents: write\nsteps:\n"
                "  - run: git push origin HEAD:main\n", encoding="utf-8")
            (root / "b.yaml").write_text("name: Reader\npermissions:\n  contents: read\n",
                                         encoding="utf-8")
            receipt = inventory(root)
            self.assertEqual(receipt["workflows_scanned"], 2)
            self.assertEqual(len(receipt["potential_writers"]), 1)
            self.assertEqual(receipt["potential_writers"][0]["path"], str(root / "a.yml"))
            self.assertEqual(receipt["state"], "HOLD")
            self.assertFalse(receipt["universal_writer_enforcement_proven"])


if __name__ == "__main__":
    unittest.main()
