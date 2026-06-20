# QIKVRT V45.16 — QV45 + IETF Evidence Merge Release, Clean Checkout Overlay-Staging Repair

This package carries the uploaded `QV45_WINZIP_OK.zip` artifact and merges/releases it together with the V45.13 rejected-confirmation evidence, the V45.14 packaging/ZIP-preview evidence, the V45.15 untracked-working-tree checkout failure evidence, and the IETF/EFFECT_ACK evidence case.

V45.16 repairs the V45.15 checkout failure:

- the extracted package is first copied into a temporary overlay staging directory;
- the working tree is then cleaned before `origin/main` checkout;
- `origin/main` is used as canonical base;
- QV45 + V45.16 evidence are restored after checkout;
- push must be fast-forward;
- tag `v45.16` is immutable: no force tag update;
- release assets are not clobbered: existing assets are downloaded and hash-verified.

Incoming QV45 artifact SHA256:

```text
4e6baa3a3998774ae65120ce620669558e1d50dc8572c601ce4a75a2e4be37b8
```

Run after fully extracting the ZIP, not from Windows compressed-folder preview:

```cmd
QIKVRT_V45_16_RUN_LOCAL_VERIFY.cmd
QIKVRT_V45_16_REAL_GITHUB_RELEASE.cmd
```

Required exact confirmation:

```text
JA, ICH AKZEPTIERE
```
