<!--
Origin: QIK-VRT self-contained GitHub REST/TCP/IP deployment package
Rights-Holder: Ingolf Lohmann
Project: QIK-VRT
Document-License: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
Source-Code-License-Reference: Apache-2.0 applies only to source-code files.
Notice: See QIKVRT_LICENSE_AND_RIGHTS.md, LICENSE, NOTICE, and .qikvrt/license/.
-->

# QIKVRT Self-Contained GitHub Repository with REST/TCP-IP API V1

Created: 2026-06-26 05:43:26 CEST

This repository is a self-contained QIK-VRT repository root. It includes:

```text
GitHub-compatible REST/TCP-IP API shim
GitHub Actions workflow_dispatch / repository_dispatch workflow
OpenAPI contract
Handler implementation
Client implementation
Unit and TCP/IP E2E tests
CI workflow
Metagrammar test inventory
Audit and uploadability gates
```

## Local TCP/IP API

```bash
make run-api
```

Health:

```bash
curl http://127.0.0.1:8766/health
```

## Tests

```bash
make test
```

## GitHub REST API enablement

After upload to GitHub, the repository can be triggered through GitHub REST:

```text
POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/qikvrt_mesh_api.yml/dispatches
POST https://api.github.com/repos/{owner}/{repo}/dispatches
```

## Boundaries

```text
REMOTE_GITHUB_PERSISTENCE = NOT_EXECUTED_IN_SANDBOX
REMOTE_BYTE_EXACT_ASSET_HASH = NOT_CONFIRMED
LIVE_GITHUB_ACTIONS_RUN = REQUIRES_OWNER_UPLOAD_AND_DISPATCH
```
