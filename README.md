<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# QALL Delivery Bundle / QALL-Auslieferungsbundle

## Deutsch: Was ist das?

Dieses Bundle enthält eine plattformübergreifende QIK-VRT-Delivery-, Reproduktions- und GitHub-Template-Automationsstruktur.

Direkte Startpunkte:

```text
WINDOWS.bat
LINUX.sh
MACOS.command
```

Technische Nutzdaten:

```text
_payload/
```

Lauf- und Ergebnisdateien:

```text
LOGS/
```

## English: What is this?

This bundle contains a cross-platform QIK-VRT delivery, reproduction, and GitHub-template automation structure.

Direct start files:

```text
WINDOWS.bat
LINUX.sh
MACOS.command
```

Technical payload:

```text
_payload/
```

Runtime and result files:

```text
LOGS/
```

## Deutsch: Urheber / Rechteinhaber

```text
Ingolf Lohmann
```

## English: Author / rights holder

```text
Ingolf Lohmann
```

## Deutsch: Lizenzhinweise

Grundlinie, sofern in den enthaltenen Repository-Dateien nicht abweichend oder spezifischer geregelt:

```text
QIK-VRT-Nichtsoftwarematerial: CC-BY-NC-ND-4.0
ausdrücklich markierte Software-/Skriptbestandteile: Apache-2.0
```

Vor jeder Repository-Persistenzänderung wird erneut auf Urheberrecht und Lizenzbedingungen hingewiesen. Ohne konkrete, zweifelsfreie Akzeptanz wird keine GitHub-/Repository-Schreiboperation ausgeführt.

Akzeptiert wird nur exakt:

```text
ICH AKZEPTIERE
```

## English: License notices

Baseline unless repository files contain different or more specific terms:

```text
QIK-VRT non-software material: CC-BY-NC-ND-4.0
expressly marked software/script components: Apache-2.0
```

Before every repository persistence change, copyright and license terms are shown again. Without concrete, unambiguous acceptance, no GitHub/repository write operation is performed.

Only the exact phrase is accepted:

```text
ICH AKZEPTIERE
```

## Deutsch: Gegenstellentyp

Zulässig sind exakt:

```text
NATURAL_PERSON
ARTIFICIAL_COGNITIVE_SYSTEM
LEGAL_PERSON
ORGANIZATION
OTHER
```

Bei `OTHER` muss zusätzlich beschrieben werden, was darunter konkret zu verstehen ist.

## English: Counterparty type

Exactly these values are allowed:

```text
NATURAL_PERSON
ARTIFICIAL_COGNITIVE_SYSTEM
LEGAL_PERSON
ORGANIZATION
OTHER
```

If `OTHER` is selected, an additional concrete description is required.

## Deutsch: Reflexiver Finding-Workflow

Wenn dieses Bundle beim Download, Entpacken, Starten, Konfigurieren, Nutzen, Klonen, Mergen oder Persistieren nicht auf Anhieb funktioniert, ist jedes Finding als reflexive Fehlerklasse zu behandeln.

Keine isolierten Hotfixes. Relevante Korrekturen müssen durch alle betroffenen Schichten gespiegelt werden.

## English: Reflexive finding workflow

If this bundle does not work immediately during download, extraction, startup, configuration, use, cloning, merging, or persistence, every finding must be treated as a reflexive error class.

No isolated hotfixes. Relevant corrections must be mirrored through all affected layers.


Bilingual UI Inheritance / Vererbung der zweisprachigen UI

Deutsch:
    Alles, was aus diesem Bundle, Repository oder GitHub heraus erzeugt wird,
    muss die zweisprachige Deutsch/Englisch-Eigenschaft für interaktive UI und
    Nutzerinformationen weitertragen.

English:
    Everything derived from this bundle, repository, or GitHub must preserve
    the bilingual German/English property for interactive UI and user-facing
    information.


Official License Refresh / Aktualisierung offizieller Lizenzdateien

Deutsch:
    Vor jeder Repository-Persistenz werden die offiziellen aktuellen Lizenzdateien
    von Apache-2.0 und CC-BY-NC-ND-4.0 erneut geladen und überschreiben lokale Kopien.
    Danach werden alle Dateien mit Lizenz-/Urheberrechtsinformationen angereichert
    oder manifestbasiert abgedeckt.

English:
    Before every repository persistence, the official current Apache-2.0 and
    CC-BY-NC-ND-4.0 license files are fetched again and overwrite local copies.
    Then all files are enriched with license/copyright information or covered
    by manifest records.

Sources / Quellen:
    https://www.apache.org/licenses/LICENSE-2.0.txt
    https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.txt


## GitHub Domain Factory / GitHub-Domain-Factory

### Deutsch

Dieses Bundle enthält zusätzlich:

```text
GITHUB_DOMAIN.py
GITHUB_DOMAIN.sh
GITHUB_DOMAIN.bat
GITHUB_DOMAIN.command
```

