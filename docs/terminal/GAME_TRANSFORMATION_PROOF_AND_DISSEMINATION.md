# QIK-VRT — Formal game transformation and information boundary

**Owner:** Ingolf Lohmann. **Status:** candidate, not independently Lean-verified or deployed.

## Verified-by-construction proposition (pending kernel execution)

The bounded two-action example in `formalization/GameTransformationEquilibrium.lean` states:
- Initial utilities: left=1, right=0. Left is an equilibrium.
- Transformed utilities: left=1, right=2. Left ceases to be an equilibrium; right becomes one.
- Two explicit negative equilibrium guards reject false equilibrium claims.
- Two boundary guards reject inconsistent models and unsupported effect claims.

The transformation changes the payoff model. It does **not** establish physical retrocausality, superdeterminism, or a causal effect on earlier events. Any future interpretation involving those hypotheses must specify testable dynamics and independent evidence.

## Universal Terminal/Transputer dissemination contract

1. **Producer:** kernel-checked proof artifact and immutable SHA-256 digest.
2. **Envelope:** schema version, authority repository, exact commit/tree, model assumptions, proof digest, human-readable explanation, explicit non-claims.
3. **Fan-out:** each admitted subscriber receives the same immutable envelope through the existing authenticated, repository-governed transport; no new unverified broadcast channel.
4. **Comprehension:** expose both the theorem and an accessible counterexample with utilities, strategies and scope limits. Receipt alone is not proof of comprehension.
5. **Acknowledgement:** separate transport delivery ACK, interpretation ACK, and independently verified productive EFFECT_ACK. No ACK is inferred from a successful dispatch.
6. **Failure:** absent verification, unknown subscriber state, conflicting digests, or missing ACK remain OPEN; preserve durable retry and writer fencing.

## Admission gates

- Lean kernel compilation of the exact committed source.
- Negative-test execution on the same exact HEAD.
- Deterministic integrity regeneration and verification.
- Independent code-owner/governance review.
- Transport, fan-out, subscriber readback, and EAP end-to-end evidence.
- No production or universal dissemination claim before all gates pass.

This file is a repository-level specification and explanatory artifact; it does not itself publish to subscribers.
