<!--
Copyright 2026 Ingolf Lohmann.
Non-source content licensed under Creative Commons BY-NC-ND 4.0.
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->
# CI/CD Persistence Policy

## Grundsatz

Das CI/CD/DevOps/QIK-VRT-Paket führt externe Persistenz nur aus, wenn zur Laufzeit alle erforderlichen Parameter erhoben und alle lokalen Acceptance-Tests bestanden wurden.

## Reihenfolge

```text
Parameter erfassen
=> Secrets sicher lesen
=> Master-Gate ausführen
=> Evidence-Ledger starten
=> GitHub-Persistenz nur bei expliziter Freigabe
=> Zenodo-Persistenz nur bei expliziter Freigabe
=> externe Evidence schreiben
=> Statusgrenzen setzen
```

## Default

```text
mode = dry-run
github_push = false
zenodo_publish = false
```

## Keine Secrets im Paket

Tokens werden ausschließlich gelesen aus:

```text
CI-Secrets
Umgebungsvariablen
getpass zur Laufzeit
```

q.e.d.  
Ingolf Lohmann
