# QIK-VRT Repository Status and Stall-Detection Policy v1

Status: normative repository policy
Authority repository: `Goldkelch/qik-vrt`
Mirror repository: `ingolf-lohmann/qik-vrt`

## Purpose

Every repository-status inspection must distinguish real progress from mere activity and must explicitly detect and report a stall relative to the immediately preceding verified observation.

## Mandatory observation scope

At minimum, inspect and compare:

- tracked issues and pull requests;
- associated branches and head/base SHAs;
- new commits and material changes;
- issue, PR, review and bot comments;
- GitHub Actions workflow runs, jobs, steps, conclusions and artifacts;
- required checks and mandatory gates;
- claim inventory state;
- Lean-kernel receipts and proof-object evidence;
- traceability and provenance bindings;
- Authority/Mirror content equality and synchronization evidence.

## Allowed report categories

Every report must use exactly one primary category:

1. `Auftrag angenommen`
2. `Arbeit begonnen`
3. `Teilfortschritt`
4. `Blocker`
5. `Stillstand`
6. `vollständig kernel-verifizierter Abschluss`

## Stall rule

`Stillstand` is mandatory when no new, content-relevant reaction or status progress exists compared with the previous verified observation.

A stall report must state:

- that no content-relevant change was found;
- the compared previous observation or baseline;
- the inspected objects;
- the reason no observed activity qualifies as progress;
- any continuing blocker that explains the stall.

Routine bot noise, repeated comments, identical workflow reruns, unchanged `action_required`, unchanged failures, unchanged branch heads and metadata-only updates do not constitute progress.

## Reflexive handling of a delivery failure

While an authorized delivery obligation remains open, a broken transition that
prevents its required evidence or effect from being delivered is an error and
must be fed back into the existing diagnosis/repair/readback path. The error
record binds the expected output, exact subject, first evidenced failing edge,
available receipts, owner authorization, retry condition and next work unit.
Producing another status message or repeating the same failed observer does
not discharge the delivery obligation.

An observer that cannot read its subject records `OBSERVATION_FAILED` with
`HOLD` and unknown live progress. It does not infer a whole-pipeline stall from
inaccessible data. Likewise, no active runner alone does not prove a delivery
failure: compare the open obligation with the preceding bound observation.
Historical persistence remains valid historical evidence, without being
transferred into fresh-head acceptance.

This operational clarification was authorized by Product Owner Ingolf Lohmann
on 2026-09-30. Verification of the repair and delivery remains mandatory.

## Progress rule

A report may classify `Arbeit begonnen` or `Teilfortschritt` only when new evidence changes the technical, scientific, verification or synchronization state. The report must identify the exact object, SHA, run, receipt or artifact that changed.

## Fail-closed completion rule

No report may claim `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE` or `vollständig kernel-verifizierter Abschluss` unless all of the following are simultaneously evidenced and bound to the exact candidate:

- complete claim inventory;
- native Lean-kernel receipts for every formally proved claim;
- complete source-to-claim-to-proof traceability;
- green mandatory repository gates on the exact head;
- verified Authority/Mirror synchronization and content equality.

Required invariants:

- `NO_COMPLETE_CLAIM_INVENTORY_NO_FINAL_PASS`
- `NO_KERNEL_RECEIPT_NO_FORMAL_PROOF`
- `NO_TRACEABILITY_NO_FINAL_PASS`
- `NO_GREEN_MANDATORY_GATES_NO_FINAL_PASS`
- `NO_AUTHORITY_MIRROR_EQUALITY_NO_FINAL_PASS`
- `NO_BASELINE_COMPARISON_NO_STALL_DECISION`

## Reporting contract

A status response must include:

- primary category;
- relevant change: yes/no;
- stall: yes/no;
- concise evidence;
- explicit reasoning;
- completion-gate state.

When there is no relevant change, silence is forbidden: the response must explicitly report `Stillstand` and its reason.

## Repository architecture priority

