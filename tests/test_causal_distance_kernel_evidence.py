# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Mutation controls: invalid proof packages must fail before invoking Lean."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from tools import qikvrt_causal_distance_kernel_evidence as evidence


class EvidenceMutationControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.plan = copy.deepcopy(json.loads((evidence.ROOT / evidence.PLAN).read_text()))
        for raw in [evidence.PLAN, *self.plan["source_bindings"],
                    *(evidence.PUBLICATION + "/negative/" + n for n in self.plan["negative_controls"])]:
            target = self.root / raw
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(evidence.ROOT / raw, target)

    def reject_before_execution(self, expected):
        (self.root / evidence.PLAN).write_text(json.dumps(self.plan))
        with patch.object(evidence, "ROOT", self.root), patch.object(
                evidence, "PROJECT", self.root / "formalization/QIKVRT_Formalization_v2.0"), patch.object(
                evidence.original, "run", side_effect=AssertionError("invalid candidate reached execution")):
            with self.assertRaisesRegex(evidence.original.EvidenceError, expected):
                evidence.verify()

    def test_changed_source_is_not_verified_by_old_receipt(self):
        source = next(p for p in self.plan["source_bindings"] if p.endswith("CausalDistance.lean"))
        with (self.root / source).open("a") as file:
            file.write("\n-- changed candidate\n")
        self.reject_before_execution("source identity differs")

    def test_new_project_axiom_is_not_admitted(self):
        theorem = next(iter(self.plan["expected_axioms_by_theorem"]))
        self.plan["expected_axioms_by_theorem"][theorem].append("MyUnprovedPhysics")
        self.reject_before_execution("forbidden axiom policy")

    def test_placeholder_cannot_be_hidden_by_rehashing(self):
        source = next(p for p in self.plan["source_bindings"] if p.endswith("CausalDistance.lean"))
        path = self.root / source
        path.write_text(path.read_text() + "\ntheorem bypass : False := by sorry\n")
        self.plan["source_bindings"][source] = evidence.original.identity(path, self.root)
        self.reject_before_execution("proof escape")

    def test_disconnected_module_cannot_be_hidden_by_rehashing(self):
        source = next(p for p in self.plan["source_bindings"] if p.endswith("/QIKVRTEffectAck.lean"))
        path = self.root / source
        path.write_text(path.read_text().replace("import QIKVRTEffectAck.CausalDistance\n", ""))
        self.plan["source_bindings"][source] = evidence.original.identity(path, self.root)
        self.reject_before_execution("unconnected module")


if __name__ == "__main__":
    unittest.main()