Zweck: Eine neue GitHub-Repository-Domäne anlegen und optional GitHub Pages mit einer Custom Domain konfigurieren.

Standardmäßig läuft das Skript im Trockenlauf. Reale GitHub-Wirkung entsteht erst mit:

```text
python GITHUB_DOMAIN.py --execute
```

Vor realer Wirkung fragt das Skript alle notwendigen Angaben ab:

```text
Aktion
GitHub-Zieltyp USER/ORG
Owner/Organisation
Repository-Name
Beschreibung
Sichtbarkeit
Default-Branch
Quelle EMPTY/FROM_TEMPLATE
GitHub-Pages-Einstellungen
Custom Domain
Gegenstellentyp
OTHER-Beschreibung falls OTHER
Akzeptanzphrase ICH AKZEPTIERE
GitHub-Token
```

Grenze: Das Skript registriert keine öffentliche DNS-Domain bei einem Registrar. Für GitHub Pages Custom Domains muss DNS weiterhin beim Domain-Provider korrekt gesetzt werden.

### English

This bundle additionally contains:

```text
GITHUB_DOMAIN.py
GITHUB_DOMAIN.sh
GITHUB_DOMAIN.bat
GITHUB_DOMAIN.command
```

Purpose: Create a new GitHub repository domain and optionally configure GitHub Pages with a custom domain.

By default the script runs in dry-run mode. Real GitHub effect requires:

```text
python GITHUB_DOMAIN.py --execute
```

Before real effect, the script asks for all required data:

```text
action
GitHub target type USER/ORG
owner/organization
repository name
description
visibility
default branch
source EMPTY/FROM_TEMPLATE
GitHub Pages settings
custom domain
counterparty type
OTHER description if OTHER
acceptance phrase ICH AKZEPTIERE
GitHub token
```

Boundary: The script does not register a public DNS domain at a registrar. For GitHub Pages custom domains, DNS still has to be configured correctly at the domain provider.


## License placeholder/header repair / Lizenzplatzhalter- und Header-Reparatur

### Deutsch

Dieses Paket ersetzt vor Auslieferung die bisherigen Lizenzplatzhalter durch die offiziellen Lizenztexte:

```text
LICENSES/Apache-2.0.txt
LICENSES/CC-BY-NC-ND-4.0.txt
LICENSES/Creative-Commons-BY-NC-ND-4.0.txt
```

Zusätzlich werden Sourcecode-Dateien mit SPDX-/Copyright-/Rechteinhaber-Headern versehen. Nicht-Software-Dokumente erhalten konkrete Lizenz-/Urheberrechtshinweise oder werden eindeutig über `FILE_LICENSE_HEADER_COVERAGE.tsv` und `FILE_LICENSE_HEADER_COVERAGE.json` erfasst.

### English

Before delivery, this package replaces previous license placeholders with the official license texts:

```text
LICENSES/Apache-2.0.txt
LICENSES/CC-BY-NC-ND-4.0.txt
LICENSES/Creative-Commons-BY-NC-ND-4.0.txt
```

Additionally, source code files receive SPDX/copyright/rights-holder headers. Non-software documents receive concrete license/copyright notices or are explicitly covered by `FILE_LICENSE_HEADER_COVERAGE.tsv` and `FILE_LICENSE_HEADER_COVERAGE.json`.


## Rekursive Lizenz-/Urheberrechts- und Umlaut-Schicht

### Deutsch

Dieses Paket trennt Sourcecode und Nicht-Software-Dokumente ausdrücklich:

- Sourcecode-Dateien enthalten keine deutschen Umlaute.
- Nicht-Software-Dateien verwenden deutsche Umlaute korrekt.
- Urheberrechts- und Lizenzrechtsinformationen werden rekursiv in allen Repository-Dateien ergänzt oder manifestiert.
- Die Regel gilt auch für verschachtelte Repository-Payloads, Klone, Templates, Forks, Releases, Repackages und Folgeartefakte.

### English

This package explicitly separates source code and non-software documents:

- Source code files contain no German umlauts.
- Non-software files use German umlauts correctly.
- Copyright and license information is recursively added to or manifested for all repository files.
- The rule also applies to nested repository payloads, clones, templates, forks, releases, repackages, and follow-up artifacts.


## GitHub Ensure Repository and Domain / GitHub-Repository und Domain sicherstellen

### Deutsch

Dieses Paket enthält zusätzlich:

```text
GITHUB_ENSURE.py
GITHUB_ENSURE.sh
GITHUB_ENSURE.bat
GITHUB_ENSURE.command
```

Zweck:

1. Prüfen, ob das angegebene GitHub-Repository existiert.
2. Falls es nicht existiert, nach strikter Akzeptanz und Gegenstellenprüfung anlegen.
3. Falls GitHub Pages oder die GitHub-Pages-Custom-Domain fehlen, anlegen bzw. konfigurieren.
4. Danach erneut prüfen und alles in `LOGS/` protokollieren.

