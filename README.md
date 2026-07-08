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

# QIKVRT V2.12.1 Unified Node Core Alignment

This package realigns the generic QIKVRT Node Onboarding architecture to the already fixed GitHub repository API. Seed and normal nodes share one identical inner core and one identical REST API. The role is selected by runtime configuration only.

Run on Windows:

```cmd
QIKVRT.cmd acceptance
```

Core assertions:

```text
API = api/qikvrt_github_api.openapi.yaml
Local shim = http://127.0.0.1:8766
GitHub API = https://api.github.com
Roles = normal | seed
Role difference = configuration/assertions only
No API fork. No seed/node code split.
```

Author/rightsholder: Ingolf Lohmann.

# QIKVRT Verfassung der Nachvollziehbarkeit v2.11
## ANSI-C/POSIX Constitutional Governance Repository

Status: V2.10 builds on V2.8 and adds autonomous discovery operation with a formal impossibility boundary for unsafe global Internet self-discovery claims.

Boundary: This repository is not an official legal act, not a surveillance instrument, and not a tool for accusing specific third parties. It is a defensive, auditable reference implementation for traceable handling of significant information effects.

Core execution model:

1. Difference is detected.
2. Information is classified.
3. Evidence grade is assigned.
4. Roles and jurisdictions are selected.
5. Multicast delivery to responsible nodes is validated.
6. Privacy, proportionality, emergency, correction, and sanctions gates are checked.
7. Traceability and nonregression anchors are recorded.
8. Final status remains blocked unless all gates pass.

Build:

```sh
make
```

Test:

```sh
make test
```

Verifier examples:

```sh
./build/qikvrt_verify --verify docs/VERFASSUNG_DER_NACHVOLLZIEHBARKEIT.md
./build/qikvrt_verify --verify-repo .
./build/qikvrt_verify --selftest-governance
```

Minimal regression ancestry:

- V2.1: full-depth ANSI-C/POSIX baseline.
- V2.2: multicast and ontology implemented downward.
- V2.7: constitution implemented upward into procedural governance.


## V2.7 Authorized Active Layer + Watchdog Keepalive

This release adds an authorized active layer: opt-in discovery manifests, local operation lifecycle, active-layer gates, self-organization metadata, evolution proposals and cognitive improvement metrics. It explicitly forbids unauthorized scanning, self-propagation, surveillance use and silent remote modification.

Commands:

```sh
make all test
./build/qikvrt_verify --selftest-active
./build/qikvrt_verify --verify-repo .
```


## V2.7 Watchdog Keepalive

Adds runtime selftests and an authorized watchdog keepalive layer for opt-in repository networks. It detects missing/stale nodes using explicit peer manifests, expected intervals, last_seen_epoch, observed_epoch, traceability records and privacy-preserved location hints when data allows. Unauthorized scanning, self-propagation, surveillance and silent node-loss deletion remain BLOCK.

Run: `make test` or `./build/qikvrt_verify --selftest-watchdog`.

## V2.7 Bootstrapper GUID Minimalregression

V2.7 ergänzt V2.5 um einen ANSI-C/POSIX-Bootstrapper. Bei erster Ausführung erzeugt `./build/qikvrt_verify --bootstrap <repo-root>` eine GUID, persistiert sie in `qikvrt/runtime/REPOSITORY_GUID.txt`, schreibt ein lokales Bootstrap-Ledger und startet die höheren Services logisch in der Reihenfolge verify, multicast, ontology, governance, active und watchdog. Der Netzwerkbeitritt ist ausschließlich als autorisierter Manifest-Login spezifiziert; unautorisiertes Scanning, Selbstverbreitung, Überwachung und stille Selbstmutation bleiben BLOCK.


## V2.7 TCP/IP autonomy sanity layer

V2.7 adds a bounded TCP/IP autonomy proof: `--selftest-tcpip-autonomy` performs an actual loopback TCP exchange for an authorized, traceable, non-mutating selftest request. `--selftest-damage-containment` verifies quarantine-required handling and authorized multicast notice for failed/missing peers. This is safe autonomy, not scanning, not self-propagation and not remote repair.


## V2.8 Autonomous Discovery Operation

V2.8 adds a formal and executable autonomous discovery operation layer. It proves the safe boundary: global Internet self-discovery without any seed, endpoint, registry, routable multicast, or scanning is not a valid claim. The repository therefore implements authorized seed-peer discovery, local multicast where permitted, persistent operation, watchdog keepalive, and peer-requestable sanity selftests while blocking global address scanning, unauthorized probing, self-propagation, surveillance use, and remote mutation without authorization.

Runtime selftest: `./build/qikvrt_verify --selftest-autonomous-discovery`

## V2.8 Minimalregression

