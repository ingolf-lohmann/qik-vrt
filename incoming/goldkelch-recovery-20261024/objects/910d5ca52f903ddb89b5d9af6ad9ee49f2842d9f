<!-- QIKVRT-DE-EN-DOC-HEADER
Deutsch: Dieses Dokument ist Teil des QIK-VRT-Repositories und ist zweisprachig anschlussfähig zu führen. Maßgeblich sind Urheberschaft, Lizenz, Traceability, Requirements, Tests und Nichtregression.
English: This document is part of the QIK-VRT repository and must remain bilingual-accessible. Authorship, license, traceability, requirements, tests, and non-regression are mandatory.
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
Software license / Software-Lizenz: Apache-2.0 unless otherwise stated.
Documentation license / Dokumentationslizenz: CC BY-NC-ND 4.0 unless otherwise stated.
-->

---
QIKVRT-Artifact: license-header
Version: 2.13.4
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated.
Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; no final pass without evidence.
---

# ZIP Layout Compatibility / Windows tar Extraction Repair

Version: 2.10.3

## Purpose

This document fixes the archive-layout defect reported by the Windows acceptance runner:

`FEHLER_ENTPACKT_ABER_LEER | Windows tar | 0 files | Entpackt, aber keine Inhaltsdatei gefunden`

The V2.10 ZIP was internally valid but used a single top-level wrapper directory. A runner that extracts into a target directory and expects repository files at the extraction root can classify that layout as empty.

## Required flat ZIP layout

A QIK-VRT repository release ZIP MUST expose the repository root directly after extraction. The following files and directories MUST be present at the extraction root:

- `README.md`
- `Makefile`
- `SHA256SUMS.txt`
- `docs/`
- `include/`
- `src/`
- `tests/`
- `qikvrt/`
- `release/`

## Forbidden wrapper-only layout

`NO_WRAPPER_ONLY_EXTRACTION` means a ZIP MUST NOT require an acceptance runner to descend into a generated wrapper directory before repository files become visible.

Forbidden example:

```text
extract-target/
  QIKVRT_VERFASSUNG_..._REPOSITORY/
    README.md
    Makefile
    SHA256SUMS.txt
```

Required example:

```text
extract-target/
  README.md
  Makefile
  SHA256SUMS.txt
  docs/
  src/
  tests/
  qikvrt/
```

## Runtime checks

The repository provides two runtime checks:

- `--selftest-zip-layout` validates the layout contract.
- `--validate-root-layout <root>` checks that the actual extraction root contains repository files directly.

## Acceptance rule

A release MUST NOT claim Windows acceptance if the ZIP extracts successfully but leaves the target root without directly visible repository files.

## Boundary

This repair changes archive packaging and acceptance checks only. It does not change the GitHub seed-discovery trust model, does not enable scanning, does not enable self-propagation, and does not perform remote mutation.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
