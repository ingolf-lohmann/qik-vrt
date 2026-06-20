# QIKVRT V45.12

Evidence-freeze continuation after V45.11 real GitHub effect.

## Local verify

Run:

```cmd
QIKVRT_V45_12_RUN_LOCAL_VERIFY.cmd
```

## Build ZIP and SHA256

Run:

```cmd
QIKVRT_V45_12_BUILD_ZIP_AND_HASH.cmd
```

## Real GitHub evidence-freeze release

Run:

```cmd
QIKVRT_V45_12_REAL_GITHUB_RELEASE.cmd
```

Then enter exactly:

```text
JA, ICH AKZEPTIERE
```

Origin example:

```text
Goldkelch/qik-vrt
```

## V45.12 freeze rule

V45.12 refuses force tag updates and release asset clobbering. If the remote tag already exists but points elsewhere, the run blocks. If a release asset already exists, it is downloaded and SHA256-verified instead of overwritten.

Local package status: `PASS_LOCAL_ZIP_AND_HASH`. Remote status remains `BLOCK_UNTIL_LIVE_GITHUB_EVIDENCE_FREEZE` until the real GitHub wrapper succeeds.
