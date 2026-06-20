<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Double-Click Default Action and Three License Areas

V22 repairs the usability failure where `qikvrt.cmd` started without arguments and delegated to `qikvrt.py` without a command.

## Default behavior

When no command is supplied, launchers default to:

```text
master-gate
```

This is the expected behavior for a canonical repository launcher: start the repository self-check.

## Python missing

If Python is missing, the launcher attempts the accepted runtime download flow:

```text
runtime/download_python_runtime.ps1
```

If download fails, the log contains a responsible continue path instead of a dead block.

## License areas

```text
1. Python runtime = Python Software Foundation License Version 2
2. QIK-VRT source code = Apache-2.0
3. QIK-VRT non-source content = CC-BY-NC-ND-4.0
```

These areas are separated by path, provenance and classification.

q.e.d. Ingolf Lohmann
