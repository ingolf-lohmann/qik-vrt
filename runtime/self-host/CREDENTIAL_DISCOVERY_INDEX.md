# Credential and original-runtime recovery discovery index

**Index only. Never store secret values, token bodies, private keys, personal tokens, raw environment dumps or private material in this file.** The existence of a variable name or source-code resolver does not prove a currently provisioned credential. GitHub Actions secrets and variables, OS Secret Service and original host private files are separate protected stores; this repository contains their **contracts and references**, not necessarily their readable values.

## Canonical serialized recovery work unit

The single ordered, fail-closed recovery contract is [`state/work_units/QIKVRT_NATIVE_RECOVERY_SERIALIZED_20261114_V1.json`](../../state/work_units/QIKVRT_NATIVE_RECOVERY_SERIALIZED_20261114_V1.json). It binds credential discovery, original host recovery, exact-HEAD tests, native Transputer/Terminal readback, existing Sites persistence and independent EMP/EAP acceptance into one fenced successor chain. It is an executable-work specification, **not** proof that an executor has consumed it or that a productive effect occurred.

## Deterministic lookup order

| Need | Existing authoritative contract / consumer | Provisioning or protected source | Verification |
| --- | --- | --- | --- |
| GitHub Authority authentication | `tools/qikvrt_authority_credentials.py` | Existing scoped app/admin token or protected personal SSO profile; never assume generic `GITHUB_TOKEN` has authority | Resolver checks scope, expiry and source |
| Original production host binding | `runtime/self-host/README.md`, `.github/workflows/qikvrt_ci.yml` | `vars.QIKVRT_LINUX_HOST_BINDING_JSON` and independent `vars.QIKVRT_LINUX_HOST_BINDING_SHA256` | Exact daemon/volume/node/HEAD/TREE/image/manifest pins and protected host identity readback |
| Original mTLS | `runtime/self-host/host-prepare.sh`, `tools/qikvrt_self_host_container.py` | `secrets.QIKVRT_LINUX_HOST_CA`, `secrets.QIKVRT_LINUX_HOST_CERT`, `secrets.QIKVRT_LINUX_HOST_KEY` | Actual protected mTLS connection, never a placeholder |
| Existing original private-file fallback | `tools/qikvrt_authority_credentials.py::production_material`, `state/work_units/QIKVRT_PRODUCTION_ORIGINAL_MATERIAL_SOURCE_20261029.json` | `QIKVRT_PRODUCTION_MATERIAL_SOURCE` plus independent `QIKVRT_PRODUCTION_MATERIAL_SOURCE_SHA256` pointing to pre-existing original private files | Validate descriptor SHA, owner, mode, non-symlink paths and original binding pin; do not export bytes |
| Original GitHub production environment handoff | `src/qikvrt_github_api_shim.py`, `runtime/self-host/README.md` | Existing private PersonalAuth/SSO profile and protected `qikvrt-production` environment | Native authenticated handoff and exact protected environment admission |
| Existing S1 native runtime recovery | `tools/qikvrt_self_host.py`, `runtime/self-host/README.md`, `runtime/self-host/MESH_ACTIVATION.json` | Existing admitted Originalhost, persistent volume, image digest, supervisor and protected CI deployment consumer | Native exact-event REST prepare/commit/readback, restart persistence and public HTTPS readback |
| Mesh endpoint admission | `runtime/self-host/MESH_ACTIVATION.json`, `state/work_units/QIKVRT_IONOS_NATIVE_TERMINAL_FIRST_20261025_V1.json` | Actual admitted native runtime endpoint, not a guessed URL | `qikvrt_native_connection`: ready=true and no `ADMITTED_MESH_RUNTIME_ENDPOINT` gate |

## Autonomous execution rule

On `ADMITTED_MESH_RUNTIME_ENDPOINT` or failed native recovery, inspect this index and its referenced source contracts **before** reporting credential absence. Check availability only through authorized consumers and metadata/readbacks, never by committing credentials or printing secret values. First revalidate original host identity and independent pins; if admitted, reuse existing stopped-container recovery and read back its effect. If access is unavailable, record the precise missing admission in the repository queue, keep that lane blocked, and continue unrelated executable work. Principal authorization is not a substitute for platform permissions or an independent EAP receipt.

Historical work-unit evidence can establish that an adapter was implemented, not that private material is currently accessible. Do not fabricate a provisioned runtime or treat GitHub workflow `action_required` as success. The current index is a lookup contract, not proof of production restoration.
