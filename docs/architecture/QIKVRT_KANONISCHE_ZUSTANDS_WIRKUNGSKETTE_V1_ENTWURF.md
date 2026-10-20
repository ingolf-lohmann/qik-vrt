# QIK-VRT: Kanonische Zustands- und Wirkungskette – Spezifikationsentwurf V1

Status: ENTWURF · Subjektbasis: `main` `a38455c739f7f475b2a93447de1db4ea87e4200c`
Herkunft: Abschnitt 1 ist OWNER_ASSERTED (Ingolf Lohmann, 2026-10-21). Abschnitte 2 bis 4 sind ein maschineller Beitrag des Claude-Mirror-Knotens und noch nicht angenommen.
Dieses Dokument belegt keine Implementierung und keine erfolgte Ausführung.

## 1. Architektur (OWNER_ASSERTED)

| Stufe | Komponente | Ergebnis |
|---|---|---|
| 1 Formaler Kern | Lean Kernel | beweisbarer lokaler Endzustand |
| 2 Ausführung | TEMDD | evidenzgebundener Zustandsübergang |
| 3 Universelle Grenze | Universal Terminal / Transputer | Serialisierung → kanonischer Carrier → Deserialisierung |
| 4 Wirkungsbeweis | TEST → OBSERVE → READBACK → ACCEPT → EFFECT_ACK_DONE | nachgewiesene, bestätigte Wirkung |

Beweislasten:
- TEST: Die spezifizierte Funktion wird geprüft.
- OBSERVE: Das tatsächliche Verhalten wird beobachtet.
- READBACK: Der resultierende Zustand wird unabhängig zurückgelesen.
- ACCEPT: Die Evidenz wird anhand definierter Akzeptanzkriterien angenommen.
- EFFECT_ACK_DONE: terminaler Status der gesamten Kette, nicht bloß eine Empfangsbestätigung.

Ein formaler Beweis des lokalen Zustands garantiert allein weder die korrekte Ausführung noch die Wirkung an einer externen Systemgrenze.

**Invariante I0:** Kein EFFECT_ACK_DONE ohne erfolgreiches ACCEPT; kein ACCEPT ohne auswertbare Evidenz aus TEST, OBSERVE und READBACK.

## 2. Zu spezifizierende Lücken (Mirror-Beitrag)

### L1 ACCEPT-Instanz
- **I1:** Die akzeptierende Identität ist weder der Erzeuger der Evidenz noch der Carrier. `accept.identity ∉ {evidence.producer, carrier.identity}`.
- ACCEPT ist eine Rolle mit benannter Identität, kein Schritt, den der Erzeuger selbst ausführt.
- Ein ACCEPT-Record nennt: Akzeptanzkriterien (Version, Hash), die bewerteten Evidenz-Hashes, die Identität und den Zeitpunkt (UTC).

### L2 Fehlerpfade als Zustände
Jede Stufe endet in genau einem der folgenden Zustände:

| Zustand | Bedeutung | Nachfolger |
|---|---|---|
| PASS | Beweislast der Stufe erfüllt | nächste Stufe |
| HOLD | Voraussetzung fehlt, benannter Träger | dieselbe Stufe nach Behebung |
| NACK | Evidenz widerlegt die Stufe | SUCCESSOR mit `corrects` |
| CONTINUE | Teilevidenz, Kette offen | dieselbe oder eine frühere Stufe |

- **I2:** Ein Carrier-Abbruch (z. B. ein Push, der mit HTTP 403 abgewiesen wird) ist HOLD auf Stufe 3 mit benanntem Träger. Er ist weder NACK beim Empfänger noch ein Eingang.
- **I3:** HOLD und CONTINUE sind nie NOOP. Offene Arbeit wird nie als „unverändert“ gemeldet.

