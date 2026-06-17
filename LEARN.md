<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright (c) 2026 Ingolf Lohmann; Urheber/Rechteinhaber / Rights-Holder: Ingolf Lohmann -->

# LEARN

## Verbindliche Lernregel

Jegliches Finding aus Tests, Audits, Builds oder Prüfberichten ist als Learning einzuordnen und lokal umzusetzen.

Das gilt ausdrücklich auch für:

- Warnungen
- Runtime-Grenzen
- nicht ausführbare Testteile
- fehlende Dependencies
- optionale Pfade
- nicht nachgewiesene GitHub-/Push-/Commit-/Upload-Zustände
- Pfadlängenbefunde
- Hash-/Sidecar-Befunde
- Skriptannahmen

## Aktuelles Learning

Finding:

```text
Windows-PowerShell-Runtime-Test konnte in dieser Linux-Sandbox nicht real ausgeführt werden.
```

Umsetzung:

```text
F001_WINDOWS_RUNTIME_BOUNDARY = IMPLEMENTED_LOCALLY
```

Folge:

```text
Kein echter Windows-Lauf wird behauptet.
Kein GitHub-Erfolg wird behauptet.
Der nächste reale Windows-Lauf muss STATUS.txt und MANIFEST.txt erzeugen.
```


## F002_REPO_QALL_MD_MISSING

Finding:

```text
Original-requirements test found that QALL.md was missing inside nested REPO.zip.
```

Learning:

```text
Repository-internal standard markers must be present, not only generated during runtime.
```

Implementation:

```text
QALL.md added to nested REPO.zip root.
LEARN.json/LEARN.md updated in bundle root and repository.
```


## L003_POWERSHELL_LINUX_SANDBOX_MAPPING

Windows-/PowerShell-Funktionen werden auf Linux-Sandbox-Funktionen gespiegelt.

Umsetzung:

```text
MAP.json
MAP.md
```

Grenze:

```text
Linux-Sandbox-Äquivalenz ersetzt keinen echten Windows-Runtime-Lauf.
GitHub-API-Pfade bleiben BLOCK, solange keine echten Credentials und keine erfolgreiche API-Ausführung vorliegen.
```


## L004_GITHUB_MAPPING_PERSISTENCE

Das Mapping und die Verfahrensweise müssen nach erfolgreicher Windows-Batch-Ausführung mit GitHub-API auch im GitHub-Repository enthalten sein.

Umsetzung:

```text
RUN.ps1 lädt MAP/LEARN/POLICY/Standardmarker per GitHub API hoch.
STATUS.txt enthält bei Erfolg GITHUB_MAPPING_POLICY_LEARNING=OK.
```


## L005_LINUX_MACOS_SYNC_LAYERS_MISSING

Finding:

```text
Linux- und macOS-Reproduktionsschichten waren im gelieferten Repository-Bundle noch nicht integriert.
```

Learning:

```text
Cross-platform sync layers must be included or explicitly blocked before delivery.
```

Implementation:

```text
RUN.sh
LINUX.sh
START.command
SYNC.json
SYNC.md
MAP019
MAP020
MAP021
```


## L006_AUTO_TOKEN_ONLY_GITHUB_PERSISTENCE

Ziel:

```text
Alle Plattformskripte laufen vollautomatisch.
Nur der GitHub-Token wird abgefragt.
Zielrepository: Goldkelch/qik-vrt
Branch: main
```

Erfolg:

```text
GITHUB_AUTO_TOKEN_ONLY=OK
```

nur nach echten API-PUTs und GET-Verifikation.

## L007_TEMPLATE_ADAPTIVE_OWNER_REPO

GitHub-Template-Instanzen müssen Owner/Repo/Branch automatisch aus dem lokalen Repository-Kontext übernehmen. Kein altes Ziel darf stillschweigend weiterverwendet werden.

## L008_TEMPLATE_CLONE_ACCEPTANCE_TEST

Template-adaptive target detection is now an Acceptance-Test before delivery.

## L009_DELIVERY_UX_STRUCTURE

Unnötige Details werden unter `_internal/` verdeckt. Startdateien und `LOGS/` liegen gemeinsam sichtbar im Root.

## L010_ROOT_ONLY_THREE_PLATFORM_SCRIPTS