This policy is intended to be consumed by repository-native workflows and issue-agent logic. Future automation should persist each observation as a machine-readable snapshot, compare it with the prior snapshot, and derive the category deterministically before emitting a human-readable report.


## Pipeline reliability measurement (owner directive, 2026-09-30)

This section specifies the next implementation of the existing stall detector.
Its presence is NOT evidence of deployed instrumentation or node-wide adoption.
Human contribution: Ingolf Lohmann requested per-node stall frequency/duration
and initially MTBF as the sole optimization objective. The subsequent owner
instruction expands this to the KPI tree below. AI contribution: operational
definitions, evidence constraints and acceptance cases below.

### Objective and invariants

Use the non-compensatory KPI tree in `policy/PIPELINE_KPI_TREE_V1.json`.
MTBF remains a reliability indicator, but is no longer the sole optimization
objective. Compare under the SAME declared workload, service obligation,
measurement coverage, stall threshold and recovery criterion.
Correctness, TEMDD evidence, authorization, security, losslessness and existing
required gates are hard feasibility constraints, not competing score weights.
Do not improve the number by rejecting work, reducing coverage, weakening gates,
lengthening timeouts, relabeling an outage as idle, or leaving an incident open.
MTTR and downtime remain compulsory diagnostics; a candidate with worse
availability or longer recovery is not admitted as a reliability improvement.
A claim of statistically established improvement requires a declared comparison
method and sufficient exposure; a small-sample point estimate is descriptive only.

### Scope and clocks

Each record binds node ID, repository, scope/work-unit, exact HEAD AND TREE,
evaluator commit/tree, policy version/hash, observer ID, source event IDs,
source timestamps, observation timestamp and measurement window.
Run evidence additionally carries run ID, attempt, event, workflow and actual
checkout scope. A trusted-main observer is not a candidate test.
Use UTC for persisted event times, monotonic clocks for local elapsed durations;
reject negative intervals, clock rollback and incompatible clock epochs.
Polling gives bounded onset/recovery intervals, not invented exact timestamps.

### State and incident semantics

Keep separate states: PRODUCTIVE, IDLE, WAITING_WITHIN_CONTRACT,
STALLED, BLOCKED and OBSERVATION_UNKNOWN.
IDLE requires positive evidence of no owed work; an empty or inaccessible query
does not prove idle. Pending admission is not productive execution.
A pipeline failure begins when an owed, declared progress/effect deadline is
missed. Authorized waiting is separately visible; it becomes a service failure
if the declared delivery obligation is missed, without bypassing its gate.
A failed subjob is not automatically a pipeline failure if redundant processing
continues to satisfy the same obligation.

Heartbeat, comments, retries, commits and a successful observer do not reset the
progress deadline. Only a validated semantic checkpoint satisfying the declared
obligation qualifies. Close an incident only after the same work scope has a
verified progress/effect readback and the versioned recovery criterion is met.
Repeated observations of one incident increment its duration, not failure count.
Overlapping per-work-unit stalls use union duration at node level; retain
individual incidents. A node-level incident ends only when all missed node
obligations have recovered. Mesh failure uses its declared end-to-end service
predicate, never the sum or mean of node MTBFs.

Persist incident IDs, onset/recovery bounds, cause status (UNKNOWN until proven),
last useful checkpoint, pending work, current age and evidence references.
Restarts replay the durable append-only ledger idempotently. HEAD mutation starts
a new validation subject but does NOT erase operational downtime or reset the
incident. Link successor records for operational continuity; never transfer
candidate validation (PREDECESSOR_EVIDENCE_TRANSFER=false).

### Computation and uncertainty

For a declared, fully observed service window:
- failure_count = distinct node-level transitions into pipeline failure;
- operating_seconds = known available service time, excluding downtime;
- MTBF_seconds = operating_seconds / failure_count, if failure_count > 0;
- downtime_seconds = union of failed-service intervals, including open incidents
  clipped at the window end;
- MTTR_seconds = sum of fully observed completed recovery durations /
  count of those recoveries (report open/censored cases separately);
