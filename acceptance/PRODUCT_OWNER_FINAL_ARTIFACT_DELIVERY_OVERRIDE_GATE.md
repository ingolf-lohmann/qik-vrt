<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# PRODUCT_OWNER_FINAL_ARTIFACT_DELIVERY_OVERRIDE_GATE

## Fehlerklassen

```text
OWNER_FINAL_DELIVERY_OVERRIDE_NOT_MATERIALIZED
FINAL_DELIVERY_OVERRIDE_CONFUSED_WITH_EXTERNAL_EVIDENCE
FALSE_EXTERNAL_CLAIM_AFTER_OWNER_OVERRIDE
DELIVERY_BLOCK_NOT_RESCINDED_AFTER_OWNER_AUTHORIZATION
```

## Regel

Der Product Owner darf Final Artifact Delivery trotz offener externer Evidenzbedingungen freigeben.

Diese Freigabe ersetzt nicht den faktischen Nachweis externer Vorgänge.

Erlaubt:

```text
FINAL_ARTIFACT_DELIVERY_AUTHORIZED_BY_PRODUCT_OWNER_OVERRIDE
```

Nicht erlaubt:

```text
GitHub Release wurde erstellt
Windows-Feldtest wurde in dieser Sandbox ausgeführt
Python-Binary ist eingebettet
```

q.e.d. Ingolf Lohmann
