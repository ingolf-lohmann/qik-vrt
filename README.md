# QIKVRT V45.11

Windows-safe local QIKVRT repository with interactive Product Owner acceptance, Git bootstrap, GitHub origin handling, remote-branch divergence repair, release asset build, GitHub Release creation, and remote-effect evidence gate.

## Why V45.11 exists

V45.10 reached the real GitHub integration path but failed when the freshly initialized local repository created an independent root commit and then tried `git pull --ff-only origin main`. Because `Goldkelch/qik-vrt` already had `origin/main`, that produced a divergent-history block.

V45.11 fixes this by treating `origin/main` as the canonical base when it exists. The extracted ZIP content is backed up as an overlay, `origin/main` is checked out, the QIKVRT overlay is restored, and a normal non-divergent overlay commit is created on top of the remote branch. That means the later push can be a fast-forward push instead of a false or unsafe unrelated-history merge.

## Run

```cmd
QIKVRT_V45_11_RUN_LOCAL_VERIFY.cmd
QIKVRT_V45_11_BUILD_ZIP_AND_HASH.cmd
QIKVRT_V45_11_REAL_GITHUB_RELEASE.cmd
```

Use exact confirmation:

```text
JA, ICH AKZEPTIERE
```

Use origin input:

```text
Goldkelch/qik-vrt
```

## Gate rule

No local PASS can claim a real GitHub release. The remote release gate remains BLOCK until real GitHub evidence exists: branch SHA, pushed ref, tag, release id, release URL and release asset hash verification.
