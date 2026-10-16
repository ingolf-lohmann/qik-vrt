/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
(function () {
  "use strict";
  const form = document.getElementById("question-form");
  const question = document.getElementById("question");
  const output = document.getElementById("answer-output");
  const status = document.getElementById("answer-status");
  if (!form || !question || !output || !status) return;

  function localFallback(value, reason) {
    if (!window.QIKVRTLocalEngine || typeof window.QIKVRTLocalEngine.answerLocal !== "function") {
      status.textContent = "CONTINUE · Weder Antwortdienst noch lokale Regelkonsole verfügbar.";
      output.textContent = "Keine Antwort verfügbar. Es wurde keine Aussage erfunden.";
      return;
    }
    try {
      const analysis = window.QIKVRTLocalEngine.answerLocal(value, null);
      if (typeof analysis !== "string" || !analysis.trim()) throw new Error("EMPTY_LOCAL_ANALYSIS");
      output.textContent = analysis;
      status.textContent = "LOCAL_RULE_ANALYSIS · " + reason +
        " Nur lokale Prüfstruktur, keine frei recherchierte Antwort.";
    } catch (_error) {
      status.textContent = "CONTINUE · Analyse nicht abgeschlossen.";
      output.textContent = "Keine belastbare Ausgabe verfügbar.";
    }
  }

  function renderEvidence(result) {
    const sources = Array.isArray(result.sources) ? result.sources : [];
    const lines = [String(result.answer || "Keine belastbare Antwort.")];
    if (sources.length) {
      lines.push("", "Quellen (Dokumentbelege, keine unabhängige Bestätigung):");
      for (const source of sources.slice(0, 3)) {
        const url = String(source.url || "");
        if (!/^https:\/\/github\.com\/ingolf-lohmann\/qik-vrt\/blob\/[a-f0-9]{40}\//.test(url) &&
            !/^https:\/\/github\.com\/ingolf-lohmann\/qik-vrt\/blob\/main\//.test(url)) continue;
        lines.push("[" + String(source.id || "") + "] " + String(source.title || "") +
          "\n" + url + "\nSHA-256: " + String(source.sha256 || "") +
          "\nQuellenklasse: " + String(source.evidence_class || "UNKNOWN"));
      }
    }
    lines.push("", "Geltungsgrenze: " + String(result.evidence_boundary || "UNVERIFIED"));
    lines.push("Unabhängig bestätigt: nein · Veröffentlichungseffekt: nein · EFFECT_ACK_DONE: nein");
    output.textContent = lines.join("\n");
    const code = String(result.status || "UNKNOWN");
    status.textContent = code + " · " + (code === "GENERATED_UNVERIFIED"
      ? "KI-Entwurf, nicht unabhängig verifiziert."
      : "Quellenorientierung, keine allgemeine KI-Antwort.");
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const value = question.value.trim();
    if (!value || value.length > 2000) {
      status.textContent = "CONTINUE · Bitte eine Frage von 1 bis 2.000 Zeichen eingeben.";
      output.textContent = "Es wurde keine Frage verarbeitet.";
      return;
    }
    status.textContent = "SOURCE_CHECK_PENDING · Gesicherten Antwortdienst prüfen …";
    output.textContent = "Bitte warten. Keine Aussage wird ohne Quelle als verifiziert ausgegeben.";
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: value }),
        credentials: "same-origin",
        cache: "no-store",
        signal: controller.signal
      });
      if (!response.ok) throw new Error("ANSWER_API_UNAVAILABLE");
      const result = await response.json();
      if (!result || result.schema !== "qikvrt-public-qa/1") throw new Error("INVALID_ANSWER_CONTRACT");
      renderEvidence(result);
    } catch (_error) {
      localFallback(value, "Antwortdienst nicht erreichbar.");
    } finally {
      clearTimeout(timeout);
    }
  });

  form.addEventListener("reset", function () {
    output.textContent = "Die QIK-VRT-Quellenprüfung startet nach deiner Eingabe.";
    status.textContent = "LOCAL_ONLY · Noch keine Frage bearbeitet.";
  });
})();
