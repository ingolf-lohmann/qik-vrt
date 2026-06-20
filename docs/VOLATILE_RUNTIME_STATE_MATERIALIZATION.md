<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# Volatile Runtime State Materialization

V38 repariert den V37-Feldfehler: `runtime/DEPENDENCIES.json` war registriert, aber im Windows-Paket nicht materialisiert.

V38 materialisiert die Pflichtdateien als volatile Runtime-State-Dateien und hält sie weiterhin aus `SHA256SUMS.txt` heraus.

q.e.d. Ingolf Lohmann
