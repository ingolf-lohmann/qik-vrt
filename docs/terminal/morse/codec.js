/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex. */
(function (root) {
  'use strict';
  const MAGIC = Uint8Array.of(81, 73, 75, 77, 1), MAX_BYTES = 16384, HEADER = 45;
  const codes = ['-----', '.----', '..---', '...--', '....-', '.....', '-....', '--...',
    '---..', '----.', '.-', '-...', '-.-.', '-..', '.', '..-.'];
  const inverse = new Map(codes.map((code, n) => [code, n]));
  const cryptoAPI = root.crypto || (typeof require === 'function' ? require('node:crypto').webcrypto : null);
  const bytes = value => {
    if (!(value instanceof Uint8Array) || value.length > MAX_BYTES) throw Error('MORSE_BYTE_LIMIT_OR_TYPE');
    return new Uint8Array(value);
  };
  async function digest(raw) {
    if (!cryptoAPI?.subtle) throw Error('SHA256_UNAVAILABLE');
    return new Uint8Array(await cryptoAPI.subtle.digest('SHA-256', raw));
  }
  function concat(a, b) { const out = new Uint8Array(a.length + b.length); out.set(a); out.set(b, a.length); return out; }
  function hex(raw) { return Array.from(raw, n => n.toString(16).padStart(2, '0')).join(''); }
  async function encode(value) {
    const raw = bytes(value), header = new Uint8Array(13);
    header.set(MAGIC); new DataView(header.buffer).setUint32(9, raw.length, false);
    const frame = new Uint8Array(HEADER + raw.length);
    frame.set(header); frame.set(await digest(concat(header, raw)), 13); frame.set(raw, HEADER);
    return Array.from(frame).flatMap(n => [codes[n >>> 4], codes[n & 15]]).join(' ');
  }
  async function decode(text) {
    if (typeof text !== 'string' || !text || text.length > (MAX_BYTES + HEADER) * 12) throw Error('MORSE_FRAME_REQUIRED_OR_TOO_LARGE');
    const tokens = text.split(' ');
    if (tokens.length % 2) throw Error('MORSE_INCOMPLETE_BYTE');
    const frame = new Uint8Array(tokens.length / 2);
    for (let i = 0; i < tokens.length; i += 2) {
      const a = inverse.get(tokens[i]), b = inverse.get(tokens[i + 1]);
      if (a === undefined || b === undefined) throw Error('MORSE_UNKNOWN_TOKEN_OR_NONCANONICAL_SPACING');
      frame[i / 2] = (a << 4) | b;
    }
    if (frame.length < HEADER || MAGIC.some((n, i) => n !== frame[i])) throw Error('MORSE_VERSION_OR_HEADER');
    const view = new DataView(frame.buffer), raw = frame.slice(HEADER);
    if (view.getUint32(5, false) !== 0 || view.getUint32(9, false) !== raw.length || raw.length > MAX_BYTES) throw Error('MORSE_LENGTH_MISMATCH');
    const expected = await digest(concat(frame.slice(0, 13), raw));
    if (expected.some((n, i) => n !== frame[13 + i])) throw Error('MORSE_INTEGRITY_MISMATCH');
    return raw;
  }
  const api = Object.freeze({MAX_BYTES, encode, decode, hex, digest, sha256: async raw => hex(await digest(raw))});
  root.QikMorse = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(globalThis);