- observed_availability = operating_seconds /
  (operating_seconds + downtime_seconds), when the denominator is positive.

Report eligible service seconds, known observed seconds, idle seconds,
authorized-wait seconds and unknown seconds separately. Overlapping concurrent
jobs must not multiply node exposure. Readiness exposure during idle may count
only under an explicit service contract with independent readiness evidence;
otherwise label the estimate active-workload-only.

Zero observed failures means MTBF=null, status=NO_FAILURE_OBSERVED and recorded
exposure; never infinity or proven reliability. Unknown intervals must not
silently count as uptime or downtime. A window crossing a telemetry gap is
INCOMPLETE; retain coverage and bounds and do not rank it as an improvement.
An incident already open at window start is left-censored and is not a new
failure; disclose it and do not fabricate its onset. A still-open incident is
right-censored, keeps increasing in age and cannot disappear from reporting.

HTTP 404 from the external observer is OBSERVATION_UNKNOWN for the target node
unless independent evidence proves a pipeline failure. Record observer
availability separately, including failure to persist telemetry.
Use a repository-native monitor with independently scheduled observation and
durable storage; a process unable to observe its own death cannot certify uptime.

### Required implementation and acceptance

Extend the existing repository status/watchdog and ledger path, not a parallel
controller. Every registered node must independently publish a bound adoption
receipt and measured window; missing nodes remain UNKNOWN. A Mirror record does
not establish Authority adoption. Keep node and Mesh scope distinct.

Required executable tests before activation:
1. Regular idle produces no failure.
2. Owed work crossing its deadline creates exactly one incident.
3. Repeated polls/retries/noise do not reset onset or increase failure count.
4. Same-scope verified recovery closes it; unrelated green runs do not.
5. An open incident contributes downtime through window end.
6. Observer 404, incomplete pagination and telemetry gaps remain UNKNOWN.
7. Duplicate/out-of-order events, process restart and replay are deterministic.
8. HEAD/TREE changes retain operational history but invalidate candidate evidence.
9. Concurrent stalls use union durations; cross-node incidents are not summed
   into Mesh MTBF.
10. Zero failures, zero exposure, left/right censoring and clock rollback are
    handled explicitly.
11. A benchmark with reduced work, relaxed thresholds, missing nodes, worse
    recovery or weaker mandatory gates cannot win the optimization comparison.
12. Kill the pipeline and separately kill its observer; independently verify
    detection, durable recording, restart/replay and real work recovery.

Reference definitions:
https://www.ibm.com/think/topics/mttr-vs-mtbf
https://cloud.ibm.com/docs/resiliency?topic=resiliency-understanding-ha

Activation requires executable instrumentation, the tests above, repository
integrity materialization, exact-head gates and per-node readback. Until then:
SPECIFICATION_CANDIDATE; INSTRUMENTATION_NOT_VERIFIED; MESH_ADOPTION_NOT_VERIFIED.

## KPI tree expansion (subsequent owner directive, 2026-09-30)

Machine-readable authority for this candidate: `policy/PIPELINE_KPI_TREE_V1.json`.
This supersedes the earlier MTBF-only ranking and preserves the incident semantics
above. The root is **verified, timely, reliable fulfillment of service obligations**.
The tree is a diagnostic hierarchy, not a proved causal model or weighted score.

