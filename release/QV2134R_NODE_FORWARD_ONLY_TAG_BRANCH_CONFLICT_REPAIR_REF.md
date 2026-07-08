# QIKVRT V2.13.4R Node forward-only tag/branch conflict repair

Scope: general node variant only. No seed deploy path is included.
Basis: V2.13.4Q committed-artifact hash parity repair and V2.13.4P/4O node git transport path.

External symptom after V2.13.4Q: committed-artifact hash parity was locally established, but pushing to `qikvrt-node/v2.13.4-node` was rejected with `fetch first` because that remote branch already contained prior work from the successful 2.13.4P run. The package still used the historical default tag `v2.13.4-node`, which already had a public release.

Repair:
- Default node tag is moved forward-only to `v2.13.4-node-r` unless `QIKVRT_RELEASE_TAG` is explicitly provided.
- Workflow trigger explicitly accepts `v2.13.4-node-r` and keeps the broader `v2.13.4-node-*` trigger.
- Primary branch non-fast-forward still falls back to `qikvrt-node/<tag>`.
- If that fallback branch already exists and is non-fast-forward, deploy uses a HEAD-suffixed conflict branch `qikvrt-node/<tag>-<shorthead>` instead of blocking.
- Authentication and permission failures remain hard BLOCK conditions.
- GitHub Actions uploads the committed `release/artifacts/qv2134_node.zip` verbatim to preserve local/public hash parity.

No false pass: existing public `v2.13.4-node` is not overwritten by default. Force tag operations still require explicit `QIKVRT_FORCE_TAG=1`.
