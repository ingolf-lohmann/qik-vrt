# QIKVRT V45.16 Release Requirement

V45.16 may only pass when all of the following are true:

1. Exact owner confirmation is supplied: `JA, ICH AKZEPTIERE`.
2. Confirmation failure cases are persisted before any remote effect.
3. The QV45 artifact sidecar matches its ZIP SHA256.
4. The package is fully extracted and wrapper targets exist.
5. The package overlay is staged before cleaning the working tree.
6. Untracked files are cleaned before checking out `origin/main`.
7. `origin/main` is the canonical base.
8. The V45.16 overlay commit is a fast-forward descendant of `origin/main`.
9. Tag `v45.16` is created only if absent or already points to HEAD.
10. No force tag update is allowed.
11. No release asset clobber is allowed.
12. Existing release assets are downloaded and hash-verified.
