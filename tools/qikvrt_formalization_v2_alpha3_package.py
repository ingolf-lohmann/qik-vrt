#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the deterministic QIK-VRT Formalization v2 alpha.3 publication set."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import stat
import zipfile
from types import ModuleType
from typing import Any


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_PACKAGE_PATH = (
    REPOSITORY_ROOT
    / "formalization/QIKVRT_Formalization_v2.0/scripts/package_release.py"
)
OUTPUT_NAME = "QIKVRT_Formalization_v2.0-alpha.3.zip"
ARCHIVE_PREFIX = "QIKVRT_Formalization_v2.0-alpha.3/"
ZIP_TIMESTAMP = (2026, 7, 24, 0, 0, 0)
MANIFEST_SCHEMA = "qikvrt_formalization_v2_alpha3_zenodo_manifest_v1"
TARGET_VERSION = "2.0.0-alpha.3"
SOURCE_RECORD_ID = 21518464
CONCEPT_RECORD_ID = 21488115
SOURCE_DOI = "10.5281/zenodo.21518464"
AUTHORITY_COMMIT = "3d640b05e815ff8644fe7640ddd7dcf89d4094c4"
AUTHORITY_TREE = "6056f024cc0376f6820eca948205c30ac75d7d41"
CONTENT_TREE_SHA256 = "964801915be7eb1f33bfad52326c33bf47582fa77bd44dd572a46fc21ad79dcb"

UPLOAD_INPUTS = (
    (
        "ALPHA3_RELEASE_NOTES.md",
        "docs/publications/2026-07-24-formalization-completion/RELEASE_NOTES.md",
    ),
    (
        "FORMALIZATION_SCOPE.md",
        "formalization/QIKVRT_Formalization_v2.0/FORMALIZATION_SCOPE.md",
    ),
    (
        "VERIFICATION_REPORT.md",
        "formalization/QIKVRT_Formalization_v2.0/VERIFICATION_REPORT.md",
    ),
    (
        "EVIDENCE_BOUNDARY.md",
        "docs/publications/2026-07-23-effect-ack-lean-status/EVIDENCE_BOUNDARY.md",
    ),
    (
        "MANUSCRIPT_PROOF_MAP.md",
        "formalization/QIKVRT_Formalization_v2.0/MANUSCRIPT_PROOF_MAP.md",
    ),
    (
        "CLAIM_GRAPH.json",
        "formalization/QIKVRT_Formalization_v2.0/claims/CLAIM_GRAPH.json",
    ),
    (
        "DRAFT01_SOURCE_PROVENANCE.json",
        "formalization/QIKVRT_Formalization_v2.0/effect_ack/DRAFT01_SOURCE_PROVENANCE.json",
    ),
    (
        "DRAFT01_CLAIM_MATRIX.json",
        "formalization/QIKVRT_Formalization_v2.0/effect_ack/DRAFT01_CLAIM_MATRIX.json",
    ),
    (
        "CITATION.cff",
        "docs/publications/2026-07-24-formalization-completion/CITATION.cff",
    ),
    (
        "ZENODO_FILESET.md",
        "docs/publications/2026-07-24-formalization-completion/ZENODO_FILESET.md",
    ),
    (
        "LICENSE_NOTICE.md",
        "docs/publications/2026-07-23-effect-ack-lean-status/LICENSE_NOTICE.md",
    ),
    (
        "LICENSE-CODE",
        "formalization/QIKVRT_Formalization_v2.0/LICENSE-CODE",
    ),
    ("CC-BY-NC-ND-4.0.txt", "LICENSES/CC-BY-NC-ND-4.0.txt"),
    (
        "ALPHA2_INPUT.json",
        "formalization/QIKVRT_Formalization_v2.0/release_authorization/ALPHA2_INPUT.json",
    ),
    (
        "ALPHA2_EFFECT_ACK_DONE.json",
        "formalization/QIKVRT_Formalization_v2.0/release_authorization/ALPHA2_EFFECT_ACK_DONE.json",
    ),
    (
        "ALPHA2_PUBLIC_SOURCE_EVIDENCE.json",
        "release/formalization-v2-alpha2-public-source-evidence.json",
    ),
)

EXTRA_ARCHIVE_INPUTS = (
    "tools/qikvrt_formalization_v2_alpha3_package.py",
    "tools/qikvrt_formalization_v2_alpha3_zenodo.py",
    "release/formalization-v2-alpha2-public-source-evidence.json",
    "docs/publications/2026-07-24-formalization-completion/RELEASE_NOTES.md",
    "docs/publications/2026-07-24-formalization-completion/CITATION.cff",
    "docs/publications/2026-07-24-formalization-completion/ZENODO_FILESET.md",
)


