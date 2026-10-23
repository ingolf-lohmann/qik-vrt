#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
"""Verified loader for the QIK-VRT aphorism-corpus materializer."""
from __future__ import annotations

import hashlib
import zlib
from pathlib import Path

_IMPL_PATH = Path(__file__).resolve().with_name("qikvrt_aphorism_corpus_v2_impl") / "impl.py.zlib"
_IMPL_COMPRESSED_BYTES = 5915
_IMPL_COMPRESSED_SHA256 = "7beb72e0b0210b2998ce1fa90e7255854aa7416535b45b16c5c27e0e14bd09e4"
_IMPL_SOURCE_SHA256 = "24d2a4e9c58e14e161dea0a2122c67c6f90093c8e6d408e2ce17253340509a41"

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
