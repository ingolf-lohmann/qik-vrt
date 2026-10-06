# IETF 169906: bounded successor from main

This successor starts with the unchanged current-main tree at
`71f8c15319bf79456ac177d80941b4f59d372996`. Its only imported content is the
26-file accepted v3 IETF package and nine-file post-effect package from
PR #452, HEAD `c3de0a29d27702dfe7a39279017fea59ae905346`, tree
`743c0fc49cdb1536f84271acb6167f0f1931c191`.

The source branch and its history remain intact. The new commit has main as
its sole parent; the old Collective stack is not an ancestor introduced by this
change. `SOURCE_GIT_CAPSULE.json` proves the exact selected source
commit/tree/path/mode/blob/byte relationships offline through the existing
native integrity validator. `SUCCESSOR_PROVENANCE.json` defines the bounded diff.

All imported bytes are frozen, including accepted XML/TXT/local HTML, public
server HTML, the exact server difference, historical pending manifests and
historical validation reports. XML/TXT match the archived public bytes; the
full server HTML differs while its body matches exactly. The post-effect
receipt documents publication after the historical pending state. Neither
record is rewritten or promoted into a fresh successor observation.

Earlier v1/v2 packages and the referenced Collective PDF/ZIP documents stay at
their original immutable commits. No Collective document bytes, unrelated
runtime changes, old work units, reviews, workflow results or approvals are
imported as current evidence. The frozen v3 validator's original `main()` needs
those off-scope documents; it remains an unchanged historical entrypoint.
The successor verifier reuses its normative, derivation and rendered-content
checks, supplying only the original XML from its validated historical Git
capsule in an isolated temporary directory. This is not a new renderer run or
a claim that the off-scope documents exist in the new worktree.

Run the fresh successor gate:

```sh
make ietf-epistemic-main-successor-test
make test
```

The existing CI runs this gate on the actual candidate HEAD. Its negative
controls reject off-scope imports, changed bytes and rewritten pending flags;
the reused v3 semantic controls execute again. Applicable native workflows,
including the code-owner event observer, must be freshly observed on this PR.
Observer success establishes the main-base selector only; independent native
approval and governance enforcement retain their separate boundaries.

No new IETF submission, merge, force push or general QIK-VRT completion is
authorized or asserted here. The containing Git commit binds these records;
later gate/public readbacks belong to that exact successor PR and HEAD.

Source locators:

- https://github.com/ingolf-lohmann/qik-vrt/pull/452
- https://github.com/ingolf-lohmann/qik-vrt/tree/c3de0a29d27702dfe7a39279017fea59ae905346
- https://datatracker.ietf.org/api/submission/169906/status
- https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-epistemic-status/

Copyright 2026 Ingolf Lohmann. Documentation: CC-BY-NC-ND-4.0.
