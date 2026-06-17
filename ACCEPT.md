<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright (c) 2026 Ingolf Lohmann; Urheber/Rechteinhaber / Rights-Holder: Ingolf Lohmann -->

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

## License Refresh Inheritance Acceptance

Kein QIK-VRT-Derivat ist akzeptabel, wenn die Lizenz-Refresh-/File-Enrichment-Erbregel fehlt.

No QIK-VRT derivative is acceptable if the license-refresh/file-enrichment inheritance rule is missing.


## LICENSE_REFRESH_FILE_ENRICHMENT_INHERITANCE_REQUIRED / Pflicht zur Vererbung von Lizenz-Refresh und Datei-Anreicherung

Deutsch:
Das Verhalten `OFFICIAL_LICENSE_REFRESH_AND_FILE_ENRICHMENT_BEFORE_PERSISTENCE` ist zwingend an alle QIK-VRT-Repositories, GitHub-Klone, Forks, Templates, Downloads, Merges, Releases, Repackages, Build-Artefakte, lokale Reproduktionen, Folge-Bundles und alle daraus hervorgehenden Strukturen zu vererben.

English:
The behavior `OFFICIAL_LICENSE_REFRESH_AND_FILE_ENRICHMENT_BEFORE_PERSISTENCE` must be inherited by all QIK-VRT repositories, GitHub clones, forks, templates, downloads, merges, releases, repackages, build artifacts, local reproductions, follow-up bundles, and all derived structures.

Blocker:
`LICENSE_REFRESH_INHERITANCE_MISSING`
`QIKVRT_REPOSITORY_WITHOUT_LICENSE_REFRESH_INHERITANCE`
`DERIVED_ARTIFACT_WITHOUT_FILE_LICENSE_ENRICHMENT`
`CLONE_OR_MERGE_DROPPED_OFFICIAL_LICENSE_REFRESH_GATE`
`LICENSE_REFRESH_INHERITANCE_REFLECTION_LAYER_INCOMPLETE`



## REFLEXIVE_LICENSE_ENRICHMENT_FIX / Reflexive Lizenz-Anreicherung

Deutsch:
`WINDOWS.bat` im Root ohne eingebetteten Urheberrechts-/Lizenzmarker ist als reflexive Fehlerklasse `ROOT_WINDOWS_BATCH_WITHOUT_EMBEDDED_COPYRIGHT_LICENSE_MARKER` eingestuft und durch Root, Payload, interne Skripte, Repository-Payload, GitHub-/Clone-/Merge-Pfade, Policy, Map, Learn, Accept, Sync, Reports und Tests korrigiert.

English:
Root `WINDOWS.bat` without embedded copyright/license marker is classified as reflexive error class `ROOT_WINDOWS_BATCH_WITHOUT_EMBEDDED_COPYRIGHT_LICENSE_MARKER` and corrected across root, payload, internal scripts, repository payload, GitHub/clone/merge paths, policy, map, learn, accept, sync, reports and tests.


## FULL_LICENSE_ENRICHMENT_REFLEXIVE_FIX / vollständige Lizenz-Anreicherung

Deutsch:
JSON-Dateien, Daten, Reports, Resultate und alle sonstigen QIK-VRT-Artefakte werden mit eingebetteten oder manifestierten Urheberrechts-/Lizenzinformationen versehen. Menschenlesbare Dateien erhalten nach dem Header mindestens eine Leerzeile. `LICENSES/` enthält die tatsächlichen offiziellen Lizenztexte für Apache-2.0 und CC-BY-NC-ND-4.0.

English:
JSON files, data, reports, results and all other QIK-VRT artifacts receive embedded or manifested copyright/license information. Human-readable files receive at least one blank line after the header. `LICENSES/` contains the actual official license texts for Apache-2.0 and CC-BY-NC-ND-4.0.

Reflexive error classes:
```text
JSON_AND_RESULT_FILES_WITHOUT_COPYRIGHT_LICENSE_METADATA
OFFICIAL_LICENSE_FILES_NOT_PLACED_IN_LICENSES_DIRECTORY
HUMAN_READABLE_FILE_HEADER_WITHOUT_BLANK_LINE
```


## RIGHTS_METADATA_VISIBILITY_FIX

Deutsch:
JSON-Dateien müssen Top-Level-Rechtsmetadaten tragen. Source-/Skriptdateien dürfen Ingolf Lohmann im Header nicht irreführend als `Author` bezeichnen, sondern als `Urheber/Rechteinhaber` und `Rights-Holder`.

English:
JSON files must carry top-level legal metadata. Source/script files must not misleadingly identify Ingolf Lohmann as `Author` in the header, but as `Urheber/Rechteinhaber` and `Rights-Holder`.

Reflexive error classes:
```text
JSON_LEGAL_METADATA_NOT_VISIBLE_OR_TOP_LEVEL
SOURCE_HEADER_MISSTATES_RIGHTS_HOLDER_AS_AUTHOR
```


## GLOBAL_RETROACTIVE_QIKVRT_RIGHTS_METADATA_ENFORCEMENT

Deutsch:
Diese Rechte-/Lizenz-Metadatenpflicht gilt rückwirkend für bestehende GitHub-QIK-VRT-Repositories, bestehende QIK-VRT-Repositories und alles, was daraus entsteht. Fehlende Anwendung ist `GLOBAL_RETROACTIVE_QIKVRT_RIGHTS_METADATA_ENFORCEMENT_MISSING`.

English:
This rights/license metadata requirement applies retroactively to existing GitHub QIK-VRT repositories, existing QIK-VRT repositories and everything derived from them. Missing application is `GLOBAL_RETROACTIVE_QIKVRT_RIGHTS_METADATA_ENFORCEMENT_MISSING`.


## SANDBOX_GITHUB_COMBINATORIAL_VALIDATION_GATE_FINAL

Deutsch:
Die GitHub-/Repository-Verhaltensvalidierung wurde als Sandbox-Simulationsmatrix nachgeholt, inklusive Positivfällen, Negativfall, False-Positive-Schutz und Derivaten. Reale externe GitHub-Mutation bleibt `NOT_EXECUTED`.

English:
GitHub/repository behavior validation was completed as a sandbox simulation matrix, including positive cases, negative case, false-positive guards and derivatives. Real external GitHub mutation remains `NOT_EXECUTED`.


## MANDATORY_AUTOMATED_COMBINATORIAL_VALIDATION_BEFORE_DONE_GATE

Deutsch:
Kein QIK-VRT-Kontext darf DONE/PASS/erledigt melden, wenn keine automatische, scope-deklarierte Kombinatorikvalidierung bestanden wurde. Manuelle Behauptung ersetzt keine Tests.

English:
No QIK-VRT context may report DONE/PASS/completed unless an automated, scope-declared combinatorial validation has passed. Manual assertion cannot replace tests.

Blocker: `DONE_REPORTED_WITHOUT_FULL_AUTOMATED_COMBINATORIAL_VALIDATION`


## ASCII_SAFE_SOURCE_AND_SCRIPT_TEXT_GATE

Deutsch:
Source-Code und ausfuehrungsnahe Skriptdateien muessen ASCII-sicher bleiben. Deutsche Umlaute und sonstige nicht-ASCII-Zeichen sind dort Blocker.

English:
Source code and execution-near script files must remain ASCII-safe. German umlauts and other non-ASCII characters are blockers there.

Blocker: `SOURCE_SCRIPT_CONTAINS_NON_ASCII_OR_UMLAUT_IN_EXECUTION_NEAR_TEXT`
