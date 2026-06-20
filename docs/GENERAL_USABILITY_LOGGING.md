<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# General Usability, Logging, Exit Codes and Repair Hints

V17 repairs general usability, not only Windows usability.

Central machine-readable logfile:

```text
logs/qikvrt_last_run.jsonl
```

Required events:

```text
run_start
command_start
stdout
stderr
check_result
repair_hint
run_end
```

Entrypoints:

```text
qikvrt.py
qikvrt.sh
qikvrt.cmd
qikvrt.bat
qikvrt.ps1
```

Windows has an additional acknowledgement requirement. CMD/BAT use `pause`; PowerShell uses `Read-Host`.

The master gate clears cached `tests.*` modules before executing backfill tests, so the current package is tested, not a stale imported helper.

q.e.d. Ingolf Lohmann
