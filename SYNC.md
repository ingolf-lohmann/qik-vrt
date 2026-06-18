<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# SYNC

## Synchron-Testschichten

Dieses Bundle enthält jetzt explizite Reproduktionspfade für:

```text
Windows
Linux-Sandbox / POSIX
macOS / POSIX
GitHub-Persistenzpfad
```

## Windows

```text
START.bat
RUN.ps1
REPO.zip enthält START.bat und PATCH.ps1
```

Status: implementiert, in dieser Linux-Sandbox nicht real als Windows-Runtime ausgeführt.

## Linux-Sandbox / POSIX

```text
RUN.sh
LINUX.sh
```

Status: implementiert und in dieser Sandbox ausführbar.

## macOS

```text
START.command
RUN.sh
```

Status: implementiert, hier nicht auf realem macOS ausgeführt.

## GitHub

Der GitHub-Pfad persistiert Mapping-/Learning-/Policy-Artefakte nur bei echter API-Ausführung.

Kein GitHub-Erfolg ohne echten API-Nachweis.


## Vollautomatischer Token-only-GitHub-Pfad

```text
Zielrepository: Goldkelch/qik-vrt
Branch: main
Einzige Eingabe: GitHub token
```

Windows:

```text
START.bat
```

Linux:

```text
./RUN.sh
```

macOS:

```text
START.command
```

## Template-Adaptivität

Nach Nutzung als GitHub-Template und lokalem Clone soll nur noch der Token eingegeben werden; Ziel wird aus `.git/config` erkannt.

## Acceptance Gate

Template-clone target autodetection must pass before delivery of new bundles.

## Delivery-Struktur

Start und Ergebnisort sind auf gleicher sichtbarer Ebene: Root + `LOGS/`.

## MinRoot

Synchronstart erfolgt über genau drei sichtbare Plattformdateien.

## Lizenz-/INI-Struktur

Root enthält README und INI als notwendige Nutzungs- und Lizenzoberfläche.

## Cross-Platform-Fix-Spiegelung

Windows, Linux und macOS müssen dieselbe relevante Fixlogik tragen.

## License Acceptance Preservation

Acceptance Gate und Acceptance Record werden in GitHub-/Template-/Clone-Persistenzpfade einbezogen.

## Strict Acceptance Sync

Strict-Acceptance-Gate wird bei Clone, Download, Nutzung und Merge erhalten.

## Strict Counterparty Type Sync

Strikte Gegenstellentyp-Prüfung wird bei Clone, Download, Nutzung und Merge erhalten.

## OTHER Counterparty Sync

OTHER-Beschreibungspflicht wird bei Clone, Download, Nutzung, Merge und Persistenz erhalten.

## Reflexive Finding Sync

Reflexive Finding Workflow muss bei Clone, Download, Nutzung, Merge und Persistenz erhalten bleiben.

## Bilingual UI Sync

Zweisprachige UI-/Nutzerinformation muss bei Clone, Download, Nutzung, Merge und Persistenz erhalten bleiben.

Bilingual UI/user information must be preserved during clone, download, use, merge and persistence.

## Bilingual Inheritance Sync

Die zweisprachige Eigenschaft wird bei Clone, Download, Nutzung, Merge und Persistenz synchron gehalten.

The bilingual property is kept in sync during clone, download, use, merge and persistence.

## Official License Refresh Sync

Lizenz-Refresh und Datei-Enrichment werden bei GitHub, Clone, Merge und Folge-Bundles erhalten.

License refresh and file enrichment are preserved across GitHub, clone, merge and follow-up bundles.

## GITHUB_DOMAIN_FACTORY

Deutsch: Die GitHub-Domain-Factory ist in die jeweilige SYNC.md-Schicht integriert und erbt Akzeptanz-, Gegenstellen-, Lizenz-, Zweisprachigkeits- und Vererbungsregeln.

English: The GitHub Domain Factory is integrated into the respective SYNC.md layer and inherits acceptance, counterparty, license, bilingual, and inheritance rules.

## OFFICIAL_LICENSE_PLACEHOLDER_AND_HEADER_FIX

Deutsch: Offizielle Lizenztexte und Datei-Header/-Notices müssen vor Delivery materialisiert sein. Platzhalter oder bloße spätere Fetch-Versprechen sind BLOCK.

English: Official license texts and file headers/notices must be materialized before delivery. Placeholders or mere later-fetch promises are BLOCK.

## RECURSIVE_LICENSE_AND_UMLAUT_LAYER

Deutsch: Sourcecode bleibt ohne deutsche Umlaute. Nicht-Software-Dokumente verwenden deutsche Umlaute korrekt. Lizenz- und Urheberrechtsinformationen werden rekursiv in allen Repository-Dateien ergänzt oder manifestiert.

English: Source code remains free of German umlauts. Non-software documents use German umlauts correctly. License and copyright information is recursively added to or manifested for all repository files.