def _load_base_package() -> ModuleType:
    spec = importlib.util.spec_from_file_location("qikvrt_alpha2_package_base", BASE_PACKAGE_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("BLOCK: cannot load the existing formalization package builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _regular_file(path: pathlib.Path) -> pathlib.Path:
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or path.is_symlink():
        raise SystemExit(f"BLOCK: package input is not a regular file: {path}")
    return path


def _md5(data: bytes) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    digest.update(data)
    return digest.hexdigest()


def _file_entry(path: pathlib.Path, name: str, root: pathlib.Path) -> dict[str, Any]:
    path = _regular_file(path)
    data = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "name": name,
        "size": len(data),
        "md5": _md5(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _validate_completed_graph(root: pathlib.Path) -> None:
    graph_path = root / "formalization/QIKVRT_Formalization_v2.0/claims/CLAIM_GRAPH.json"
    graph = json.loads(_regular_file(graph_path).read_text(encoding="utf-8"))
    counts = graph.get("counts")
    expected = {
        "nodes": 43,
        "definitionNodes": 20,
        "strongBindings": 42,
        "kernelCheckedClaims": 42,
        "conditionalCheckedClaims": 6,
        "pendingNodes": 0,
    }
    if counts != expected:
        raise SystemExit(f"BLOCK: completed claim-graph counts differ: {counts!r}")
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        raise SystemExit("BLOCK: completed claim graph has no node array")
    pending = [
        item.get("id")
        for item in nodes
        if isinstance(item, dict)
        and item.get("epistemicCategory") in {"DEFINITION", "MATHEMATICAL", "CONDITIONAL"}
        and item.get("formalizationStatus") == "PENDING"
    ]
    if pending:
        raise SystemExit(f"BLOCK: formal nodes remain pending: {pending}")


def build_archive(root: pathlib.Path, output: pathlib.Path) -> str:
    base = _load_base_package()
    files = set(base.release_inputs(root))
    for relative in EXTRA_ARCHIVE_INPUTS:
        files.add(_regular_file(root / relative))
    payloads = [
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in sorted(files, key=lambda item: item.relative_to(root).as_posix())
    ]
    provenance = {
        "schema": "qikvrt_formalization_v2_alpha3_archive_provenance_v1",
        "version": TARGET_VERSION,
        "archive_prefix": ARCHIVE_PREFIX,
        "authority_commit": AUTHORITY_COMMIT,
        "authority_tree": AUTHORITY_TREE,
        "repository_content_tree_sha256": CONTENT_TREE_SHA256,
        "entries": [
            {
                "path": relative,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for relative, data in payloads
        ],
    }
    provenance_bytes = (
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    payloads.append(("ARCHIVE_PROVENANCE.json", provenance_bytes))

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for relative, data in sorted(payloads):
            info = zipfile.ZipInfo(ARCHIVE_PREFIX + relative, ZIP_TIMESTAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def build_publication(
    root: pathlib.Path,
    archive: pathlib.Path,
    archive_checksum: pathlib.Path,
    checksum_index: pathlib.Path,
    manifest_path: pathlib.Path,
) -> dict[str, Any]:
    _validate_completed_graph(root)
    archive_sha256 = build_archive(root, archive)
    archive_checksum.parent.mkdir(parents=True, exist_ok=True)
    archive_checksum.write_text(
        f"{archive_sha256}  {OUTPUT_NAME}\n", encoding="ascii", newline="\n"
    )

    checksum_inputs = [
        (OUTPUT_NAME, _regular_file(archive)),
        (OUTPUT_NAME + ".sha256", _regular_file(archive_checksum)),
    ]
    checksum_inputs.extend(
        (name, _regular_file(root / relative)) for name, relative in UPLOAD_INPUTS
    )
    names = [name for name, _path in checksum_inputs]
    if len(names) != 18 or len(names) != len(set(names)):
        raise SystemExit("BLOCK: Alpha 3 checksum input set is not exactly 18 unique files")
    checksum_index.parent.mkdir(parents=True, exist_ok=True)
    checksum_index.write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}\n"
            for name, path in checksum_inputs
        ),
        encoding="ascii",
        newline="\n",
    )

    files = [
        _file_entry(archive, OUTPUT_NAME, root),
        _file_entry(archive_checksum, OUTPUT_NAME + ".sha256", root),
    ]
    files.extend(_file_entry(root / relative, name, root) for name, relative in UPLOAD_INPUTS)
    files.append(_file_entry(checksum_index, "ZENODO_SHA256SUMS", root))
    if len(files) != 19 or len({item["name"] for item in files}) != 19:
        raise SystemExit("BLOCK: Alpha 3 manifest does not contain exactly 19 unique uploads")

    source_evidence_sha256 = hashlib.sha256(
        (root / "release/formalization-v2-alpha2-public-source-evidence.json").read_bytes()
    ).hexdigest()
    metadata = {
        "title": "QIK-VRT: Quellengebundene Lean-4-Formalisierung des 62-seitigen Manuskripts – Alpha 3 mit vollständiger Formalumgebungsabdeckung",
        "upload_type": "software",
        "publication_date": "2026-07-24",
        "version": TARGET_VERSION,
        "language": "deu",
        "creators": [
            {
                "name": "Lohmann, Ingolf",
                "affiliation": "Independent researcher; QIK-VRT",
            }
        ],
        "access_right": "open",
        "license": "other-nc",
        "description": (
            "<p>Reproduzierbarer Alpha-3-Stand der quellengebundenen Lean-4-"
            "Formalisierung des gesperrten 62-seitigen QIK-VRT-Manuskripts. "
            "Alle 20 Definitionsumgebungen und alle 20 theorem-artigen Umgebungen "
            "besitzen einen geschlossenen maschinenlesbaren Status; 42 starke "
            "quellengebundene Bindungen sind materialisiert und kein formaler Knoten "
            "bleibt offen.</p><p>Sechs Aussagen bleiben ausdrücklich bedingt, wobei "
            "jede zusätzliche Annahme im Lean-Typ sichtbar ist. Empirische, "
            "interpretative, metaphysische, spirituelle, retrokausale und "
            "quantengravitative Aussagen werden nicht zu mathematischen Theoremen "
            "hochgestuft.</p>"
        ),
        "keywords": [
            "QIK-VRT",
            "Lean 4",
            "formal verification",
            "machine-verifiable science",
            "claim graph",
            "source provenance",
            "proof objects",
            "axiom audit",
            "conditional proof",
            "reproducible research",
        ],
        "related_identifiers": [
            {
                "identifier": SOURCE_DOI,
                "relation": "isNewVersionOf",
                "scheme": "doi",
                "resource_type": "software",
            },
            {
                "identifier": "10.5281/zenodo.21482023",
                "relation": "isSupplementTo",
                "scheme": "doi",
                "resource_type": "publication-workingpaper",
            },
        ],
        "notes": (
            "Formal-environment completion with explicit epistemic boundaries. "
            f"Authority commit {AUTHORITY_COMMIT}; Git tree {AUTHORITY_TREE}; "
            f"repository content-tree SHA-256 {CONTENT_TREE_SHA256}; deterministic "
            f"archive SHA-256 {archive_sha256}; public Alpha-2 source-evidence "
            f"SHA-256 {source_evidence_sha256}. Zenodo persistence establishes "
            "identity and byte fixity, not peer review or empirical confirmation."
        ),
    }
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "software": {
            "source_record_id": SOURCE_RECORD_ID,
            "concept_record_id": CONCEPT_RECORD_ID,
            "metadata": metadata,
            "files": files,
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=pathlib.Path, default=REPOSITORY_ROOT)
    parser.add_argument(
        "--archive",
        type=pathlib.Path,
        default=REPOSITORY_ROOT / "release/formalization-v2" / OUTPUT_NAME,
    )
    parser.add_argument("--archive-checksum", type=pathlib.Path)
    parser.add_argument(
        "--zenodo-checksums",
        type=pathlib.Path,
        default=REPOSITORY_ROOT / "release/formalization-v2/ZENODO_SHA256SUMS-alpha.3",
    )
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=REPOSITORY_ROOT / "release/formalization-v2-alpha3-zenodo.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.repository_root.resolve(strict=True)
    archive = args.archive.resolve()
    archive_checksum = (
        args.archive_checksum.resolve()
        if args.archive_checksum is not None
        else pathlib.Path(str(archive) + ".sha256")
    )
    manifest = build_publication(
        root,
        archive,
        archive_checksum,
        args.zenodo_checksums.resolve(),
        args.manifest.resolve(),
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "version": TARGET_VERSION,
                "file_count": len(manifest["software"]["files"]),
                "archive": archive.relative_to(root).as_posix(),
                "manifest": args.manifest.resolve().relative_to(root).as_posix(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
