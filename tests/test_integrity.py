#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools import qikvrt_integrity as integrity


class IntegrityGenerationTests(unittest.TestCase):
    def _repository(self, root: pathlib.Path) -> None:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / ".gitignore").write_text(
            "__pycache__/\n*.pyc\nlogs/\nunit_state/\ne2e_state/\n.qikvrt/runtime/\n",
            encoding="utf-8",
        )
        (root / "tools").mkdir()
        (root / "tools/qikvrt_integrity.py").write_text("# generator\n", encoding="utf-8")
        (root / "LEGACY_INTEGRITY_INVENTORIES.md").write_text("legacy map\n", encoding="utf-8")
        (root / "source.txt").write_text("tracked\n", encoding="utf-8")
        (root / "nested").mkdir()
        (root / "nested/tracked.txt").write_text("nested tracked\n", encoding="utf-8")
        (root / "new_source.py").write_text("print('untracked source')\n", encoding="utf-8")
        (root / "state").mkdir()
        (root / "state/launcher_acceptance_record.json").write_text(
            '{"accepted": true}\n', encoding="utf-8"
        )
        (root / "logs").mkdir()
        (root / "logs/runtime.jsonl").write_text("volatile\n", encoding="utf-8")
        (root / "__pycache__").mkdir()
        (root / "__pycache__/cache.pyc").write_bytes(b"cache")
        subprocess.run(
            [
                "git", "-C", str(root), "add", ".gitignore", "source.txt",
                "nested/tracked.txt",
                "state/launcher_acceptance_record.json",
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"],
            check=True,
        )

    def test_generation_is_reproducible_and_detects_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self._repository(root)
            first = integrity.generate(root)
            self.assertTrue(first.ok)
            self.assertTrue(integrity.verify(root).ok)
            outputs_before = {
                name: (root / name).read_bytes()
                for name in (integrity.MANIFEST_NAME, integrity.INDEX_NAME, integrity.DETACHED_NAME)
            }
            subprocess.run(
                [
                    "git", "-C", str(root), "-c", "user.name=Test",
                    "-c", "user.email=test@example.invalid", "commit",
                    "--allow-empty", "-qm", "history-only change",
                ],
                check=True,
            )
            self.assertTrue(integrity.verify(root).ok)
            second = integrity.generate(root)
            self.assertTrue(second.ok)
            self.assertEqual(
                outputs_before,
                {
                    name: (root / name).read_bytes()
                    for name in (integrity.MANIFEST_NAME, integrity.INDEX_NAME, integrity.DETACHED_NAME)
                },
            )
            manifest = json.loads((root / integrity.MANIFEST_NAME).read_text(encoding="utf-8"))
            entries = {entry["path"]: entry for entry in manifest["files"]}
            self.assertNotIn("git_head", manifest)
            self.assertNotIn("source_head_before_generation", manifest)
            self.assertEqual(
                manifest["repository_content_tree_sha256"],
                integrity._content_tree_sha256(manifest["files"]),
            )
            manifest_bytes = (root / integrity.MANIFEST_NAME).read_bytes()
            with tempfile.TemporaryDirectory() as outside_metadata_directory:
                outside_manifest = pathlib.Path(outside_metadata_directory) / "manifest.json"
                outside_manifest.write_bytes(manifest_bytes)
                (root / integrity.MANIFEST_NAME).unlink()
                os.symlink(outside_manifest, root / integrity.MANIFEST_NAME)
                unsafe_metadata = integrity.verify(root)
                self.assertFalse(unsafe_metadata.ok)
                self.assertIn("must not be a symlink", unsafe_metadata.message)
                (root / integrity.MANIFEST_NAME).unlink()
                (root / integrity.MANIFEST_NAME).write_bytes(manifest_bytes)
            self.assertIn("new_source.py", entries)
            self.assertNotIn("logs/runtime.jsonl", entries)
            self.assertNotIn("__pycache__/cache.pyc", entries)
            self.assertFalse(entries["state/launcher_acceptance_record.json"]["immutable"])
            self.assertEqual(entries[integrity.MANIFEST_NAME]["exclusion_reason"], "cycle_prevention")
            self.assertEqual(
                manifest["integrity_authority"]["legacy_global_inventories"],
                list(integrity.LEGACY_GLOBAL_INVENTORIES),
            )
            (root / "source.txt").write_text("changed\n", encoding="utf-8")
            verification = integrity.verify(root)
            self.assertFalse(verification.ok)
            self.assertIn("differs from deterministic regeneration", verification.message)

            # A deliberate working-tree deletion is part of the prospective
            # content tree and must not make generation crash or preserve a
            # file that no longer exists.
            (root / "source.txt").unlink()
            self.assertTrue(integrity.generate(root).ok)
            self.assertTrue(integrity.verify(root).ok)
            regenerated = json.loads(
                (root / integrity.MANIFEST_NAME).read_text(encoding="utf-8")
            )
            self.assertNotIn(
                "source.txt", {entry["path"] for entry in regenerated["files"]}
            )

            with tempfile.TemporaryDirectory() as outside_directory:
                outside = pathlib.Path(outside_directory) / "mutable.py"
                outside.write_text("print('mutable external source')\n", encoding="utf-8")
                link = root / "external_source.py"
                os.symlink(outside, link)
                with self.assertRaisesRegex(RuntimeError, "must not be a symlink"):
                    integrity.generate(root)
                link.unlink()

            with tempfile.TemporaryDirectory() as outside_parent_directory:
                outside_parent = pathlib.Path(outside_parent_directory)
                (outside_parent / "tracked.txt").write_text(
                    "nested tracked\n", encoding="utf-8"
                )
                (root / "nested/tracked.txt").unlink()
                (root / "nested").rmdir()
                os.symlink(outside_parent, root / "nested")
                with self.assertRaisesRegex(RuntimeError, "must not be a symlink"):
                    integrity.generate(root)


if __name__ == "__main__":
    unittest.main()
