<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Machine-Readable JSONL Logging and Exit-State Semantics

V21 repairs the field-test failure where raw Windows paths made JSONL invalid.

## Rules

```text
Every JSONL line must parse with json.loads.
Windows paths in JSON use forward slashes or escaped backslashes.
A non-zero exit code must never be reported as DONE.
A non-zero exit code must include a repair hint, error class, or continue path.
CMD/BAT must not echo raw unescaped Windows paths into JSON.
```

q.e.d. Ingolf Lohmann
