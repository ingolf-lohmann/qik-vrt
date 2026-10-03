# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Canonical QIKVRT V1 standpoint and lossless finite-set byte codec.

The shared signature describes the protocol. It is not a secret, an approval,
or the contents of a snapshot. Payloads are opaque bytes and are never executed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import struct
from typing import Iterable

from src.qikvrt_effect_ack import canonical_json

VERSION = 1
SIGNATURE_BYTES = 400
STABLE_ID_BYTES = IDENTITY_BYTES = 32
SIGNATURE_MAGIC = b"QIKVRTSP"
SNAPSHOT_MAGIC = b"QIKVRTSS"
SIGNATURE_HEADER = struct.Struct(">8sHHHH32s")
SNAPSHOT_HEADER = struct.Struct(">8sHHQQ")
PAYLOAD_LENGTH = struct.Struct(">Q")
SIGNATURE_DOMAIN = b"QIKVRT-STANDPOINT-V1\x00"
IDENTITY_DOMAIN = b"QIKVRT-ELEMENT-V1\x00"

# Materialization of the declared invariants, not a recovered historical image.
SIGNATURE_DESCRIPTOR = {
    "codec": "QIKVRT",
    "element_binding": ["signature", "stable_id", "payload"],
    "element_identity": "SHA-256",
    "external_service_required": False,
    "format": VERSION,
    "order": "stable_id_bytes",
    "payload": "opaque_bytes",
    "serialization": "canonical_binary",
    "signature_bytes": SIGNATURE_BYTES,
    "validation": "fail_closed",
}
_SIGNATURE_PAYLOAD = canonical_json(SIGNATURE_DESCRIPTOR).encode("utf-8")
_SIGNATURE_PREFIX = struct.pack(
    ">8sHHHH", SIGNATURE_MAGIC, VERSION, SIGNATURE_BYTES,
    len(_SIGNATURE_PAYLOAD), 0,
)
QIKVRT_SIGNATURE = (
    _SIGNATURE_PREFIX
    + hashlib.sha256(
        SIGNATURE_DOMAIN + _SIGNATURE_PREFIX + _SIGNATURE_PAYLOAD
    ).digest()
    + _SIGNATURE_PAYLOAD
    + bytes(SIGNATURE_BYTES - SIGNATURE_HEADER.size - len(_SIGNATURE_PAYLOAD))
)
SIGNATURE_SHA256 = hashlib.sha256(QIKVRT_SIGNATURE).hexdigest()
MIN_ELEMENT_BYTES = SIGNATURE_BYTES + STABLE_ID_BYTES + IDENTITY_BYTES + 8
MIN_SNAPSHOT_BYTES = SNAPSHOT_HEADER.size + SIGNATURE_BYTES


class CodexError(ValueError):
    """Invalid, noncanonical, unsupported or over-budget input."""


def validate_signature(signature: bytes) -> None:
    """Accept only the exact V1 standpoint, including its zero padding."""
    if type(signature) is not bytes or len(signature) != SIGNATURE_BYTES:
        raise CodexError("signature must be exactly 400 immutable bytes")
    magic, version, size, length, flags, digest = SIGNATURE_HEADER.unpack_from(signature)
    if (magic, version, size, flags) != (SIGNATURE_MAGIC, VERSION, SIGNATURE_BYTES, 0):
        raise CodexError("unsupported signature header")
    if length != len(_SIGNATURE_PAYLOAD):
        raise CodexError("noncanonical signature payload length")
    end = SIGNATURE_HEADER.size + length
    payload = signature[SIGNATURE_HEADER.size:end]
    expected_digest = hashlib.sha256(SIGNATURE_DOMAIN + signature[:16] + payload).digest()
    if not hmac.compare_digest(digest, expected_digest):
        raise CodexError("signature payload digest mismatch")
    if signature[end:] != bytes(SIGNATURE_BYTES - end):
        raise CodexError("noncanonical signature padding")
    # Recomputing a digest does not authorize a different standpoint.
    if not hmac.compare_digest(signature, QIKVRT_SIGNATURE):
        raise CodexError("signature differs from the bound QIKVRT V1 standpoint")


def _identity(signature: bytes, stable_id: bytes, payload: bytes) -> bytes:
    digest = hashlib.sha256(IDENTITY_DOMAIN)
    digest.update(VERSION.to_bytes(2, "big"))
    digest.update(signature)
    digest.update(stable_id)
    digest.update(PAYLOAD_LENGTH.pack(len(payload)))
    digest.update(payload)
    return digest.digest()


@dataclass(frozen=True, slots=True)
class Element:
    """Immutable element: shared standpoint, stable label and content identity.

    Callers assign and persist a distinct 32-byte stable_id per logical element.
    Identical payloads may belong to different elements. A content change keeps
    the stable label and yields a new identity; the codec invents no labels.
    """

    stable_id: bytes
    payload: bytes
    signature: bytes = QIKVRT_SIGNATURE
    identity: bytes = field(init=False)

    def __post_init__(self) -> None:
        validate_signature(self.signature)
        if type(self.stable_id) is not bytes or len(self.stable_id) != STABLE_ID_BYTES:
            raise CodexError("stable_id must be exactly 32 immutable bytes")
        if type(self.payload) is not bytes or len(self.payload) > 2**64 - 1:
            raise CodexError("payload must be immutable bytes with a uint64 length")
        object.__setattr__(self, "identity", _identity(self.signature, self.stable_id, self.payload))


