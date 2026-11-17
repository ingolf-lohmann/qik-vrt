#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministically keep the human and machine publication indexes complete."""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys
from typing import Any, Sequence

DEFAULT_ROOT = pathlib.Path(__file__).resolve().parents[1]
MACHINE_INDEX = pathlib.Path("docs/publications/index.json")
HUMAN_INDEX = pathlib.Path("docs/publications/index.html")
PUBLICATIONS_DIRECTORY = pathlib.Path("docs/publications")
EXPECTED_SCHEMA = "qikvrt_publication_overview_v1"
DRIFT_SIGNATURE = "publication overview drift:"
COLLECTION_PATTERN = re.compile(
    r'(?P<open><div class="collection-list">\n)'
    r'(?P<body>.*?)'
    r'(?P<close>      </div>)',
    re.DOTALL,
)
DATE_PREFIX = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})-")
PUBLICATION_ID = re.compile(r"^Publication ID:\s*`(?P<value>[^`]+)`\s*$", re.MULTILINE)
INDEX_STATE = re.compile(
    r"^Publication Index State:\s*`(?P<value>[^`]+)`\s*$",
    re.MULTILINE,
)
HEADING = re.compile(r"^(?P<level>#{1,2})\s+(?P<value>\S.*)$", re.MULTILINE)
VALID_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class PublicationOverviewBlock(RuntimeError):
    """A fail-closed publication overview error."""


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PublicationOverviewBlock(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PublicationOverviewBlock(f"{path} must contain one JSON object")
    if value.get("schema") != EXPECTED_SCHEMA:
        raise PublicationOverviewBlock(f"unsupported publication index schema in {path}")
    bundles = value.get("publication_bundles")
    if not isinstance(bundles, list) or not all(isinstance(item, dict) for item in bundles):
        raise PublicationOverviewBlock("publication_bundles must be a list of objects")
    return value


def _read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PublicationOverviewBlock(f"cannot read {path}: {exc}") from exc


def _heading_values(text: str) -> tuple[str, str | None]:
    h1: str | None = None
    h2: str | None = None
    for match in HEADING.finditer(text):
        value = match.group("value").strip()
        if match.group("level") == "#" and h1 is None:
            h1 = value
        elif match.group("level") == "##" and h2 is None:
            h2 = value
        if h1 is not None and h2 is not None:
            break
    if h1 is None:
        raise PublicationOverviewBlock("publication README has no H1 title")
    return h1, h2


def _derive_identifier(text: str, directory_name: str) -> str:
    match = PUBLICATION_ID.search(text)
    value = match.group("value").strip() if match else directory_name
    value = value.lower().replace(" ", "-")
    value = re.sub(r"[^a-z0-9._-]+", "-", value).strip("-._")
    if not VALID_IDENTIFIER.fullmatch(value):
        raise PublicationOverviewBlock(f"cannot derive a safe publication id from {directory_name}")
    return value


def _derive_state(text: str) -> str:
    explicit = INDEX_STATE.search(text)
    if explicit:
        value = explicit.group("value").strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", value):
            raise PublicationOverviewBlock("Publication Index State is not a safe identifier")
        return value
    lower = text.casefold()
    if "human physics review" in lower or "human-physics-review" in lower:
        return "repository_candidate_human_physics_review_pending"
    if "human acoustic review" in lower or "menschliche verbatim-prüfung offen" in lower:
        return "repository_candidate_human_acoustic_review_pending"
    if "open_candidate" in lower or "physikalische korrespondenz" in lower:
        return "repository_candidate_open_correspondence"
    return "repository_candidate"


def _date_label(directory_name: str) -> str:
    match = DATE_PREFIX.match(directory_name)
    if not match:
        return "Neu"
    return f"{match.group('day')}.{match.group('month')}."


def _metadata(root: pathlib.Path, readme: pathlib.Path) -> dict[str, str]:
    text = _read_text(readme)
    title, subtitle = _heading_values(text)
    relative = readme.relative_to(root).as_posix()
    directory_name = readme.parent.name
    return {
        "id": _derive_identifier(text, directory_name),
        "title": title,
        "subtitle": subtitle or "Repository-Bündel mit expliziten Evidenzgrenzen",
        "path": relative,
        "state": _derive_state(text),
        "date_label": _date_label(directory_name),
    }


def _local_readmes(root: pathlib.Path) -> list[pathlib.Path]:
    directory = root / PUBLICATIONS_DIRECTORY
    if not directory.is_dir():
        raise PublicationOverviewBlock(f"publication directory is absent: {directory}")
    result = sorted(path for path in directory.glob("*/README.md") if path.is_file())
    if not result:
        raise PublicationOverviewBlock("no local publication README files were found")
    return result


def _validate_bundles(bundles: list[dict[str, Any]]) -> None:
    paths: set[str] = set()
    identifiers: set[str] = set()
    for item in bundles:
        path = item.get("path")
        identifier = item.get("id")
        if not isinstance(path, str) or not path:
            raise PublicationOverviewBlock("publication bundle path is missing")
        if not isinstance(identifier, str) or not VALID_IDENTIFIER.fullmatch(identifier):
            raise PublicationOverviewBlock(f"invalid publication bundle id for {path}")
        if path in paths:
            raise PublicationOverviewBlock(f"duplicate publication bundle path: {path}")
        if identifier in identifiers:
            raise PublicationOverviewBlock(f"duplicate publication bundle id: {identifier}")
        paths.add(path)
        identifiers.add(identifier)


def _row(repository: str, item: dict[str, str]) -> str:
    path = item["path"]
    href = f"https://github.com/{repository}/blob/main/{path}"
    return (
        f'        <a class="collection-row" href="{html.escape(href, quote=True)}">'
        f'<time>{html.escape(item["date_label"])}</time><span>'
        f'<strong>{html.escape(item["title"])}</strong>'
        f'<small>{html.escape(item["subtitle"])}</small></span>'
        f'<b>Öffnen →</b></a>'
    )


def _project_public_corpus(root: pathlib.Path, index: dict[str, Any], text: str) -> str:
    """Project the existing exact corpus; never infer publication from a candidate."""
    config = index.get("verified_public_corpus")
    if config is None:
        return text
    if not isinstance(config, dict):
        raise PublicationOverviewBlock("verified_public_corpus must be an object")

    def load(key: str) -> dict[str, Any]:
        relative = config.get(key)
        if not isinstance(relative, str):
            raise PublicationOverviewBlock(f"public corpus lacks {key}")
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()):
            raise PublicationOverviewBlock("public corpus path escaped the repository")
        try:
            value = json.loads(_read_text(path))
        except ValueError as exc:
            raise PublicationOverviewBlock(f"invalid public corpus {key}") from exc
        if not isinstance(value, dict):
            raise PublicationOverviewBlock(f"public corpus {key} must be an object")
        return value

    coverage = load("coverage_path")
    metadata = load("metadata_path")
    readback = load("readback_path")
    records = coverage.get("zenodo", [])
    ids = [item["record_id"] for item in records]
    if (not ids or len(ids) != len(set(ids))
            or sorted(ids) != sorted(readback.get("zenodo_record_ids", []))
            or readback.get("all_public_queries_complete") is not True
            or readback.get("all_native_family_versions_complete") is not True
            or readback.get("all_original_files_match_fresh_metadata") is not True):
        raise PublicationOverviewBlock("public corpus coverage/readback is incomplete")
    native = metadata.get("records", {})
    indexed = {entry["doi"]: entry for entry in index["zenodo_records"]}
    rendered = []
    for item in sorted(records, key=lambda value: value["record_id"]):
        rid = item["record_id"]
        record = native.get(str(rid), {})
        if (record.get("id") != rid or record.get("submitted") is not True
                or record.get("status") != "published"
                or record.get("doi") != item.get("doi")
                or str(record.get("conceptrecid")) != str(item.get("concept_record_id"))):
            raise PublicationOverviewBlock(f"public corpus identity/state mismatch: {rid}")
        doi = record["doi"]
        concept = record["conceptdoi"]
        entry = indexed.get(doi)
        if entry is None:
            entry = {"id": f"zenodo-record-{rid}", "title": record["metadata"]["title"],
                     "doi": doi, "doi_url": f"https://doi.org/{doi}",
                     "state": "published_record"}
            index["zenodo_records"].append(entry)
            indexed[doi] = entry
        if entry.get("concept_doi", concept) != concept:
            raise PublicationOverviewBlock(f"conflicting concept DOI: {rid}")
        entry.update({"record_id": rid, "concept_doi": concept,
                      "version": record["metadata"].get("version"),
                      "publication_date": record["metadata"]["publication_date"],
                      "native_title": record["metadata"]["title"],
                      "record_url": f"https://zenodo.org/records/{rid}",
                      "corpus_coverage_path": config["coverage_path"]})
        esc = html.escape
        rendered.append(
            f'<tr><td>{rid}</td><td>{esc(entry["native_title"])}</td>'
            f'<td>{esc(str(entry["version"] or "nicht angegeben"))}</td>'
            f'<td><a href="https://doi.org/{doi}">{doi}</a></td>'
            f'<td><a href="https://doi.org/{concept}">{concept}</a></td></tr>'
        )
    revisions = coverage.get("ietf", [])
    if sorted(row["name"] for row in revisions) != sorted(readback.get("ietf_revision_names", [])):
        raise PublicationOverviewBlock("public IETF revision/readback mismatch")
    ietf_index = {entry["id"]: entry for entry in index["ietf_documents"]}
    for revision in revisions:
        if revision.get("http_status") != 200:
            raise PublicationOverviewBlock("unpublished IETF revision in public coverage")
        name = revision["name"]
        if name not in ietf_index:
            entry = {"id": name, "title": name,
                     "state": "published_internet_draft", "official_url": revision["url"],
                     "corpus_readback_path": config["readback_path"],
                     "boundary": "Individual Internet-Draft; work in progress; not an RFC or IETF consensus."}
            index["ietf_documents"].append(entry)
            ietf_index[name] = entry
    revision_rows = "".join(
        f'<li><a href="{html.escape(row["url"], quote=True)}">{html.escape(row["name"])}</a></li>'
        for row in revisions
    )
    draft_count = len({row["name"].rsplit("-", 1)[0] for row in revisions})
    candidates = [row for row in index["ietf_documents"]
                  if row["id"] not in {item["name"] for item in revisions}]
    candidate_rows = "".join(
        f'<li>{html.escape(row["id"])} — {html.escape(row["state"])}</li>'
        for row in candidates
    )
    begin = "<!-- QIKVRT_PUBLIC_CORPUS_BEGIN -->"
    end = "<!-- QIKVRT_PUBLIC_CORPUS_END -->"
    section = (f'{begin}\n<section class="section" id="gesamtbestand"><div class="wrap">'
               '<h2>Vollständiger ermittelter öffentlicher Bestand</h2>'
               f'<p>Registerabgleich: {html.escape(readback["observed_at"])}. '
               f'{len(records)} Zenodo-Versionen in {coverage["zenodo_concept_family_count"]} '
               'Concept-Linien. Concept-DOIs bündeln Fassungen und sind keine zusätzlichen Publikationen. '
               'Vollständig für die dokumentierten öffentlichen Autorenabfragen und Versionslisten; '
               'private, nicht indexierte oder anders zugeordnete Einträge bleiben eine Erfassungsgrenze. '
               'DOI und Archivierung belegen keine unabhängige Replikation oder physikalische Bestätigung.</p>'
               '<div style="overflow-x:auto"><table><thead><tr><th>Record</th><th>Titel</th>'
               '<th>Version</th><th>Versions-DOI</th><th>Concept-DOI</th></tr></thead><tbody>'
               + "\n".join(rendered) + '</tbody></table></div>'
               '<h3>Tatsächlich veröffentlichte IETF-Revisionen</h3>'
               f'<p>{draft_count} individuelle Dokumentreihen, {len(revisions)} Revisionen; keine RFCs.</p>'
               f'<ul>{revision_rows}</ul>'
               '<h3>Lokale Vorbereitungen mit getrenntem Status</h3>'
               f'<ul>{candidate_rows}</ul>'
               '<p>Lokale Profile und nicht eingereichte Vorbereitungen behalten ihren eigenen Status. '
               'Vollständige Einordnung und Originaldateibindungen: '
               f'<a href="{html.escape(config["coverage_path"].removeprefix("docs/publications/"), quote=True)}">'
               'CORPUS_COVERAGE.json</a>.</p></div></section>\n' + end)
    if begin in text or end in text:
        if text.count(begin) != 1 or text.count(end) != 1:
            raise PublicationOverviewBlock("ambiguous public corpus projection block")
        return re.sub(re.escape(begin) + r".*?" + re.escape(end), lambda _: section,
                      text, flags=re.DOTALL)
    anchor = '  <section class="section" id="grenzen">'
    if anchor not in text:
        raise PublicationOverviewBlock("human index lacks public corpus insertion anchor")
    return text.replace(anchor, section + "\n\n" + anchor, 1)


