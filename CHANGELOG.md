<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Changelog

This file summarizes current public milestones. Git history and release pages
remain the authoritative detailed record.

## Unreleased

- Competition-readiness documentation, community guidance, and a no-network
  effect-haltpoint demonstration were merged into `main` through
  [PR #1](https://github.com/Goldkelch/qik-vrt/pull/1) at merge commit
  `0d9c90eaeec73405e0a360e94830e7d28db2bbc2`. The fixed release tag remains
  unchanged.

## 2026.07.22 — IETF EFFECT_ACK Draft -01

- Recorded the published `draft-lohmann-qikvrt-effect-ack-01` revision with
  official Datatracker and archive URLs, byte counts, and SHA-256 digests.
- Updated current source, documentation, and acceptance anchors to revision
  `-01` while preserving revision `-00` provenance and release evidence.
- Integrated the reviewed machine-verifiable formalization and offline
  transcription tooling across the public two-node repository mesh.
- Published tag `v2026.07.22-ietf-effect-ack-01` without moving or replacing
  any earlier tag.

## 2026.07.20 — Wirkungshaltepunkt-Evolution

- Published the five-state QIK-VRT effect-haltpoint reference implementation.
- Made `EFFECT_ACK_DONE` the sole ordinary-release state.
- Added bounded, fail-closed decision paths, canonical protocol hashes,
  versioned responsibility records, API and security controls, integrity
  tooling, and release-bound publication checks.
- Verified 102 tests in nine modules, including 41 protocol/conformance tests
  and five license-transition tests.
- Published release tag
  `v2026.07.20-wirkungshaltepunkt-evolution` at commit
  `a8a9cb2666a91411489d4fc90a5306908f8428ea`.