V2.10 is the minimal regression point for autonomous repository operation: bootstrap GUID, authorized active layer, watchdog keepalive, TCP/IP sanity, damage containment, and autonomous discovery operation must all be present. Global Internet discovery without seed, endpoint, registry, routable multicast, or scanning is explicitly not claimed and is blocked by the gates.

## V2.10 GitHub Seed Discovery

V2.10 sets `https://github.com/Goldkelch/qik-vrt` as the single initial seed for QIK-VRT repository discovery. The proof is graph-theoretic: all QIK-VRT peers that publish authorized peer manifests reachable from this seed can be discovered without further third-party registry/search services. The boundary remains strict: no global address scanning, no unauthorized probing, no self-propagation, no surveillance use and no remote mutation without authorization.

Runtime selftest:

```sh
./build/qikvrt_verify --selftest-github-seed-discovery
```

## V2.10 Minimalregression

V2.10 is the minimal regression point for GitHub-seed-based autonomous discovery: `https://github.com/Goldkelch/qik-vrt` is the single initial seed; peer discovery is graph reachability from the seed manifest; repository GUID, peer manifest, watchdog keepalive, peer-requestable sanity and audit logging are mandatory; global address scanning, unauthorized probing, self-propagation, surveillance use and remote mutation without authorization remain blocked.


## V2.10 Real GitHub Seed Integration

V2.10 defines `https://github.com/Goldkelch/qik-vrt` as the real, tested initial seed. Acceptance requires live seed reachability evidence, raw `MANIFEST.json` validation, REST/TCPIP capability manifest validation, no global address scanning, no unauthorized probing, and persisted reference results. The runtime sanity path is implemented by `--selftest-real-github-seed-integration` and `--validate-github-seed-manifest`. V2.10 is the minimal regression point for this capability.


## V2.10.3 Windows tar flat ZIP extraction repair

The acceptance runner report `FEHLER_ENTPACKT_ABER_LEER` showed that a ZIP with an internal wrapper directory can be interpreted as empty by Windows tar based release runners. V2.10.3 therefore requires flat ZIP packaging: `README.md`, `Makefile`, `SHA256SUMS.txt`, `docs/`, `src/`, `tests/`, and `qikvrt/` are visible directly at the extraction root. Runtime checks: `--selftest-zip-layout` and `--validate-root-layout <root>`.


## V2.10.3 Windows Shell ZIP Compatibility Repair

V2.10.3 corrects the real Windows Shell ZIP extraction report `FEHLER_ENTPACKT_ABER_LEER` from `archiv_report(4).tsv`. The release ZIP is packaged with explicit directory entries and DOS/Windows ZIP metadata while preserving flat root content.


## V2.10.3 Short Path Packaging

Delivered as `qv211.zip` to avoid Windows acceptance runner path-length failures. See `docs/SP.md`.


## V2.11 Live Evidence Closure

V2.11 adds live-evidence and article-claim-matrix gates. Full live GitHub acceptance requires an external C/POSIX runner with DNS/HTTPS access; absent that evidence, full live pass is blocked.


## Windows-only acceptance

For Windows environments without POSIX shell, run from the extracted repository root:

```cmd
QIKVRT.cmd acceptance
```

This uses PowerShell for SHA256, JSON/JSONL parsing, live GitHub seed fetch, compiler detection, C build where a compiler is available, and all QIK-VRT selftests. See `docs/WIN.md`.


## Windows compiler discovery repair v2.11.3

`qv2113w.zip` repairs the external qv2112w Windows result where `winget` returned exit 0 for LLVM but no compiler was found on PATH. The Windows runner now probes known install locations and executes discovered compilers by full path. See `docs/WCB.md`.

## Windows StrictMode singleton array repair v2.11.5

`qv2115w.zip` repairs the external qv2114w Windows result where PowerShell 5.1 StrictMode aborted on `.Length` for a singleton compiler candidate object. The Windows runner now normalizes candidate collections with `To-ObjectArray` and uses `Get-ObjectArrayCount`; it does not read `.Count` or `.Length` from potentially singleton compiler objects.

## v2.11.7 Windows final aggregation repair

External Windows evidence from qv2116w demonstrated successful live GitHub fetch, Zig runtime compiler bootstrap, C build and all C selftests. Earlier LLVM clang build attempts failed because clang lacked a usable Windows C runtime/include path (`stdio.h` not found). v2.11.7 preserves those attempt-level BLOCK records but evaluates final acceptance from required final gates, so recovered fallback builds no longer produce a false final BLOCK.

## V2.11.8 Generic QIKVRT Node Onboarding + visible Windows runner

This release replaces any person-bound default node profile with a generic QIKVRT Node Onboarding profile.
A node starts as a neutral repository node with a local GUID, optional operator alias, authorized seed graph access, privacy-preserved runtime evidence, watchdog readiness and no person-bound default identity.

