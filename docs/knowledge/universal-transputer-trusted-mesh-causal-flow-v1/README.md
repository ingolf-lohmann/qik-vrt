# Universal Transputer – Trusted Mesh – Causal Information Flow

> **Erkenntnisknoten V1 · redaktioneller, quellengebundener Forschungskandidat · 09.11.2026**
>
> Autor und verantwortlicher Urheber der referenzierten Arbeiten: Ingolf Lohmann. Dieser Knoten ist eine additive redaktionelle Synthese, keine Änderung an Originalen, keine neue unabhängige Fachbegutachtung und keine produktive DoD-Erklärung.

## 1. Leitidee

Das universale Terminal nimmt Informationen auf, zeigt sie an und ermöglicht ihre Prüfung. Der universale Transputer steht als **Architekturthese** für die Verarbeitung und Rückkopplung über Knoten hinweg. Das Trusted Mesh Repository stellt versionierte Identitäten, Ereignisse, Herkunft, Widerspruch und verifizierbare Zustandsübergänge bereit. **Bidirektionaler Informationsfluss** meint im technischen Layer Hin- und Rückweg einschließlich Empfang, Prüfung und Bestätigung. Eine physikalische Übertragung in die Vergangenheit folgt daraus **nicht**.

Der zugrunde liegende Erkenntnisgang ist ein Round Trip:

**Originalquelle → Unterscheidung → Hypothese/Behauptung → Modell → überprüfbare Relation → Gegentest → evidenzgebundene Revision → persistierte Fassung.**

Das Repository soll die Erkenntnis tragen, nicht den Erkenntnisprozess durch bloße Statusverwaltung ersetzen.

## 2. Getrennte Erkenntnisebenen

| Gegenstand | Klasse | Tragfähige Aussage | Nicht gedeckt |
|---|---|---|---|
| Universaler Transputer | Autorenthese / Architektur | Schnittstelle und Verarbeitung werden in Beziehung gesetzt. [UT] | Alle Naturvorgänge seien Turing-universell oder formal gleich einem Rechner. |
| Medienagnostische Bidirektionalität | Engineering-Hypothese | Versionierte Payloads und Rückmeldungen sind als Protokoll modellierbar. [BI, MESH] | Ein physikalischer Rückwärts-Zeitkanal. |
| Kausalität ist Relation, nicht Sequenz | These mit engerem formalen Modell | Die VRTCore-Syntax unterscheidet bloße Reihenfolge und eine explizit belegte Brückenrelation. [RC, RCM] | Ein empirischer Nachweis realer Kausalmechanismen oder Retrokausalität. |
| Lichtkegel | source-bound klassische Physik | Lorentzsche Geometrie legt ein klassisches Modell kausaler Trennungen fest. [QCE] | Ein daraus bereits bewiesener QCE-Grenzübergang. |
| Trusted Mesh | Engineering-Vertrag | Signierte Events, Hashes, Replay und unabhängige Übernahmebedingungen sind technisch spezifiziert. [MESH, OPS] | Dass alle Nodes produktiv verbunden und EAP-bestätigt seien. |
| Evidenzgeschlossenes Wachstum | archivierter Modellbezug | Bereits belegte Ableitungspfade bleiben im angegebenen additiven Modell nachvollziehbar. [UT] | Automatische Wahrheit aller späteren Schlussfolgerungen. |

## 3. Drei nicht zusammenlegbare Driftschutz-Schichten

**D1 — Identität:** Wer hat welche Originalbytes, Version und Quelle geliefert? Identifikationsfehler dürfen nicht durch Plausibilität geheilt werden.

**D2 — Erkenntnisstatus:** Ist die Aussage ein Originalzitat, eine Hypothese, ein formaler Satz im deklarierten Modell, eine Beobachtung, eine Deutung oder ein offener Widerspruch? Neue Evidenz darf eine Bewertung ändern, aber nicht den historischen Claim umetikettieren.

**D3 — Wirkung:** Ist die Information nur gesendet, empfangen, lokal validiert, zugelassen, ausgeführt oder unabhängig zurückgelesen? Transport-ACK, Git-Commit, CI-Erfolg und `EFFECT_ACK_DONE` bezeichnen **verschiedene** Zustände.

