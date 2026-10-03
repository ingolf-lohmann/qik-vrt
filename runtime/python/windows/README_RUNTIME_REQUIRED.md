<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Runtime Required

The active Windows starter consumes the verified content-addressed cache defined
in `runtime/toolchains/CACHE_REGISTRY.json` through the existing
`tools/bootstrap-runtime.ps1 -Profile windows-start` path.

Required executable:

```text
.qikvrt/toolchains/python-embed/3.12.10/windows-amd64/sha256/<archive-sha256>/runtime/python.exe
```

The freshly observed Windows Server 2022 x64 carrier passed cold/warm offline
startup and all 11 negative/logger controls. The exact-source receipts and
digests are bound in the existing toolchain registry. Closure is scoped to
the verified materialized cache carrier; Main activation requires review.

```text
PASS_MATERIALIZED_CARRIER_NATIVE_OFFLINE_START_VERIFIED
```

No false DONE is claimed.

q.e.d. Ingolf Lohmann
