# QIKVRT V45.19 Release Notes

Persists the four QIK-VRT/quantum-gravity PDF documents and repairs V45.18 missing-origin detection.

## Repaired error class

`BLOCK_GIT_REMOTE_GET_URL_ORIGIN_NATIVE_COMMAND_ERROR_BEFORE_BOOTSTRAP`

PowerShell native stderr from `git remote get-url origin` must not abort the bootstrap path when origin is absent. V45.19 uses safe `git remote` listing via `Test-QikvrtGitRemoteExists` before adding origin.

No force-tag update. No asset clobber. Owner acceptance required before any remote effect.
