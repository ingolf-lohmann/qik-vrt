<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Captured Authority-404: fresh main-based React replay

The observation is byte-identical input from #468, SHA-256
`7fe62ee41e0fa286ce515dca1bd0decb48fe2f8315c0d8f3c30c03285f488eec`.
It is not a new provider or branch-endpoint observation. Its status, original
error, response body/hash, timestamp and provider request ID are projected
into a controlled repository-source input.

`baseline-mesh-react.js` is the exact #476 source blob
`d0a3232ec1353a4a00e8a4ae958470985120637e` at HEAD
`b9e03ef678f1304c6cada3cfc37b311b7faea5b9`, preserved solely as the inert
before-input. Its file-view component is stubbed during source replay; none
of its Storage, Origin, Self-Host or prior test receipts is executed/imported.

`authority-404-before-after.json` is generated again from the new candidate
monitor source and this baseline. The actual locked React creates elements;
controlled hooks/I/O and the original snapshot replica perform the replay.
The original 14 feedback controls are retained. Two additional controls check
the exact production bundle/source slices and storage-free static resource
closure. A single onboarding assertion outside this integration scope is
replaced by the static monitor fallback assertion; offline/no-fetch and
workflow status assertions remain.

Five groups are measured: state, impact, status with uncertainty, responsible
actor and next REST step, repair progress (six visible labels). The replay
produces `0/5 → 5/5` with identical three GETs and one controlled event stream.
Generate a new report, then run the drift/fixture tests:

```sh
node docs/monitor/react-feedback.test.mjs --feedback-report evidence/monitor-feedback/react/authority-404-before-after.json
node --test docs/monitor/react-feedback.test.mjs
```

The separate browser test loads the actual ReactDOM and resources in pinned
Chromium. Its current run must supply a fresh HEAD/TREE/source-bound artifact;
the report here never implies a browser result, Main merge, deployment,
provider repair, human comprehension, native approval or `EFFECT_ACK_DONE`.
`PREDECESSOR_EVIDENCE_TRANSFER=false`.

Original equivalent source changes:
`53f3807d5414699cc52dcb6c654983c080cbb40a` (feedback) and
`53040b450853b0ab5a3d59765b86030b3bd0c978` (retained alert contract).
The integration history is additive and starts directly from current Main;
source locators are provenance, not transferred acceptance.
