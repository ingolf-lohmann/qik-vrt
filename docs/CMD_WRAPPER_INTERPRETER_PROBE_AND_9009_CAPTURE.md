<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# CMD Wrapper Interpreter Probe and 9009 Capture

V39 repariert den Feldfehler:

```text
exit_code=9009
no target_process_result
```

`command_start` wird erst nach erfolgreicher Interpreter-Probe geschrieben. Interpreter-Fehler werden vom CMD-Wrapper selbst als maschinenlesbares `target_process_result` materialisiert.

q.e.d. Ingolf Lohmann
