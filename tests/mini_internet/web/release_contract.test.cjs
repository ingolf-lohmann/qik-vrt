// Execute the actual verifyRelease function from app.jsx in an isolated Node VM.
// No network, no browser, no production admission. Regression against signature,
// digest, origin, and check/use substitution.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const crypto = require("node:crypto");
const { webcrypto } = crypto;
const { subtle } = webcrypto;

const source = fs.readFileSync(__dirname + "/app.jsx", "utf8");
const start = source.indexOf("async function verifyRelease(");
const end = source.indexOf("\nfunction App()", start);
assert(start >= 0 && end > start, "verifyRelease function must exist");
const fnSource = source.slice(start, end);
const encoder = new TextEncoder();
const bytes = encoder.encode(JSON.stringify({ feature: "verified" }));
const digest = crypto.createHash("sha256").update(bytes).digest("hex");

async function run() {
  const keys = await subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  const jwk = await subtle.exportKey("jwk", keys.publicKey);
  let fetches = [];
  let assetBytes = bytes;
  const context = {
    window: { __QIKVRT_RELEASE_KEY__: jwk },
    crypto: webcrypto, TextEncoder, TextDecoder, Uint8Array, Array,
    atob: (s) => Buffer.from(s, "base64").toString("binary"),
    fetch: async (url) => {
      fetches.push(url);
      return { ok: true, arrayBuffer: async () => assetBytes.slice().buffer };
    }
  };
  vm.createContext(context);
  vm.runInContext(`
    const PINNED_RELEASE_KEY_JWK = window.__QIKVRT_RELEASE_KEY__;
    const hex = (buf) => Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
    const b64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
    ${fnSource}
    globalThis.testVerifyRelease = verifyRelease;
  `, context);
  const sign = async (text) => Buffer.from(await subtle.sign(
    { name: "ECDSA", hash: "SHA-256" }, keys.privateKey, encoder.encode(text)
  )).toString("base64");
  const manifest = (extra = {}) => JSON.stringify({
    schema: "qikvrt.client.release.v2", version: "v1",
    asset: "/release/v1.json", sha256: digest, ...extra
  });
  const good = manifest();
  const signature = await sign(good);
  const verified = await context.testVerifyRelease(good, signature);
  assert.equal(verified.digest, digest);
  assert.equal(verified.payload.feature, "verified");
  assert.deepEqual(fetches, ["/release/v1.json"]);
  console.log("PASS valid signature, digest and single exact-byte read");

  fetches = [];
  await assert.rejects(context.testVerifyRelease(good, await sign(manifest({version:"v2"}))), /RELEASE_SIGNATURE_INVALID/);
  assert.equal(fetches.length, 0);
  console.log("PASS signed-manifest substitution rejected before fetch");

  fetches = [];
  assetBytes = encoder.encode('{"feature":"tampered"}');
  await assert.rejects(context.testVerifyRelease(good, signature), /RELEASE_HASH_MISMATCH/);
  assert.equal(fetches.length, 1);
  assetBytes = bytes;
  console.log("PASS asset tampering rejected");

  for (const asset of ["https://evil.test/release.json", "//evil.test/release.json", "/../release.json", "/release.js"]) {
    fetches = [];
    const text = manifest({asset});
    await assert.rejects(context.testVerifyRelease(text, await sign(text)), /RELEASE_ASSET_PATH_INVALID/);
    assert.equal(fetches.length, 0);
  }
  console.log("PASS signed but unsafe asset paths rejected");

  fetches = [];
  const wrong = manifest({sha256:"0".repeat(64)});
  await assert.rejects(context.testVerifyRelease(wrong, await sign(wrong)), /RELEASE_HASH_MISMATCH/);
  console.log("PASS signed incorrect digest rejected");
  fetches = [];
  for (const extra of [
    {schema:"unrecognized.release.v0"},
    {version:"v-1"},
    {sha256:"invalid"}
  ]) {
    const text = manifest(extra);
    await assert.rejects(context.testVerifyRelease(text, await sign(text)),
      /RELEASE_(SCHEMA_MISMATCH|VERSION_INVALID|DIGEST_INVALID)/);
    assert.equal(fetches.length, 0);
  }
  console.log("PASS signed but invalid schema, version and digest format rejected");

  fetches = [];
  // The trust root is a lexical const in the VM; mutating context properties
  // cannot alter it. Execute isolated function copies with explicit bad roots.
  const noRoot = vm.runInContext("(" + fnSource.replaceAll("PINNED_RELEASE_KEY_JWK", "undefined") + ")", context);
  await assert.rejects(noRoot(good, signature), /RELEASE_TRUST_ROOT_MISSING/);
  assert.equal(fetches.length, 0);
  const wrongCurve = vm.runInContext("(" + fnSource.replaceAll("PINNED_RELEASE_KEY_JWK", '({kty:"EC",crv:"P-384"})') + ")", context);
  await assert.rejects(wrongCurve(good, signature), /RELEASE_TRUST_ROOT_MISSING/);
  assert.equal(fetches.length, 0);
  console.log("PASS missing and wrong-curve trust root rejected before fetch");

  fetches = [];
  const other = await subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  const otherSig = Buffer.from(await subtle.sign({name:"ECDSA",hash:"SHA-256"},other.privateKey,encoder.encode(good))).toString("base64");
  await assert.rejects(context.testVerifyRelease(good, otherSig), /RELEASE_SIGNATURE_INVALID/);
  assert.equal(fetches.length, 0);
  console.log("PASS foreign signing key rejected");

}
run().catch((err) => { console.error(err); process.exitCode = 1; });
