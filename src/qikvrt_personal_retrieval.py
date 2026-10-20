# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Optional local, read-only source ranking; no download, generation or effect ACK."""
from __future__ import annotations
import hashlib
import json
import math
import re
import threading
from pathlib import Path

MODEL = "perplexity-ai/pplx-embed-v2-late-0.6b"
REVISION = "8fc2de24534aa3610d85fa59c463313a5f096455"
LOCK = Path(__file__).resolve().parents[1] / "runtime/models/pplx-embed-v2-late-0.6b.lock.json"

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

class RetrievalUnavailable(ValueError):
    pass

def validate(query, sources, limit):
    if not isinstance(query, str) or not query.strip() or len(query) > 512:
        raise RetrievalUnavailable("RETRIEVAL_QUERY_INVALID")
    if type(limit) is not int or not 1 <= limit <= 8:
        raise RetrievalUnavailable("RETRIEVAL_LIMIT_INVALID")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 32:
        raise RetrievalUnavailable("RETRIEVAL_SOURCES_INVALID")
    checked, ids = [], set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"id", "text", "sha256"}:
            raise RetrievalUnavailable("RETRIEVAL_SOURCE_FIELDS_INVALID")
        identity, text = source["id"], source["text"]
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", identity) or identity in ids:
            raise RetrievalUnavailable("RETRIEVAL_SOURCE_ID_INVALID")
        if not isinstance(text, str) or not text.strip() or len(text) > 512:
            raise RetrievalUnavailable("RETRIEVAL_SOURCE_CHUNK_INVALID")
        sha = hashlib.sha256(text.encode()).hexdigest()
        if source["sha256"] != sha:
            raise RetrievalUnavailable("RETRIEVAL_SOURCE_HASH_MISMATCH")
        ids.add(identity)
        checked.append(dict(source))
    return sorted(checked, key=lambda row: row["id"])

class LocalRetrieval:
    def __init__(self, encoder, *, evidence_class="TEST_DOUBLE_NOT_MODEL_INFERENCE"):
        # Direct injection supports existing deterministic tests. Production
        # callers use from_directory, which validates the frozen model bytes.
        self.encoder, self.evidence_class = encoder, evidence_class
        self.lock = threading.RLock()

    @classmethod
    def from_directory(cls, directory):
        root = Path(directory).expanduser()
        if root.is_symlink() or not root.is_dir():
            raise RetrievalUnavailable("LOCAL_MODEL_DIRECTORY_REQUIRED")
        lock = json.loads(LOCK.read_text())
        if lock["model"] != MODEL or lock["revision"] != REVISION:
            raise RetrievalUnavailable("MODEL_LOCK_IDENTITY_INVALID")
        if any(path.is_symlink() for path in [root, *root.parents, *root.rglob("*")]):
            raise RetrievalUnavailable("LOCAL_MODEL_SYMLINK_REFUSED")
        expected_files = {row["file"] for row in lock["files"]}
        actual_files = {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}
        if actual_files != expected_files:
            raise RetrievalUnavailable("LOCAL_MODEL_FILE_SET_MISMATCH")
        before = {}
        for row in lock["files"]:
            rel = Path(row["file"])
            if rel.is_absolute() or ".." in rel.parts:
                raise RetrievalUnavailable("MODEL_LOCK_PATH_INVALID")
            path = root / rel
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    digest.update(block)
            stat = path.stat()
            if stat.st_size != row["bytes"] or digest.hexdigest() != row["sha256"]:
                raise RetrievalUnavailable("LOCAL_MODEL_BYTES_MISMATCH")
            before[row["file"]] = (stat.st_size, stat.st_mtime_ns)
        # An explicit local directory and local_files_only avoid implicit Hub
        # retrieval. The exact module configuration is covered by the lock.
        try:
            from sentence_transformers import MultiVectorEncoder
        except ImportError:
            raise RetrievalUnavailable("LOCAL_RETRIEVAL_DEPENDENCIES_UNAVAILABLE") from None
        encoder = MultiVectorEncoder(str(root.resolve()), device="cpu",
                                     trust_remote_code=False, local_files_only=True)
        encoder.max_seq_length = 4096
        if any((lambda s: (s.st_size, s.st_mtime_ns))((root / name).stat()) != state
               for name, state in before.items()):
            raise RetrievalUnavailable("LOCAL_MODEL_CHANGED_DURING_LOAD")
        return cls(encoder, evidence_class="LOCAL_MODEL_INFERENCE")

    def search(self, query, sources, limit=3):
        sources = validate(query, sources, limit)
        request = {"query": query, "sources": sources, "limit": limit}
        with self.lock:
            try:
                docs = self.encoder.encode_document([row["text"] for row in sources])
                queries = self.encoder.encode_query([query])
                matrix = self.encoder.similarity(queries, docs)
                scores = [float(value) for value in matrix[0]]
            except Exception:
                raise RetrievalUnavailable("LOCAL_RETRIEVAL_INFERENCE_FAILED") from None
        if len(scores) != len(sources) or any(not math.isfinite(value) for value in scores):
            raise RetrievalUnavailable("LOCAL_RETRIEVAL_SCORES_INVALID")
        order = sorted(range(len(sources)), key=lambda index: (-scores[index], sources[index]["id"]))[:limit]
        return {"schema": "qikvrt_local_source_ranking_v1", "scope": "LOCAL_SOURCE_RANKING_ONLY",
                "model": MODEL, "model_revision": REVISION,
                "evidence_class": self.evidence_class,
                "request_sha256": hashlib.sha256(canonical(request)).hexdigest(),
                "results": [{"source_id": sources[i]["id"], "source_sha256": sources[i]["sha256"],
                             "score": scores[i]} for i in order],
                "field_values_extracted": False, "productive_acceptance": False}
