#!/usr/bin/env python3
"""Reject publication outputs whose references have no visible exact locator."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def compact(value):
    return re.sub(r"\s+", "", value)


def source_errors(sources):
    errors = []
    seen = set()
    if not isinstance(sources, list) or not sources:
        return ["NONEMPTY_SOURCE_LIST_REQUIRED"]
    for index, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            errors.append(f"SOURCE_{index}:OBJECT_REQUIRED")
            continue
        identifier = str(source.get("id", ""))
        if not identifier or identifier in seen:
            errors.append(f"SOURCE_{index}:UNIQUE_ID_REQUIRED")
        seen.add(identifier)
        if not isinstance(source.get("title"), str) or not source["title"].strip():
            errors.append(f"SOURCE_{identifier}:TITLE_REQUIRED")
        urls = source.get("urls", [])
        if not isinstance(urls, list):
            errors.append(f"SOURCE_{identifier}:URL_LIST_REQUIRED")
            urls = []
        if not urls and not source.get("doi") and not source.get("isbn"):
            errors.append(f"SOURCE_{identifier}:EXACT_LOCATOR_REQUIRED")
        for url in urls:
            if not isinstance(url, str):
                errors.append(f"SOURCE_{identifier}:URL_STRING_REQUIRED")
                continue
            parsed = urlsplit(url)
            if parsed.scheme not in ("https", "http") or not parsed.netloc or re.search(r"\s", url) or parsed.username or parsed.password:
                errors.append(f"SOURCE_{identifier}:INVALID_URL:{url}")
            if parsed.hostname in {"github.com", "api.github.com", "raw.githubusercontent.com", "gitlab.com", "codeberg.org"}:
                errors.append(f"SOURCE_{identifier}:REPOSITORY_CITATION_REQUIRES_PUBLISHED_ZENODO_ARCHIVE")
        if source.get("origin") in {"repository", "repository_runtime", "workflow"}:
            archive = source.get("archive", {})
            if not isinstance(archive, dict) or archive.get("status") != "PUBLISHED_PUBLIC_BYTE_VERIFIED":
                errors.append(f"SOURCE_{identifier}:ARCHIVE_PUBLICATION_PENDING")
            else:
                archive_doi = archive.get("doi", "")
                record_url = archive.get("record_url", "")
                if not isinstance(archive_doi, str) or not re.fullmatch(r"10\.5281/zenodo\.[1-9][0-9]*", archive_doi) or source.get("doi") != archive_doi:
                    errors.append(f"SOURCE_{identifier}:VERIFIED_ZENODO_VERSION_DOI_REQUIRED")
                if not isinstance(record_url, str) or not re.fullmatch(r"https://zenodo\.org/records/[1-9][0-9]*", record_url):
                    errors.append(f"SOURCE_{identifier}:ZENODO_RECORD_URL_REQUIRED")
                if not any(isinstance(url, str) and url in {record_url, f"https://doi.org/{archive_doi}"} for url in urls):
                    errors.append(f"SOURCE_{identifier}:VISIBLE_ZENODO_LOCATOR_REQUIRED")
                try:
                    receipt_raw = Path(archive["receipt_path"]).read_bytes()
                    if hashlib.sha256(receipt_raw).hexdigest() != archive.get("receipt_sha256"):
                        raise ValueError("RECEIPT_HASH_MISMATCH")
                    receipt = json.loads(receipt_raw)
                    if receipt.get("status") != "PUBLISHED_PUBLIC_BYTE_VERIFIED" or receipt.get("doi") != archive_doi or receipt.get("record_url") != record_url:
                        raise ValueError("RECEIPT_IDENTITY_MISMATCH")
                    files = receipt.get("files", [])
                    if not files or any(not isinstance(f, dict) or not f.get("name") or not re.fullmatch(r"[0-9a-f]{64}", str(f.get("sha256", ""))) or f.get("byte_exact_public_redownload") is not True for f in files):
                        raise ValueError("BYTE_EXACT_PUBLIC_FILE_RECEIPT_REQUIRED")
                except (OSError, KeyError, TypeError, ValueError):
                    errors.append(f"SOURCE_{identifier}:PUBLICATION_READBACK_RECEIPT_INVALID")
        doi = source.get("doi")
        if doi and (not isinstance(doi, str) or not re.fullmatch(r"10\.\d{4,9}/\S+", doi)):
            errors.append(f"SOURCE_{identifier}:INVALID_DOI")
        isbn = source.get("isbn")
        if isbn:
            digits = re.sub(r"[-\s]", "", str(isbn)).upper()
            valid = False
            if re.fullmatch(r"\d{13}", digits):
                valid = sum(int(d) * (1 if n % 2 == 0 else 3) for n, d in enumerate(digits)) % 10 == 0
            elif re.fullmatch(r"\d{9}[\dX]", digits):
                valid = sum((10 - n) * (10 if d == "X" else int(d)) for n, d in enumerate(digits)) % 11 == 0
            if not valid:
                errors.append(f"SOURCE_{identifier}:INVALID_ISBN")
    return errors


def inspect_artifact(path, sources):
    data = path.read_bytes()
    links = None
    if path.suffix.lower() == ".pdf":
        import fitz
        with fitz.open(path) as document:
            text = "\n".join(page.get_text() for page in document)
            links = {link["uri"] for page in document for link in page.get_links() if "uri" in link}
            page_count = len(document)
    elif path.suffix.lower() in (".txt", ".md"):
        text = data.decode("utf-8")
        page_count = None
    else:
        raise ValueError("UNSUPPORTED_ARTIFACT_FORMAT")
    visible = compact(text)
    errors = []
    for source in sources:
        identifier = source["id"]
        if compact(source["title"]) not in visible:
            errors.append(f"SOURCE_{identifier}:TITLE_NOT_VISIBLE")
        for url in source.get("urls", []):
            if compact(url) not in visible:
                errors.append(f"SOURCE_{identifier}:URL_NOT_VISIBLE:{url}")
            if links is not None and url not in links:
                errors.append(f"SOURCE_{identifier}:URL_LINK_MISMATCH:{url}")
        for key in ("doi", "isbn"):
            if source.get(key) and compact(str(source[key])) not in visible:
                errors.append(f"SOURCE_{identifier}:{key.upper()}_NOT_VISIBLE")
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest(), "pages": page_count, "status": "FAIL" if errors else "PASS", "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, action="append", required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    sources = manifest.get("sources", [])
    errors = source_errors(sources)
    if manifest.get("schema") != "QIKVRT_VISIBLE_SOURCES_V1":
        errors.append("MANIFEST_SCHEMA_MISMATCH")
    results = []
    if not errors:
        for path in args.artifact:
            try:
                results.append(inspect_artifact(path, sources))
            except Exception as error:
                results.append({"path": str(path.resolve()), "status": "FAIL", "errors": [f"READBACK_FAILED:{type(error).__name__}:{error}"]})
    status = "PASS" if not errors and results and all(item["status"] == "PASS" for item in results) else "FAIL"
    result = {"schema": "QIKVRT_VISIBLE_SOURCES_CHECK_V1", "status": status, "source_count": len(sources), "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(), "network_reachability_checked": False, "claim_support_checked_automatically": False, "errors": errors, "artifacts": results}
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.receipt:
        args.receipt.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