### L3 Verfeinerung Lean-Kern → TEMDD
- Der Lean-Beweis gilt für das Modell. Die Übereinstimmung von `src/qikvrt_temdd_event_ledger.py` mit dem Modell ist eine eigene Beweislast (Stufe 1½).
- Mindestform: eine Abbildungstabelle Modellzustand ↔ Ledger-Ereignisart (OBSERVE, CLASSIFY, ACTION, EFFECT, READBACK, SUCCESSOR, HOLD) und Übergangstests, die jede im Modell erlaubte Kante ausführen und jede verbotene Kante als HOLD abweisen.
- **I4:** Ohne nachgewiesene Verfeinerung darf ein Lean-Beweis nicht als Evidenz für Stufe 2 oder höher zitiert werden.

### L4 Unabhängigkeit des READBACK
READBACK gilt nur dann als unabhängig, wenn alle drei Bedingungen erfüllt sind:
1. ein anderer Prozess als der Schreiber,
2. eine andere Identität als der Schreiber,
3. ein Lesepfad über die Zielgrenze (z. B. Authority-git, öffentliche GET-API), nicht über den lokalen Speicher des Schreibers.
- **I5:** Ein Readback in derselben Sitzung über denselben lokalen Speicher ist `READBACK_LOCAL` und erfüllt Stufe 4 nicht.

### L5 Bindung Carrier ↔ Evidenz
- Jeder Carrier trägt: `sha256` der übertragenen Bytes, Basis-Commit, Ziel-Ref, Absender- und Empfängeridentität.
- Die Deserialisierung prüft vor jeder Anwendung `sha256` und Basis-Commit und wendet nur ff-only an. Bei Abweichung: HOLD.
- **I6:** Die ACCEPT-Evidenz referenziert exakt den Carrier-Hash, der deserialisiert wurde. Evidenz ohne diese Bindung ist nicht akzeptierbar.

## 3. Prüfbarkeit
Jede Invariante I0 bis I6 braucht mindestens einen Test, der ihre Verletzung als HOLD bzw. NACK erkennt. Erst dann ist sie durchgesetzt; vorher ist sie nur spezifiziert.

## 4. Anwendung auf PR #555 (Claude-Mirror, 2026-10-20)

| Stufe | Zustand | Evidenz |
|---|---|---|
| 1 Lean | nicht geprüft | – |
| 2 TEMDD | PASS (lokal) | EFFECT `ledger_digest 90a677a48c3742754502ac0c235d1b2dc5172c2104e5a61b2e3f29a0cfc35608` |
| 3 Serialisierung | PASS | git-Bundle |
| 3 Carrier | HOLD (I2) | Push mit HTTP 403 abgewiesen; Träger: Prinzipal |
| 4 TEST | PASS | Integrität PASS; personal-retrieval 9/9 Unit-Tests, 9/9 UI-Tests |
| 4 OBSERVE | HOLD | Modell nicht gestartet (kein Host, keine Modelldateien) |
| 4 READBACK | READBACK_LOCAL (I5) | `/api/temdd/events`, gleiche Sitzung |
| 4 ACCEPT | offen | – |
| EFFECT_ACK_DONE | ausgeschlossen (I0) | – |

## 5. Carrier-Evidenz für den Claude-Mirror-Bundle

- Bundle SHA-256: `d0b1c993e9c6edfeddd227310c2a7d9662eace2b2bfc97ede4e40978fdc466b0`
- Basis-Commit: `a38455c739f7f475b2a93447de1db4ea87e4200c`
- Erwarteter HEAD: `dae356e4df1b3892e58768047b1a5edd1e68c52e`
- Ziel-Ref: `communication/claude/mirror-20261020T1827Z`
- Lokale `git bundle list-heads`-Prüfung ergab den erwarteten HEAD.
- `git bundle verify` konnte ohne Repository mit Basis-Commit nicht abgeschlossen werden; ein isolierter Clone meldete den fehlenden Basis-Commit als Voraussetzung.
- Diese Dokumentation speichert die Identität und den Prüfstatus des Bundles, nicht die Binärbytes selbst.
- Kein Push, unabhängiger Readback, ACCEPT oder EFFECT_ACK_DONE wird hiermit behauptet.
