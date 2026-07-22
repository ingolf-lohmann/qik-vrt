<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Zweiphasige Automation der offiziellen QIK-VRT-Statuserklärung

## Gegenwärtiger Zustand

Die Automation ist im eingecheckten Zustand **inert**. Der Marker
`release/status-clarification-request.json` enthält `action: inactive`,
`confirm: NOT_AUTHORIZED`, ausschließlich Null-Identitäten und keine DOI. Ein
normaler Push auf `main` reserviert nichts, erzeugt keinen Tag und publiziert
nichts. Eine Wirkung benötigt jeweils einen separat geprüften, nicht forcierten
Push eines Marker-only-Commits auf den unten festgelegten Branch.

Die Automation erzeugt ausschließlich einen neuen, eigenständigen
Statusbericht. Die vorhandenen Zenodo-Records `21498772`, `21498773`,
`21498774` und `21488115` sind unveränderliche Schutzanker. Der Client besitzt
keinen `newversion`-Pfad und blockiert jede Mutation dieser IDs.

## Fester Vertrag

| Element | Wert |
|---|---|
| Autoritätsrepository | `Goldkelch/qik-vrt` |
| Spiegelrepository | `ingolf-lohmann/qik-vrt` |
| Reserve-Branch | `automation/status-clarification-reserve-20260722` |
| Finalize-Branch | `automation/status-clarification-finalize-20260722` |
| Zustandsbranch | `qikvrt/status-report-state` |
| Tag | `v2026.07.22-status-clarification-1.0.0` |
| Marker | `release/status-clarification-request.json` |
| Schema | `policy/qikvrt-status-report-release-request.schema.json` |
| Client | `tools/qikvrt_status_zenodo.py` |

Der Marker bindet die beiden repository-spezifischen `main`-Commits, ihren
identischen Git-Tree, den Client sowie sämtliche Manifestbytes per SHA-256.
Der aktive Commit darf gegenüber seinem unmittelbaren `main`-Quellparent
ausschließlich den Marker ändern. Ein Merge- oder Mehr-Eltern-Commit ist keine
Autorisierung. Der annotierte Tag zeigt immer auf den jeweiligen Quellparent,
nie auf den Marker-Commit.

## Drei Manifestebenen

Die DOI wird nicht vorweggenommen. Deshalb trennt Schema 2 drei Dateien:

1. `release/status-clarification-zenodo-reservation-manifest.json` bindet
   Metadaten, Report-ID, das Template-Manifest und genau eine erlaubte
   DOI-Einbettungsstelle.
2. `release/status-clarification-zenodo-template.json` bindet die endgültige
   Dateiliste vor der Reservierung. Genau eine autorisierte Datei enthält
   einmal `10.5281/zenodo.__RESERVED__`.
3. `release/status-clarification-zenodo.json` ist das Finalmanifest. Gegenüber
   dem Template ist ausschließlich die bytegenaue Ersetzung dieses einen
   Sentinels durch die von Zenodo reservierte DOI zulässig.

Im Reserve-Marker sind Client-, Reservierungsmanifest- und Templatehash
gesetzt; `final_manifest_sha256`, Reservierungsevidenz und DOI bleiben Null.
Im Finalize-Marker sind alle drei Manifesthashes, der Hash der öffentlichen
Reservierungsevidenz und die reservierte DOI gesetzt.

Der aktuelle Clientvertrag lautet:

```text
reserve
  --reservation-manifest release/status-clarification-zenodo-reservation-manifest.json
  --final-template-manifest release/status-clarification-zenodo-template.json
  --reservation OUT
  --repository-root .

finalize
  --reservation-manifest release/status-clarification-zenodo-reservation-manifest.json
  --final-template-manifest release/status-clarification-zenodo-template.json
  --final-manifest release/status-clarification-zenodo.json
  --reservation IN
  --result OUT
  --repository-root .
```

Der Zenodo-Token ist ausschließlich als `ZENODO_ACCESS_TOKEN` zulässig. Er
darf weder als Argument noch in Evidenz, Artifact oder Zustandsbranch
erscheinen.

## Phase 1: Reservierung

Nur `Goldkelch/qik-vrt` kann die Reservierung ausführen.

1. Beide `main`-Commits und der gemeinsame Tree werden endgültig bestimmt.
2. Client, Reservierungsmanifest und Template werden vollständig geprüft und
   gehasht. Das Finalmanifest existiert noch nicht beziehungsweise ist nicht
   autorisiert.
3. Vom exakten Goldkelch-`main` wird der Reserve-Branch erzeugt.
4. Ein zweiter Commit ändert ausschließlich den Marker zu `action: reserve`,
   bindet beide Commits, Tree und Hashes und verwendet
   `RESERVE_ONE_NEW_STATUS_REPORT_DRAFT_NO_PUBLISH`.
