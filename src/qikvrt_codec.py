# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Versioned, lossless byte transport and canonical QIK-VRT mesh snapshots.

New containers and snapshots share the fixed 400-byte V1 standpoint. Historical
generic-seed containers require explicit legacy decoding and never establish
standpoint conformance. SHA-256 detects corruption; it does not authenticate a
person. See policy/QIKVRT_CODEC_CONTRACT_V1.json.
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

from src.qikvrt_effect_ack import (
    EffectAckEngine, EffectAckRequest, EffectAckResult, canonical_json,
)

from src.qikvrt_standpoint_codex import (
    DEFAULT_LIMITS, QIKVRT_SIGNATURE, SIGNATURE_BYTES, CodexError, Element,
    Limits, deserialize, serialize, validate_signature,
)

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


def _standpoint(value: bytes) -> bytes:
    try:
        validate_signature(value)
    except CodexError as exc:
        raise CodecError("SIGNATURE_MISMATCH: fixed QIKVRT V1 standpoint required") from exc
    return value


def _expected_signature(value: bytes, allow_legacy_seed: bool) -> bytes:
    if type(allow_legacy_seed) is not bool:
        raise CodecError("INVALID_LEGACY_FLAG")
    return _seed(value) if allow_legacy_seed else _standpoint(value)


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
    canonical_standpoint: bool


def encode_stream(
    source: BinaryIO, sink: BinaryIO, *, signature: bytes = QIKVRT_SIGNATURE,
    profile: str = "balanced", block_bytes: int = DEFAULT_BLOCK_BYTES,
    probe: bool = True,
) -> StreamInfo:
    """Encode finite binary input with O(block_bytes) auxiliary storage.

    probe=False provides the same framed baseline with full compression trials.
    Source/sink errors propagate; the caller owns transactional persistence.
    """
    signature = _standpoint(signature)
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
                      raw_hash.hexdigest(), hashlib.sha256(signature).hexdigest(), True)


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
    source: BinaryIO, sink: BinaryIO, *, signature: bytes = QIKVRT_SIGNATURE,
    max_output_bytes: int | None = None, max_block_bytes: int = MAX_BLOCK_BYTES,
    allow_legacy_seed: bool = False,
) -> StreamInfo:
    """Verify each block before writing; accept the container only on return.

    A bad late footer can follow already-written, individually verified blocks.
    Use a temporary sink for atomic acceptance; the CLI does this automatically.
    Legacy decoding still requires the caller's exact external expected seed;
    it never extracts or trusts a seed from the container itself.
    """
    signature = _expected_signature(signature, allow_legacy_seed)
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
                              raw_hash.hexdigest(), hashlib.sha256(signature).hexdigest(),
                              hmac.compare_digest(signature, QIKVRT_SIGNATURE))
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


def encode(data: bytes, *, signature: bytes = QIKVRT_SIGNATURE, profile: str = "balanced",
           block_bytes: int = DEFAULT_BLOCK_BYTES, probe: bool = True) -> bytes:
    if type(data) is not bytes:
        raise CodecError("BYTES_REQUIRED")
    out = io.BytesIO()
    encode_stream(io.BytesIO(data), out, signature=signature, profile=profile,
                  block_bytes=block_bytes, probe=probe)
    return out.getvalue()


def decode(data: bytes, *, signature: bytes = QIKVRT_SIGNATURE,
           max_output_bytes: int | None = DEFAULT_DECODE_LIMIT,
           allow_legacy_seed: bool = False) -> bytes:
    if type(data) is not bytes:
        raise CodecError("BYTES_REQUIRED")
    out = io.BytesIO()
    decode_stream(io.BytesIO(data), out, signature=signature,
                  max_output_bytes=max_output_bytes, allow_legacy_seed=allow_legacy_seed)
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


# Local feedback adapter. The existing container and 400-byte standpoint remain
# unchanged. No provider transport, repository writer or permit issuer is added.
_INVERT_BITS = bytes(255 - n for n in range(256))
_DIRECTIONS = ("left-to-right", "right-to-left")


@dataclass(frozen=True)
class BitFrame:
    """One finite, byte-aligned clock trigger; bit order is MSB first."""

    direction: str
    sequence: int
    tick: int
    payload: bytes
    hop: int = 0
    parent_sha256: str = ""
    version: int = 1
    port: int = 0

    def __post_init__(self) -> None:
        if type(self.version) is not int or self.version != 1:
            raise CodecError("UNSUPPORTED_FEEDBACK_VERSION")
        if type(self.direction) is not str or self.direction not in _DIRECTIONS:
            raise CodecError("INVALID_DIRECTION")
        for name in ("sequence", "tick", "hop"):
            _integer(getattr(self, name), 0, 2**64 - 1, "INVALID_" + name.upper())
        _integer(self.port, 0, 3, "INVALID_PORT")
        if type(self.payload) is not bytes:
            raise CodecError("BYTES_REQUIRED")
        if (type(self.parent_sha256) is not str
                or (self.hop == 0 and self.parent_sha256 != "")
                or (self.hop > 0 and (len(self.parent_sha256) != 64
                    or any(c not in "0123456789abcdef" for c in self.parent_sha256)))):
            raise CodecError("INVALID_PARENT_BINDING")

    @property
    def sha256(self) -> str:
        metadata = canonical_json({
            "schema": "qikvrt_bit_frame_v1", "direction": self.direction,
            "sequence": self.sequence, "tick": self.tick, "hop": self.hop,
            "parent_sha256": self.parent_sha256, "payload_bytes": len(self.payload),
            "port": self.port,
        }).encode("utf-8")
        return hashlib.sha256(b"QIKVRT-FEEDBACK-FRAME-V1\0" + metadata
                              + b"\0" + self.payload).hexdigest()


