# QIK-VRT: verbindlicher Fortsetzungsvertrag (PR #655)

Dieser Vertrag ist der stabile Arbeitskontext über ChatGPT-Eingabe-/Ausgabe-Zyklen hinweg. Das Repository ist Authority; Chat-Antworten sind keine Authority. Der Vertrag ist eine Spezifikation, **kein Nachweis seiner vollständigen Implementierung**.

## Ziel und unveränderliche Definition of Done

1. Ein eigenständiger HTML5/React-Client und der ChatGPT-Client verwenden denselben versionierten Terminal-Vertrag; die Darstellung darf keine fremden oder veralteten PR-IDs als aktuellen Zustand ausgeben.
2. Authentifizierte Aufträge passieren den originalen, zugelassenen Universalterminal-/Transputer-Adapter; bei fehlender Zulassung gilt fail-closed.
3. Auftrag -> persistiertes Ereignis -> Repository-native Ausführung -> PR -> exakte native CI -> Governance -> Main -> Host-/Domain-Readback -> EFFECT_ACK sind getrennt belegte Kausalstufen.
4. Die exakte Zieldomäne raumzeitterminal.de liefert die spezifizierte Oberfläche und einen überprüfbaren produktiven Effekt. Ohne Domain-, Host- und Effekt-Readback keine Abnahme.
5. CI-Artefakte, Logabrufdefekte, Integritätsregeneration, Lean-Kernel-Nachweise und Veröffentlichung werden mit exaktem HEAD/TREE und eigenständigen Belegen geführt.
6. Alle schreibenden Fortsetzungen sind repository-native, ereignisgetrieben und ohne externe/interne Timer. Stündliche ChatGPT-Aufgaben sind ausschließlich lesend.

## Deterministische Fortsetzung jedes Chat-Zyklus

1. **READ**: Authority Main, PR #655, exakten HEAD/TREE, Workflow-Runs und Jobs sowie native Terminal-Admission rücklesen. Veraltete gespeicherte SHAs nie als aktuell ausgeben.
2. **DIFF**: Ist-Zustand gegen die sechs DoD-Gates und zuletzt persistierte Belege vergleichen; zuerst den frühesten kausalen Blocker bestimmen.
3. **ACT**: Einen nachgewiesenen, sicher ausführbaren Repository-Fix ausführen; keine Secrets auslesen, keine unzugelassene Produktionswirkung behaupten.
4. **VERIFY**: Den neuen Commit und dessen exakte CI prüfen. Bot-Commits mit `action_required` nicht als Testnachweis werten. Log-404 von Testfehler trennen.
5. **PERSIST**: Diagnose, Änderungsreferenz, Prüfergebnis und nächsten kausalen Schritt im Repository nachführen; unverifizierte Gates explizit offen lassen.
6. **REPORT**: Im Chat nur nachweisbare Änderungen und den laufenden Stand anzeigen. Zwischenbericht ≠ Abschluss; niemals `DONE` ohne sämtliche Gates.

## Zustandsmodell

`UNVERIFIED -> OBSERVED -> RUNNING -> PASSED | FAILED | BLOCKED`.

Ein Gate ist nur `PASSED`, wenn sein eigener unveränderlicher Nachweis vorliegt. Die Gesamtzustandsfunktion ist `DONE` genau dann, wenn **alle** sechs DoD-Gates durch Readbacks erfüllt sind; andernfalls `IN_PROGRESS` oder `BLOCKED`. Keine Schlussfolgerung von CI-Erfolg auf produktiven Effekt.

## Aktuelle bekannte Risiken (nicht als Live-Status verwenden)

- PR #655 ist Draft; ein vollständig zugelassener Original-Terminal-Adapter und produktiver Effekt sind nicht belegt.
- Die Integritätsregeneration erzeugt Bot-Commits, deren Folge-Workflows `action_required` erhalten können. Erneutes Triggern ist eine Zwischenmaßnahme, keine endgültige Lösung.
- Die vorhandene HTML-Datei ist bislang Vanilla-JavaScript, nicht die geforderte eigenständige React-Implementierung.
- Die Bridge liefert derzeit `503 ORIGINAL_TERMINAL_TRANSPUTER_ADAPTER_NOT_ADMITTED` für Mutationen. Das ist korrektes Fail-Closed-Verhalten, aber keine fertige Auftragseinreichung.

