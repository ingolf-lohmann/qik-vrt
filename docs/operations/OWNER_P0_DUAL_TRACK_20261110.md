# Owner P0: Two-track execution mandate (2026-11-10)

Authority: `ingolf-lohmann/qik-vrt`. Owner authorization: Ingolf Lohmann, Product Owner. Workspace task: `8078d9f5-f36a-43ca-80a7-c4a622f8691d` (active, high; owner-designated P0).

## Track A: Software deployment

Continue the existing evidence-bound DevOps workflow. Prioritize the smallest causal repair to exact-HEAD CI, reproducibility, integrity, governance, original-host TLS/mTLS, admitted Mesh runtime and independently verified EAP. Apply TEMDD on CI failures. Never promote, merge, deploy or claim `EFFECT_ACK_DONE` without the applicable independent gates. Preserve existing automation; do not create competing schedulers.

## Track B: Confidential hardware patent preparation

Maintain a *separate nonpublic* invention inventory, disclosure chronology, prior-art review, enablement material, claim candidates and filing strategy. Do not place unpublished enabling details, circuit drawings or claim drafts in public repository files, issues, PRs, logs or automation outputs. A public mandate is not a patent application. Formal filing requires a separately verified receipt from the competent office.

## Scheduling and evidence

Owner designates both tracks as P0 relative to other discretionary work, subject to security and governance gates. Advance independent reversible steps in parallel when possible. Record each completed action with exact subject, timestamp, source, method and receipt. Deadlock/livelock or an absent admitted endpoint is an explicit blocker requiring diagnosis; do not equate periodic observation with progress. Do not claim the repository scheduler has accepted this mandate until a native workflow run/readback proves it.

Baseline readback 2026-11-10 16:07 UTC: main HEAD `c90889c42fa7a74c855aabb5db3809235d87bc7b`, TREE `d107fce2daf87ef207cb5557992d363e89d2e8eb`; `raumzeitterminal.de` HTTPS 525, Mesh 2/2 UNKNOWN, native `ready=false`, `EFFECT_ACK_DONE=false`. These are observations, not a production admission.
