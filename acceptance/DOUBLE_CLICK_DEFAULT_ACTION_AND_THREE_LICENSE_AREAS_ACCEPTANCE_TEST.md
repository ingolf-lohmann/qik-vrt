<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# DOUBLE_CLICK_DEFAULT_ACTION_AND_THREE_LICENSE_AREAS_ACCEPTANCE_TEST

## Error classes

```text
DOUBLE_CLICK_WITHOUT_ARGUMENTS_NOT_HANDLED
MISSING_DEFAULT_COMMAND_ON_INTERACTIVE_LAUNCH
ARGPARSE_FAILURE_ON_EMPTY_LAUNCH
NO_PARAMETER_LAUNCH_NOT_USABILITY_SAFE
PYTHON_THIRD_PARTY_LICENSE_AREA_NOT_SEPARATED
```

## Rule

A canonical launcher started by double-click with no parameters must do what users generally expect: run a meaningful default action.

Default action:

```text
master-gate
```

No-parameter startup must not fail with an unclear argparse error.

The repository also has three cleanly separated license areas:

```text
Python runtime third-party area = Python Software Foundation License Version 2
QIK-VRT source code = Apache-2.0
QIK-VRT non-source content = CC-BY-NC-ND-4.0
```

q.e.d. Ingolf Lohmann
