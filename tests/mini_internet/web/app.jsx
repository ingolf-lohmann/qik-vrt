// QIK-VRT Mini-Internet terminal client (React 19). Every displayed state is a server readback.
import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

const PINNED_RELEASE_KEY_JWK = window.__QIKVRT_RELEASE_KEY__; // injected at build time, not fetched

const hex = (buf) => Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
const b64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

async function verifyRelease(manifestText, signatureB64) {
  const key = await crypto.subtle.importKey("jwk", PINNED_RELEASE_KEY_JWK,
    { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, key,
    b64(signatureB64), new TextEncoder().encode(manifestText));
  if (!ok) throw new Error("RELEASE_SIGNATURE_INVALID");
  const m = JSON.parse(manifestText);
  if (m.schema !== "qikvrt.client.release.v2") throw new Error("RELEASE_SCHEMA_MISMATCH");
  if (typeof m.asset !== "string" || !m.asset.startsWith("/") || m.asset.startsWith("//") || !m.asset.endsWith(".json") || m.asset.includes("..") || !/^[a-zA-Z0-9/_-]+$/.test(m.asset.slice(1, -5))) throw new Error("RELEASE_ASSET_PATH_INVALID");
  if (typeof m.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(m.sha256)) throw new Error("RELEASE_DIGEST_INVALID");
  if (typeof m.version !== "string" || !/^v[0-9]+$/.test(m.version)) throw new Error("RELEASE_VERSION_INVALID");
  const asset = await fetch(m.asset, { cache: "no-store" });
  if (!asset.ok) throw new Error("RELEASE_ASSET_HTTP_" + asset.status);
  const bytes = await asset.arrayBuffer();
  const digest = hex(await crypto.subtle.digest("SHA-256", bytes));
  if (digest !== m.sha256) throw new Error("RELEASE_HASH_MISMATCH");
  // Use exactly the verified bytes; no second fetch (no check/use gap).
  return { manifest: m, payload: JSON.parse(new TextDecoder().decode(bytes)), digest };
}

function App() {
  const [runtime, setRuntime] = useState(null);
  const [release, setRelease] = useState(null);
  const [journal, setJournal] = useState([]);
  const seen = useRef(new Set());
  const log = (line) => setJournal((j) => [new Date().toISOString() + " " + line, ...j].slice(0, 40));

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const r = await fetch("/runtime", { cache: "no-store" });
        const x = await r.json();
        if (!alive) return;
        setRuntime(x);
        window.__qikvrtReadbacks = (window.__qikvrtReadbacks || []).concat([{ t: Date.now(), seq: x.seq }]);
        const rel = await (await fetch("/client-release", { cache: "no-store" })).json();
        if (rel.version && !seen.current.has(rel.version)) {
          try {
            const v = await verifyRelease(rel.manifest, rel.signature);
            if (v.manifest.version !== rel.version) throw new Error("RELEASE_ENVELOPE_VERSION_MISMATCH");
            const activation = await fetch("/activated", { method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ version: v.manifest.version, sha256: v.digest }) });
            if (!activation.ok) throw new Error("RELEASE_ACTIVATION_HTTP_" + activation.status);
            const readbackResponse = await fetch("/readback/active", { cache: "no-store" });
            if (!readbackResponse.ok) throw new Error("RELEASE_READBACK_HTTP_" + readbackResponse.status);
            const readback = await readbackResponse.json();
            if (!Array.isArray(readback.activated) || !readback.activated.some((entry) => entry.version === v.manifest.version && entry.sha256 === v.digest)) throw new Error("RELEASE_ACTIVATION_RECEIPT_INVALID");
            seen.current.add(rel.version);
            setRelease(v);
            log("ACTIVATED " + v.manifest.version + " sha256=" + v.digest.slice(0, 16));
          } catch (e) {
            await fetch("/rejected", { method: "POST", headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ version: rel.version, reason: String(e.message || e) }) });
            log("REJECTED " + rel.version + " " + String(e.message || e));
          }
        }
      } catch (e) {
        log("READBACK_BLOCKED " + String(e.message || e));
      }
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  return (
    <main>
      <h1>QIK-VRT · Mini-Internet Terminal</h1>
      <section>
        <h2>Runtime-Readback</h2>
        <p data-testid="runtime">{runtime ? `seq=${runtime.seq} server_utc=${runtime.server_utc} activity=${runtime.activity}` : "warte auf Readback"}</p>
      </section>
      <section>
        <h2>Aktive Client-Version</h2>
        <p data-testid="release">{release ? `${release.manifest.version} · ${release.payload.feature} · sha256=${release.digest}` : "keine verifizierte Version"}</p>
      </section>
      <section>
        <h2>Journal</h2>
        <ol data-testid="journal">{journal.map((l) => <li key={l}>{l}</li>)}</ol>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
