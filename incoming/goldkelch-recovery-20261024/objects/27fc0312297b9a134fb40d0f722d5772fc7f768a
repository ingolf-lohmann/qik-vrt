<!-- QIKVRT-DE-EN-DOC-HEADER
Deutsch: Dieses Dokument ist Teil des QIK-VRT-Repositories und ist zweisprachig anschlussfähig zu führen. Maßgeblich sind Urheberschaft, Lizenz, Traceability, Requirements, Tests und Nichtregression.
English: This document is part of the QIK-VRT repository and must remain bilingual-accessible. Authorship, license, traceability, requirements, tests, and non-regression are mandatory.
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
Software license / Software-Lizenz: Apache-2.0 unless otherwise stated.
Documentation license / Dokumentationslizenz: CC BY-NC-ND 4.0 unless otherwise stated.
-->

---
QIKVRT-Artifact: license-header
Version: 2.13.4
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated.
Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; no final pass without evidence.
---

# GitHub Seed Discovery

## Zweck

Der initiale Seed für die Auffindbarkeit von QIK-VRT Repositories im Internet ist das GitHub Repository `Goldkelch/qik-vrt`.

Dieses Dokument formalisiert die zulässige Discovery-Logik: Ein QIK-VRT-Knoten darf ausgehend von genau diesem single initial seed autorisierte QIK-VRT-Manifeste lesen, daraus peer manifests ableiten, Repository GUIDs prüfen, autorisierte TCP/IP Endpunkte oder lokale Policy-Endpunkte berücksichtigen und den erreichbaren QIK-VRT-Repository-Graphen traversieren.

## Grenze

Der Beweis gilt nicht als Behauptung einer magischen Internet-Auffindbarkeit ohne Startinformation. Der Startpunkt ist ausdrücklich der Seed `https://github.com/Goldkelch/qik-vrt`.

Der Seed ist der einzige initial benötigte externe Dienst. Danach darf die Repository-Discovery ohne zusätzliche fremde Registry-, Suchmaschinen-, Tracker-, Telemetrie- oder Plattformdienste auskommen, sofern alle QIK-VRT-Peers ihre peer manifest Einträge über den Seed-Graphen veröffentlichen.

## Formales Modell

Die Discovery wird als gerichteter Graph modelliert:

`G = (V, E)`

- `V` = QIK-VRT Repository-Knoten mit repository GUID.
- `E` = autorisierte Manifest-Verweise von einem Repository auf ein anderes.
- `S` = Seed-Knoten `Goldkelch/qik-vrt`.
- Ein Repository ist auffindbar genau dann, wenn es von `S` aus über autorisierte Manifest-Kanten erreichbar ist.

Damit gilt:

`DISCOVERABLE(repo) <=> REACHABLE_FROM_SEED(S, repo)`

## Beweisziel

Der Beweis lautet nicht: jedes beliebige Repository im Internet wird ohne Hinweise gefunden.

Der Beweis lautet:

Wenn jedes QIK-VRT Repository seine Zugehörigkeit durch repository GUID, peer manifest und autorisierte Kante im Seed-erreichbaren Graphen veröffentlicht, dann können alle QIK-VRT Repositories ausgehend von `Goldkelch/qik-vrt` autonom auffindbar gemacht werden, ohne weitere externe Dienste in Anspruch zu nehmen.

## Betriebsregeln

- Goldkelch/qik-vrt ist der single initial seed.
- Jeder Knoten braucht eine repository GUID.
- Jeder Knoten braucht ein peer manifest.
- Jeder Knoten muss seine autorisierten Peers deklarieren.
- Jeder Peer muss Sanity-Selftests requestbar machen.
- Jeder Peer muss watchdog keepalive unterstützen.
- Jeder Peer muss Audit-Ledger führen.
- Netzwerkbetrieb bleibt persistent operation.
- No service except seed.
- No global address scanning.
- No unauthorized probing.
- No self propagation.
- No surveillance instrument.
- No remote mutation without authorization.

## Runtime-Sanity

Zur Laufzeit müssen Knoten regelmäßig prüfen:

1. Ist die lokale repository GUID vorhanden?
2. Ist der Seed `Goldkelch/qik-vrt` konfiguriert?
3. Ist das seed manifest autorisiert?
4. Sind peer manifests formal gültig?
5. Sind alle bekannten Peers über den Seed-Graphen erreichbar?
6. Sind Sanity-Selftests peer-requestable?
7. Sind Watchdog-Heartbeats aktuell?
8. Sind Audit-Spuren append-only vorhanden?
9. Liegt kein globaler Scan und kein unautorisiertes Probing vor?

## Final-Pass-Regel

Kein Final-Pass ohne GitHub Seed Discovery Gates.

`GITHUB_SEED_DISCOVERY_OK` ist nur zulässig, wenn Seed, Manifest, GUID, Reachability, Watchdog, Peer-Sanity, Audit und Boundary-Gates PASS sind.

## Machine-readable phrase anchors

graph reachability
no global address scanning
peer-requestable sanity
no service except seed


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
