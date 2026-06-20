<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Runtime Dependency and Console ASCII Safety

V18 repairs the real Windows field-test failure: Python was not found.

## Runtime discovery order

```text
runtime/python/windows/python.exe
python/python.exe
py -3
python
python3
```

## If Python is missing

The Windows launcher writes a JSONL event to:

```text
logs/qikvrt_last_run.jsonl
```

It prints an ASCII-only error, shows the logfile path and exit code, waits for user acknowledgement, and exits with code 9009.

## Important status

This package does not contain the real Windows Python binary because the build sandbox could not resolve python.org. Therefore the runtime self-contained gate is intentionally BLOCK until a real Python runtime is bundled.

q.e.d. Ingolf Lohmann