def split_bit_lanes(payload: bytes) -> tuple[bytes, bytes]:
    """Return zero/one position masks, preserving every original bit position.

    A set bit in either mask marks a bit routed to that lane. Lane values are
    implicit (zero above, one below); counts alone cannot reconstruct order.
    Native byte translation avoids allocating a Python object per bit.
    """
    if type(payload) is not bytes:
        raise CodecError("BYTES_REQUIRED")
    return payload.translate(_INVERT_BITS), payload


def join_bit_lanes(zeros: bytes, ones: bytes) -> bytes:
    if type(zeros) is not bytes or type(ones) is not bytes:
        raise CodecError("BYTES_REQUIRED")
    if zeros != ones.translate(_INVERT_BITS):
        raise CodecError("BIT_LANES_NOT_COMPLETE_AND_DISJOINT")
    return ones


@dataclass(frozen=True)
class FeedbackPolicy:
    """Fixed local chain and four-port selection, separate from CI admission.

    Each route is (port, start_byte, stop_byte); -1 means the output end.
    Empty routes select no feedback. Disjoint ranges covering the output select
    complete feedback; other valid ranges select partial feedback.
    """

    operation: str = "identity"
    routes: tuple[tuple[int, int, int], ...] = ()
    max_input_bytes: int = MAX_BLOCK_BYTES
    max_output_bytes: int = MAX_BLOCK_BYTES
    max_hops: int = 1

    def __post_init__(self) -> None:
        if type(self.operation) is not str or self.operation not in ("identity", "encode", "decode"):
            raise CodecError("UNKNOWN_FEEDBACK_OPERATION")
        for name in ("max_input_bytes", "max_output_bytes"):
            _integer(getattr(self, name), 0, MAX_BLOCK_BYTES, "INVALID_" + name.upper())
        _integer(self.max_hops, 0, 1024, "INVALID_HOP_LIMIT")
        if type(self.routes) is not tuple or len(self.routes) > 4:
            raise CodecError("FOUR_PORT_ROUTES_REQUIRED")
        ports = set()
        for route in self.routes:
            if type(route) is not tuple or len(route) != 3:
                raise CodecError("INVALID_ROUTE")
            port, start, stop = route
            _integer(port, 0, 3, "INVALID_PORT")
            _integer(start, 0, self.max_output_bytes, "INVALID_ROUTE_START")
            _integer(stop, -1, self.max_output_bytes, "INVALID_ROUTE_STOP")
            if port in ports or (stop != -1 and stop < start):
                raise CodecError("DUPLICATE_PORT_OR_REVERSED_RANGE")
            ports.add(port)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(canonical_json({
            "schema": "qikvrt_feedback_policy_v1", "operation": self.operation,
            "routes": self.routes, "max_input_bytes": self.max_input_bytes,
            "max_output_bytes": self.max_output_bytes, "max_hops": self.max_hops,
        }).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FeedbackStep:
    frame: BitFrame
    policy_sha256: str
    zeros: bytes
    ones: bytes
    processed: bytes
    ports: tuple[tuple[int, bytes], ...]
    effect_ack: EffectAckResult


def feedback_step(frame: BitFrame, policy: FeedbackPolicy) -> FeedbackStep:
    """One pure local trigger. Produces feedback data, never repository effects.

    Caller owns duplex sequencing, durable replay journal and external admission.
    Full decoding finishes before any selected bytes become visible to callers.
    No clock sleeps, recursive execution, arbitrary callbacks or auto-release.
    """
    if type(frame) is not BitFrame or type(policy) is not FeedbackPolicy:
        raise CodecError("FRAME_AND_POLICY_REQUIRED")
    if len(frame.payload) > policy.max_input_bytes:
        raise CodecError("FEEDBACK_INPUT_LIMIT_EXCEEDED")
    if frame.hop > policy.max_hops:
        raise CodecError("FEEDBACK_HOP_LIMIT_EXCEEDED")
    zeros, ones = split_bit_lanes(frame.payload)
    restored = join_bit_lanes(zeros, ones)
    if policy.operation == "decode":
        processed = decode(restored, max_output_bytes=policy.max_output_bytes)
    elif policy.operation == "encode":
        # Refuse before allocating encoded output beyond the configured limit.
        worst_case = HEADER_BYTES + FOOTER.size + len(restored) + (
            (len(restored) + DEFAULT_BLOCK_BYTES - 1) // DEFAULT_BLOCK_BYTES) * BLOCK.size
        if worst_case > policy.max_output_bytes:
            raise CodecError("FEEDBACK_ENCODE_BOUND_EXCEEDED")
        processed = encode(restored)
    else:
        processed = restored
    if len(processed) > policy.max_output_bytes:
        raise CodecError("FEEDBACK_OUTPUT_LIMIT_EXCEEDED")
    ports = []
    ranges = []
    for port, start, stop in policy.routes:
        end = len(processed) if stop == -1 else stop
        if not start <= end <= len(processed):
            raise CodecError("FEEDBACK_RANGE_OUTSIDE_OUTPUT")
        if any(start < b and a < end for a, b in ranges):
            raise CodecError("OVERLAPPING_FEEDBACK_RANGES")
        ranges.append((start, end))
        ports.append((port, processed[start:end]))
    binding = canonical_json({
        "frame_sha256": frame.sha256, "policy_sha256": policy.sha256,
        "processed_sha256": hashlib.sha256(processed).hexdigest(),
        "ports": [{"port": p, "bytes": len(data),
                   "sha256": hashlib.sha256(data).hexdigest()} for p, data in ports],
    }).encode("utf-8")
    ack = EffectAckEngine().evaluate(EffectAckRequest(
        protocol_root_id="qikvrt:local-feedback:" + frame.sha256,
        input_id="LOCAL_FEEDBACK_PROPOSAL", payload=binding, transport_ack=True,
        context_checked=True, semantics_reconstructed=True, effect_anticipated=True,
        policy_allows_release=False,
        reasons=("LOCAL_FEEDBACK_ONLY_NO_AUTHENTICATED_PROVIDER_EFFECT",),
        next_required_checks=("EXISTING_EXECUTOR_ADMISSION_AND_NATIVE_EFFECT_READBACK",),
    ))
    return FeedbackStep(frame, policy.sha256, zeros, ones, processed, tuple(ports), ack)


def local_refeed(step: FeedbackStep, policy: FeedbackPolicy, *, port: int,
                 sequence: int, tick: int) -> BitFrame:
    """Create a next local frame only; no automatic execution or external ACK."""
    if type(step) is not FeedbackStep or type(policy) is not FeedbackPolicy:
        raise CodecError("STEP_AND_POLICY_REQUIRED")
    _integer(port, 0, 3, "INVALID_PORT")
    _integer(sequence, 0, 2**64 - 1, "INVALID_SEQUENCE")
    _integer(tick, 0, 2**64 - 1, "INVALID_TICK")
    if step.policy_sha256 != policy.sha256:
        raise CodecError("FEEDBACK_POLICY_CHANGED")
    observed = feedback_step(step.frame, policy)
    if (step.zeros, step.ones, step.processed, step.ports) != (
            observed.zeros, observed.ones, observed.processed, observed.ports):
        raise CodecError("FEEDBACK_STEP_TAMPERED")
    if step.frame.hop >= policy.max_hops:
        raise CodecError("FEEDBACK_HOP_LIMIT_EXCEEDED")
    if sequence <= step.frame.sequence or tick <= step.frame.tick:
        raise CodecError("NONADVANCING_SEQUENCE_OR_TICK")
    for selected_port, data in step.ports:
        if selected_port == port:
            return BitFrame(step.frame.direction, sequence, tick, data,
                            step.frame.hop + 1, step.frame.sha256, port=port)
    raise CodecError("PORT_HAS_NO_FEEDBACK")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("encode", "decode"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--signature-file", type=Path,
                        help="Verify an explicit expected signature; default is the fixed V1 standpoint")
    parser.add_argument("--allow-legacy-seed", action="store_true",
                        help="Decode historical generic-seed transport with an explicit signature file")
    parser.add_argument("--profile", choices=tuple(PROFILES), default="balanced")
    parser.add_argument("--block-bytes", type=int, default=DEFAULT_BLOCK_BYTES)
    parser.add_argument("--max-output-bytes", type=int, default=None)
    args = parser.parse_args(argv)
    temporary = None
    try:
        signature = QIKVRT_SIGNATURE if args.signature_file is None else args.signature_file.read_bytes()
        if args.allow_legacy_seed and (args.operation != "decode" or args.signature_file is None):
            raise CodecError("LEGACY_DECODE_REQUIRES_EXPLICIT_SIGNATURE_FILE")
        _expected_signature(signature, args.allow_legacy_seed)
        protected = [args.input.resolve()]
        if args.signature_file is not None:
            protected.append(args.signature_file.resolve())
        if args.output.resolve() in protected:
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
                              max_output_bytes=args.max_output_bytes,
                              allow_legacy_seed=args.allow_legacy_seed)
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