def _project_editorial_publications(root: pathlib.Path, index: dict[str, Any], text: str) -> str:
    """Extend the catalog from exact saved readbacks, without refreshing old corpus claims."""
    paths = sorted((root / "evidence/publications").glob("*/*/EDITORIAL_COMPLETION.json"))
    registered = {r["editorial_readback_path"] for r in index.get("zenodo_records", [])
                  if isinstance(r, dict) and "editorial_readback_path" in r}
    available = {p.with_name("PUBLIC_ZENODO_READBACK.json").relative_to(root).as_posix() for p in paths}
    if not registered.issubset(available):
        raise PublicationOverviewBlock("cataloged editorial readback is unavailable")
    if not paths:
        return text
    from tools import qikvrt_publication_router as router
    _, publication, _ = router._publication_dependencies()
    entries = index.get("zenodo_records")
    if not isinstance(entries, list) or not all(isinstance(r, dict) for r in entries):
        raise PublicationOverviewBlock("Zenodo catalog must be a list of objects")
    by_doi = {r.get("doi"): r for r in entries}
    if len(by_doi) != len(entries):
        raise PublicationOverviewBlock("ambiguous Zenodo catalog identity")
    rows, seen = [], set()
    for path in paths:
        relative = path.relative_to(root).as_posix()
        try:
            completion, intake, manifest, _ = router._validated_editorial_completion(root, relative, persisted=True)
            public = completion["public_zenodo_verification"]
            readback = path.with_name("PUBLIC_ZENODO_READBACK.json")
            safe = publication._safe_relative(
                root, readback.relative_to(root).as_posix(), "editorial public readback", must_exist=True)
            saved, _ = publication.zenodo._load_json_file(safe)
            if saved != public:
                raise ValueError("editorial readback and completion differ")
        except (OSError, ValueError, RuntimeError) as exc:
            raise PublicationOverviewBlock("invalid exact editorial catalog evidence: " + relative) from exc
        doi, rid = public["doi"], public["record_id"]
        if doi in seen:
            raise PublicationOverviewBlock("multiple editorial receipts claim the same DOI")
        seen.add(doi)
        entry = by_doi.get(doi)
        if entry is None:
            entry = {"id": "zenodo-record-" + str(rid), "title": manifest["metadata"]["title"],
                     "doi": doi, "doi_url": "https://doi.org/" + doi, "state": "published_record"}
            entries.append(entry)
            by_doi[doi] = entry
        if entry.get("record_id", rid) != rid or entry.get("record_url", public["record_url"]) != public["record_url"]:
            raise PublicationOverviewBlock("editorial DOI conflicts with catalog identity")
        entry.update({"record_id": rid, "record_url": public["record_url"],
                      "editorial_readback_path": readback.relative_to(root).as_posix(),
                      "editorial_completion_path": relative, "manifest_sha256": intake["manifest_sha256"],
                      "public_byte_verification": "SAVED_EXACT_ANONYMOUS_READBACK_NOT_LIVE_REOBSERVATION",
                      "website_delivery_verified": False})
        for bundle in index["publication_bundles"]:
            if bundle["path"] == "docs" + intake["website"]["path"] + "README.md":
                if bundle["id"] != intake["publication_id"]:
                    raise PublicationOverviewBlock("editorial publication and bundle identifiers differ")
                bundle.update(doi=doi, record_url=public["record_url"], editorial_readback_path=entry["editorial_readback_path"],
                              state="zenodo_public_byte_verified_website_delivery_pending")
        esc = html.escape
        rows.append('<li><strong>' + esc(manifest["metadata"]["title"]) + '</strong> — '
                    '<a href="' + esc(entry["doi_url"], quote=True) + '">' + esc(doi) + '</a> — '
                    '<a href="' + esc(public["record_url"], quote=True) + '">' + esc(public["record_url"]) + '</a></li>')
    begin, end = "<!-- QIKVRT_EDITORIAL_VERIFIED_BEGIN -->", "<!-- QIKVRT_EDITORIAL_VERIFIED_END -->"
    section = (begin + '\n<section class="section" id="verlagspublikationen"><div class="wrap">'
               '<h2>Nachweisgebundene Verlagspublikationen</h2>'
               '<p>Originaldateien gemäß gespeichertem anonymem Zenodo-Readback bytegenau geprüft. '
               'Dies ist keine neue Online-Prüfung. Die Website-Auslieferung benötigt eine eigene Abnahme.</p><ul>'
               + "".join(rows) + '</ul></div></section>\n' + end)
    if begin in text or end in text:
        if text.count(begin) != 1 or text.count(end) != 1:
            raise PublicationOverviewBlock("ambiguous editorial catalog projection")
        return re.sub(re.escape(begin) + r".*?" + re.escape(end), lambda _: section, text, flags=re.DOTALL)
    for anchor in ('  <section class="section" id="grenzen">', '</main>', '</body>', '</html>'):
        if anchor in text:
            return text.replace(anchor, section + "\n" + anchor, 1)
    raise PublicationOverviewBlock("human index lacks an editorial insertion anchor")


