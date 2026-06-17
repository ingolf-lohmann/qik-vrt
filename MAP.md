<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright (c) 2026 Ingolf Lohmann; Urheber/Rechteinhaber / Rights-Holder: Ingolf Lohmann -->

# MAP

## PowerShell zu Linux-Sandbox — 1:1-Mapping

Dieses Mapping spiegelt die Windows-/PowerShell-Funktionen des Bundles auf die Linux-Sandbox-Prüffunktionen.

**Grenze:** Linux-Sandbox-Äquivalenz ersetzt keinen echten Windows-Lauf. GitHub-Erfolg wird nur bei echter API-Ausführung behauptet.

| ID | Zweck | Windows / PowerShell | Linux-Sandbox | Äquivalenz | Grenze |
|---|---|---|---|---|---|
| MAP001_BAT_ENTRY | Start entry point | cmd.exe /c START.bat | python-controlled workflow invoking equivalent steps directly | FUNCTIONAL | cmd.exe itself is Windows-only; sandbox mirrors the effects, not the shell runtime. |
| MAP002_POWERSHELL_RUNTIME | Run PowerShell script | powershell.exe | python3 execution of equivalent ZIP/JSON/hash logic | FUNCTIONAL | No real Windows PowerShell runtime is executed in this Linux sandbox. |
| MAP003_PATH_ROOT | Resolve bundle root | Split-Path | Path('/mnt/data/...').parent or extracted work directory | EXACT | Path separator differs; logical root is equivalent. |
| MAP004_REMOVE_DIRECTORY | Clean OUT/WORK folders | Remove-Item | shutil.rmtree(path) | EXACT | Permission semantics differ only by platform. |
| MAP005_CREATE_DIRECTORY | Create directories | New-Item | Path.mkdir(parents=True, exist_ok=True) | EXACT | Directory creation result is equivalent. |
| MAP006_TEST_PATH | Check file/path existence | Test-Path | Path.exists() | EXACT | Case sensitivity can differ. |
| MAP007_READ_HOST | Interactive user input | Read-Host | parameterized test values or input() equivalent | FUNCTIONAL | Noninteractive sandbox tests inject values; interactive console behavior is not identical. |
| MAP008_EXPAND_ARCHIVE | Extract ZIP | Expand-Archive | zipfile.ZipFile(...).extractall(...) | EXACT | Both validate/extract ZIP; metadata details may differ. |
| MAP009_COMPRESS_ARCHIVE | Create output ZIP | Compress-Archive | zipfile.ZipFile(..., 'w', ZIP_DEFLATED) | FUNCTIONAL | Byte-identical ZIP is not guaranteed; file content and logical structure are tested. |
| MAP010_HASH_SHA256 | Create SHA256 sidecar | Get-FileHash | hashlib.sha256(path.read_bytes()).hexdigest() | EXACT | Same SHA256 digest algorithm. |
| MAP011_JSON_WRITE | Write JSON | ConvertTo-Json / Set-Content | json.dumps(..., ensure_ascii=False, indent=2); Path.write_text(..., encoding='utf-8') | FUNCTIONAL | Formatting may differ; JSON semantics are tested. |
| MAP012_TEXT_WRITE | Write status and manifest text | Set-Content | Path.write_text(...) | EXACT | Line ending may differ; content semantics are equivalent. |
| MAP013_GITHUB_API_GET | Read GitHub content metadata | Invoke-RestMethod | not executed without credential/network authorization; would map to urllib/requests/web API | BLOCK | No GitHub write/read success is claimed without real API execution and credentials. |
| MAP014_GITHUB_API_PUT | Persist files to GitHub | Invoke-RestMethod | not executed without credential/network authorization; would map to urllib/requests/web API | BLOCK | GitHub success remains false until real API PUT succeeds. |
| MAP015_BASE64 | Base64 encode GitHub API content | [Convert]::ToBase64String | base64.b64encode(path.read_bytes()).decode('ascii') | EXACT | Exact content bytes produce exact base64 string. |
| MAP016_ERROR_EXIT | Block on hard failure | exit | raise SystemExit(code) or report FAIL | FUNCTIONAL | Process runtime differs; status semantics are equivalent. |
| MAP017_STATUS_BOUNDARY | No false success claims | Set-Content | JSON report plus status file generation | EXACT | No commit/push/upload/release is inferred from local output. |

## Aktuell geblockte Mapping-Pfade

- MAP013_GITHUB_API_GET
- MAP014_GITHUB_API_PUT

Grund: Kein GitHub-Erfolg ohne echte Credentials, echte API-Ausführung und echten Response-Nachweis.


## MAP018_GITHUB_MAPPING_PERSISTENCE

Nach erfolgreicher Windows-Ausführung mit aktivierter GitHub-API werden Mapping, Learning, Policy und Standardmarker ins GitHub-Repository geschrieben:

```text
MAP.json
MAP.md
LEARN.json
LEARN.md
QALL.json
QALL.md
START.bat
PATCH.ps1
bundle/POLICY.json
bundle/MAP.json
bundle/MAP.md
bundle/LEARN.json
bundle/LEARN.md
```

