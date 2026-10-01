# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Versioned, lossless byte transport and canonical QIK-VRT mesh snapshots.

The byte transport requires an externally expected 400-byte seed. Snapshot
adapters reuse the existing standpoint codex and its exact canonical seed. SHA-256 bindings detect corruption, not
authenticate a person. See policy/QIKVRT_CODEC_CONTRACT_V1.json.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import os
import struct
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable

from src.qikvrt_standpoint_codex import (
    DEFAULT_LIMITS, QIKVRT_SIGNATURE, Element, Limits, deserialize, serialize,
)

SIGNATURE_BYTES = 400
DEFAULT_BLOCK_BYTES = 256 * 1024
MAX_BLOCK_BYTES = 16 * 1024 * 1024
DEFAULT_DECODE_LIMIT = 256 * 1024 * 1024
MAGIC = b"QIKVRTC\0"
VERSION = 1
HEADER = struct.Struct(">8sBBHI")
BLOCK = struct.Struct(">BII32s")
FOOTER = struct.Struct(">BQQ32s")
HEADER_BYTES = HEADER.size + SIGNATURE_BYTES
RAW, ZLIB, END = 0, 1, 255
PROFILES = {"raw": 0, "fast": 1, "balanced": 6, "compact": 9}


class CodecError(ValueError):
    """Malformed, unsupported, mismatched or resource-exceeding input."""


def _seed(value: bytes) -> bytes:
    if type(value) is not bytes or len(value) != SIGNATURE_BYTES:
        raise CodecError("SIGNATURE_MUST_BE_EXACTLY_400_BYTES")
    return value


def _integer(value: int, lower: int, upper: int, name: str) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise CodecError(name)
    return value


def _read_up_to(source: BinaryIO, size: int) -> bytes:
    """Fill a bounded block even when a blocking binary reader returns short reads."""
    parts: list[bytes] = []
    remaining = size
    while remaining:
        part = source.read(remaining)
        if type(part) is not bytes or len(part) > remaining:
            raise CodecError("BLOCKING_BINARY_READER_REQUIRED")
        if not part:
            break
        parts.append(part)
        remaining -= len(part)
    return b"".join(parts)


def _read_exact(source: BinaryIO, size: int) -> bytes:
    value = _read_up_to(source, size)
    if len(value) != size:
        raise CodecError("TRUNCATED_INPUT")
    return value


