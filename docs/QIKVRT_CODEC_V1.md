<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# QIK-VRT Codec V1

Ingolf Lohmann authorizes a versioned lossless codec for static data and streams
as part of the QIK-VRT personal Digital Twin architecture. Its executable scope
is arbitrary byte transport and canonical finite mesh snapshots. The normative
byte layout and boundaries are in
`policy/QIKVRT_CODEC_CONTRACT_V1.json`; implementation:
`src/qikvrt_codec.py`.

The current source tree contained model-bound formal codec laws and JSON/REST
serialization, but no executable general byte compression codec. This successor
reuses the Python standard library's RFC 1950/RFC 1951 zlib implementation and
the existing repository integrity generator. The benchmark baseline is the
declared framed full-block compression trial, not an invented historical
QIK-VRT compressor.

## Seed and identity

Every mesh element carries the identical **400 exact seed bytes** and a separate
32-byte identity. No checksum digit sum is used. New identities use SHA-256 of
a domain label, the seed and a fresh 32-byte CSPRNG nonce; identical payloads may
belong to distinct elements. An element's identity can remain stable when its
payload changes; snapshot hashes change with the payload. Duplicate identities
are rejected, even when their payloads differ.

Available owner statements specify the common seed's length and purpose, but do
not bind its contents. Consequently there is **no default or fabricated owner
seed**. Callers supply the exact 400 bytes through the API or `--signature-file`.
Decoders require an independently supplied expected seed and compare every
element to it. The synthetic test/benchmark seed is explicitly a fixture.
This implementation fixes an envelope around the supplied bytes; it does not
assert that an arbitrary fixture is the owner's final standpoint signature.
SHA-256 provides collision-resistant bindings under its usual cryptographic
assumptions. A common marker or unkeyed hash is not a person's authenticated
digital signature and does not attest an external physical effect.

## Canonical snapshots and transport

A snapshot starts with a 20-byte big-endian header, the common seed, then elements
in strictly increasing bytewise identity order. Each element contains
`identity32 || seed400 || payload_length_u64 || exact_payload`. A 32-byte
SHA-256 trailer binds all preceding bytes. Unknown versions/flags, duplicate or
unsorted identities, mixed seeds, malformed lengths and trailing input fail
closed. For every accepted snapshot `S`,
`dump_snapshot(load_snapshot(S, seed), seed) == S`. The same finite element set
has the same snapshot bytes regardless of input iteration order.

The compression container starts with a 416-byte header, followed by bounded
independent blocks and a 49-byte END footer. The header binds version, maximum
block size and common seed. Every block binds method, raw/stored lengths and
raw SHA-256; the footer binds exact wire bytes, block count and total raw bytes.
Raw blocks prevent compression-induced payload expansion. Complete framing
adds at most `465 + 41 * ceil(input_bytes / block_bytes)` bytes. Empty input has
zero blocks. Only the last block may be shorter than the declared block size.

For every successfully encoded finite byte string `x`,
`decode(encode(x, seed), seed) == x`, subject to the consumer's explicit resource
limits. Compression is byte-preserving: there is no JSON normalization, text
conversion or environment-specific representation of arbitrary input bytes.
Different compression profiles or zlib versions can produce different valid
transport bytes. Canonical snapshot byte identity is independent of this storage
choice. Re-encoding compressed input is not promised to reproduce its original
compressed bitstream across runtimes; preserve the exact container when its wire
hash matters.

## Time and space profiles

| Profile | Compression trial | Purpose |
| --- | --- | --- |
| `raw` | None | Lowest compression work; bounded framing overhead |
| `fast` | zlib level 1, with distributed sampling | Prefer throughput; sampling may miss compressible regions |
| `balanced` (default) | Full block, zlib level 6 | Balanced compression without sampling shortcuts |
| `compact` | Full block, zlib level 9 | Prefer space within this algorithm and block layout |

Only `fast` samples. Four distributed 2048-byte samples are compressed at level
1 for blocks of at least 65536 bytes. A sample ratio of at least 0.98 selects RAW
without the full compression trial. This accelerates incompressible workloads
but is not an entropy proof. The benchmark includes an adversarial sample layout
that exposes the tradeoff; regression tests require `balanced` and `compact` to
compress those data fully. No profile is asserted to be fastest or smallest for
all inputs, environments or future versions. Lossless compression cannot shorten
every possible finite input: injectivity and the number of available shorter
bit strings exclude that claim.

`encode_stream` and `decode_stream` use bounded blocks, default 256 KiB, at most
16 MiB. Auxiliary space is O(block size), not total stream size. Decoding caps
each zlib result at its declared length plus one byte and rejects unfinished,
concatenated, dictionary-dependent and oversized streams. Short blocking
reads/writes work; nonblocking `None` and zero-progress writes fail closed.
Version 1 has explicit unsigned 64-bit byte/block counters. Static APIs allocate
their returned bytes; their default decode limit is 256 MiB and can be explicitly
changed. Snapshots are finite in-memory sets with separate element/payload limits.

A stream can be produced incrementally for as long as input and resources remain
available. Complete-container acceptance requires a verified END footer. A
nonterminating stream is never falsely reported as a complete finite container.
`decode_stream` verifies each block before writing it, but a late footer failure
may follow already-written blocks. Callers stage output when whole-container
atomicity is required. The CLI always stages beside the destination, validates
the complete input, and replaces the destination only after success.

## Use and reproduce

```python
from src.qikvrt_codec import encode, decode, new_element, dump_snapshot, load_snapshot

# seed is independently supplied, exact 400-byte owner/application configuration.
wire = encode(payload, signature=seed, profile="balanced")
assert decode(wire, signature=seed) == payload
element = new_element(payload, signature=seed)
snapshot = dump_snapshot([element], signature=seed)
assert dump_snapshot(load_snapshot(snapshot, signature=seed), signature=seed) == snapshot
```

```sh
python3 -B -m src.qikvrt_codec encode input.bin output.qikvrt --signature-file seed.bin
python3 -B -m src.qikvrt_codec decode output.qikvrt restored.bin --signature-file seed.bin
make codec-test
python3 -B tools/qikvrt_codec_benchmark.py --repeats 7 --output /tmp/codec-benchmark.json
```

The versioned endian-defined wire format contains no operating-system or CPU
layout assumptions. A compatible runtime needs byte I/O, SHA-256 and the
documented zlib decoding method. Tests and measurements establish the observed
Linux runtime only. Windows, macOS, Docker/cloud deployments and future runtimes
remain separate acceptance subjects. Future versions must register their own
layouts and explicitly retain V1 decoding; unknown versions fail closed rather
than being guessed.

## Digital Twin and effect boundary

Existing API: `policy/QIKVRT_DIGITAL_TWIN_REST_CONTRACT_V1.json`,
`src/qikvrt_digital_twin_rest.py`. Its JSON state/receipt bytes can be transported
losslessly by this codec; encoding them does not authorize executing their
contents. The Siemens reference module is absent on the observed Main and is
already being restored through PR #422. This codec does not duplicate that work
or claim a tested Siemens tenant connection.

Owner-asserted personal Digital Twin capability, reality correspondence and the
REST/meta-transistor architecture are retained as attributed product goals.
The implementation tests do not establish autonomous execution in every human
role, physical FPGA operation, Siemens Horizon tenant integration, authenticated
personal-browser release, scientific consensus or perpetual future compatibility.
The existing personal-capability boundary and `TRANSPORT_ACK != EFFECT_ACK`
remain in force. No release/deployment/publication effect is granted by encoding,
successful tests or this contract alone.
