# Versioned V3 review acceptance, version 2

Copyright 2026 Ingolf Lohmann. CC-BY-NC-ND-4.0.

This is an explicitly selected extension of the existing publisher's detached
activation check. It neither activates a contract nor authorizes an upload.
`policy/ZENODO_MACHINE_PROOF_V3_PRODUCTION.md`, the machine-proof policies and
all eight historical policy/schema controls remain unchanged.

| Detached activation schema | Accepted review | Native governance |
| --- | --- | --- |
| `qikvrt_zenodo_v3_contract_activation_v1` | Independent Code Owner, actual `APPROVED`, distinct PR author | Original active ruleset, approval count at least one, Code Owner, stale dismissal and last-push approval |
| `qikvrt_zenodo_v3_contract_activation_v2` with `OWNER_PRINCIPAL_REVIEW` | Exact-head/base Principal decision, actual `COMMENTED`, validated by the existing Owner record and `qikvrt_required_review_gate.py` | Active Main ruleset and strict required `QIKVRT required code-owner review`, integration ID 15368; independently verified native status and trusted Main workflow source |
| The same v2 schema with `INDEPENDENT_NATIVE_APPROVAL` | Original independent approval requirements, plus complete current decisions and no later revocation | Original independent requirements and the same trusted status evidence |

There is no automatic fallback, inferred APPROVED state or conversion of an old
activation into a new one. A Principal-authored PR is permitted only by the
existing explicitly bound Owner decision. An independent reviewer cannot
approve their own PR. A technical disposition cannot satisfy either route.

The activation-v2 file keeps the v1 fields and adds `review_policy`, the exact
`{path,bytes,sha256,git_blob_sha}` identity of
`policy/zenodo-v3-review-acceptance-v2.json`. Its `review` adds `basis` and
`base_sha`. `contracts` has the original eleven controls plus that policy,
the existing review gate, lifecycle policy, original Owner record and trusted
review workflow: sixteen exact identities. The additional policy is byte-pinned
by the existing publisher. No proof, return, historical receipt or upload file
is rewritten to select this route.

The v2 canonical statement is:

```text
ACTIVATE_REVIEWED_V3_PRODUCTION_CONTRACT review_contract=qikvrt_zenodo_v3_review_acceptance_v2 contracts_sha256=<canonical-contract-list-sha256> repository=ingolf-lohmann/qik-vrt pr_number=<n> head_sha=<head> base_sha=<base> review_id=<id> review_basis=<basis>
```

This is a format specification, not an Owner decision. The actual detached
decision must follow the completed exact-head review and merge. The separate
canonical `AUTHORIZE_EXACT_UPLOAD` must still follow activation and candidate
return, bind the immutable proof and exact candidate bytes, and be validated
before any consumption lock or Zenodo call.

The live REST check reads every review/status page within the existing bounded
transport. Duplicate identities, missing pages, a later rejection/dismissal,
revocation, changed HEAD/TREE/base, untrusted status writers and missing rules
block. The latest dedicated status must succeed after the selected review and
before the merge. Its target must resolve to the actual completed successful
Main run of `.github/workflows/qikvrt_required_review_gate.yml`, with Authority
repository/source binding and exact preserved gate/policy/Owner/workflow blobs.
The PR and complete review inventory are reobserved before leaving the gate.
For v2, ruleset targets must explicitly include Main or all branches; an
unresolved `~DEFAULT_BRANCH` alias alone cannot establish Main enforcement.

The existing V3 evidence schema carries the normalized versioned activation.
Recovery phases, canonical exact-upload statement, global create-only remote
consumption ref and decision-derived consumption key remain unchanged across
versions. Re-selecting a review version cannot create another use of a grant.
The existing transport still performs public byte-exact redownload verification.

On the observed Main `b226770c064a167ee3a9cc70996f05db1b3bc6d1`, the two
proof-bearing V3 preparations are the collective-functional-consciousness
article and its separate effective-continuity Gesamtausgabe. Neither has a
live V3 publication manifest or detached activation in the inspected Main
files. The similarly named historical ontology request uses a different schema
and workflow. V1/v2 requests and the PR551 historical Zenodo readback are not
silently migrated. Contract incompatibility is not evidence of a failed upload.

Reproducible regression command:

```sh
python3 -S -B -m unittest -v tests.test_zenodo_machine_proof_policy
```

The existing mandatory evidence-contract test already includes this module.
Fixture publication and recovery are simulations with no external effects.
Source integration, CI, native governance, detached activation, exact upload
authorization and public Zenodo readback remain separate evidence obligations.
