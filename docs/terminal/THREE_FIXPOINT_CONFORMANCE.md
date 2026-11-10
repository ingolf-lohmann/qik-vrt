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