@dataclass(frozen=True, slots=True)
class Limits:
    """Local resource budget, separate from the V1 wire representation."""

    max_snapshot_bytes: int = 64 * 1024 * 1024
    max_elements: int = 100_000
    max_payload_bytes: int = 16 * 1024 * 1024

    def __post_init__(self) -> None:
        values = (self.max_snapshot_bytes, self.max_elements, self.max_payload_bytes)
        if any(type(value) is not int or not 0 <= value <= 2**64 - 1 for value in values):
            raise CodexError("limits must be uint64 integers, not booleans")


DEFAULT_LIMITS = Limits()


def _limits(limits: Limits) -> None:
    if type(limits) is not Limits:
        raise CodexError("limits must be a Limits instance")


def serialize(elements: Iterable[Element], *, limits: Limits = DEFAULT_LIMITS) -> bytes:
    """Serialize a finite set in increasing stable-ID byte order.

    Snapshot, dump and serialization name this same wire representation.
    No timestamp, platform byte order, text normalization or hidden state enters
    the encoding. Nothing is returned until the complete set has been checked.
    """
    _limits(limits)
    if MIN_SNAPSHOT_BYTES > limits.max_snapshot_bytes:
        raise CodexError("snapshot exceeds byte budget")
    ordered = []
    stable_ids: set[bytes] = set()
    identities: set[bytes] = set()
    size = MIN_SNAPSHOT_BYTES
    try:
        iterator = iter(elements)
    except TypeError as exc:
        raise CodexError("elements must be iterable") from exc
    for element in iterator:
        if len(ordered) >= limits.max_elements:
            raise CodexError("element count exceeds budget")
        if type(element) is not Element:
            raise CodexError("snapshot members must be Element instances")
        if type(element.payload) is bytes and len(element.payload) > limits.max_payload_bytes:
            raise CodexError("payload exceeds byte budget")
        if type(element.payload) is bytes and size + MIN_ELEMENT_BYTES + len(element.payload) > limits.max_snapshot_bytes:
            raise CodexError("snapshot exceeds byte budget")
        # Validate again at the boundary, even for a frozen dataclass.
        checked = Element(element.stable_id, element.payload, element.signature)
        if type(element.identity) is not bytes or not hmac.compare_digest(element.identity, checked.identity):
            raise CodexError("element identity mismatch")
        if checked.stable_id in stable_ids or checked.identity in identities:
            raise CodexError("duplicate element identity or stable_id")
        if len(checked.payload) > limits.max_payload_bytes:
            raise CodexError("payload exceeds byte budget")
        size += MIN_ELEMENT_BYTES + len(checked.payload)
        if size > limits.max_snapshot_bytes:
            raise CodexError("snapshot exceeds byte budget")
        stable_ids.add(checked.stable_id)
        identities.add(checked.identity)
        ordered.append(checked)
    ordered.sort(key=lambda element: element.stable_id)
    records = b"".join(
        element.signature + element.stable_id + element.identity
        + PAYLOAD_LENGTH.pack(len(element.payload)) + element.payload
        for element in ordered
    )
    return (
        SNAPSHOT_HEADER.pack(SNAPSHOT_MAGIC, VERSION, SIGNATURE_BYTES, len(ordered), len(records))
        + QIKVRT_SIGNATURE + records
    )


def deserialize(data: bytes, *, limits: Limits = DEFAULT_LIMITS) -> tuple[Element, ...]:
    """Validate the whole canonical snapshot before exposing any element."""
    _limits(limits)
    if type(data) is not bytes:
        raise CodexError("snapshot must be immutable bytes")
    if not MIN_SNAPSHOT_BYTES <= len(data) <= limits.max_snapshot_bytes:
        raise CodexError("snapshot length is truncated or exceeds budget")
    magic, version, signature_size, count, body_size = SNAPSHOT_HEADER.unpack_from(data)
    if (magic, version, signature_size) != (SNAPSHOT_MAGIC, VERSION, SIGNATURE_BYTES):
        raise CodexError("unsupported snapshot header")
    if body_size != len(data) - MIN_SNAPSHOT_BYTES:
        raise CodexError("snapshot body length mismatch or trailing bytes")
    if count > limits.max_elements or count > body_size // MIN_ELEMENT_BYTES:
        raise CodexError("element count is impossible or exceeds budget")
    validate_signature(data[SNAPSHOT_HEADER.size:MIN_SNAPSHOT_BYTES])
    offset = MIN_SNAPSHOT_BYTES
    previous: bytes | None = None
    identities: set[bytes] = set()
    elements = []
    for _ in range(count):
        if len(data) - offset < MIN_ELEMENT_BYTES:
            raise CodexError("truncated element header")
        signature = data[offset:offset + SIGNATURE_BYTES]
        validate_signature(signature)
        offset += SIGNATURE_BYTES
        stable_id = data[offset:offset + STABLE_ID_BYTES]
        offset += STABLE_ID_BYTES
        identity = data[offset:offset + IDENTITY_BYTES]
        offset += IDENTITY_BYTES
        length = PAYLOAD_LENGTH.unpack_from(data, offset)[0]
        offset += PAYLOAD_LENGTH.size
        if previous is not None and stable_id <= previous:
            raise CodexError("duplicate stable_id or noncanonical element order")
        if length > limits.max_payload_bytes or length > len(data) - offset:
            raise CodexError("payload length is truncated or exceeds budget")
        element = Element(stable_id, data[offset:offset + length], signature)
        offset += length
        if not hmac.compare_digest(identity, element.identity):
            raise CodexError("element identity digest mismatch")
        if identity in identities:
            raise CodexError("duplicate element identity")
        identities.add(identity)
        previous = stable_id
        elements.append(element)
    if offset != len(data):
        raise CodexError("surplus elements or trailing bytes")
    return tuple(elements)
