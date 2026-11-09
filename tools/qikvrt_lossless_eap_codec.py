"""QIK-VRT lossless binary streaming reference codec (candidate, not production EAP)."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct

START = b"001"
END = b"100"
MAX_PAYLOAD = 16 * 1024 * 1024
HEADER = len(START) + 8 + 32


def encode(payload: bytes) -> bytes:
    """Losslessly frame any bytes, including embedded 001/100 sequences."""
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too large")
    return START + struct.pack(">Q", len(payload)) + hashlib.sha256(payload).digest() + payload + END


@dataclass(frozen=True)
class Decoded:
    payload: bytes
    sha256: str


class Decoder:
    """Incremental bounded decoder; no side effects or implicit acknowledgements."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> list[Decoded]:
        if not isinstance(chunk, bytes):
            raise TypeError("chunk must be bytes")
        self._buffer.extend(chunk)
        out: list[Decoded] = []
        while True:
            if len(self._buffer) >= len(START) and self._buffer[:3] != START:
                raise ValueError("invalid start marker")
            if len(self._buffer) < HEADER:
                break
            length = struct.unpack(">Q", self._buffer[3:11])[0]
            if length > MAX_PAYLOAD:
                raise ValueError("declared payload too large")
            total = HEADER + length + len(END)
            if len(self._buffer) < total:
                break
            digest = bytes(self._buffer[11:43])
            payload = bytes(self._buffer[HEADER:HEADER + length])
            if self._buffer[HEADER + length:total] != END:
                raise ValueError("invalid end marker")
            if hashlib.sha256(payload).digest() != digest:
                raise ValueError("payload integrity mismatch")
            out.append(Decoded(payload, digest.hex()))
            del self._buffer[:total]
        return out

    def finish(self) -> None:
        if self._buffer:
            raise ValueError("truncated frame")


@dataclass(frozen=True)
class EffectReceipt:
    event_id: str
    payload_sha256: str
    state: str


def acknowledge_effect(event_id: str, decoded: Decoded, *, authorized: bool,
                       executed: bool, independently_verified: bool) -> EffectReceipt:
    """A verified effect must be supplied by an external trusted verifier."""
    if not event_id:
        raise ValueError("event_id required")
    state = ("EFFECT_ACK_DONE" if authorized and executed and independently_verified
             else "EFFECT_ACK_HOLD")
    return EffectReceipt(event_id, decoded.sha256, state)
