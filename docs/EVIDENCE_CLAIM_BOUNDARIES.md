# Evidence claim boundaries

This document applies the QIK-VRT evidence rule that **model, formal proof,
cryptographic/protocol validation and observed runtime effect are separate claim
layers**.

Evidence MUST NOT be promoted from one layer to another merely because the
layers describe the same architectural idea. Evidence also MUST NOT be reused
across Git heads, pull requests, runtime subjects or environments without an
explicit rebinding proof.

The machine-readable normative companion is
`interfaces/evidence-claim-boundaries-v1.json`.

## 1. Model / architecture

A model can establish definitions, architecture and model-local dependency
relations. It does not by itself establish that a theorem has been kernel
checked, that a cryptographic transition is valid, that an implementation
conforms to the model, or that a productive effect occurred.

## 2. Formal proof

A formal claim is limited to the exact theorem statements accepted by the
specified proof kernel for the exact source, dependencies and toolchain that
were checked.

Definitions alone are not proof. A theorem about an abstract model is not an
implementation-refinement proof unless such a refinement theorem is itself
present and kernel checked.

## 3. Cryptographic and protocol validation

Protocol validation requires the checks claimed by the protocol, including
canonical serialization, actual digest computation, required input/policy/
evidence/predecessor bindings, authentication, freshness and independent state
re-derivation.

The following are explicitly insufficient as substitutes:

- checking only that a purported digest has 64 characters;
- accepting a caller-supplied `acknowledged=true`;
- accepting a list merely because it has the expected length;
- accepting duplicate clause identifiers where completeness requires a unique
  clause set.

A digest can bind bytes. It does not prove the semantic truth of those bytes.

## 4. Runtime effect

A runtime-effect claim requires an independently observed readback bound to the
exact runtime subject. Where EAP applies, this includes the relevant
principal/request/subject/input/epoch bindings and the native receipt/readback
required by the active profile.

A local test, repository integration, successful workflow, hash-chain check or
formal proof is not a productive effect.

In particular, no merge, deployment, publication or `EFFECT_ACK_DONE` may be
inferred unless that exact effect has its own bound evidence.

## Non-transfer rule

The default rule is fail-closed:

> No evidence transfer between claim layers, Git heads, PRs, runtime subjects or
> environments without an explicit proof that binds the source evidence to the
> target claim.

This rule is intended to prevent accidental strengthening of a valid narrow
claim into a broader unsupported one.
