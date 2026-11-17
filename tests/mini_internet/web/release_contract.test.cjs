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
const start = source.indexOf("const PINNED_RELEASE_KEY_JWK =");
const end = source.indexOf("\nfunction App()", start);
assert(start >= 0 && end > start, "release verifier and trust root must exist");
const verifierSource = source.slice(start, end);
const encoder = new TextEncoder();
const bytes = encoder.encode(JSON.stringify({ feature: "verified" }));
const digest = crypto.createHash("sha256").update(bytes).digest("hex");

async function run() {
  const keys = await subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  const jwk = await subtle.exportKey("jwk", keys.publicKey);
  let fetches = [];
  let assetBytes = bytes;
  function createVerifier(root) {
    const calls = { imports: 0 };
    const context = {
      window: { __QIKVRT_RELEASE_KEY__: root },
      crypto: { subtle: {
        importKey: (...args) => { calls.imports++; return subtle.importKey(...args); },
        verify: subtle.verify.bind(subtle),
        digest: subtle.digest.bind(subtle)
      } },
      TextEncoder, TextDecoder, Uint8Array, Array,
      atob: (s) => Buffer.from(s, "base64").toString("binary"),
      fetch: async (url) => {
        fetches.push(url);
        return { ok: true, arrayBuffer: async () => assetBytes.slice().buffer };
      }
    };
    vm.createContext(context);
    vm.runInContext(verifierSource + "\nglobalThis.testVerifyRelease = verifyRelease;", context);
    return { verify: context.testVerifyRelease, calls };
  }
  const verifier = createVerifier(jwk);
  const sign = async (text) => Buffer.from(await subtle.sign(
    { name: "ECDSA", hash: "SHA-256" }, keys.privateKey, encoder.encode(text)
  )).toString("base64");
  const manifest = (extra = {}) => JSON.stringify({
    schema: "qikvrt.client.release.v2", version: "v1",
    asset: "/release/v1.json", sha256: digest, ...extra
  });
  const good = manifest();
  const signature = await sign(good);
  const verified = await verifier.verify(good, signature);
  assert.equal(verified.digest, digest);
  assert.equal(verified.payload.feature, "verified");
  assert.deepEqual(fetches, ["/release/v1.json"]);
  console.log("PASS valid signature, digest and single exact-byte read");

  fetches = [];
  await assert.rejects(verifier.verify(good, await sign(manifest({version:"v2"}))), /RELEASE_SIGNATURE_INVALID/);
  assert.equal(fetches.length, 0);
  console.log("PASS signed-manifest substitution rejected before fetch");

  fetches = [];
  assetBytes = encoder.encode('{"feature":"tampered"}');
  await assert.rejects(verifier.verify(good, signature), /RELEASE_HASH_MISMATCH/);
  assert.equal(fetches.length, 1);
  assetBytes = bytes;
  console.log("PASS asset tampering rejected");

  for (const asset of ["https://evil.test/release.json", "//evil.test/release.json", "/../release.json", "/release.js"]) {
    fetches = [];
    const text = manifest({asset});
    await assert.rejects(verifier.verify(text, await sign(text)), /RELEASE_ASSET_PATH_INVALID/);
    assert.equal(fetches.length, 0);
  }
  console.log("PASS signed but unsafe asset paths rejected");

  fetches = [];
  const wrong = manifest({sha256:"0".repeat(64)});
  await assert.rejects(verifier.verify(wrong, await sign(wrong)), /RELEASE_HASH_MISMATCH/);
  console.log("PASS signed incorrect digest rejected");
  fetches = [];
  for (const extra of [
    {schema:"unrecognized.release.v0"},
    {version:"v-1"},
    {sha256:"invalid"}
  ]) {
    const text = manifest(extra);
    await assert.rejects(verifier.verify(text, await sign(text)),
      /RELEASE_(SCHEMA_MISMATCH|VERSION_INVALID|DIGEST_INVALID)/);
    assert.equal(fetches.length, 0);
  }
  console.log("PASS signed but invalid schema, version and digest format rejected");

  const wrongCurveKeys = await subtle.generateKey({ name: "ECDSA", namedCurve: "P-384" }, true, ["sign", "verify"]);
  const privateJwk = await subtle.exportKey("jwk", keys.privateKey);
  for (const [name, root] of [
    ["missing", undefined],
    ["wrong curve", await subtle.exportKey("jwk", wrongCurveKeys.publicKey)],
    ["private key material", privateJwk],
    ["empty private field", { ...jwk, d: "" }],
    ["wrong key type", { ...jwk, kty: "RSA" }]
  ]) {
    fetches = [];
    // Each context evaluates the unchanged source, including its lexical pin.
    const invalid = createVerifier(root);
    await assert.rejects(invalid.verify(good, signature), /RELEASE_TRUST_ROOT_MISSING/);
    assert.equal(invalid.calls.imports, 0, name + " must be rejected before key import");
    assert.equal(fetches.length, 0, name + " must be rejected before asset fetch");
    console.log("PASS " + name + " trust root rejected before key import and fetch");
  }

  fetches = [];
  const other = await subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  const otherSig = Buffer.from(await subtle.sign({name:"ECDSA",hash:"SHA-256"},other.privateKey,encoder.encode(good))).toString("base64");
  await assert.rejects(verifier.verify(good, otherSig), /RELEASE_SIGNATURE_INVALID/);
  assert.equal(fetches.length, 0);
  console.log("PASS foreign signing key rejected");

}
run().catch((err) => { console.error(err); process.exitCode = 1; });
