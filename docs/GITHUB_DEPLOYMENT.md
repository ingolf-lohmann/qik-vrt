<!--
Origin: QIK-VRT V38 remote format repair and dispatch attestation kit
Rights-Holder: Ingolf Lohmann
Project: QIK-VRT
Document-License: Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)
Source-Code-License-Reference: Apache-2.0 applies only to source-code files.
Notice: See RIGHTS.md / QIKVRT_LICENSE_AND_RIGHTS.md, LICENSE, NOTICE, and .q/lic/.
-->

# GitHub Deployment

1. Unzip this repository ZIP into a clean repository root.
2. Commit all files.
3. Push to GitHub.
4. Open Actions and confirm `QIKVRT CI` and `QIKVRT Mesh API`.
5. Run `QIKVRT CI`.
6. Run `QIKVRT Mesh API` with `operation=release_status`, `artifact_id=status`, `dry_run=true`.
7. Download and inspect the audit artifact.

Only after the live workflow dispatch succeeds is GitHub-side API enablement externally confirmed.
