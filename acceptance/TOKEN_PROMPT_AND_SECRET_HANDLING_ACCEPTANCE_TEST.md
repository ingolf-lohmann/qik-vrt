<!--
Copyright 2026 Ingolf Lohmann.
Non-source content licensed under Creative Commons BY-NC-ND 4.0.
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->
# TOKEN_PROMPT_AND_SECRET_HANDLING_ACCEPTANCE_TEST

## Fehlerklasse

`TOKEN_SECRET_HANDLING_NOT_SAFE`

Deutsch:

`TOKEN_SECRET_HANDLING_NICHT_SICHER`

## Regel

Tokens dürfen nicht im Paket gespeichert werden; sie werden aus CI-Secrets, Umgebungsvariablen oder getpass-Laufzeitabfrage gelesen und redaktiert protokolliert.

q.e.d.  
Ingolf Lohmann