**Kerninvariante:** Eine höhere Ebene darf keine fehlende Evidenz der darunterliegenden Ebene synthetisch erzeugen. Ein Widerspruch eines Knotens bleibt als eigenständiges, zuordenbares Ereignis erhalten.

## 4. Geometrie und Bildsprache als getrennte Analogien

Für ein **nicht entartetes** Dreieck mit Ecken A, B, C gilt in baryzentrischen Koordinaten

`P = αA + βB + γC,     α + β + γ = 1.`

Ein Punkt liegt im abgeschlossenen Dreieck genau dann, wenn `α, β, γ ≥ 0`. Als Denkfigur können die drei Gewichte für **Quelle, Evidenz und Geltungsbereich** stehen; das beweist keine Wahrheit einer Aussage. Ein physikalischer Lichtkegel ist dagegen ein Modell kausaler Signalgrenzen und **kein** äquivalentes Diagramm des dreieckigen Prüfverfahrens.

Die **Pac-Man-Mund-/Morse-Linien-Skizze** beschreibt als Bildsprache Öffnung, Aufnahme, Codierung, Weitergabe und Rückmeldung. **Blaues Licht** illustriert im hochgeladenen Text den langen Weg einer Entdeckung zur Anerkennung. Beide Motive sind in diesem Knoten ausdrücklich nur **Analogien aus dem gelieferten Gesprächsauszug**, keine neu lokalisierte eigenständige Authority-Originalquelle und keine QIK-VRT-Messung.

## 5. Prüffähiger nächster Erkenntnisschritt

**Hypothese H1, verteilte Systeme:** Bei einem identitätsgebundenen Zweiweg-Protokoll lassen sich jede angenommene Nachricht, jedes Gegenargument und jedes Empfangs-/Wirkungsreceipt nach Unterbrechung, Wiederanlauf und Replay rekonstruieren, ohne ihren historischen Rohinhalt zu verändern.

**Minimaler Versuch:** Zwei isolierte Knoten senden originalbytesgebundene Ereignisse und Gegenbelege. Der Empfänger prüft Quelle, Hash, Sequenz und Evidenzklasse, schreibt ein Empfangsreceipt, und der Sender verifiziert dieses auf einem getrennten Lesepfad. Negativfälle: ausgelassene Sequenz, doppelte ID mit geändertem Inhalt, falscher HEAD, veraltetes Receipt, fehlende Zulassung, ungeprüfter Effekt. Zu messen: Lücken, Erkennungsrate, Replay-Konvergenz, Hash-Übereinstimmung und unabhängig gebundene ACKs.

**Wissenschaftliche Grenze:** Ein erfolgreicher Versuch wäre Evidenz für eine verteilte Informationsprotokoll-Eigenschaft unter konkreten Bedingungen. Er wäre **kein** Nachweis physikalischer Retrokausalität, einer Weltformel oder einer produktiven QIK-VRT-Originalhost-Abnahme.

## 6. Quellen und Herkunft

Basis: Authority `ingolf-lohmann/qik-vrt`, Main `37f8e4eb805292a31024a9e6213afc85d3a6a4a2`, TREE `79ef4e99b05e38fab37957cb75547c616b619032`. Die zugehörigen unveränderten Originale sind im maschinenlesbaren Schwesterartefakt `NODE.json` mit Git-Blob-Identitäten und Geltungsbereichen verzeichnet.

Zusätzliche Gesprächssynthese, 09.11.2026: bereitgestellter Text (5556 Originalbytes; SHA-256 `4f6b445688921dfad29d5ef4931ce24012593bfa29dde79d9932257b37446e3a`). Dessen Wortlaut wird nicht als vom Repository unabhängig verifizierte Primärquelle ausgegeben.

Leseschlüssel: [UT] universaler Transputer; [BI] bidirektionaler Medienfluss; [RC/RCM] relationale Kausalität; [QCE] Lichtkegel/QCE; [ROUND/FORM] Round Trip; [MESH/OPS] verteilte Systeme. **Kein Claim- oder Effekt-Status wird durch dieses Dokument erhöht.**
