# QIK-VRT controlled assessment, risk and operating procedure

Revision: 2026-10-22. Responsible project Principal/Product and Code Owner:
Ingolf Lohmann. Status: engineering procedure candidate under the Principal's
instruction to close the AI Act gaps. This is not a legal opinion, an accepted
QMS, a declaration of conformity or proof of deployment.

## 1. Scope and authority

Reuse `system-boundary.md`, `classification-memorandum.md`, the existing
requirements/control register and `tools/qikvrt_eu_ai_act_evidence_gate.py`.
The initial assessed implementation is the unchanged core/Personal integration
at a8017ab67824f01ec4d215cf7af83b8b0779283c, tree
94317a4da76fac49b63bb129badcbbd21471c092. New assessment tooling has its own
candidate content hashes and test receipt; it is not retrospectively part of
that source revision. The two originally reviewed HTML files are unresolved.

Principal instruction, received in this interaction on 2026-10-22: save the
review only as an intermediate state, close the gaps and remain interoperable
with internal and external change. Attribution: Ingolf Lohmann, Principal.
This records conversational authorization; no handwritten, biometric or
cryptographic signature is claimed.

Project governance is distinct from legal role allocation. The Principal owns
scope decisions and project release approval. Engineering produces exact-bound
source/test records. A competent accountable reviewer decides legal applicability
and the selected conformity route. Provider/deployer legal entities, designated
operational staff and their competence/authority evidence remain OPEN; names
must not be invented or appointments inferred from source ownership.

## 2. Change control and continuity

Before each assessment, record the independently observed source commit/tree,
purpose digest, model, data and deployment configurations and law revision.
Invoke the existing evidence gate with an explicit bundle and observed subject.
Any change to those inputs invalidates dependent predecessor records. A material
incident, supplier/IdP/model change, new affected group or legal change requires
the same reassessment. No timer, silent N/A or reset of history substitutes for it.

Preserve original records and append a successor referencing the predecessor.
Determine impacted requirements, re-run the appropriate tests, obtain accountable
decisions, and independently re-read deployed effects. A code fix, marker match,
old approval or process exit zero never authorizes conformity or productive use.

`BINDINGS_VALID` means byte/context references are consistent, including when a
receipt's contents are untrue. Authenticity, test execution, legal correctness,
completeness and effective operation need separate review and evidence.
Run file-binding inspection against a stable read-only source snapshot. The
validator does not fence concurrent filesystem writers or make the filesystem
immutable; production fencing remains an independent runtime control.
Green-claim warning terms are conservative lexical checks: quotations and
negations containing those terms can also require review. They do not implement
a semantic legal-language classifier or guarantee detection of every paraphrase.
`BINDINGS_INCOMPLETE` retains known open gaps; `BINDINGS_INVALID` rejects a
contradiction, unsafe reference or stale proof. None is a legal conformity PASS.

## 3. Risk methodology and acceptance

For every intended use and reasonably foreseeable misuse identify hazards,
affected persons, severity, likelihood, supporting facts, owner, mitigation,
verification, remaining risk and overall interaction with other controls.
Consider health/safety/fundamental rights, minors and vulnerable groups.
Severity 1–5 ranges from negligible reversible inconvenience to catastrophic
harm. Likelihood 1–5 ranges from rare under documented conditions to frequent.
The product of the estimates is an engineering prioritisation aid, not an
empirical probability or legal acceptance finding.

Unknown likelihood, severity, affected groups or control effectiveness stays
OPEN and blocks risk acceptance. Scores 10–25 require mitigation and re-review;
5–9 require mitigation and explicit accountable review; 1–4 are candidates for
acceptance only after effectiveness evidence and a reasoned residual-risk
decision. No score auto-accepts a legal prohibition, serious safety/fundamental
rights risk or the combined residual risk. Record alternatives and prefer risk
elimination by design, then safeguards, then operator information/training.

The initial hazards in `AI_ACT_EVIDENCE_BUNDLE.json` are identified engineering
risks; all estimates, effectiveness and residual-risk decisions are OPEN. Review
on each material change, risk signal, corrective action or release, and at a
documented management review. No historical review cadence proves execution.

## 4. Data and supplier inventory

Inventory the actual models, datasets and configurations for each deployment:
provider/version, origin/rights, collection purpose, processing location,
recipients, affected groups, quality/representativeness/bias limitations,
access/retention and change owner. Distinguish training, validation and testing
data. This candidate adds no model training. Its unit tests use synthetic
temporary receipts; those fixtures are not production data or legal decisions.
The initial repository inventory concerns source and documentation only;
connected-model/provider, production dataset and contractual inventories remain
OPEN. Do not infer absence from a missing inventory or copy secrets into it.

Before supplier/model replacement verify interface compatibility, provenance,
rights, required downstream information, security/data responsibilities and
impact on the intended purpose. An OIDC login does not confer model entitlement.

