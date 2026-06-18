<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

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

## MAP_GITHUB_DOMAIN_FACTORY

Deutsch: Windows, Linux und macOS starten dieselbe Python-GitHub-Domain-Factory. Reale GitHub-Wirkung erfordert Token, Netzwerk, `--execute`, ausreichende Rechte und exakte Akzeptanz.

English: Windows, Linux, and macOS start the same Python GitHub Domain Factory. Real GitHub effect requires token, network, `--execute`, sufficient permissions, and exact acceptance.

## OFFICIAL_LICENSE_PLACEHOLDER_AND_HEADER_FIX

Deutsch: Offizielle Lizenztexte und Datei-Header/-Notices müssen vor Delivery materialisiert sein. Platzhalter oder bloße spätere Fetch-Versprechen sind BLOCK.

English: Official license texts and file headers/notices must be materialized before delivery. Placeholders or mere later-fetch promises are BLOCK.

## RECURSIVE_LICENSE_AND_UMLAUT_LAYER

Deutsch: Sourcecode bleibt ohne deutsche Umlaute. Nicht-Software-Dokumente verwenden deutsche Umlaute korrekt. Lizenz- und Urheberrechtsinformationen werden rekursiv in allen Repository-Dateien ergänzt oder manifestiert.

English: Source code remains free of German umlauts. Non-software documents use German umlauts correctly. License and copyright information is recursively added to or manifested for all repository files.

## GITHUB_REPOSITORY_DOMAIN_ENSURE_CREATE_IF_MISSING

Deutsch: Fehlende GitHub-Repositories und fehlende GitHub-Pages-Custom-Domain-Konfigurationen werden nach strikter Akzeptanz angelegt bzw. konfiguriert. Öffentliche DNS-/Registrar-Domains sind ausdrücklich ausgenommen.

English: Missing GitHub repositories and missing GitHub Pages custom-domain configurations are created or configured after strict acceptance. Public DNS/registrar domains are explicitly excluded.

## SCRIPT_TERMINATION_AND_INFORMATION_HEADER_GUARD

Deutsch: Jedes Skript terminiert mit Status, Exit-Code und konkreten Fehlerdetails. Jede künftig erzeugte Datei, jeder Stream und jedes sonstige Informationsobjekt erhält Urheberrechts- und Lizenzrechtsinformationen per Header oder Manifestabdeckung.

English: Every script terminates with status, exit code, and concrete error details. Every future generated file, stream, and other information object receives copyright and license information via header or manifest coverage.

## GITHUB_REPOSITORY_METADATA_DETAILS_TOPICS_LICENSE_CITATION

Deutsch: QIK-VRT-GitHub-Repositories benötigen Description, Topics, bestmögliche GitHub-Lizenzdarstellung und `CITATION.cff`.

English: QIK-VRT GitHub repositories require description, topics, best-effort GitHub license display, and `CITATION.cff`.

## POWERSHELL_PARAM_BLOCK_GUARD_PLACEMENT

Deutsch: PowerShell-Guards müssen bei vorhandenen top-level `param(...)`-Blöcken hinter dem vollständigen Parameterblock stehen.

English: PowerShell guards must be placed after the complete top-level `param(...)` block when such a block exists.
