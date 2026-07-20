<!--
Copyright 2026 Ingolf Lohmann.
Non-source content in this file is licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).
See LICENSES/CC-BY-NC-ND-4.0.txt.
-->

# WINDOWS_ZIP_EXTRACTION_COMPATIBILITY_GATE

## Fehlerklassen

```text
WINDOWS_ZIP_EXTRACTION_FAILURE
FINAL_ARTIFACT_NOT_WINDOWS_EXTRACTABLE
ZIP_INTERNAL_PATHS_TOO_LONG_FOR_WINDOWS_EXPLORER
WINDOWS_DELIVERY_PACKAGE_NOT_VALIDATED_BEFORE_RELEASE
ARTIFACT_DELIVERY_WITHOUT_WINDOWS_ZIP_COMPATIBILITY_GATE
```

## Regel

Ein Final-Delivery-ZIP muss unter Windows entpackbar sein.

V36 erzwingt daher:

```text
ZIP file name = QV36_WINZIP_OK.zip
top-level directory = QV36
max internal ZIP path length <= 120
no duplicate entries
no absolute paths
no path traversal
```

q.e.d. Ingolf Lohmann
