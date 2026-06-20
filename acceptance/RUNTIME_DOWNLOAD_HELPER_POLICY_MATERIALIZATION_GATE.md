<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# RUNTIME_DOWNLOAD_HELPER_POLICY_MATERIALIZATION_GATE

## Feldbefund

```text
FAIL missing runtime/download_python_runtime.policy.json
```

## Regel

Wenn `runtime/download_python_runtime.ps1` registriert ist, muss `runtime/download_python_runtime.policy.json` vor `check_required_files` materialisiert und im finalen ZIP nachgewiesen werden.

q.e.d. Ingolf Lohmann
