<!--
Copyright 2026 Ingolf Lohmann.
Non-source content licensed under Creative Commons BY-NC-ND 4.0.
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->
# MONTHLY_CONTENT_PHYSICAL_INCLUSION_ACCEPTANCE_TEST

## Fehlerklasse

`MONTHLY_CONTENT_NOT_PHYSICALLY_INCLUDED`

Deutsch:

`MONATSINHALT_NICHT_PHYSISCH_ENTHALTEN`

## Regel

Wenn ein Paket den Repository- oder Monatsinhalt beansprucht, muss es einen physischen Payload und ein `QIKVRT_MONTHLY_ARTIFACT_MANIFEST.json` enthalten. `pdf_count` und `artifact_count` müssen größer als Null sein. Jeder Manifest-Eintrag muss als Datei im Payload existieren und mit SHA256 übereinstimmen.

q.e.d.  
Ingolf Lohmann