Erfolg gilt nur, wenn die API-PUT-Operationen erfolgreich abgeschlossen wurden und `STATUS.txt` enthält:

```text
GITHUB_MAPPING_POLICY_LEARNING=OK
```


## MAP019_POSIX_LOCAL_REPRODUCTION

Linux/macOS local reproduction is mirrored through `RUN.sh`.

```text
PowerShell: Expand-Archive / Compress-Archive / Get-FileHash
POSIX: unzip / zip / sha256sum or shasum
```

## MAP020_MACOS_LAUNCHER

macOS launcher:

```text
START.command -> /bin/sh RUN.sh
```

## MAP021_SYNC_LAYER_DISCLOSURE

All platform layers must be disclosed as implemented/tested/not tested. No platform DONE without real platform execution.


## MAP022_TOKEN_ONLY_WINDOWS_GITHUB

Windows path:

```text
START.bat -> RUN.ps1 -> asks only GitHub token
target = Goldkelch/qik-vrt
branch = main
```

## MAP023_TOKEN_ONLY_POSIX_GITHUB

Linux/macOS path:

```text
RUN.sh / START.command -> GH.py -> asks only GitHub token
target = Goldkelch/qik-vrt
branch = main
```

Boundary:

```text
GitHub success requires real token, real PUT operations and GET verification.
```

## MAP024_TEMPLATE_TARGET_AUTODETECT

Owner/Repo/Branch werden aus QALL_ENV, GitHub-Actions-Env, `.git/config`, `QALL_TARGET.json` oder Fallback-Abfrage ermittelt.

## MAP025_TEMPLATE_CLONE_ACCEPTANCE

Synthetic `.git/config` clone context is used to verify owner/repo/branch autodetection.

## MAP026_DELIVERY_VISIBLE_LOGS

Startdateien liegen sichtbar im Root; Lauf- und Log-Ergebnisse liegen sichtbar in `LOGS/`.

## MAP027_MINROOT_THREE_PLATFORM_SCRIPTS

Root-Einstieg wird auf exakt drei Plattformskripte reduziert.

## MAP028_PAYLOAD_INTERNAL_AND_ROOT_INI_README

Interne technische Details liegen unter `_payload/_internal/`; Root enthält drei Plattformskripte plus README und INI.

## MAP029_CROSS_PLATFORM_FIX_MIRROR

Fixes aus Linux-Sandbox-Tests werden auf Windows PowerShell und macOS POSIX gespiegelt.

## MAP031_LICENSE_ACCEPTANCE_BEFORE_PERSISTENCE

Windows, Linux und macOS führen vor GitHub-/Repository-Schreiboperationen ein License-Acceptance-Gate aus.

## MAP032_STRICT_ACCEPTANCE_PRESERVATION

Windows, Linux, macOS, GitHub-Persistenz und Klone führen das strikte Acceptance-Gate fort.

## MAP033_STRICT_COUNTERPARTY_TYPE_PRESERVATION

Windows, Linux, macOS, GitHub-Persistenz und Klone erhalten die strikte Gegenstellentyp-Prüfung.

## MAP034_OTHER_COUNTERPARTY_DESCRIPTION

`OTHER` führt zu zusätzlicher Beschreibungspflicht und Persistenzfeld `counterparty_other_description`.

## MAP035_REFLEXIVE_USER_TEST_FINDING_WORKFLOW

Nutzer-Findings erzwingen Schichtenkorrektur: Root, Payload, Windows, Linux, macOS, GitHub, Clone, Merge, Lizenz-/Akzeptanzgates, Policy, Learn, Accept, Sync, Reports und Tests.

## MAP036_BILINGUAL_UI_USER_INFO

Interaktive Prompts, Block-/Done-Meldungen, README, NOTICE und QALL.ini-Kommentare werden Deutsch/Englisch gespiegelt.

Interactive prompts, block/done messages, README, NOTICE and QALL.ini comments are mirrored German/English.

## MAP037_BILINGUAL_UI_INHERITANCE

Clone, Download, Fork, Template, Merge, Release, Repackage, Build-Artefakt, lokale Reproduktion und Folge-Bundle müssen DE/EN erhalten.

Clone, download, fork, template, merge, release, repackage, build artifact, local reproduction and follow-up bundle must preserve DE/EN.

## MAP038_OFFICIAL_LICENSE_REFRESH_AND_FILE_ENRICHMENT

Persistenzpfade führen offiziellen Lizenz-Refresh und Datei-Enrichment aus.

Persistence paths run official license refresh and file enrichment.

## MAP039_LICENSE_REFRESH_FILE_ENRICHMENT_INHERITANCE

Alle QIK-VRT-Repositories und Derivate tragen die Lizenz-Refresh-/File-Enrichment-Erbregel.

All QIK-VRT repositories and derivatives carry the license-refresh/file-enrichment inheritance rule.


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