**Autoritative Aktualität:** Live-Zustand immer aus GitHub-/Native-Readbacks, niemals aus dieser Momentaufnahme ableiten.
# Versioned common-workspace intake — 1 November 2026

The existing `QIKVRT workflow executor` consumes only task IDs admitted in
`state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json#/workspace_task_intake`.
It reads the task's current version and complete canonical UTF-8 payload from
the established common workspace. The source permit is coordination only;
task prose, subsequent editor updates and a receipt grant no productive rights.
The original native Terminal/Transputer and all separately admitted effect
workflows retain their existing boundaries. No scheduler is added.

The existing Site exposes `GET /api/v1/authority/tasks/{id}` and
`POST /api/v1/authority/acceptances`. Its service identity is a short-lived
GitHub Actions RS256 OIDC token with the exact Site audience, repository ID,
Owner ID, Main ref, workflow path, workflow SHA, run ID and attempt. The Site
independently reads executing-run metadata and current Main/commit/tree, verifies
the exact source-contract bytes and reobserves Main before admission. This
uses job-scoped `id-token: write`, `contents: read` and `actions: read`; it exports
no visitor session or long-lived credential. Missing issuer/API/storage access
is UNVERIFIED/HOLD, not an empty task list or successful adoption.

Workload tokens use the explicit `X-QIKVRT-Workflow-Identity` header admitted
by this same source contract. Standard `Authorization` remains the platform's
identity namespace. The first actual Main run41284897131 failed HTTP403 before
any independently observed acceptance (issue662); its original log/artifact
remain failure evidence. Missing receiver logs do not identify the denial's
origin. The existing client now retains request stage and allowlisted error
code, plus boolean declared-claim comparisons labelled NOT authentication.
Never persist the JWT, request credential, raw error message or private claims.

The actual receiver also requires runtime-level outbound-fetch controls: Workerd
rejects `redirect: error` before sending. Receiver v14 preserves the verified
`manual` repair and rejects every redirect. Its original Workerd regression,
original native HOLD artifacts and independently observed public API quota denial
are retained under the existing native-identity-repair evidence directory.
Only fixed public source labels, numeric upstream status and explicit zero quota
may extend the native denial boundary. Unknown fields, response messages, tokens
and observation clocks cannot enter it. Owner-only `get_context` diagnostics do
not grant workflow or productive authority; an exhausted REST quota remains HOLD
until a fresh source read succeeds. A source repair never closes issue #662.

Acceptance is keyed by task ID and exact version, binds its canonical payload
SHA-256 and actual accepting run/HEAD/TREE/contract, and is stored transactionally
with one journal event. Concurrent duplicates return the original receipt.
A version change between reading and acceptance is rejected. A later version
requires a fresh read and its own receipt; the old record remains historical.
After an uncertain POST, a successor reads the task first. Tokens and original
task text do not enter public workflow artifacts or this repository.

The original authenticated MCP `get_task` returns `workflowAcceptance` only for
the currently read task version. An independent member must read that stored
receipt and cross-check the actual GitHub run and original artifact before
claiming the handover gate closed. Local tests, Site publication, source merge,
workflow success and the producer's own GET do not alone close that gate.
Every receipt keeps `productive_effect_verified=false` and `effect_ack_done=false`.
The static client release's remaining gates and productive DoD remain open.

The client-side Authority GET uses the original job token and `gh api --include`
to distinguish a denied Main ref, commit, role policy, governance policy or
CODEOWNERS read. Its HOLD artifact retains only that fixed resource label,
HTTP status and bounded numeric rate-limit remaining/reset and Retry-After
headers. A generic 403 is not classified as quota exhaustion without the quota
observation. Provider bodies, arbitrary headers and raw stderr are never copied.
Exhaustion requires quota reset **and a fresh original readback**; this diagnostic
does not schedule retries, admit stale Main, change roles or grant any effect.

Human direction and authorization: Ingolf Lohmann. Implementation and isolated
verification: OpenAI Codex. This source contract does not attest a new human
inspection, Claude adoption, platform protection or productive-domain effect.
