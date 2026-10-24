# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tarfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/qikvrt_aphorism_corpus_v2.py"
DEST = ROOT / "docs/publications/2026-08-04-aphorism-corpus-scientific-assessment"
WORKFLOW = ROOT / ".github/workflows/qikvrt_batch04_integrity.yml"


def load_tool():
    spec = importlib.util.spec_from_file_location("qikvrt_aphorism_corpus_v2", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load aphorism materializer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AphorismCorpusV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tool = load_tool()

    def test_payload_is_bounded_and_contains_no_audio(self) -> None:
        raw = self.tool.payload_bytes()
        self.assertEqual(self.tool.sha256_bytes(raw), self.tool.PAYLOAD_SHA256)
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:xz") as archive:
            names = archive.getnames()
        self.assertGreaterEqual(len(names), 40)
        self.assertIn("ASR_LEDGER.json", names)
        self.assertIn(
            "QIK-VRT_Aphorism_Corpus_Scientific_Assessment_2026-08-04.tex",
            names,
        )
        self.assertFalse(
            any(
                pathlib.Path(name).suffix.lower()
                in {".m4a", ".wav", ".mp3", ".ogg", ".aac", ".flac"}
                for name in names
            )
        )

    def test_declared_boundaries_remain_fail_closed(self) -> None:
        files = self.tool.payload_files()
        claims = json.loads(files["CLAIM_MATRIX.json"][0].decode("utf-8"))
        self.assertEqual(
            claims["release_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )
        ledger = json.loads(files["ASR_LEDGER.json"][0].decode("utf-8"))
        self.assertEqual(ledger["automatic_asr_two_pass_count"], 7)
        self.assertEqual(ledger["human_acoustic_verbatim_certification_count"], 0)
        self.assertTrue(
            all(item["verbatim_status"] == "NOT_VERIFIED" for item in ledger["items"])
        )

    def test_reading_copy_corrects_names_and_preserves_original_asr_bytes(self) -> None:
        with tarfile.open(fileobj=io.BytesIO(self.tool.payload_bytes()), mode="r:xz") as archive:
            originals = {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
        files = self.tool.payload_files()
        tex_name = "QIK-VRT_Aphorism_Corpus_Scientific_Assessment_2026-08-04.tex"
        original = originals[tex_name].decode()
        corrected = files[tex_name][0].decode()
        self.assertTrue(any(name in original for name in self.tool.AUTHOR_NAME_CORRECTIONS))
        self.assertTrue(all(name not in corrected for name in self.tool.AUTHOR_NAME_CORRECTIONS))
        self.assertIn("Ingolf Lohmann", corrected)
        self.assertIn("Redaktionelle Namenskorrektur", corrected)
        receipt = json.loads(files["AUTHOR_NAME_CORRECTION.json"][0])
        self.assertEqual(sum(x["count"] for x in receipt["replacements_in_article"]), 24)
        self.assertEqual(len(receipt["replacements_in_article"]), 10)
        self.assertNotIn("unveränderte Modellausgaben", corrected)
        for item in receipt["original_asr_files_unchanged"]:
            self.assertEqual(originals[item["path"]], files[item["path"]][0])
            self.assertEqual(item["sha256"], hashlib.sha256(originals[item["path"]]).hexdigest())
        for name, (raw, _mode) in files.items():
            if name.startswith("transcripts/editorial/"):
                self.assertFalse(any(w.encode() in raw for w in self.tool.AUTHOR_NAME_CORRECTIONS))
        self.assertIs(receipt["scientific_claims_changed"], False)
        self.assertIs(receipt["human_acoustic_verbatim_certification"], False)

    def test_unrecognized_correction_predecessor_is_rejected(self) -> None:
        with self.assertRaisesRegex(SystemExit, "predecessor differs"):
            self.tool.corrected_author_names({
                "QIK-VRT_Aphorism_Corpus_Scientific_Assessment_2026-08-04.tex": (b"Ingolf Lohmann", 0o644),
            })

    def test_pdf_reading_check_rejects_original_misspellings_and_missing_notice(self) -> None:
        self.assertFalse(self.tool.author_name_reading_check("Ingolf Lohmann"))
        prefix = "Ingolf Lohmann Redaktionelle Namenskorrektur "
        self.assertTrue(self.tool.author_name_reading_check(prefix))
        for wrong in self.tool.AUTHOR_NAME_CORRECTIONS:
            with self.subTest(wrong=wrong):
                self.assertFalse(self.tool.author_name_reading_check(prefix + wrong))

    def test_repository_writer_provisions_publication_runtime_before_use(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        provision = (
            "- name: Provision and verify aphorism publication runtime when present"
        )
        materialize = (
            "- name: Materialize aphorism-corpus scientific assessment when present"
        )
        self.assertIn(provision, workflow)
        self.assertIn(materialize, workflow)
        self.assertLess(workflow.index(provision), workflow.index(materialize))

        start = workflow.index(provision)
        end = workflow.index(materialize)
        block = workflow[start:end]
        for token in (
            "sudo apt-get update -o Acquire::Retries=3",
            "apt-get install --yes --no-install-recommends",
            "texlive-xetex",
            "texlive-latex-extra",
            "texlive-lang-german",
            "texlive-fonts-recommended",
            "fonts-lmodern",
            "poppler-utils",
            "command -v xelatex",
            "command -v pdfinfo",
            "command -v pdftotext",
            "command -v pdftoppm",
            "command -v pdffonts",
            "xelatex --version",
            "dpkg-query --show",
        ):
            self.assertIn(token, block)

    def test_repository_writer_serializes_and_fails_closed_on_ref_drift(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "group: qikvrt-repository-evidence-${{ github.head_ref || github.ref_name }}",
            workflow,
        )
        self.assertNotIn(
            "qikvrt-repository-evidence-${{ github.event_name }}-",
            workflow,
        )
        commit_step = workflow.index("- name: Commit materialized repository evidence")
        block = workflow[commit_step:]
        for token in (
            'source_head="$(git rev-parse --verify HEAD^{commit})"',
            'git ls-remote --heads origin "refs/heads/$TARGET_REF"',
            "BLOCK: target ref advanced before repository evidence persistence",
            "remote_head_after_commit",
            "BLOCK: target ref advanced while repository evidence was materialized",
            'git push origin "HEAD:$TARGET_REF"',
        ):
            self.assertIn(token, block)
        self.assertLess(
            block.index("BLOCK: target ref advanced before repository evidence persistence"),
            block.index("git commit -m \"ci: materialize repository evidence\""),
        )
        self.assertLess(
            block.index("remote_head_after_commit"),
            block.index('git push origin "HEAD:$TARGET_REF"'),
        )

    def test_materialized_bundle_when_present(self) -> None:
        if not DEST.is_dir():
            self.skipTest("repository evidence materializer has not run on this head")
        completed = subprocess.run(
            [sys.executable, "-B", str(TOOL), "--check", "--json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        self.assertIn(
            '"state": "SOURCE_AND_GENERATED_BYTES_VERIFIED"',
            completed.stdout,
        )
        receipt = json.loads((DEST / "PDF_RENDER_RECEIPT.json").read_text())
        self.assertIs(receipt["render"]["cross_references_stable"], True)
        self.assertGreaterEqual(receipt["render"]["latex_passes"], 2)


if __name__ == "__main__":
    unittest.main()