## 5. Human oversight and operator instructions

Show system/model identity, intended purpose, known limits, uncertainty and
whether an item is a proposal, admitted instruction, execution or verified effect.
Operators inspect the actual evidence and can refuse, escalate, override or stop
within their authenticated authority. Never present a recommendation as a human
decision or encourage blind repetition after an unchanged error.

The original ledger provides `Ledger.stop`, replay and writer/subject checks.
Source presence does not establish an accessible authenticated operator stop.
Before operation demonstrate authorised stop to a safe state, denial of an
unauthorised stop/override, revocation, interrupted-effect accounting and safe
recovery on each actual host. Preserve ambiguous acknowledgements and reconcile
by readback before retry. No destructive reset, purge or reconstructed journal
may stand in for recovery. Operator training covers automation bias, limitations,
anomalies, intervention and escalation; retain exercises and competence records.

For controlled test-only review, execute the evidence gate and inspect OPEN/
BLOCK findings. If purpose, role or a required safety/control test is unresolved,
do not infer readiness for regulated production use. No blanket prohibition or
classification of other QIK-VRT editions is made by this scoped procedure.

## 6. Logging, retention and incident handling

Define required events per applicable purpose, including identity/role, source
and subject, timestamps, decisions, evidence digests, actions, interruption,
revocation, ambiguous outcome and independent readback. Exclude credentials,
raw biometric templates and unnecessary personal content. Use the existing
native ledger and admission controls; no parallel production journal is added.

Set purpose-specific retention/access/legal-hold/deletion policy after the legal
and data-protection decision. Where Art. 19 applies, account for the statutory
minimum and applicable exceptions; do not turn it into a global hard-coded
retention period. Do not delete existing original journals under this procedure.
Test durable restart, log coverage, access, tamper detection, export/retrieval,
legal hold and authorised expiry/deletion using disposable fixtures first.
Hash verification alone is not immutable storage, writer fencing or archival
availability. Production retention and disaster-recovery evidence remain OPEN.

For an incident: preserve exact-subject evidence privately; contain affected
operations through the admitted path; assess severity, affected persons and
applicable notification duties/deadlines; assign corrective action; verify the
original failure and residual effects; record closure and revisit risk/control
and supplier records. Notification routing/legal deadlines must be decided
under the current law for the actual provider/deployer and incident; the tool
does not infer them. Do not send notices or disclose evidence without authority.

## 7. QMS and release evidence

Maintain controlled design/change records, verification/validation criteria,
supplier/data controls, risk management, monitoring, incident/corrective action,
authority communication, document retention, resource and accountability records.
These address topics for the Art. 17 assessment, not a completed statutory QMS.
The licensed EN 18286 text and any presumption of conformity are separate routes;
no clause-level standard compliance is asserted without the licensed assessment.

For each applicable requirement retain implementation location, exact build,
test/environment/metrics/thresholds, current operational readback, limitations,
reviewer and dated residual-risk decision. Determine Art. 43 procedure first;
obtain notified-body evidence only where required. Complete applicable
declaration, marking, registration, transparency and post-market obligations.
Release needs the existing protected review/check and host acceptance path.

## 8. Legal reference boundary

Reference: Regulation (EU) 2024/1689, current consolidated text and applicable
transition provisions. Article-specific decisions remain in the existing
classification memorandum; this engineering procedure does not close them.

- https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-9
- https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-17
- https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-19
- https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-43
- https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50

## 9. Reproduction

`make eu-ai-act-evidence-gate-test` runs the existing gate tests and both the
documentary and typed-binding audit against the captured assessment context.
The captured context is the baseline, not live discovery. Supply a freshly
observed context to detect external/model/configuration changes. An unchanged
captured JSON cannot prove that the live system is unchanged.

`make eu-ai-act-evidence-readiness` uses the same tool with `--require-complete`.
It must fail while any selected binding, applicability or evidence item is OPEN.
This is an explicit readiness checkpoint, not an automatic deployment hook or
legal classifier. Even consistent complete bindings require separate accountable
legal and operational acceptance; no tool exit code grants that acceptance.

Initial machine status: classification OPEN; implementation/control coverage
PARTIAL; original HTML bindings OPEN; model/data/deployment inventory OPEN;
operational and legal acceptance NOT ESTABLISHED. Preserve these duties until
each has its own closure evidence. Overall COMPLIANCE_NOT_ESTABLISHED.

The candidate includes a source-bound local receipt for 47 supported original
ledger/terminal/subject-binding tests. It preserves the unsuccessful full native
run and its socket restriction separately. The full `make test` attempt stopped
at a publication-finalizer Git-history dependency; the remaining independent
targets were executed separately. Neither result establishes deployment or
conformity, and neither failed full-run result is relabelled as successful.
