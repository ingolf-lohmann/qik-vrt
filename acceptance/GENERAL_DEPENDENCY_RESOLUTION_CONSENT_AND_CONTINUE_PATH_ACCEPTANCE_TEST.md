<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# GENERAL_DEPENDENCY_RESOLUTION_CONSENT_AND_CONTINUE_PATH_ACCEPTANCE_TEST

## Error classes

```text
DEPENDENCY_RESOLUTION_LOGIC_WINDOWS_ONLY
DEPENDENCY_DOWNLOAD_CONSENT_NOT_PLATFORM_GENERAL
RUNTIME_REPAIR_FLOW_NOT_GENERALIZED
DEPENDENCY_RESOLUTION_POLICY_MISSING
PLATFORM_ADAPTER_WITHOUT_GENERAL_DEPENDENCY_CONTRACT
GENERAL_DEPENDENCY_RESOLUTION_GATE_NOT_ENFORCED
```

## Rule

Dependency resolution is not a Windows special case.

Every runtime environment and platform adapter must implement the same canonical dependency contract:

```text
discover
log
license context
provenance
hash requirement
consent
download or continue
repair hint
retry / rebuild path
```

Windows CMD/BAT, PowerShell, Unix/macOS shell, Python launcher, CI, container and IDE flows are adapters of the same rule.

q.e.d. Ingolf Lohmann