def build_outputs(root: pathlib.Path) -> tuple[bytes, str, dict[str, Any]]:
    machine_path = root / MACHINE_INDEX
    human_path = root / HUMAN_INDEX
    index = _load_json(machine_path)
    html_text = _read_text(human_path)
    bundles = index["publication_bundles"]
    _validate_bundles(bundles)

    existing_paths = {str(item["path"]) for item in bundles}
    existing_ids = {str(item["id"]) for item in bundles}
    discovered = [_metadata(root, path) for path in _local_readmes(root)]
    missing_json: list[dict[str, str]] = []
    for item in discovered:
        if item["path"] in existing_paths:
            continue
        if item["id"] in existing_ids:
            raise PublicationOverviewBlock(
                f"new publication id collides with an existing bundle: {item['id']}"
            )
        entry = {key: item[key] for key in ("id", "title", "path", "state")}
        bundles.append(entry)
        existing_paths.add(item["path"])
        existing_ids.add(item["id"])
        missing_json.append(item)

    repository = index.get("repository")
    if not isinstance(repository, str) or "/" not in repository:
        raise PublicationOverviewBlock("publication index repository is invalid")
    collection = COLLECTION_PATTERN.search(html_text)
    if collection is None:
        raise PublicationOverviewBlock("human publication index has no collection-list block")

    missing_html = [item for item in discovered if item["path"] not in html_text]
    if missing_html:
        body = collection.group("body")
        if body and not body.endswith("\n"):
            body += "\n"
        body += "\n".join(_row(repository, item) for item in missing_html) + "\n"
        html_text = (
            html_text[: collection.start()]
            + collection.group("open")
            + body
            + collection.group("close")
            + html_text[collection.end() :]
        )

    _validate_bundles(bundles)
    indexed_paths = {str(item["path"]) for item in bundles}
    local_paths = {item["path"] for item in discovered}
    uncovered_json = sorted(local_paths - indexed_paths)
    uncovered_html = sorted(path for path in local_paths if path not in html_text)
    if uncovered_json or uncovered_html:
        raise PublicationOverviewBlock(
            f"coverage remains incomplete: json={uncovered_json}, html={uncovered_html}"
        )

    html_text = _project_public_corpus(root, index, html_text)
    html_text = _project_editorial_publications(root, index, html_text)
    machine_bytes = (
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    ).encode("utf-8")
    detail = {
        "missing_machine_entries": [item["path"] for item in missing_json],
        "missing_human_entries": [item["path"] for item in missing_html],
        "local_bundle_count": len(local_paths),
        "indexed_bundle_count": len(indexed_paths),
    }
    return machine_bytes, html_text, detail