The Windows launcher now keeps the console visible after completion, writes `console.out.txt` and `console.err.txt`, and records the command exit code. For automated execution set `QIKVRT_NO_PAUSE=1`.


## V2.11.9 Node Onboarding Testbed

This release adds the generic QIKVRT Node Onboarding Testbed. The default runtime profile is `generic-qikvrt-node`, not a person-bound node. The testbed verifies the chain from the Ontology of Difference through constitutional governance, bootstrap, authorized seed discovery, watchdog keepalive, live evidence and the QIKVRT REST API contract. Runtime check: `--selftest-node-onboarding-testbed`.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.


## V2.13.4 Delivery Corrections

- Author / Urheber and rights holder visibility added across source and document layers.
- Source headers and document headers/footers are now acceptance-gated.
- Full reusable test environment gate covers ontology, requirements, unit, integration, acceptance, performance, security and runtime REST API layers.
- Seed and Node are delivered as separate independent ZIP artifacts inside the overall delivery: `seed/qv2134_seed.zip` and `node/qv2134_node.zip`.
- Both role packages use the same QIKVRT Node Core and the same GitHub-compatible API. Role difference is configuration only.


## Runtime Role Package

This independent ZIP is configured as role `node` via `qikvrt/config/ROLE.json`. The API and inner core remain identical across seed and normal node packages.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->


## Repository Setup / Repository-Einrichtung (DE/EN)

Deutsch: Dieses Rollenpaket (`node`) führt beim ersten Setup eine Repository-GUID ein, fragt GitHub Owner/Repository mit Defaultwerten ab und persistiert diese Parameter. Danach verwenden Deploy, Onboarding und Runtime die gespeicherten Werte ohne weitere Mensch-Maschine-Interaktion.

English: This role package (`node`) creates a repository GUID during first setup, asks for GitHub owner/repository with defaults, and persists these parameters. Afterwards deploy, onboarding, and runtime use the stored values without further human-machine interaction.

Windows:

```cmd
QIKVRT.cmd setup
QIKVRT.cmd register
```

POSIX:

```sh
sh QIKVRT.sh setup
sh QIKVRT.sh register
```

Persisted configuration / Persistierte Konfiguration:

- `qikvrt/runtime/REPOSITORY_GUID.txt`
- `qikvrt/config/REPOSITORY_TARGET.json`
- `qikvrt/config/ONBOARDING.json`
- `qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json`

Footer / Fußzeile: QIKVRT | Ingolf Lohmann | Apache-2.0 | CC BY-NC-ND 4.0 | NO_TRACEABILITY_NO_FINAL_PASS


## Unified public entrypoints / Einheitliche öffentliche Einstiegspunkte

Deutsch: Dieses Repository hat genau einen öffentlichen Windows-Einstiegspunkt (`QIKVRT.cmd`) und genau einen öffentlichen POSIX-Einstiegspunkt (`QIKVRT.sh`). Setup, Register, Deploy und Acceptance/Test werden über Modi ausgeführt: `setup`, `register`, `deploy`, `acceptance`. Das GitHub-Token wird beim Deploy zur Laufzeit abgefragt, falls `GITHUB_TOKEN` nicht gesetzt ist und kein Dry-Run verwendet wird. Der Token wird nicht persistiert.

English: This repository has exactly one public Windows entry point (`QIKVRT.cmd`) and exactly one public POSIX entry point (`QIKVRT.sh`). Setup, register, deploy and acceptance/test are selected through modes: `setup`, `register`, `deploy`, `acceptance`. The GitHub token is prompted at deployment runtime if `GITHUB_TOKEN` is not set and dry-run mode is not used. The token is not persisted.

---

QIKVRT bilingual footer / Zweisprachiger Footer. Author / Urheber: Ingolf Lohmann. Software license: Apache-2.0. Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated.

## V2.13.4 Windows Acceptance Single Entrypoint Repair

Deutsch: `RUN_WINDOWS_ACCEPTANCE.cmd` wurde als Required Gate entfernt. `QIKVRT.cmd acceptance` ist der Windows-Acceptance-Einstieg.

English: `RUN_WINDOWS_ACCEPTANCE.cmd` was removed as a required gate. `QIKVRT.cmd acceptance` is the Windows acceptance entrypoint.


## DE: Windows-Bootstrap-Pflicht / EN: Mandatory Windows bootstrap

DE: `QIKVRT.cmd` erzwingt Administratorrechte, persistiert zuerst Urheber-/Lizenzakzeptanz und Repository-GUID, installiert oder nutzt danach Chocolatey und loest weitere Windows-Abhaengigkeiten zur Laufzeit ueber Chocolatey auf. Der Default-Modus ist `deploy`.

