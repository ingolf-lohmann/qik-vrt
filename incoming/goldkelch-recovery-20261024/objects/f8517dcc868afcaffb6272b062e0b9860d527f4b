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

# Windows Shell ZIP Compatibility Repair

## Purpose

This document materializes the QIKVRT acceptance correction for the Windows Shell ZIP extraction path reported by `archiv_report(4).tsv`. V2.10.1 was flat at the repository root, but the Windows Shell ZIP extraction method still reported `FEHLER_ENTPACKT_ABER_LEER` with zero extracted files.

## Error class

`WINDOWS_SHELL_ZIP_EXTRACTION_EMPTY_AFTER_FLAT_REPAIR`

The failure is treated as a real packaging acceptance failure. A release archive is not Windows-runner accepted merely because POSIX `unzip` can read it. It must also be packaged with Windows Shell compatible ZIP metadata.

## Required ZIP profile

The V2.10.3 release ZIP uses a conservative Windows Shell compatible profile:

- flat repository files at archive root;
- explicit directory entries for `docs/`, `include/`, `src/`, `tests/`, `tools/`, `release/`, and `qikvrt/` subtrees;
- DOS/Windows `create_system = 0` ZIP metadata;
- DOS archive attribute for files;
- DOS directory attribute for directories;
- forward-slash internal paths only;
- no absolute paths;
- no drive letters;
- no parent-directory traversal;
- no wrapper-only archive root;
- root `README.md`, `Makefile`, and `SHA256SUMS.txt` remain directly visible after extraction.

## Boundary

This repair does not weaken QIKVRT traceability. Directory entries are allowed in this release because the real Windows Shell acceptance path requires an extractor-compatible archive profile. Directory entries are metadata, not payload files, and are excluded from `SHA256SUMS.txt`.

## QIKVRT rule

`NO_WINDOWS_SHELL_EMPTY_EXTRACTION_FINAL_PASS`

No future release may claim full Windows acceptance when a Windows Shell extraction report says `FEHLER_ENTPACKT_ABER_LEER`.

## Minimal acceptance

A release candidate passes this gate only when:

1. ZIP root contains direct content files;
2. the archive contains explicit directory entries;
3. all ZIP entries are relative and safe;
4. directory entries use DOS directory attributes;
5. file entries use DOS archive attributes;
6. `SHA256SUMS.txt` validates all payload files;
7. the repository root-layout validator passes after extraction;
8. the Windows Shell extraction report no longer reports zero files.



---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