def _write(sink: BinaryIO, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = sink.write(view)
        if type(written) is not int or not 0 < written <= len(view):
            raise CodecError("BLOCKING_BINARY_WRITER_REQUIRED")
        view = view[written:]


def _probably_incompressible(data: bytes) -> bool:
    # Four distributed samples; native zlib avoids a Python byte histogram.
    # This is a speed heuristic, never a promise of optimal compression.
    if len(data) < 64 * 1024:
        return False
    sample_bytes = 2048
    offsets = (0, len(data) // 3, 2 * len(data) // 3, len(data) - sample_bytes)
    sample = b"".join(data[p:p + sample_bytes] for p in offsets)
    return len(zlib.compress(sample, 1)) >= len(sample) * 0.98


@dataclass(frozen=True)
class StreamInfo:
    raw_bytes: int
    wire_bytes: int
    blocks: int
    payload_sha256: str
    signature_sha256: str


def encode_stream(
    source: BinaryIO, sink: BinaryIO, *, signature: bytes,
    profile: str = "balanced", block_bytes: int = DEFAULT_BLOCK_BYTES,
    probe: bool = True,
) -> StreamInfo:
    """Encode finite binary input with O(block_bytes) auxiliary storage.

    probe=False provides the same framed baseline with full compression trials.
    Source/sink errors propagate; the caller owns transactional persistence.
    """
    signature = _seed(signature)
    _integer(block_bytes, 4096, MAX_BLOCK_BYTES, "INVALID_BLOCK_BYTES")
    if type(profile) is not str or profile not in PROFILES:
        raise CodecError("UNKNOWN_PROFILE")
    if type(probe) is not bool:
        raise CodecError("INVALID_PROBE_FLAG")
    header = HEADER.pack(MAGIC, VERSION, 0, HEADER_BYTES, block_bytes) + signature
    _write(sink, header)
    wire_hash = hashlib.sha256(header)
    raw_hash = hashlib.sha256()
    total = blocks = 0
    wire_bytes = len(header)
    while True:
        raw = _read_up_to(source, block_bytes)
        if not raw:
            break
        if blocks == 2**64 - 1 or total > 2**64 - 1 - len(raw):
            raise CodecError("V1_COUNTER_EXHAUSTED")
        method, payload = RAW, raw
        if profile != "raw" and not (
            probe and profile == "fast" and _probably_incompressible(raw)
        ):
            compressed = zlib.compress(raw, PROFILES[profile])
            if len(compressed) < len(raw):
                method, payload = ZLIB, compressed
        frame = BLOCK.pack(method, len(raw), len(payload), hashlib.sha256(raw).digest())
        _write(sink, frame)
        _write(sink, payload)
        wire_hash.update(frame)
        wire_hash.update(payload)
        raw_hash.update(raw)
        total += len(raw)
        blocks += 1
        wire_bytes += len(frame) + len(payload)
    footer_prefix = struct.pack(">BQQ", END, total, blocks)
    wire_hash.update(footer_prefix)
    footer = footer_prefix + wire_hash.digest()
    _write(sink, footer)
    return StreamInfo(total, wire_bytes + len(footer), blocks,
                      raw_hash.hexdigest(), hashlib.sha256(signature).hexdigest())


def _inflate(payload: bytes, raw_bytes: int) -> bytes:
    inflater = zlib.decompressobj()
    try:
        raw = inflater.decompress(payload, raw_bytes + 1)
    except zlib.error as exc:
        raise CodecError("INVALID_ZLIB_STREAM") from exc
    if (len(raw) != raw_bytes or not inflater.eof or inflater.unused_data
            or inflater.unconsumed_tail):
        raise CodecError("INVALID_ZLIB_LENGTH_OR_TERMINATION")
    return raw


def decode_stream(
    source: BinaryIO, sink: BinaryIO, *, signature: bytes,
    max_output_bytes: int | None = None, max_block_bytes: int = MAX_BLOCK_BYTES,
) -> StreamInfo:
    """Verify each block before writing; accept the container only on return.

    A bad late footer can follow already-written, individually verified blocks.
    Use a temporary sink for atomic acceptance; the CLI does this automatically.
    """
    signature = _seed(signature)
    _integer(max_block_bytes, 4096, MAX_BLOCK_BYTES, "INVALID_BLOCK_LIMIT")
    if max_output_bytes is not None:
        _integer(max_output_bytes, 0, 2**64 - 1, "INVALID_OUTPUT_LIMIT")
    header = _read_exact(source, HEADER_BYTES)
    magic, version, flags, header_bytes, block_bytes = HEADER.unpack(header[:HEADER.size])
    if (magic, version, flags, header_bytes) != (MAGIC, VERSION, 0, HEADER_BYTES):
        raise CodecError("UNSUPPORTED_OR_NONCANONICAL_HEADER")
    _integer(block_bytes, 4096, max_block_bytes, "BLOCK_LIMIT_EXCEEDED")
    if not hmac.compare_digest(header[HEADER.size:], signature):
        raise CodecError("SIGNATURE_MISMATCH")
    wire_hash = hashlib.sha256(header)
    raw_hash = hashlib.sha256()
    total = blocks = 0
    wire_bytes = len(header)
    short_block = False
    while True:
        method = _read_exact(source, 1)[0]
        if method == END:
            footer = bytes([method]) + _read_exact(source, FOOTER.size - 1)
            _, expected_bytes, expected_blocks, expected_hash = FOOTER.unpack(footer)
            wire_hash.update(footer[:17])
            if ((expected_bytes, expected_blocks) != (total, blocks)
                    or not hmac.compare_digest(wire_hash.digest(), expected_hash)):
                raise CodecError("FOOTER_MISMATCH")
            if _read_up_to(source, 1):
                raise CodecError("TRAILING_INPUT")
            return StreamInfo(total, wire_bytes + len(footer), blocks,
                              raw_hash.hexdigest(), hashlib.sha256(signature).hexdigest())
        if method not in (RAW, ZLIB) or short_block:
            raise CodecError("UNKNOWN_METHOD_OR_NONCANONICAL_BLOCK_ORDER")
        frame = bytes([method]) + _read_exact(source, BLOCK.size - 1)
        _, raw_bytes, stored_bytes, expected_hash = BLOCK.unpack(frame)
        if (not 0 < raw_bytes <= block_bytes or not 0 < stored_bytes <= raw_bytes
                or (method == RAW and stored_bytes != raw_bytes)
                or (method == ZLIB and stored_bytes >= raw_bytes)):
            raise CodecError("NONCANONICAL_BLOCK_LENGTHS")
        if (total > 2**64 - 1 - raw_bytes or blocks == 2**64 - 1
                or (max_output_bytes is not None and total + raw_bytes > max_output_bytes)):
            raise CodecError("OUTPUT_LIMIT_EXCEEDED")
        payload = _read_exact(source, stored_bytes)
        raw = payload if method == RAW else _inflate(payload, raw_bytes)
        if not hmac.compare_digest(hashlib.sha256(raw).digest(), expected_hash):
            raise CodecError("BLOCK_HASH_MISMATCH")
        _write(sink, raw)
        raw_hash.update(raw)
        wire_hash.update(frame)
        wire_hash.update(payload)
        total += raw_bytes
        blocks += 1
        wire_bytes += len(frame) + len(payload)
        short_block = raw_bytes < block_bytes


def encode(data: bytes, *, signature: bytes, profile: str = "balanced",
           block_bytes: int = DEFAULT_BLOCK_BYTES, probe: bool = True) -> bytes:
    if type(data) is not bytes:
        raise CodecError("BYTES_REQUIRED")
    out = io.BytesIO()
    encode_stream(io.BytesIO(data), out, signature=signature, profile=profile,
                  block_bytes=block_bytes, probe=probe)
    return out.getvalue()


def decode(data: bytes, *, signature: bytes,
           max_output_bytes: int | None = DEFAULT_DECODE_LIMIT) -> bytes:
    if type(data) is not bytes:
        raise CodecError("BYTES_REQUIRED")
    out = io.BytesIO()
    decode_stream(io.BytesIO(data), out, signature=signature, max_output_bytes=max_output_bytes)
    return out.getvalue()


def encode_snapshot(
    elements: Iterable[Element], *, limits: Limits = DEFAULT_LIMITS,
    profile: str = "balanced", block_bytes: int = DEFAULT_BLOCK_BYTES,
) -> bytes:
    """Compress the existing canonical standpoint codec's exact snapshot bytes."""
    snapshot = serialize(elements, limits=limits)
    return encode(snapshot, signature=QIKVRT_SIGNATURE, profile=profile, block_bytes=block_bytes)


def decode_snapshot(data: bytes, *, limits: Limits = DEFAULT_LIMITS) -> tuple[Element, ...]:
    """Validate complete transport, then the existing canonical snapshot contract."""
    if type(limits) is not Limits:
        raise CodecError("SNAPSHOT_LIMITS_REQUIRED")
    snapshot = decode(data, signature=QIKVRT_SIGNATURE,
                      max_output_bytes=limits.max_snapshot_bytes)
    return deserialize(snapshot, limits=limits)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("encode", "decode"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--signature-file", required=True, type=Path)
    parser.add_argument("--profile", choices=tuple(PROFILES), default="balanced")
    parser.add_argument("--block-bytes", type=int, default=DEFAULT_BLOCK_BYTES)
    parser.add_argument("--max-output-bytes", type=int, default=None)
    args = parser.parse_args(argv)
    temporary = None
    try:
        signature = _seed(args.signature_file.read_bytes())
        if args.output.resolve() in (args.input.resolve(), args.signature_file.resolve()):
            raise CodecError("OUTPUT_MUST_BE_DISTINCT_FROM_INPUT_AND_SEED")
        with args.input.open("rb") as source, tempfile.NamedTemporaryFile(
            mode="wb", dir=args.output.parent, prefix=".qikvrt-codec-", delete=False
        ) as sink:
            temporary = Path(sink.name)
            if args.operation == "encode":
                encode_stream(source, sink, signature=signature, profile=args.profile,
                              block_bytes=args.block_bytes)
            else:
                decode_stream(source, sink, signature=signature,
                              max_output_bytes=args.max_output_bytes)
            sink.flush()
            os.fsync(sink.fileno())
        os.replace(temporary, args.output)
        temporary = None
    except (OSError, CodecError) as exc:
        parser.exit(2, f"BLOCK: {exc}\n")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
