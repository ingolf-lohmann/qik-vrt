<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# ACCEPT

## Template-Clone-Acceptance-Test

Dieser Acceptance-Test ist ab jetzt Pflicht für neue Bundles.

## Ziel

Ein Repository, das aus einem GitHub-Template erzeugt und lokal geklont wurde, muss sein GitHub-Ziel automatisch aus `.git/config` erkennen.

## Testfall

Simulierte Template-Instanz:

```text
remote origin = https://github.com/TemplateOwner/TemplateInstance.git
```

Erwartung:

```text
owner = TemplateOwner
repo = TemplateInstance
branch = main
source = .git_config
```

## Akzeptanzkriterien

```text
kein altes Ziel Goldkelch/qik-vrt
TARGET.json wird erzeugt
REPO_OUT.zip wird erzeugt
QALL_TARGET_RESOLVED.json ist in REPO_OUT.zip enthalten
ohne Token blockiert der Lauf erst bei github_token_missing
kein GitHub-Erfolg wird behauptet
```

## Aktuelles Ergebnis

```text
PASS
```

## Grenze

Dieser Test ist ein lokaler Linux-Sandbox-Test mit synthetischem `.git/config`.
Ein realer GitHub-Netzwerk-Clone wird dadurch nicht behauptet.

## Delivery-Acceptance

Delivery-Bundle muss sichtbare Startdateien und sichtbare `LOGS/` enthalten; interne Details liegen in `_internal/`.

## MinRoot-Acceptance

Delivery ist nur gültig, wenn im Root genau drei Skriptdateien liegen.

## Cross-Fix Acceptance

Neue Bundles sind nur akzeptabel, wenn Linux-Fixes nicht isoliert bleiben.

## License Acceptance Gate

Keine Repository-Persistenz ohne konkreten Acceptance-Record für die jeweilige Schreibhandlung.

## Strict Acceptance Acceptance-Test

Vage Eingaben wie `JA` oder `YES` müssen blockieren. Nur die exakte Phrase darf einen Acceptance-Record erzeugen.

## Strict Counterparty Type Acceptance-Test

Mehrdeutige Typen wie `Firma`, `KI vielleicht`, leere Angaben oder freie Texte blockieren.

## OTHER Counterparty Acceptance-Test

`OTHER` ohne Beschreibung muss blockieren; `OTHER` mit Beschreibung muss die Beschreibung im Acceptance-Record persistieren.

## Reflexive Finding Acceptance

Ein neues Bundle ist nach Nutzer-Finding nur akzeptabel, wenn das Finding als Fehlerklasse persistiert und durch alle relevanten Schichten korrigiert wurde.

## Bilingual UI Acceptance

Nutzergerichtete Texte müssen Deutsch/Englisch sein.

User-facing text must be German/English.

## Bilingual Inheritance Acceptance

Abgeleitete Artefakte sind nur akzeptabel, wenn die DE/EN-UI-/Nutzerinformation erhalten bleibt.

Derived artifacts are acceptable only if DE/EN UI/user information is preserved.

## Official License Refresh Acceptance

Repository-Persistenz ist nur akzeptabel, wenn offizielle Lizenzdateien aktualisiert und alle Dateien lizenzseitig angereichert/manifestiert wurden.

Repository persistence is acceptable only if official license files are refreshed and all files are license-enriched/manifest-covered.

## GITHUB_DOMAIN_FACTORY

Deutsch: Die GitHub-Domain-Factory ist in die jeweilige ACCEPT.md-Schicht integriert und erbt Akzeptanz-, Gegenstellen-, Lizenz-, Zweisprachigkeits- und Vererbungsregeln.

English: The GitHub Domain Factory is integrated into the respective ACCEPT.md layer and inherits acceptance, counterparty, license, bilingual, and inheritance rules.

## OFFICIAL_LICENSE_PLACEHOLDER_AND_HEADER_FIX

Deutsch: Offizielle Lizenztexte und Datei-Header/-Notices müssen vor Delivery materialisiert sein. Platzhalter oder bloße spätere Fetch-Versprechen sind BLOCK.

English: Official license texts and file headers/notices must be materialized before delivery. Placeholders or mere later-fetch promises are BLOCK.

## RECURSIVE_LICENSE_AND_UMLAUT_LAYER

Deutsch: Sourcecode bleibt ohne deutsche Umlaute. Nicht-Software-Dokumente verwenden deutsche Umlaute korrekt. Lizenz- und Urheberrechtsinformationen werden rekursiv in allen Repository-Dateien ergänzt oder manifestiert.

English: Source code remains free of German umlauts. Non-software documents use German umlauts correctly. License and copyright information is recursively added to or manifested for all repository files.
