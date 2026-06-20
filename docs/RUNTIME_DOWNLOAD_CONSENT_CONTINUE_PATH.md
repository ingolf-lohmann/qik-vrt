<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Runtime Download Consent and Continue Path

V19 repairs the V18 error: missing runtime must not only block. The package now offers a guided CONTINUE path.

When Python is missing, Windows launchers ask whether to download the official Python embeddable runtime from python.org. Before download, provenance and license references are displayed and logged.

```text
runtime/download_python_runtime.ps1
runtime/RUNTIME_DEPENDENCY_MANIFEST.json
third_party/python/THIRD_PARTY_PYTHON_RUNTIME_PROVENANCE.json
logs/qikvrt_last_run.jsonl
```

No false bundled-runtime DONE is claimed until `runtime/python/windows/python.exe` exists.

q.e.d. Ingolf Lohmann