Standardmäßig läuft das Skript als Trockenlauf:

```text
python GITHUB_ENSURE.py
```

Reale GitHub-Wirkung entsteht erst mit:

```text
python GITHUB_ENSURE.py --execute
```

Grenze: Das Skript registriert keine öffentliche DNS-/Registrar-Domain. Es konfiguriert nur GitHub-Repository und GitHub Pages. DNS muss beim Domain-Provider gesetzt werden.

### English

This package additionally contains:

```text
GITHUB_ENSURE.py
GITHUB_ENSURE.sh
GITHUB_ENSURE.bat
GITHUB_ENSURE.command
```

Purpose:

1. Check whether the requested GitHub repository exists.
2. If it does not exist, create it after strict acceptance and counterparty validation.
3. If GitHub Pages or the GitHub Pages custom domain are missing, create or configure them.
4. Re-check and record everything in `LOGS/`.

By default the script runs as dry-run:

```text
python GITHUB_ENSURE.py
```

Real GitHub effect requires:

```text
python GITHUB_ENSURE.py --execute
```

Boundary: The script does not register a public DNS/registrar domain. It configures only GitHub repository and GitHub Pages. DNS must be configured at the domain provider.


## Skripttermination und Informationsobjekt-Header

### Deutsch

Dieses Paket erzwingt:

- Jedes Skript terminiert mit eindeutiger Rückmeldung.
- Erfolg wird als `SCRIPT_TERMINATION=PASS` gemeldet.
- Fehler werden als `SCRIPT_TERMINATION=ERROR`, `FAIL` oder `BLOCK` mit Exit-Code und Fehlerdetails protokolliert.
- Jede künftig erzeugte Datei muss einen passenden Header oder eine eindeutige Manifestabdeckung erhalten.
- Streams und sonstige Informationsobjekte müssen ebenfalls über ein Manifest mit Urheberrechts-, Lizenzrechts- und Provenance-Angaben abgedeckt werden.

### English

This package enforces:

- Every script terminates with an explicit report.
- Success is reported as `SCRIPT_TERMINATION=PASS`.
- Errors are reported as `SCRIPT_TERMINATION=ERROR`, `FAIL`, or `BLOCK` with exit code and error details.
- Every future generated file must receive an appropriate header or explicit manifest coverage.
- Streams and other information objects must also be covered by a manifest with copyright, license, and provenance information.


## GitHub-Repository-Metadaten: Description, Topics, Lizenz, Citation

### Deutsch

Dieses Paket ergänzt die GitHub-Repository-Metadaten um:

- eine QIK-VRT-Kurzbeschreibung für das GitHub-Description-Feld,
- eine ausführliche Beschreibung in `QIKVRT_REPOSITORY_DETAILS.md`,
- maximal 20 GitHub-konforme QIK-VRT-Topics,
- eine bestmögliche GitHub-Lizenzdarstellung durch `LICENSE` als Apache-2.0-Wurzeldatei,
- getrennte Creative-Commons-Abdeckung für Nicht-Softwarematerial,
- eine gepflegte `CITATION.cff`,
- ein Skript `GITHUB_METADATA.py`, das diese Metadaten bei realer GitHub-Ausführung aktualisiert.

Reale GitHub-Wirkung entsteht erst mit:

```text
python GITHUB_METADATA.py --execute
```

### English

This package adds GitHub repository metadata:

- a QIK-VRT short description for the GitHub description field,
- a detailed description in `QIKVRT_REPOSITORY_DETAILS.md`,
- up to 20 GitHub-compliant QIK-VRT topics,
- best-effort GitHub license display through `LICENSE` as Apache-2.0 root file,
- separate Creative Commons coverage for non-software material,
- a maintained `CITATION.cff`,
- a `GITHUB_METADATA.py` script that updates these metadata fields during real GitHub execution.

Real GitHub effect requires:

```text
python GITHUB_METADATA.py --execute
```


## PowerShell-param-Guard-Fix

### Deutsch

Dieses Paket korrigiert die PowerShell-Regel:

- Header und Kommentare dürfen vor `param(...)` stehen.
- Ausführbarer Termination-/Logging-Guard darf nicht vor `param(...)` stehen.
- Wenn ein PowerShell-Skript einen top-level `param(...)`-Block besitzt, wird der Guard erst nach dem vollständigen Parameterblock eingefügt.
- Diese Prüfung wird rekursiv auf Root-Dateien, Repository-Payloads und verschachtelte ZIPs angewandt.

### English

This package corrects the PowerShell rule:

- Headers and comments may appear before `param(...)`.
- Executable termination/logging guard code must not appear before `param(...)`.
- If a PowerShell script has a top-level `param(...)` block, the guard is inserted only after the complete parameter block.
- This check is applied recursively to root files, repository payloads, and nested ZIPs.
