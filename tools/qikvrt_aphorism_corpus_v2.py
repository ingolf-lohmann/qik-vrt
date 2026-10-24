#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
"""Verified loader for the QIK-VRT aphorism-corpus materializer."""
from __future__ import annotations

import hashlib
import json
import zlib
from pathlib import Path

_IMPL_PATH = Path(__file__).resolve().with_name("qikvrt_aphorism_corpus_v2_impl") / "impl.py.zlib"
_IMPL_COMPRESSED_BYTES = 5834
_IMPL_COMPRESSED_SHA256 = "0a1b48161d86c092ab733b94ef7407e78069466549ee710ee9018f522e269e7b"
_IMPL_SOURCE_SHA256 = "4c69dbbcb42c037608d9b42a803f1367ece897d192d47cfd7665e193d5c7e2c0"

AUTHOR_NAME = "Ingolf Lohmann"
AUTHOR_NAME_CORRECTIONS = (
    "Ingolph Lomann", "Ingolph Lommern", "Ingolv Lohmann", "Ingolv Lomann",
    "Englouf Lohmann", "Engolv Loman", "Engel und Lomann", "Engel und Loman",
    "engolf Lommann", "engolfloh man",
)


def author_name_reading_check(text):
    return (AUTHOR_NAME in text and "Redaktionelle Namenskorrektur" in text
            and not any(wrong in text for wrong in AUTHOR_NAME_CORRECTIONS))


def corrected_author_names(files):
    """Correct reading copies while retaining the exact original ASR evidence."""
    result = dict(files)
    tex_name = "QIK-VRT_Aphorism_Corpus_Scientific_Assessment_2026-08-04.tex"
    original_tex, mode = result[tex_name]
    text = original_tex.decode("utf-8")
    replacements = []
    for wrong in AUTHOR_NAME_CORRECTIONS:
        count = text.count(wrong)
        if count:
            replacements.append({"original": wrong, "corrected": AUTHOR_NAME, "count": count})
            text = text.replace(wrong, AUTHOR_NAME)
    if not replacements:
        raise SystemExit("BLOCK: author-name correction predecessor differs")
    notice = (
        "\\begin{boundarybox}{Redaktionelle Namenskorrektur vom 24. Oktober 2026}\n"
        "Der Autor heißt Ingolf Lohmann. In den wiedergegebenen ASR-Texten wurde "
        "ausschließlich sein falsch erkannter Name berichtigt. Die unveränderten "
        "maschinellen Originalausgaben und ihre Prüfsummen bleiben im Begleitpaket "
        "erhalten. Dies ist keine akustische Verbatim-Zertifizierung und ändert "
        "keine wissenschaftliche Aussage.\n\\end{boundarybox}\n\n"
    )
    text = text.replace("\\tableofcontents", notice + "\\tableofcontents", 1)
    text = text.replace(
        "Die folgenden Texte sind unveränderte Modellausgaben",
        "Die folgenden Texte sind ASR-Lesefassungen mit redaktionell korrigierter Namensschreibweise",
    )
    text = text.replace(
        "ihre Unterschiede werden nicht geglättet.",
        "ihre Unterschiede werden bis auf die offengelegte Namenskorrektur nicht geglättet.",
    )
    text = text.replace("Automatischer Pass 1 - Originaldatei", "Lesefassung aus automatischem Pass 1")
    text = text.replace("Automatischer Pass 2 - normalisierter Cross-Check", "Lesefassung aus automatischem Pass 2")
    result[tex_name] = (text.encode("utf-8"), mode)
    originals = []
    for name, (raw, _mode) in sorted(files.items()):
        if name == "ASR_LEDGER.json" or name.startswith("transcripts/"):
            originals.append({"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
        if name.startswith("transcripts/") and name.endswith(".txt"):
            reading = raw.decode("utf-8")
            for wrong in AUTHOR_NAME_CORRECTIONS:
                reading = reading.replace(wrong, AUTHOR_NAME)
            result["transcripts/editorial/" + name.removeprefix("transcripts/")] = (reading.encode("utf-8"), 0o644)
    correction = {
        "schema": "qikvrt-author-name-correction/v1", "author": AUTHOR_NAME,
        "authorized_by": "Direct Principal instruction, Ingolf Lohmann, 2026-10-24",
        "scope": "AUTHOR_NAME_SPELLING_ONLY", "replacements_in_article": replacements,
        "original_tex_sha256": hashlib.sha256(original_tex).hexdigest(),
        "corrected_tex_sha256": hashlib.sha256(result[tex_name][0]).hexdigest(),
        "original_asr_files_unchanged": originals,
        "reading_transcripts": "transcripts/editorial/",
        "human_acoustic_verbatim_certification": False,
        "scientific_claims_changed": False, "zenodo_publication_verified": False,
    }
    result["AUTHOR_NAME_CORRECTION.json"] = ((json.dumps(correction, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"), 0o644)
    appendix = (
        "\n## Namenskorrektur vom 24. Oktober 2026\n\n"
        "Der Autor heißt **Ingolf Lohmann**. Artikel und redaktionelle Lesetranskripte "
        "verwenden diese Schreibweise. `AUTHOR_NAME_CORRECTION.json` dokumentiert "
        "die Namenskorrekturen und die unveränderten ASR-Originale; "
        "`transcripts/editorial/` enthält die korrigierten Lesefassungen. "
        "Die Korrektur bestätigt weder den übrigen erkannten Wortlaut noch eine "
        "Zenodo-Veröffentlichung.\n"
    )
    raw, mode = result["README.md"]
    result["README.md"] = (raw + appendix.encode("utf-8"), mode)
    return result

def _load_verified_source() -> bytes:
    if not _IMPL_PATH.is_file() or _IMPL_PATH.is_symlink():
        raise SystemExit(f"BLOCK: materializer implementation is absent or symlinked: {_IMPL_PATH}")
    compressed = _IMPL_PATH.read_bytes()
    if len(compressed) != _IMPL_COMPRESSED_BYTES:
        raise SystemExit(f"BLOCK: materializer compressed implementation length differs: {len(compressed)}")
    if hashlib.sha256(compressed).hexdigest() != _IMPL_COMPRESSED_SHA256:
        raise SystemExit("BLOCK: materializer compressed implementation SHA-256 mismatch")
    try:
        source = zlib.decompress(compressed)
    except Exception as exc:
        raise SystemExit(f"BLOCK: materializer implementation cannot be decompressed: {exc}") from exc
    if hashlib.sha256(source).hexdigest() != _IMPL_SOURCE_SHA256:
        raise SystemExit("BLOCK: materializer source SHA-256 mismatch")
    return source

exec(
    compile(_load_verified_source(), str(Path(__file__).with_suffix(".verified-impl.py")), "exec"),
    globals(),
    globals(),
)
