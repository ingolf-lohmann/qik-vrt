<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# CANONICAL_REPOSITORY_MUST_NOT_DEAD_BLOCK_PRIMARY_ACCEPTANCE_TEST

## Rang

```text
PRIMARY_ACCEPTANCE_GATE = TRUE
RANK = 1
```

## Fehlerklassen

```text
CANONICAL_REPOSITORY_DEAD_BLOCKED
BLOCK_WITHOUT_CONTINUE_PATH
BLOCK_WITHOUT_REPAIR_HINT
BLOCK_WITHOUT_CONSENT_PATH
BLOCK_WITHOUT_LICENSE_CONTEXT
BLOCK_WITHOUT_PROVENANCE_REQUIREMENT
BLOCK_WITHOUT_RETRY_OR_REBUILD_PATH
SILENT_FAILURE_WITHOUT_LOG
```

## Regel

Ein kanonisches Repository darf nicht sterben. Es darf nicht stumpf blockieren und nicht ins Nirvana laufen.

Ein `BLOCK` ist nur zulaessig als Schutz- oder Haltezustand, wenn er zugleich den naechsten verantwortbaren Anschluss anbietet.

Jeder blockierende Befund muss maschinenlesbar enthalten:

```text
blocking_gate
error_class
human_readable_reason
machine_readable_reason
continue_path
repair_hint
next_responsible_action
required_consent
license_or_rights_context
provenance_requirement
retry_or_rebuild_path
logfile
evidence_file
exit_code
```

## Kernformel

```text
BLOCK_WITHOUT_CONTINUE_PATH = INVALID
PROTECTIVE_BLOCK_WITH_CONTINUE_PATH = VALID
```

q.e.d.  
Ingolf Lohmann
