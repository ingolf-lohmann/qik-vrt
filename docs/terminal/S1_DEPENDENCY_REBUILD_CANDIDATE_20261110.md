# S1 dependency-carrier rebuild candidate — TEMDD 2026-11-10

Authority: `ingolf-lohmann/qik-vrt`. Principal: Ingolf Lohmann.
Scope: **new, separately identified dependency image**, not a retroactive replacement of PR #494.

## RED: original causal failure

Exact-HEAD S1 job in QIKVRT CI run 42813193628 failed at "Verify and reuse original PR494 Docker carrier" with HTTP 404. `runtime/self-host/CONTAINER_CARRIER.json` still binds artifact 11521962723, 382994793 bytes, SHA-256 5a912ccde96253bdba5f5e82cd0a36a4ff89de58dabbe57977bc1acf298d9695. Historical run 37710500668 lists artifact 13562706664, 383384043 bytes. The difference is **not** evidence of substitutability; never overwrite the original contract.

## GREEN candidate experiment

The existing `runtime` stage of `runtime/self-host/Dockerfile` is reused. New named target `s1-dependency-carrier-candidate` binds exact Git HEAD and TREE and runs as UID 10001. In the separate read-only candidate workflow, two BuildKit builds run without Docker layer cache from the same digest-pinned Python/Node base references and one exact source. The native `container-oci-check` verifies each complete OCI blob, source labels and non-root user; independent image digests must agree.

The source stage still resolves Debian packages from mutable repositories, so **equality within one run is a limited reproducibility test**, not a globally frozen dependency snapshot. A future admission requires a complete package-version/binary repository lock and a second cross-run verified build if needed. The candidate OCI archive SHA-256 and byte length are recorded separately; no old digest or approval is inherited.

## Required next gating

1. Current PR-HEAD readback with native full-test and source-integrity trio.
2. Candidate workflow green, persisted image artifact and independent download/readback of the SHA-256-bound OCI archive.
3. Separate source/package/OCI identity promotion: implement an explicit new versioned carrier contract and review it, without changing old PR494 evidence.
4. Native smoke, full application CI, rights/security governance, owner review, then exact-Main release gating.
5. Originalhost mTLS identity, TLS/domain readback, writer fencing, durable original EAP ACK journal and independently verified productive effect.

No temporary Docker image, uploaded ZIP, or model success grants `EFFECT_ACK_DONE=true`. Until every applicable gate has succeeded: **OPEN/BLOCKED**.

Reproduce scope: `python3 -B -m unittest -v tests.test_s1_dependency_rebuild_candidate`.
