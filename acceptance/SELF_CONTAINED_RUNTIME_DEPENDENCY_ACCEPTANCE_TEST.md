<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# SELF_CONTAINED_RUNTIME_DEPENDENCY_ACCEPTANCE_TEST

```text
DEPENDENCY_RUNTIME_NOT_BUNDLED
PYTHON_NOT_FOUND_ON_WINDOWS_REAL_MACHINE
CANONICAL_REPOSITORY_NOT_SELF_CONTAINED
```

A canonical repository that claims self-contained execution must include the runtime it requires. If `python.exe` is not bundled and no installed Python exists, the launcher must write a structured log, show a clear ASCII-safe message, keep the window open on Windows, and exit with a deterministic non-zero code.

q.e.d. Ingolf Lohmann
