<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# General Dependency Resolution

V23 generalizes the runtime download and dependency resolution logic.

## Core statement

Dependency resolution is not a Windows special case.

```text
Windows is an adapter.
PowerShell is an adapter.
Unix/macOS shell is an adapter.
Python launcher is an adapter.
CI/container/IDE are adapters.
```

The rule itself is:

```text
GENERAL_DEPENDENCY_RESOLUTION_CONSENT_AND_CONTINUE_PATH_GATE
```

## Required fields

Every unresolved dependency must produce:

```text
dependency_id
platform_scope
license_or_rights_context
provenance_requirement
hash_requirement
continue_path
repair_hint
retry_or_rebuild_path
logfile
evidence_file
```

## Python runtime

The Python runtime remains a third-party license area under the Python Software Foundation License Version 2.

q.e.d. Ingolf Lohmann
