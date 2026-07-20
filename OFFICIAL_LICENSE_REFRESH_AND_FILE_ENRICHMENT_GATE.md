<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# OFFICIAL_LICENSE_REFRESH_AND_FILE_ENRICHMENT_GATE

## Deutsch

Vor jeder Repository-Persistenz werden die drei benötigten Standardtexte aus
den festgelegten HTTPS-Quellen geladen und bytegenau geprüft:

```text
LICENSES/PolyForm-Noncommercial-1.0.0.txt
Quelle  https://polyformproject.org/licenses/noncommercial/1.0.0.txt
SHA-256 ffcca38841adb694b6f380647e15f17c446a4d1656fed51a1e2041d064c94cc8
Größe   4563 Bytes

LICENSES/CC-BY-NC-ND-4.0.txt
Quelle  https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.txt
SHA-256 38762e3777f4ec00a6f769062a7c3f704fb78ce08303ecff88558da4c49cf9ea
Größe   19127 Bytes

LICENSES/Apache-2.0.txt
Quelle  https://www.apache.org/licenses/LICENSE-2.0.txt
SHA-256 cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30
Größe   11358 Bytes
Rolle   Nur historische oder ausdrücklich so markierte Fassungen/Dateien
```

Aktueller QIK-VRT-Sourcecode benötigt den SPDX-Bezeichner
`PolyForm-Noncommercial-1.0.0` und den Urheberrechtshinweis. Historische
Apache-Hinweise und Fremdlizenzen dürfen nicht umetikettiert oder entfernt
werden. Nicht-Source-Dateien benötigen eine eingebettete oder manifestierte
Lizenzzuordnung; Binärdateien benötigen Manifestabdeckung.

## English

Before repository persistence, refresh and byte-verify the three standard
texts against the sources, sizes, and hashes above. PolyForm Noncommercial is
the current QIK-VRT source-code license. Apache-2.0 is retained only for prior
or specifically marked versions/files. Historical and third-party notices must
not be relabeled or removed.

## Blocker

```text
OFFICIAL_LICENSE_REFRESH_FAILED
OFFICIAL_LICENSE_FILE_NOT_OVERWRITTEN
FILE_LICENSE_ENRICHMENT_MISSING
SOURCE_FILE_WITHOUT_SPDX_OR_COPYRIGHT
HISTORICAL_LICENSE_NOTICE_REMOVED
PERSISTENCE_WITH_STALE_LICENSE_FILE
```
