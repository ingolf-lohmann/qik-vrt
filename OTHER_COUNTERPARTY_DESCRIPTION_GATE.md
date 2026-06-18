<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->

# OTHER_COUNTERPARTY_DESCRIPTION_GATE

## Standardtypen

Die vier Standardtypen / Vorbelegungen sind:

```text
NATURAL_PERSON
ARTIFICIAL_COGNITIVE_SYSTEM
LEGAL_PERSON
ORGANIZATION
```

## OTHER

`OTHER` ist zulässig, aber nur mit zusätzlicher Beschreibung.

Pflichtfeld:

```text
counterparty_other_description
```

Fehlt diese Beschreibung oder ist sie leer/zweifelhaft, gilt:

```text
BLOCK
```

## Blocker

```text
OTHER_COUNTERPARTY_DESCRIPTION_MISSING
OTHER_COUNTERPARTY_DESCRIPTION_AMBIGUOUS
OTHER_COUNTERPARTY_DESCRIPTION_NOT_PERSISTED
```
