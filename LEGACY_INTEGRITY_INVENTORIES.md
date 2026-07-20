<!--
Copyright 2026 Ingolf Lohmann.
Licensed under CC-BY-NC-ND-4.0. See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Integrity authority and legacy inventories

The current whole-repository integrity authority consists only of:

1. `REPOSITORY_FILE_MANIFEST.json` — deterministic classified inventory;
2. `SHA256SUMS.txt` — SHA-256 index of every immutable manifest entry;
3. `REPOSITORY_FILE_MANIFEST.json.sha256` — detached digest of the manifest;
4. `tools/qikvrt_integrity.py` — the generator and verifier used by the master gate.

The following older top-level files remain as historical, scoped evidence. They
are **not** current whole-repository acceptance authorities:

- `MANIFEST.json`: legacy QIKVRT ODU V2.7 package manifest;
- `FILE_INVENTORY.json`: legacy REST/TCP-IP delivery inventory;
- `SHA256SUMS`: legacy V45.20 document-bundle index;
- `tools/verify.py`: verifier for the older scoped publication package.

Manifests below `assets/`, `dist/`, `payload/`, `publication/` and similar
artifact directories remain authoritative only for the artifact named by that
manifest. They do not compete with the current repository-wide authority.

Runtime acceptance, logs, API state, bytecode caches and test state are
explicitly excluded. Their absence from the immutable index is intentional and
must never be interpreted as evidence that they were verified.
