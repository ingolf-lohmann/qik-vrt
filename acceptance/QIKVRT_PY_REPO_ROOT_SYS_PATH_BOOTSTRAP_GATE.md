<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# QIKVRT_PY_REPO_ROOT_SYS_PATH_BOOTSTRAP_GATE

## Fehlerklassen

```text
QIKVRT_PY_CANNOT_IMPORT_TOOLS_UNDER_WINDOWS_RUNTIME
PYTHON_EMBEDDED_RUNTIME_SYS_PATH_MISSING_REPO_ROOT
TOOLS_PACKAGE_IMPORT_NOT_BOOTSTRAPPED
QIKVRT_PY_IMPORTS_TOOLS_BEFORE_SYS_PATH_REPAIR
WINDOWS_RUNTIME_TARGET_IMPORT_PATH_FAILURE
```

## Feldbefund

`target_stderr.txt` zeigt:

```text
ModuleNotFoundError: No module named 'tools'
```

## Regel

`qikvrt.py` muss vor jedem Import aus `tools` den Repository-Root in `sys.path` einfügen.

q.e.d. Ingolf Lohmann