| Branch | Indicators |
| --- | --- |
| Nachgewiesene Auftragserfüllung | Fristgerechte Effekte; Verifizierter Durchsatz; Ende-zu-Ende-Latenz; Überfällige Aufträge |
| Verfügbarkeit und Stillstand | Beobachtete Verfügbarkeit; Mittlere Betriebszeit zwischen Ausfällen; Ausfallhäufigkeit; Stillstandsdauer; Alter offener Störungen; Wiederholungsfehler |
| Erkennung und Wiederherstellung | Erkennungszeit; Wiederherstellungszeit; Lange Wiederherstellungen; Autonome Wiederherstellung; Verlustfreie Wiederaufnahme |
| Fluss und Kapazität | Wartezeit bis Ausführung; Offene Arbeit; Ältester offener Auftrag; Wiederholungsaufwand; Ressourcenauslastung; Skalierungseffizienz |
| Korrektheit und Änderungssicherheit | Verlorene Effekte; Doppelte Effekte; Fehler nach Freigabe; Änderungsbedingte Ausfälle; Einhaltung verbindlicher Gates; Unzulässige Wirkungen |
| Messqualität und Selbstbeobachtung | Beobachtungsabdeckung; Vollständige Evidenzbindung; Alter der Telemetrie; Verfügbarkeit des Beobachters; Dauerhafte Messwertspeicherung |
| Mesh-Zusammenarbeit | Aktive Metrik auf allen Nodes; Verifizierte Übergaben; Übergabezeit bis Wirkung; Konsolidierungszeit; Fehlerisolation |

Every indicator declares its unit, definition, data source and direction.
Targets are explicitly UNSET, not fabricated. Bind targets, measurement windows,
service population and allowable tradeoffs in a versioned service contract before
issuing an SLO verdict. Emit descriptive values and uncertainty before that point.
No denominator, no numerical ratio; no observed failures, no infinite MTBF.
Keep incomplete observations and unfinished obligations visible.

Optimization order: valid evidence -> hard correctness/authority constraints ->
recovery of breached user-facing service obligations -> comparable service-SLO
vector -> Pareto improvement. No universal weighted score may conceal a failed
gate, missing node, unresolved incident or worsened delivery obligation.
Only owner-approved explicit budgets permit a tradeoff. Independent Mesh
service measurement is required; do not average node MTBFs or percentiles.

This change defines 7 branches and 37 indicators. It is a specification candidate;
it does not install collectors, validate runtime performance or establish adoption.

### Bounded executable successor: telemetry freshness

The existing read-only watchdog now exposes `telemetry-freshness`. It reads
`evidence/node_health/LATEST.json` from the explicitly supplied commit/tree and
requires its bytes to match `evidence/node_health/<run_id>.json` in that same
subject. `--run-id` selects one historical run receipt directly. Working-tree
receipts are never substituted. No other KPI or node adoption is measured.

```sh
python3 -B tools/qikvrt_reflexive_repository_watchdog.py telemetry-freshness \
  --expect-head "$(git rev-parse HEAD)" \
  --expect-tree "$(git rev-parse HEAD^{tree})" \
  --repository ingolf-lohmann/qik-vrt \
  --now "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
```

`--now` is the explicit readback clock input; its independent accuracy is not
certified by this collector. Repeating the same subject, evaluator bytes and
clock produces identical canonical JSON. Capture a new clock for a new observation.
The record binds source and policy bytes, evaluator bytes and committed identity
(or explicitly labels an uncommitted evaluator), node identity and measurement time.

Age is readback time minus `heartbeat_utc`. FRESH requires
`heartbeat_utc <= readback_time < expires_utc`; equality at expiry is STALE.
Expiry describes the source's existing lease, not a newly invented SLO.
Missing evidence/timestamps remain UNKNOWN; malformed, contradictory or future
clocks produce INVALID measurement status and UNKNOWN freshness. Raw receipt
fields and any independently computable age remain visible; neither file mtime
nor a zero value repairs missing timestamps. `value=null` on unknown/invalid data.
`target=null`, `UNSET_REQUIRES_VERSIONED_SERVICE_CONTRACT` and SLO verdict UNKNOWN
remain unchanged. General instrumentation, rollout and the other 36 KPIs remain
unverified. Regression acceptance is wired into the existing Makefile and watchdog
test paths; the collector itself performs no dispatch, write, push or network access.
The existing `PIPELINE_KPI_TREE_V1.json.record_contract` is checked on every
regression observation. FRESH, STALE, UNKNOWN and INVALID outputs must survive
JSON serialization/deserialization with identical canonical bytes. Invalid UTF-8,
duplicate keys, non-finite numbers, unencodable strings and excessive nesting
remain unmeasured with the exact input blob identity retained.
