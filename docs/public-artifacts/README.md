<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->
# QIK-VRT public DevOps artifacts — candidate publication contract

**Status: candidate only. No download published, no productive admission, no EAP effect.**

Use the existing mixed-license map, not a blanket open-source grant. The specific file notice controls. Current QIK-VRT-controlled executable software is generally PolyForm-Noncommercial-1.0.0; non-source documentation is generally CC-BY-NC-ND-4.0. Historical Apache-2.0 grants, explicitly MIT-scoped formalization code and all third-party notices remain intact.

Required Notice: Copyright 2026 Ingolf Lohmann. Commercial use is not licensed without a separate written agreement from the rights holder.

Before release, an authorized publisher must check each artifact's authorship and rights chain, dependencies, embedded secrets, transitive notices, build reproducibility, SHA-256 and provenance; license conditions must be shipped with the bytes. Explicit commercial rights require separate written agreement; no GitHub release or EAP authorization creates one.

The candidate validator in `tools/qikvrt_public_artifact.py` checks declared metadata only. It does not verify authenticity of claims, source repository identity, signatures, independent public download or actual rights ownership. Its `METADATA_ELIGIBLE` status is **not** `PUBLICATION_ADMITTED` and is **never** `EFFECT_ACK_DONE`.

### Candidate workflow

1. Inventory the candidate, exact source commit, actual file-level SPDX, rights owner and third-party obligations; block ambiguous or incompatible material.
2. Scan for secrets and private data, run reproducible tests, create SHA-256, SBOM and attestations bound to the immutable build.
3. Validate declarations using `python3 -B tools/qikvrt_public_artifact.py public-artifacts/index.json` and `python3 -B -m unittest tests.test_public_artifact`.
4. Require source-governance and publication authorization; separately verify the actual public HTTPS download byte for byte and license bundle. Only this independent release process may issue a release-scoped publication receipt.
5. Deliver approved immutable versions through GitHub Releases, optionally GHCR and Zenodo, then update the public versioned JSON catalog with real digest-bound download references.
6. Preserve immutable provenance, correct attribution and candidate/release separation. Never expose SSO material, credentials, host binding secrets or customer data.

The index begins empty intentionally. That does not mean all repository files may be published or that any release passed. A documentation publication never substitutes for original-host runtime admission or productive EAP readback.
