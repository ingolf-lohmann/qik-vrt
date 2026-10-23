# Byte-exact Morse transport v1

Work unit: QIKVRT_MORSE_BYTE_TRANSPORT_20261023.
Human purpose and authorization: Ingolf Lohmann; implementation: OpenAI Codex.
Source under review: https://www.meta.ai/share/a/eee3d5d5-f50e-497e-a083-1b3bfbd1b71b

The former letter translator changes case and drops punctuation. The successor
must preserve every input byte, including UTF-8, line endings and binary data.
Use versioned binary framing with length and SHA-256 integrity, then encode its
hexadecimal digits with Morse. Reject malformed or corrupted frames explicitly.

Reuse the existing native ledger, OwnerREST prepare/commit and independent
Terminal readback. Persist result bytes in the original ledger and derive actual
downloads from the persisted result. Preserve authenticated loopback admission,
writer fencing, source identity and every predecessor journal.

Acceptance: cross-language byte equality; corruption rejection; durable result
readback after process restart; lost-response recovery without duplicate effects;
real downloads matching their receipt. Public host activation remains separate.

RFC 8785 preserves Unicode strings; any NFC/LF preprocessing requires its own
profile and cannot be labelled lossless recovery of the original bytes.
