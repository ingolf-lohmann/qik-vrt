"""TEMDD RED: durable fenced admission required for successor publication."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "tools/qikvrt_autonomous_self_heal.py"

class WriterFencingRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        cls.parts = {node.name: ast.get_source_segment(source, node) for node in tree.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

    def test_no_unfenced_branch_patch(self):
        self.assertNotIn('api.call("PATCH", "git/refs/heads/"',
                         self.parts["export_rest_successor"])

    def test_atomic_multiref_cas_required(self):
        self.assertIn("updateRefs", self.parts["export_rest_successor"])

    def test_durable_claim_must_bind_lease_and_fence(self):
        claim = self.parts["claim_pr_plan"].lower()
        self.assertIn("lease", claim)
        self.assertIn("fencing", claim)

if __name__ == "__main__":
    unittest.main()
