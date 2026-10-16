/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
(function () {
  "use strict";
  const form = document.getElementById("question-form");
  const question = document.getElementById("question");
  const output = document.getElementById("answer-output");
  const status = document.getElementById("answer-status");
  if (!form || !question || !output || !status) return;
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const value = question.value.trim();
    if (!value || value.length > 2000) {
      status.textContent = "CONTINUE · Bitte eine Frage von 1 bis 2.000 Zeichen eingeben.";
      output.textContent = "Es wurde keine Frage verarbeitet.";
      return;
    }
    if (!window.QIKVRTLocalEngine || typeof window.QIKVRTLocalEngine.answerLocal !== "function") {
      status.textContent = "CONTINUE · Lokale Regelkonsole nicht verfügbar.";
      output.textContent = "Keine Analyse möglich. Es wurde keine Antwort erfunden.";
      return;
    }
    try {
      const analysis = window.QIKVRTLocalEngine.answerLocal(value, null);
      if (typeof analysis !== "string" || !analysis.trim()) throw new Error("EMPTY_LOCAL_ANALYSIS");
      output.textContent = analysis;
      status.textContent = "LOCAL_RULE_ANALYSIS · Strukturierung abgeschlossen; keine allgemeine KI-Antwort, keine externe Quellenprüfung.";
    } catch (_error) {
      status.textContent = "CONTINUE · Analyse nicht abgeschlossen.";
      output.textContent = "Keine belastbare Ausgabe verfügbar. Es wurde keine Antwort erfunden.";
    }
  });
  form.addEventListener("reset", function () {
    output.textContent = "Die lokale QIK-VRT-Analyse startet nach deiner Eingabe.";
    status.textContent = "LOCAL_ONLY · Noch keine Frage bearbeitet.";
  });
})();
