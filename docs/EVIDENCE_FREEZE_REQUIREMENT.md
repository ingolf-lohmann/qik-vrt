# QIKVRT V45.12 Evidence Freeze Requirement

V45.12 closes the V45.11 tag-pointer drift finding by introducing an evidence-freeze release rule.

## Mandatory rules

1. Product Owner acceptance must be persisted before any real GitHub effect.
2. `origin/main` remains the canonical base; local overlay commits must be descendants of `origin/main`.
3. A tag may be created when absent.
4. An existing remote tag may not be moved. No `git tag -f`, no `git push --force`.
5. A release asset may be uploaded when absent.
6. An existing release asset may not be clobbered. No `gh release upload --clobber`.
7. If an existing release asset is present, it must be downloaded and hash-verified against the local asset.
8. Evidence must bind `local_commit_sha`, `remote_commit_sha`, `remote_tag_sha`, `release_url`, acceptance record, and asset hash verification.

## Closed failure class

`V45_11_TAG_FORCE_UPDATE_AND_EVIDENCE_POINTER_DRIFT` is prevented by V45.12 because the tag is never force-updated and assets are never overwritten. A new tag must be used for a new effect state.
