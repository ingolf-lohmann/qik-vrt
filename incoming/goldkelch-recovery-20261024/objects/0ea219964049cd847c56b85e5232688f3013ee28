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

# Windows Acceptance Runner v2.11.3

This repository contains a Windows-only acceptance runner.

Start from the repository root:

```cmd
QIKVRT.cmd acceptance
```

The runner is PowerShell 5.1 compatible and does not require POSIX tools. It uses:

- `Get-FileHash` for SHA256 verification
- `ConvertFrom-Json` for JSON and JSONL validation
- `Invoke-WebRequest` for the live GitHub seed fetch
- Windows package mechanisms for compiler bootstrap

## Runtime dependency closure

If no C compiler is found, the runner attempts to close the dependency at runtime:

1. If `winget.exe` is available, it installs `LLVM.LLVM`.
2. If `choco.exe` is available, it installs `llvm`.
3. The runner refreshes the current process PATH from Machine/User environment variables.
4. It probes known Windows compiler install locations even when PATH was not updated.
5. It can execute `clang.exe`, `gcc.exe`, or Visual Studio `VsDevCmd.bat` by full path.
6. If no buildable compiler is found, it may attempt Visual Studio Build Tools with the C++ workload through `winget`.

If package installation is denied by policy, missing privileges, missing package manager, or offline execution, the runner records a `BLOCK`. It does not claim a false C-build PASS.

## Evidence output

Results are persisted at:

```text
qikvrt\runtime\win_acceptance\WIN_ACCEPTANCE_RESULT.tsv
qikvrt\runtime\win_acceptance\WIN_ACCEPTANCE_RESULT.json
qikvrt\runtime\win_acceptance\GH_MANIFEST.json
qikvrt\runtime\win_acceptance\GH_REST_TCPIP_MANIFEST.json
```

## Boundary

No unauthorized scanning, probing, self-propagation, surveillance, or remote mutation is performed. The live network operation is limited to the configured GitHub seed raw manifest URLs.

## v2.11.5 StrictMode array repair

External qv2114w evidence showed that PowerShell 5.1 StrictMode can return a single compiler candidate as a singleton object rather than as an array. The runner now treats compiler candidate discovery as an explicit object-array contract and uses `Get-ObjectArrayCount` rather than `.Length` or `.Count` on candidate objects.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
