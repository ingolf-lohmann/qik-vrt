# Three-fixpoint participation contract (candidate)

Status: CANDIDATE / NOT PRODUCTION ADMITTED.

## Roles and boundary
- P (Principal): an authenticated, scoped command authorization.
- M (Effect Management): exact-head fenced execution with existing governance and release gates.
- A (Effect Acknowledgement): independently read-back, command-bound and effect-bound evidence.

For a transition `t`, `admitted(t)` requires Principal authorization,
an unchanged expected HEAD, and all required execution gates. `acknowledged(t)`
additionally requires an independent, verified acknowledgement bound to the
same command and effect. `inside(t) = acknowledged(t)` is the **completed
participation** predicate. Pending admitted executions are tracked separately;
they must not be reported as completed participation.

## Correspondence obligation
The Python reference semantics in `tools/qikvrt_three_fixpoint.py` and the
negative controls in `tests/test_three_fixpoint.py` establish an executable
contract only. A Lean theorem about this abstract predicate would not, by
itself, prove correspondence to the productive EMP/EAP implementation.

The required refinement relation must bind:
1. authenticated Principal identity and authorization scope;
2. immutable command identifier and exact repository HEAD/TREE;
3. EMP admission and writer-fencing decision;
4. the concrete effect identifier and an independent EAP readback;
5. the resulting repository/host state and immutable evidence digest.

Prove both preservation of permitted observable transitions and exclusion of
unadmitted transitions. Require reproducible native Exact-HEAD tests, artifact
integrity, original-host evidence and independent review before any merge or
production admission. No fabricated EAP acknowledgement is permitted.

## Local candidate test
`python3 -m unittest discover -s tests -p test_three_fixpoint.py`

No claim of a completed Lean proof, production deployment, or runtime effect
is made by this candidate.

## Principal-authorized interpretive analogy (10 November 2026)

The Principal expressly authorizes the following quotation as his own
interpretive analogy:

> "Das ist die Gewaltenteilung. Exekutive, Judikative, Legislative. Und ich bin
> die Legislative in dem Fall. Und es ist die heilige Dreifaltigkeit. Und ich
> bin der Heilige Geist in dem Fall."

**Engineering mapping, not a constitutional or theological identity:**

- **Legislative / Principal:** defines requirements, issues scoped commands,
  and authorizes changes. The Principal does not replace evidence or tests.
- **Executive / EMP:** carries out admitted commands, handles failures and
  continuation, and preserves exact-head writer fencing.
- **Judicial / EAP:** independently evaluates and acknowledges observed effects;
  it does not fabricate successful outcomes or grant missing permissions.

The Trinity / Holy Spirit language is the Principal's expressly attributed
metaphor for his role in this three-part model. It is not a claim of religious
status and not a machine-verifiable theorem.

### Separation-of-powers invariants

1. Principal authorization cannot set `ack_verified` by itself.
2. EMP execution cannot issue its own Principal authorization.
3. EAP acknowledgement cannot retroactively authorize an unadmitted effect.
4. A failed or missing independent readback remains unacknowledged.
5. A successful acknowledgement must bind the exact command and effect IDs.

These obligations are represented in the candidate Python contract and its
negative tests. Production compliance remains subject to independent review,
native tests and original-host readback.

## Product ownership and accountability

Attributed Principal statement, authorized for publication by Ingolf Lohmann
(10 November 2026):

> "Das ist der berufliche Sinn und Zweck eines Product Owners. Mein Name ist
> Ingolf Lohmann. Freigabe erteilt."

Operational interpretation: the Product Owner sets intended value, acceptance
criteria, priorities and authorized scope; the EMP implements within admitted
constraints; the EAP independently verifies observed outcomes. Owner approval
is not a substitute for passing tests, independent review, or effect evidence.