EN: `QIKVRT.cmd` enforces administrator rights, first persists authorship/license acceptance and repository GUID, then installs or uses Chocolatey and resolves further Windows dependencies at runtime through Chocolatey. The default mode is `deploy`.

## V2.13.4 Mutable State Integrity Repair

DE: Lizenzakzeptanz, GUID, Zielkonfiguration und Onboarding werden vor Deploy persistiert, aber nicht als immutable Release-Dateien in SHA256SUMS.txt gefuehrt. Dadurch bleibt SHA256SUMS auch nach Setup korrekt.

EN: License acceptance, GUID, target configuration and onboarding are persisted before deployment, but are not listed as immutable release files in SHA256SUMS.txt. Therefore SHA256SUMS remains valid after setup.

## QV2134E Deploy Token Property and AV-Safe Bootstrap Repair

- `tools/gh_deploy.ps1`: `Normalize-GitHubHeaderToken` now always returns an object with `token` and `removed`, including empty input; this closes the PowerShell StrictMode `.token` property failure.
- `QIKVRT.cmd`: AV-safe default entry point; no automatic elevation and no `ExecutionPolicy Bypass`.
- `tools/choco_bootstrap.ps1`: no remote Chocolatey installer via `DownloadString`/`Invoke-Expression` in the default path; existing Zig/Clang/MSVC candidates are preferred; package installation requires explicit `QIKVRT_ALLOW_PACKAGE_INSTALL=1`.
- Boundary: sandbox static verification only; external Windows GitHub upload retest remains pending.

## QIKVRT V2.13.4R Node Deploy Repair

This node-only repair changes deployment semantics from local GitHub Release REST create/upload to local `git` commit/tag/push. The target repository workflow `.github/workflows/qikvrt_node_release.yml` creates or updates the GitHub Release and uploads `qv2134_node.zip` plus its SHA256 sidecar. The local token is used only for Git transport and is not persisted.


## QIKVRT V2.13.4R Node Git Idempotent Tag Push Repair

This node-only follow-up keeps the V2.13.4K transport architecture: local deployment uses Git commit/tag/push, while GitHub Actions in the target repository creates/updates the public release and uploads the node asset.

V2.13.4R repairs the Windows PowerShell 5.1 native-command stderr misclassification observed during `git checkout -B main`. Git commands in `tools/gh_deploy.ps1` are now executed through `System.Diagnostics.Process`; stdout/stderr are captured as text and only the native process exit code decides PASS/BLOCK.


## QIKVRT V2.13.4R Node Git Idempotent Tag Push Repair

This node-only follow-up preserves the V2.13.4K/L transport architecture: local deployment uses Git commit/tag/push, while GitHub Actions in the target repository creates/updates the public release and uploads the node asset.

V2.13.4R repairs the fresh-repository remote-origin path. `git remote get-url origin` may legitimately return `error: No such remote 'origin'` immediately after `git init`; the deploy script now treats that as the normal `remote add origin` path instead of a PowerShell terminating error.


## QIKVRT V2.13.4R Node Git Idempotent Tag Push Repair

This node-only follow-up preserves the V2.13.4K/M transport architecture: local deployment uses Git commit/tag/push, while GitHub Actions in the target repository creates/updates the public release and uploads the node asset.

V2.13.4R repairs potential hanging Git processes. Git commands are executed noninteractively with timeout. Push authentication uses a per-process `http.extraheader`; no AskPass token file is created and Git Credential Manager is not allowed to open an interactive prompt.


## QIKVRT V2.13.4R Node Git Idempotent Tag Push Repair

This node-only follow-up repairs the V2.13.4N scalar-return bug in PowerShell helper functions. Internal `Invoke-GitChecked` output is now suppressed where a function must return only one value. This prevents archive path arrays from being coerced into invalid Windows paths such as a pseudo-drive named ` C`.


## QIKVRT V2.13.4R Node Git Idempotent Tag Push Repair

This node-only follow-up makes repeated deploy attempts tolerant at the local tag boundary. A local release tag already pointing to `HEAD` is reused and does not block the push. Differing local or remote tags remain protected unless `QIKVRT_FORCE_TAG=1` is set intentionally.


## QIKVRT V2.13.4R Node Forward-Only Tag/Branch Conflict Repair

V2.13.4R keeps the general node-only, Git-push-triggered release architecture from V2.13.4Q but moves the default node release tag forward to `v2.13.4-node-r`. This avoids overwriting the already-public `v2.13.4-node` release while preserving the committed-artifact hash parity policy. If the target deploy branch is non-fast-forward, the deploy path falls back to `qikvrt-node/<tag>`; if that branch already diverged, it uses a HEAD-suffixed conflict branch and still pushes the tag that triggers GitHub Actions.
