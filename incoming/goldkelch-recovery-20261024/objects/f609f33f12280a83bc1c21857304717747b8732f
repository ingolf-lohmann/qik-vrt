# QIKVRT V2.13.4R Node committed-artifact hash parity repair

Status: NODE_ONLY_REPAIR
Basis: V2.13.4P / V2.13.4O / V2.13.4H technology path

Purpose:
- Preserve the successful local git-push/tag-trigger architecture.
- Remove server-side ZIP regeneration from the GitHub Actions release path.
- Commit the exact locally generated node release artifact under `release/artifacts/`.
- Let GitHub Actions upload that committed artifact verbatim.

Acceptance gates:
- NODE_HASH_PARITY_GATE
- DEPLOY_ARTIFACT_COMMITTED_SOURCE
- GIT_COMMIT_RELEASE_ARTIFACT
- GITHUB_ACTIONS_RELEASE_TRIGGER
- PUBLIC_NODE_RELEASE_ASSET_HASH_MATCH after external retest.

No local GitHub Release REST create/upload is reintroduced.
Seed variant is not included.
