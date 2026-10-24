# TEMDD 1.1 Verification Policy Semantics

Status: `RC1_NORMATIVE_POLICY_CANDIDATE`

## Meta-Axiom

`Verification SHALL be policy-driven, not implementation-defined.`

JSON Schema defines serializable structure. Runtime predicates remain normative evaluator semantics and MUST NOT be inferred from schema validation alone.

## Deterministic evaluation input

A verification decision is a pure function of the complete bound input:

`Decision = Evaluate(Transaction, EvidenceSet, Policy, VerificationContext)`

The VerificationContext MUST bind evaluation time, trust-root set, algorithm profile, canonicalization profile and acceptance evaluator identities. Two conforming implementations receiving byte-equivalent canonical inputs MUST return the same predicate vector and terminal/non-terminal verification result.

## Fresh

`Fresh(E) iff 0 <= evaluationTime - capturedAt(E) <= maxAgeSeconds`

If `requireAfterExecution=true`, evidence MUST be temporally compatible with the bound execution under only the declared clock-skew allowance. Timestamp order alone does not establish causality.

## Trusted

Trust requires the declared evidence class, source/trust-root rules and, when required, a valid signature under an allowed algorithm and key binding.

## Bound

Subject, transaction, execution and required nonce/challenge bindings are independent predicates. Any required mismatch fails binding. Predecessor evidence MUST NOT be rebound to a mutated successor.

## Quorum

Quorum is fixed before EXECUTE. Supported modes are NONE, SINGLE, K_OF_N, MAJORITY, TWO_THIRDS and ALL. A source counts at most once. Evidence failing freshness, trust or binding does not count.

## Deterministic result

Predicate order is:

`FRESHNESS -> TRUST -> BINDING -> QUORUM -> DOMAIN_VERIFICATION -> ACCEPTANCE`

`VERIFIED = conjunction(all required predicates)`

A successful policy evaluation is not itself EFFECT_ACK_DONE. The explicit acceptance transition and all remaining TEMDD_SUCCESS predicates are still required.

## Serialization

TEMDD 1.1 Core uses RFC 8785 JCS plus SHA-256 for policy and verification-context identity.

## Failure semantics

Missing required input fails closed. Re-observation may create fresh evidence; retry does not make stale or compromised bytes trustworthy.

q.e.d.  
Ingolf Lohmann
