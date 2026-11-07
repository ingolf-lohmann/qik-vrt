<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# PIA-1 — Teilung, Teilnahme und kausaler Informationsaustausch (Kandidatenvertrag)

Status: `CANDIDATE / NONPRODUCTIVE / FAIL_CLOSED` · Owner-Freigabe 07.11.2026 (Europe/Paris).
Authority-Quellenbindung: [Issue #706](https://github.com/ingolf-lohmann/qik-vrt/issues/706).
**Wissenschaftliche Klassifikation:** konzeptionelles, logisch-informatisches Axiom; kein physikalisches Grundgesetz, keine empirische Bestätigung.

> Einheit ermöglicht Unterscheidung. Unterscheidung ermöglicht Information.
> Nachweisbarer Austausch begründet Teilnahme an einem gemeinsamen Informationsprozess.

## Mathematischer Vertrag

Sei `U` die betrachtete Grundmenge und `T: U -> Bool` eine *nachweislich bestimmte*
Teilnahmebedingung. `M = {x in U | T(x) = true}`. Nur für `x in M` ist
`s: M -> {0,1}` definiert. **0 ist ein gültiger Zustand**, nicht Ausschluss.
Ein unbekanntes oder fehlendes `T` ist `UNKNOWN/⊥`, weder `false` noch Bit `0`.
Der Modell-Prädikatbereich Bool und eine reale unvollständige Beobachtung sind zu trennen.
Explizit `T=false` bedeutet ausgeschlossen, ohne Bitzuordnung.

Die beiden Bedeutungen von *teilen* bleiben getrennt: Partitionsbildung und
Informationsmitteilung. Informationskopie und physische Wirkung sind keine Äquivalenzen.

## Konformitätsvertrag

Die reine, nebenwirkungsfreie Referenz `src/qikvrt_participation.py` akzeptiert
`{"participates": true, "bit": 0|1}` nur mit exaktem booleschem Teilnahmefeld und
exaktem Integerbit (keine Python-Subklassen-Aliasierung `0 == False`).
`false` ohne Bit ist `EXCLUDED`; `UNKNOWN`/null/fehlend ohne Bit ist `UNKNOWN`.
Ungebundenes Bit, ungültige Werte und fehlerhafte Typen ergeben `HOLD`.

Die Austauschklassifikation ordnet nur *Claims* ein:
`SENT` impliziert **nicht** `RECEIVED`; `RECEIVED` impliziert **nicht**
`EFFECT_ACK_DONE`. Selbst `sent=true, received=true, effect_ack_done=true`
ergibt **UNVERIFIED_EFFECT_CLAIM**, niemals eine produktive EAP-Freigabe.
Payload-Wiederholung, Duplicate oder Replay begründen kein Recht auf Claim-Erhöhung.
Eigenständiges Ledger-/Digest-/Writer-Fencing ist weiterhin erforderlich und wird
durch diesen kleinen Referenzvalidator nicht vorgetäuscht.

## Akzeptanz und Evidence Boundary

- RED-Commit: reine unittest-Konformitätsfälle mit noch fehlendem Referenzmodul.
- GREEN-Kandidat: reine Implementierung, Vertrag und Registrierung unter `make conformance`.
- Dieser Kandidat hat **keinen** Einfluss auf Native Runtime, Host, DNS, TLS, Manifest
  oder `EFFECT_ACK_DONE`. Produktionsadmission benötigt gesonderte authentifizierte,
  frische und exakte Subject-/Host-Readbacks, unabhängiges Review, vollständige
  Exact-HEAD-CI, Integritätsprüfung und Governance.
- Verknüpfung zu Draft PR #703 (typed claims, TEMDD/EAP) und PR #705 (Host-Identität);
  keine Ableitung eines PASS von dortigen historischen Testläufen.
