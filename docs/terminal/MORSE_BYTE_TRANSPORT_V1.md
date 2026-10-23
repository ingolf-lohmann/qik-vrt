# Byte-exact Morse transport v1

Work unit: QIKVRT_MORSE_BYTE_TRANSPORT_20261023; PR578.
Human purpose and authorization: Ingolf Lohmann. Implementation: OpenAI Codex.
Review source: https://www.meta.ai/share/a/eee3d5d5-f50e-497e-a083-1b3bfbd1b71b

The former letter translator changes case and drops punctuation. This codec
preserves the exact bytes of UTF-8 text, punctuation, line endings and binary
files. The finite MVP limit is 16,384 payload bytes per frame, including empty
payloads. It does not normalize Unicode, change case, or convert line endings.

## Wire format

Before Morse encoding: ASCII QIKM, version byte 0x01, unsigned 64-bit big-endian
payload length, 32-byte SHA-256(header + payload), then the original payload.
The header included in the hash comprises magic, version and length (13 bytes).
Every byte is represented by two uppercase hexadecimal digits, each mapped to
ordinary Morse for 0-9/A-F. Exactly one ASCII space separates the tokens; there
is no trailing newline. Invalid tokens, spacing, version, length or digest are
explicit errors. SHA-256 is a corruption check, not sender authentication.

Python and browser JavaScript implement the same frame and verification rules.
A text field starts with UTF-8 bytes; use file input to preserve a source file's
exact encoding and original line endings. Text preview is never the download.

## Portable file interface

Requires Python 3 (standard library only):

    python3 src/qikvrt_morse_transport.py encode input.bin output.morse
    python3 src/qikvrt_morse_transport.py decode output.morse recovered.bin

The output must be a new path. The self-contained HTML edition provides the
same codec and actual Blob downloads without a server. Offline verification is
explicitly distinguished from durable native persistence.

## Existing native S1 runtime

The existing tools/qikvrt_self_host.py launcher packages and serves /morse/ on
its existing native terminal listener, using terminal_profile=temdd. Its Linux
Python/Node requirements and source/volume/configuration admission remain intact.
No replacement daemon, scheduler, artifact database or executor is introduced.
Add src/qikvrt_morse_transport.py and the fixed interface assets to PACKAGE.json.

Use the existing owner_rest_grants (prepare, commit, readback); use an existing
admitted secret file. The ordinary read-only terminal token never becomes a
writer credential. Host/Origin checks, source pins and native writer fencing
remain enforced. Never publish a bearer token, native private volume or original
historical journal as a way of making the demonstration accessible.

POST /api/owner/morse/prepare and /commit take schema
qikvrt-morse-request/v1, request_id, exact subject, operation (encode/decode)
and data (canonical Base64 for encode, canonical Morse frame for decode).
They retain the existing Effect-Ack-Request prepare/commit headers and token
binding. The Terminal first persists bounded input; the native Runtime then
persists the deterministic result as an EFFECT event. Actual result bytes live
in that original event; an input observation alone is never a result receipt.

GET /api/owner/morse/receipts/<request_id> independently reads the original
SQLite journal. GET /api/owner/morse/download/<request_id>/data, /morse and
/receipt return actual persisted bytes, regenerated canonical Morse, or the
receipt, with attachment filenames and Content-Digest headers. Existing owner
and exact-subject headers are required. The browser independently downloads and
compares the persisted bytes before displaying durable success.

Replay of the same admitted request retains the event ID and digest. Changed
content under the same request ID is rejected. After a lost reply, read back
that request; retain its identity. Restart the same physical admitted volume;
a copied or unadmitted journal remains read-only under the existing ledger.

## Evidence and limits

Regression checks cover all byte values, Unicode forms, case, punctuation,
CR/LF, empty/maximal inputs, single-token corruption, cross-language frames,
authenticated HTTP, actual downloads, hard-stop/restart, lost responses, replay,
wrong identity/subject/origin and tampered stored data. Test fixtures are local
test evidence. Production activation and current peer acceptance remain separate.

RFC 8785 preserves Unicode string data; NFC/LF preprocessing would require a
separate declared profile and would not preserve the original byte sequence.
Reference: https://www.rfc-editor.org/rfc/rfc8785.html#section-3.1
Neither a hash, self-declared date, quine nor a channel establishes an independent
timestamp, computational universality, a physical claim, or global EFFECT_ACK_DONE.