Root enthält nur noch drei Skriptdateien: `WINDOWS.bat`, `LINUX.sh`, `MACOS.command`. Alles andere liegt unter `_internal/`, `_payload/` oder `LOGS/`.

## L011_INTERNAL_SUBSET_PAYLOAD_README_INI_LICENSE

`_internal/` ist logisch Teil von `_payload/` und liegt jetzt unter `_payload/_internal/`. Root enthält zusätzlich `README.md` für Zweck/Urheber/Lizenz und `QALL.ini` für zentrale Parameter.

## L012_CROSS_PLATFORM_FIX_MIRROR_REQUIRED

Linux-Sandbox-Bugfixes müssen für Windows und macOS gespiegelt werden, sofern der Fehler plattformübergreifend relevant ist. Unterlassung ist die reflexive Fehlerklasse `UNMIRRORED_LINUX_SANDBOX_FIX`.

## L014_RENEWED_LICENSE_ACCEPTANCE_BEFORE_EACH_PERSISTENCE

Vor jeder Repository-Persistenzänderung müssen Urheberrecht/Lizenzbedingungen erneut angezeigt und akzeptiert werden. Das gilt für künstlich-kognitive Systeme, natürliche Personen und juristische Personen gleichermaßen.

## L015_AMBIGUOUS_ACCEPTANCE_INPUT_BLOCKS

Jede zweifelhafte Akzeptanzeingabe blockiert. Akzeptiert wird nur exakt `ICH AKZEPTIERE`. Diese Eigenschaft muss bei Clone, Download, Nutzung und Merge erhalten bleiben.

## L016_AMBIGUOUS_COUNTERPARTY_TYPE_BLOCKS

Jede fehlende, freie, abweichende, unklare oder mehrdeutige Gegenstellentyp-Angabe blockiert. Zulässig sind nur exakt NATURAL_PERSON, ARTIFICIAL_COGNITIVE_SYSTEM, LEGAL_PERSON, ORGANIZATION oder OTHER.

## L017_OTHER_COUNTERPARTY_REQUIRES_DESCRIPTION

Bei Gegenstellentyp `OTHER` muss zusätzlich abgefragt und persistiert werden, was darunter konkret zu verstehen ist. Die vier Standardtypen bleiben als Vorbelegung/Auswahlwerte geführt.

## L018_USER_TEST_FINDING_REFLEXIVE_WORKFLOW_STANDARD

Jedes Nutzer-Test-Finding wird als reflexive Fehlerklasse behandelt und durch alle relevanten Schichten korrigiert. Keine isolierten Hotfixes.

## L019_BILINGUAL_UI_AND_USER_INFO_DE_EN

Alle interaktiven Benutzeroberflächen und alle nutzergerichteten Bundle-Informationen werden zweisprachig Deutsch/Englisch geführt.

All interactive user interfaces and all user-facing bundle information are maintained bilingually in German/English.

## L020_BILINGUAL_UI_INHERITANCE_REQUIRED

Alles aus Bundle, Repository oder GitHub Abgeleitete muss die zweisprachige DE/EN-UI-/Nutzerinformationspflicht erben.

Everything derived from the bundle, repository, or GitHub must inherit the bilingual DE/EN UI/user-information requirement.

## L021_OFFICIAL_LICENSE_REFRESH_AND_FILE_ENRICHMENT_BEFORE_PERSISTENCE

Vor jeder Repository-Persistenz werden die offiziellen Lizenzdateien von Apache-2.0 und CC-BY-NC-ND-4.0 neu geladen und lokale Kopien überschrieben. Alle Dateien werden mit Lizenz-/Urheberrechtsinformationen angereichert oder manifestiert.

Before every repository persistence, official Apache-2.0 and CC-BY-NC-ND-4.0 license files are refreshed and local copies overwritten. All files are enriched with license/copyright information or manifested.

## L022_LICENSE_REFRESH_FILE_ENRICHMENT_INHERITANCE_REQUIRED

Official-License-Refresh und File-Enrichment vererben sich zwingend auf alle GitHub-Klone, alle QIK-VRT-Repositories und alles daraus Hervorgehende.

Official license refresh and file enrichment are mandatorily inherited by all GitHub clones, all QIK-VRT repositories and all derivatives.


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
