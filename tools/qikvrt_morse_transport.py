#!/usr/bin/env python3
"""Bounded, lossless Morse-compatible transport for arbitrary byte strings.

This is an offline reference harness, not a physical telegraph modem.
"""
import argparse
import hashlib
import struct
from pathlib import Path

MAGIC = b"QVM1"
CHUNK = 32
HEADER = struct.Struct(">4sII32sI")
DIGITS = {
    "0":"-----", "1":".----", "2":"..---", "3":"...--", "4":"....-",
    "5":".....", "6":"-....", "7":"--...", "8":"---..", "9":"----.",
    "a":".-", "b":"-...", "c":"-.-.", "d":"-..", "e":".", "f":"..-."
}
REVERSE = {v:k for k,v in DIGITS.items()}


class TransportError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).digest()


def encode(data, chunk_size=CHUNK):
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    if not 1 <= chunk_size <= CHUNK:
        raise ValueError("invalid chunk size")
    chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)] or [b""]
    if len(chunks) > 1_000_000:
        raise ValueError("frame limit exceeded")
    whole = digest(data)
    lines = []
    for seq, part in enumerate(chunks):
        rec = HEADER.pack(MAGIC, seq, len(chunks), whole, len(part)) + part + digest(part)
        lines.append(" ".join(DIGITS[c] for c in rec.hex()))
    return "\n".join(lines) + "\n"


def decode(stream):
    if not isinstance(stream, str) or not stream.endswith("\n"):
        raise TransportError("terminator required")
    lines = stream[:-1].split("\n")
    if not lines or len(lines) > 1_000_000 or any(not line for line in lines):
        raise TransportError("invalid frame count")
    result = bytearray()
    whole = None
    for seq, line in enumerate(lines):
        try:
            hextext = "".join(REVERSE[token] for token in line.split(" "))
            if not hextext or len(hextext) % 2:
                raise ValueError("hex length")
            rec = bytes.fromhex(hextext)
        except (KeyError, ValueError) as exc:
            raise TransportError("invalid Morse frame") from exc
        if len(rec) < HEADER.size + 32:
            raise TransportError("truncated frame")
        magic, actual_seq, total, claimed_whole, size = HEADER.unpack_from(rec)
        if magic != MAGIC or actual_seq != seq or total != len(lines):
            raise TransportError("version/order/count mismatch")
        if size > CHUNK or len(rec) != HEADER.size + size + 32:
            raise TransportError("length mismatch")
        part = rec[HEADER.size:HEADER.size+size]
        if digest(part) != rec[-32:]:
            raise TransportError("chunk digest mismatch")
        if whole is None:
            whole = claimed_whole
        elif whole != claimed_whole:
            raise TransportError("whole digest binding mismatch")
        result.extend(part)
    data = bytes(result)
    if whole is None or digest(data) != whole:
        raise TransportError("whole digest mismatch")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="op", required=True)
    for op in ("encode", "decode"):
        cmd = subs.add_parser(op)
        cmd.add_argument("source", type=Path)
        cmd.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.destination.exists():
        parser.error("destination exists; refusing overwrite")
    data = args.source.read_bytes()
    out = encode(data).encode("ascii") if args.op == "encode" else decode(data.decode("ascii"))
    with args.destination.open("xb") as f:
        f.write(out)
        f.flush()


if __name__ == "__main__":
    main()
