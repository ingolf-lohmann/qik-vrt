<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT — öffentliche DevOps-Artefakte / Public DevOps Artifacts (V1)

**Urheber / Rechteinhaber:** Ingolf Lohmann. **Status:** öffentlicher, noch nicht in Main integrierter Veröffentlichungskandidat vom 06.11.2026. **Authority:** [ingolf-lohmann/qik-vrt](https://github.com/ingolf-lohmann/qik-vrt).

## Für Menschen und KI-Systeme

Der [maschinenlesbare Katalog](PUBLIC_ARTIFACT_INDEX_V1.json) verweist auf 19 **bereits im öffentlichen Authority-Repository vorhandene** Quellen, Werkzeuge, Prüfindizes, Lizenztexte und Nachweisverträge. Alle Quell-URLs sind auf den beobachteten Main-Commit `37f8e4eb805292a31024a9e6213afc85d3a6a4a2` fixiert; ein später veränderter Main-HEAD ändert daher nicht die referenzierten Originalbytes.

**Wichtig:** Ein öffentlich lesbarer Quelltext ist nicht automatisch ein freigegebenes Release, ein lauffähiges Deployment, eine geprüfte wissenschaftliche Aussage oder ein produktives `EFFECT_ACK_DONE`. Insbesondere dürfen geschützte Originalhost-Informationen, Identitäten, Sitzungstokens und Secrets nicht in die öffentlichen Artefakte übernommen werden.

## Sofortiger Einstieg / Quick start

1. Lies [`/AI`](https://github.com/ingolf-lohmann/qik-vrt/blob/37f8e4eb805292a31024a9e6213afc85d3a6a4a2/AI) und [`AI_CONTEXT.json`](https://github.com/ingolf-lohmann/qik-vrt/blob/37f8e4eb805292a31024a9e6213afc85d3a6a4a2/AI_CONTEXT.json) als Original-Einstieg und die deklarierte Lesereihenfolge.
2. Rufe den [JSON-Index](PUBLIC_ARTIFACT_INDEX_V1.json) ab und wähle aus `artifacts[]` eine `raw_url` mit `git_blob_sha1` und `license_hint`.
3. Lade **nur** die gewünschten öffentlichen Dateien. Prüfe ihre exakten Git-Blob-Bytes und die referenzierten SHA-256-Integritätsdateien. Beachte die Lizenz direkt an der ausgewählten Datei.
4. Benutze `tools/qikvrt_integrity.py verify` und `make test` nur in einem geeigneten, vollständig vorliegenden, lizenzierten lokalen Checkout. Einzelne heruntergeladene Dateien können kein vollständiges Repository-PASS erzeugen.
5. Für produktive Änderungen gilt weiterhin die unveränderte EAP-/Review-/Originalhost-Zulassung; Lesen, Kopieren, Herunterladen oder ein CI-Resultat ist keine Handlungsberechtigung.

### Nachweis einer einzelnen, fixierten Datei / One-file verification

```sh
REF=37f8e4eb805292a31024a9e6213afc85d3a6a4a2
curl --fail --location --silent --show-error \
  "https://raw.githubusercontent.com/ingolf-lohmann/qik-vrt/$REF/AI" -o qikvrt-AI
git hash-object qikvrt-AI
# Compare the printed Git blob SHA-1 to artifacts[path=="AI"].git_blob_sha1 in the JSON index.
```

Die SHA-1-Dateiidentität ist keine eigenständige SHA-256- oder CI-Abnahme. Für vollständige Integrität verwende `SHA256SUMS.txt`, `REPOSITORY_FILE_MANIFEST.json` und dessen detached Digest in der jeweils passenden Version.

### Maschinenzugriff / Machine access

Der öffentliche JSON-Katalog ist UTF-8 / JSON und enthält pro Eintrag `path`, `role`, `license_hint`, `git_blob_sha1`, `raw_url`, `browser_url` und `api_contents_url`. Maschinen können damit gezielt lesen, Lizenzhinweise kontrollieren und einen unveränderlichen Quellenstand zuordnen. Es wird **kein** GitHub-Token, API-Key oder Cloud-Konto für die hier beschriebenen öffentlichen GET-URLs vorausgesetzt; die anonyme Erreichbarkeit von jedem Netz ist jedoch separat zu prüfen.

## Lizenz- und Nutzungsgrenzen

Die aktuelle [Lizenzkarte](https://github.com/ingolf-lohmann/qik-vrt/blob/37f8e4eb805292a31024a9e6213afc85d3a6a4a2/LICENSE), [Lizenzanleitung](https://github.com/ingolf-lohmann/qik-vrt/blob/37f8e4eb805292a31024a9e6213afc85d3a6a4a2/LICENSE.md) und [kommerzielle Nutzungsregel](https://github.com/ingolf-lohmann/qik-vrt/blob/37f8e4eb805292a31024a9e6213afc85d3a6a4a2/COMMERCIAL_USE_POLICY.md) sind maßgeblich. Aktuelle QIK-VRT-eigene Software ist grundsätzlich `PolyForm-Noncommercial-1.0.0`, nicht pauschal Apache-2.0. Nicht-Source-Dokumentation ist grundsätzlich `CC-BY-NC-ND-4.0`. Ältere Apache-Rechte, ausdrücklich MIT-lizenzierte Teilpakete und Drittmaterial behalten ihre jeweilige Rechtslage. **Namensnennung und Rechte-/Provenienzkette erhalten.** Keine hieraus abgeleitete allgemeine kommerzielle, produktive oder KI-Trainingslizenz. Abweichende Nutzungen nur mit den tatsächlich erforderlichen gesonderten Rechten.

Die Eigentümerfreigabe zur operativen Wirkung ist **getrennt** vom jeweiligen öffentlichen Urheberrechtslizenzvertrag. Dieser Katalog ergänzt oder verändert keinen der unveränderten Standard-Lizenztexte.

## Veröffentlichungskette und Abnahme

- **Schon öffentlich:** referenzierte Quellen im öffentlichen GitHub-Repository; ein historisches Release-Asset mit eigenem SHA-256-Sidecar ist im JSON ausdrücklich als historisch gekennzeichnet.
- **Diese Änderung:** ausschließlich zwei neue indexierende Nicht-Source-Artefakte auf einem öffentlichen, überprüfbaren GitHub-Branch mit PR. Die im Index festgelegten Quelle-Commit-Bytes werden nicht verändert.
- **Noch offen:** deterministische Repository-Manifest-Regeneration, exakte Kandidaten-CI, Code-Owner-/Governance-Freigabe, Main-Merge und unabhängiger öffentlicher Readback; erst danach gegebenenfalls neuer unveränderlicher Release/Zenodo-DOI.
- **Weiterhin offen, unabhängig davon:** produktive Originalhost-/Domain-/Mesh-/EAP-Abnahme. Keine implizite `EFFECT_ACK_DONE=true`-Behauptung.

**English summary:** This is a read-only, commit-pinned, license-aware index of existing public DevOps and provenance files. The catalog is a review candidate, not a production release or authorization for commercial use. Retain file-level licenses and third-party notices; verify hashes and effect gates independently.
