# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[1]
TOOL = HERE / "tools/qikvrt_publication_overview.py"
SPEC = importlib.util.spec_from_file_location("qikvrt_publication_overview", TOOL)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PublicationOverviewTests(unittest.TestCase):
    def fixture(self, directory: str) -> pathlib.Path:
        root = pathlib.Path(directory)
        publications = root / "docs/publications"
        publications.mkdir(parents=True)
        (publications / "index.json").write_text(
            json.dumps(
                {
                    "schema": "qikvrt_publication_overview_v1",
                    "repository": "Goldkelch/qik-vrt",
                    "publication_bundles": [
                        {
                            "id": "historical",
                            "title": "Historical",
                            "path": "docs/publications/2026-01-01-historical/README.md",
                            "state": "repository_snapshot",
                            "repository_commit": "a" * 40,
                            "url": "https://example.invalid/historical",
                        }
                    ],
                    "featured_artifacts": [],
                    "zenodo_records": [],
                    "ietf_documents": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (publications / "index.html").write_text(
            '<html>\n<div class="collection-list">\n'
            '        <a class="collection-row" href="https://example.invalid/historical">'
            '<time>01.01.</time><span><strong>Historical</strong><small>Snapshot</small>'
            '</span><b>Öffnen →</b></a>\n'
            "      </div>\n</html>\n",
            encoding="utf-8",
        )
        historical = publications / "2026-01-01-historical"
        historical.mkdir()
        (historical / "README.md").write_text("# Historical\n", encoding="utf-8")
        return root

    def correction_fixture(self, directory: str) -> pathlib.Path:
        root = self.fixture(directory)
        (root / "policy").mkdir()
        (root / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json").write_text(json.dumps({
            "canonical_upstream": {"repository": "ingolf-lohmann/qik-vrt"},
            "mirror": {"repository": "Goldkelch/qik-vrt"},
        }))
        (root / "notice.md").write_text("# Dated correction\n")
        path = root / "docs/publications/index.json"
        index = json.loads(path.read_text())
        index.update(repository="ingolf-lohmann/qik-vrt", authority_repository="ingolf-lohmann/qik-vrt",
                     authority_correction={"notice_path": "notice.md"})
        path.write_text(json.dumps(index))
        return root

    def test_current_links_corrected_without_rewriting_historical_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.correction_fixture(directory)
            path = "docs/publications/2026-01-01-historical/README.md"
            floating = "https://github.com/Goldkelch/qik-vrt/blob/main/" + path
            pinned = "https://github.com/Goldkelch/qik-vrt/blob/" + "a" * 40 + "/" + path
            page = root / "docs/publications/index.html"
            page.write_text(page.read_text().replace("https://example.invalid/historical", floating)
                            + '<a href="' + pinned + '">Historical exact source</a>\n')
            MODULE.execute(root, materialize=True)
            self.assertIn(floating.replace("Goldkelch", "ingolf-lohmann"), page.read_text())
            self.assertIn(pinned, page.read_text())
            index = json.loads((root / "docs/publications/index.json").read_text())
            self.assertEqual(index["publication_bundles"][0]["url"], "https://example.invalid/historical")
            self.assertEqual(index["publication_bundles"][0]["current_source_url"],
                             floating.replace("Goldkelch", "ingolf-lohmann"))
            self.assertEqual(MODULE.execute(root, materialize=False)["state"], "CURRENT")
            self.assertEqual(page.read_text().count('id="authority-correction"'), 1)

    def test_correction_rejects_policy_role_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.correction_fixture(directory)
            path = root / "docs/publications/index.json"
            index = json.loads(path.read_text()); index["repository"] = "Goldkelch/qik-vrt"
            path.write_text(json.dumps(index))
            with self.assertRaisesRegex(MODULE.PublicationOverviewBlock, "current Authority policy"):
                MODULE.execute(root, materialize=False)

    def test_correction_rejects_missing_notice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.correction_fixture(directory)
            (root / "notice.md").unlink()
            with self.assertRaisesRegex(MODULE.PublicationOverviewBlock, "notice is absent"):
                MODULE.execute(root, materialize=False)

    def test_correction_rejects_source_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.correction_fixture(directory)
            path = root / "docs/publications/index.json"
            index = json.loads(path.read_text())
            index["publication_bundles"][0]["path"] = "../outside.md"
            path.write_text(json.dumps(index))
            with self.assertRaisesRegex(MODULE.PublicationOverviewBlock, "escaped the repository"):
                MODULE.execute(root, materialize=False)

    def test_missing_bundle_materializes_both_indexes_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            qce = root / "docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence"
            qce.mkdir()
            (qce / "README.md").write_text(
                "# QIK-VRT Quantum Causal Emergence (QCE)\n\n"
                "## Unschärfe, Planck-Übergangselement und klassischer Lichtkegel\n\n"
                "Publication ID: `qikvrt-quantum-causal-emergence-v1`\n\n"
                "Physical Correspondence = OPEN_CANDIDATE\n",
                encoding="utf-8",
            )
            first = MODULE.execute(root, materialize=False)
            self.assertEqual(first["state"], "DRIFT")
            self.assertEqual(
                first["changed_paths"],
                ["docs/publications/index.json", "docs/publications/index.html"],
            )
            materialized = MODULE.execute(root, materialize=True)
            self.assertEqual(materialized["state"], "MATERIALIZED")
            current = MODULE.execute(root, materialize=False)
            self.assertEqual(current["state"], "CURRENT")
            index = json.loads((root / "docs/publications/index.json").read_text())
            entries = {item["path"]: item for item in index["publication_bundles"]}
            path = "docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence/README.md"
            self.assertEqual(entries[path]["id"], "qikvrt-quantum-causal-emergence-v1")
            self.assertEqual(entries[path]["state"], "repository_candidate_open_correspondence")
            html = (root / "docs/publications/index.html").read_text(encoding="utf-8")
            self.assertIn(path, html)
            self.assertIn("05.08.", html)
            self.assertIn("Unschärfe, Planck-Übergangselement", html)

    def test_explicit_index_state_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            bundle = root / "docs/publications/2026-08-06-review-bound"
            bundle.mkdir()
            (bundle / "README.md").write_text(
                "# Review Bound\n\n"
                "Publication ID: `review-bound-v1`\n"
                "Publication Index State: `repository_candidate_human_physics_review_pending`\n",
                encoding="utf-8",
            )
            MODULE.execute(root, materialize=True)
            index = json.loads((root / "docs/publications/index.json").read_text())
            entry = next(item for item in index["publication_bundles"] if item["id"] == "review-bound-v1")
            self.assertEqual(
                entry["state"],
                "repository_candidate_human_physics_review_pending",
            )

    def test_existing_snapshot_entry_is_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            before = json.loads((root / "docs/publications/index.json").read_text())
            MODULE.execute(root, materialize=True)
            after = json.loads((root / "docs/publications/index.json").read_text())
            self.assertEqual(before["publication_bundles"][0], after["publication_bundles"][0])

    def test_duplicate_identifier_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            bundle = root / "docs/publications/2026-08-06-duplicate"
            bundle.mkdir()
            (bundle / "README.md").write_text(
                "# Duplicate\n\nPublication ID: `historical`\n",
                encoding="utf-8",
            )
            with self.assertRaises(MODULE.PublicationOverviewBlock):
                MODULE.execute(root, materialize=True)

    def test_cli_check_emits_exact_drift_signature(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            bundle = root / "docs/publications/2026-08-06-new"
            bundle.mkdir()
            (bundle / "README.md").write_text("# New\n", encoding="utf-8")
            process = subprocess.run(
                [sys.executable, str(TOOL), "check", "--root", str(root), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(process.returncode, 2)
            self.assertIn(MODULE.DRIFT_SIGNATURE, process.stderr)

    def public_corpus_fixture(self, directory: str) -> pathlib.Path:
        root = self.fixture(directory)
        path = root / "docs/publications/index.json"
        index = json.loads(path.read_text())
        index["verified_public_corpus"] = {
            "coverage_path": "coverage.json", "metadata_path": "metadata.json",
            "readback_path": "readback.json",
        }
        path.write_text(json.dumps(index) + "\n")
        html = root / "docs/publications/index.html"
        html.write_text(html.read_text().replace("</html>", '  <section class="section" id="grenzen"></section></html>'))
        records = [{"record_id": rid, "concept_record_id": "90", "doi": f"10.5281/zenodo.{rid}"}
                   for rid in (91, 92)]
        (root / "coverage.json").write_text(json.dumps({
            "zenodo": records, "zenodo_concept_family_count": 1,
            "ietf": [{"name": "draft-lohmann-example-00", "url": "https://www.ietf.org/archive/id/draft-lohmann-example-00.txt", "http_status": 200}],
        }))
        native = {str(rid): {"id": rid, "doi": f"10.5281/zenodo.{rid}",
                            "conceptrecid": "90", "conceptdoi": "10.5281/zenodo.90",
                            "submitted": True, "status": "published",
                            "metadata": {"title": f"Version {rid}", "publication_date": "2026-10-15"}}
                  for rid in (91, 92)}
        (root / "metadata.json").write_text(json.dumps({"records": native}))
        (root / "readback.json").write_text(json.dumps({
            "observed_at": "2026-10-15T10:00:00Z", "zenodo_record_ids": [91, 92],
            "all_public_queries_complete": True, "all_native_family_versions_complete": True,
            "all_original_files_match_fresh_metadata": True,
            "ietf_revision_names": ["draft-lohmann-example-00"],
        }))
        return root

    def test_public_corpus_projects_versions_and_native_ietf_without_counting_concepts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.public_corpus_fixture(directory)
            MODULE.execute(root, materialize=True)
            index = json.loads((root / "docs/publications/index.json").read_text())
            self.assertEqual(len(index["zenodo_records"]), 2)
            self.assertEqual({item["concept_doi"] for item in index["zenodo_records"]}, {"10.5281/zenodo.90"})
            self.assertEqual(index["ietf_documents"][0]["state"], "published_internet_draft")
            html = (root / "docs/publications/index.html").read_text()
            self.assertIn("10.5281/zenodo.91", html)
            self.assertIn("10.5281/zenodo.92", html)
            self.assertIn("draft-lohmann-example-00", html)
            self.assertEqual(MODULE.execute(root, materialize=False)["state"], "CURRENT")

    def test_public_corpus_rejects_omitted_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.public_corpus_fixture(directory)
            path = root / "coverage.json"
            value = json.loads(path.read_text())
            value["zenodo"].pop()
            path.write_text(json.dumps(value))
            with self.assertRaises(MODULE.PublicationOverviewBlock):
                MODULE.execute(root, materialize=True)

    def test_public_corpus_rejects_unpublished_native_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.public_corpus_fixture(directory)
            path = root / "metadata.json"
            value = json.loads(path.read_text())
            value["records"]["91"]["submitted"] = False
            path.write_text(json.dumps(value))
            with self.assertRaises(MODULE.PublicationOverviewBlock):
                MODULE.execute(root, materialize=True)


if __name__ == "__main__":
    unittest.main()