def execute(root: pathlib.Path, materialize: bool) -> dict[str, Any]:
    machine_path = root / MACHINE_INDEX
    human_path = root / HUMAN_INDEX
    expected_machine, expected_human, detail = build_outputs(root)
    current_machine = machine_path.read_bytes()
    current_human = human_path.read_text(encoding="utf-8")
    changed_paths: list[str] = []
    if current_machine != expected_machine:
        changed_paths.append(MACHINE_INDEX.as_posix())
    if current_human != expected_human:
        changed_paths.append(HUMAN_INDEX.as_posix())
    if changed_paths and materialize:
        machine_path.write_bytes(expected_machine)
        human_path.write_text(expected_human, encoding="utf-8")
        verify_machine, verify_human, _ = build_outputs(root)
        if verify_machine != expected_machine or verify_human != expected_human:
            raise PublicationOverviewBlock("materialization is not idempotent")
    return {
        "schema": "qikvrt_publication_overview_result_v1",
        "state": "MATERIALIZED" if changed_paths and materialize else (
            "DRIFT" if changed_paths else "CURRENT"
        ),
        "changed_paths": changed_paths,
        "detail": detail,
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "materialize"))
    parser.add_argument("--root", type=pathlib.Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        result = execute(root, args.command == "materialize")
    except (OSError, ValueError, json.JSONDecodeError, PublicationOverviewBlock) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True)
    if result["state"] == "DRIFT":
        print(f"{DRIFT_SIGNATURE} {rendered}", file=sys.stderr)
        return 2
    print(rendered if args.json else json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