5. Erst der nicht forcierte Push dieses Zweitcommits startet die Wirkung.

Der Workflow prüft Branchkopf, Push-Vorher/Nachher, beide öffentlichen
`main`-Refs, beide Git-Trees, Parent, Marker-Diff, Schema, kanonischen
Autorisierungshash, Client und Template. Danach läuft das vollständige
`make test` des Quellparents. Erst unmittelbar vor der Wirkung werden die
entscheidenden Bindungen erneut geprüft.

Vor jedem Zenodo-POST persistiert der Workflow zunächst einen deterministischen
One-shot-Intent unter
`release-state/status-clarification/zenodo-reservation-attempt.json`. Erst
der Lauf, der diesen Intent selbst erfolgreich angelegt hat, darf einen neuen
leeren Entwurf erzeugen. Liegt der Intent bei einem späteren Lauf bereits vor,
aber noch keine Reservierungsevidenz, wird kein weiterer POST gesendet: Der
mehrdeutige Zwischenzustand muss anhand der Zenodo-Entwürfe ausdrücklich
reconciliiert werden. Damit wird nach einem Antwortverlust oder Abbruch kein
zweiter Entwurf automatisch erzeugt.

Der Entwurf wird nicht veröffentlicht. Die token-authentisierte
Reservierungsevidenz wird unter
`release-state/status-clarification/zenodo-reservation.json` im dedizierten
Zustandsbranch und zusätzlich als SHA-gepinntes Actions-Artifact gespeichert.

## DOI-Einbettung zwischen den Phasen

Aus der Reservierung werden DOI und Evidenzhash gelesen. Die eine autorisierte
Template-Datei wird durch exakte Sentinel-Ersetzung erzeugt; anschließend wird
das Finalmanifest aus den tatsächlichen finalen Bytes erstellt. Diese
Änderungen gehören in einen regulär geprüften neuen `main`-Quellstand beider
Repositories. Sie gehören nicht in einen wirkenden Marker-Commit.

Damit können Reserve- und Finalize-Quellcommits verschieden sein. Jeder
Finalize-Tag bindet den dann aktuellen Parent-Commit und den identischen
finalen Tree beider Repositories.

## Phase 2: Tag und Publikation

1. Von jedem exakten finalen `main`-Commit wird separat der Finalize-Branch
   erzeugt.
2. Der zweite Commit ändert in jedem Repository ausschließlich denselben
   Marker zu `action: finalize` und bindet die repo-spezifischen Commits, den
   gemeinsamen Tree, alle Manifesthashes, Reservierungsevidenzhash und DOI.
3. Der nicht forcierte Push läuft in beiden Repositories.

Jedes Repository prüft die Reservierung, die exakte Template-zu-Final-Differenz
und beide weiterhin unveränderten `main`-Refs. Danach erstellt oder verifiziert
es mit seinem eigenen kurzlebigen `GITHUB_TOKEN` einen annotierten Tag auf
seinem jeweiligen Quellparent. Die Automation erstellt kein
GitHub-Release-Objekt.

Nur der Goldkelch-Lauf verwendet `ZENODO_ACCESS_TOKEN`. Unmittelbar vor der
Zenodo-Wirkung prüft er den eigenen und den Spiegel-Tag vollständig, darunter
Tagger, Nachricht, Zielcommit und Zieltree, und wartet begrenzt auf den
Spiegel-Tag. Erst danach lädt der Client ausschließlich die final gebundenen
Dateien hoch, liest sie zur Hashprüfung zurück und publiziert den frisch
reservierten Report. Der Spiegel-Lauf besitzt keine Zenodo-Wirkung.

## Fail-closed-Grenzen

Die Wirkung bleibt blockiert bei unter anderem:

- falschem Repository, Event, Branch oder Marker-`action`;
- Force-Push, Merge-Marker oder mehr als einer geänderten Datei;
- von `main` abweichendem Parent oder verändertem gemeinsamen Tree;
- abweichendem Schema-, Client-, Manifest- oder Evidenzhash;
- einer zweiten oder verschobenen DOI-Einbettungsstelle;
- Metadaten-, Dateilisten- oder Byteänderungen neben der DOI-Ersetzung;
- einem vorhandenen divergenten oder leichtgewichtigen Tag;
- einer fehlenden Spiegel-Tag-Barriere oder einem inzwischen verschobenen
  `main`-Ref;
- einem vorhandenen One-shot-Intent ohne eindeutig persistierte
  Reservierungsevidenz;
- einer geschützten Alt-ID, einem `newversion`-Pfad oder einer Token-Spur;
- einem fehlgeschlagenen Quelltest oder einer veränderten Autorisierungsbranch.

Ein inaktiver Marker ist kein vorläufiges PASS, sondern ausdrücklich keine
Autorisierung.
