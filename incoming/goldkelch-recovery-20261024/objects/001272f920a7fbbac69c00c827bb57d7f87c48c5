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

# Windows Compiler Bootstrap Repair v2.11.3

This repair closes the Windows runner gap observed after `qv2112w.zip`:

```text
DEPENDENCY_BOOTSTRAP_WINGET = PASS / winget.exe found; attempting LLVM.LLVM install
DEPENDENCY_BOOTSTRAP_WINGET = BLOCK / winget exit 0 but compiler not on PATH after refresh
C_COMPILER_FOUND = BLOCK
C_SELFTESTS = BLOCK
```

The defect class is:

```text
WINDOWS_COMPILER_INSTALLED_BUT_NOT_DISCOVERED_AFTER_WINGET
```

The Windows runner no longer relies only on `PATH` after `winget` exits. It now performs a deterministic compiler discovery pass over known Windows install locations, including:

- `C:\Program Files\LLVM\bin\clang.exe`
- `C:\Program Files (x86)\LLVM\bin\clang.exe`
- `%LOCALAPPDATA%\Programs\LLVM\bin\clang.exe`
- `%LOCALAPPDATA%\Microsoft\WinGet\Links\clang.exe`
- MSYS2 UCRT/MinGW/Clang paths
- Git-for-Windows MinGW GCC path
- WinLibs paths
- Visual Studio `VsDevCmd.bat` Build Tools paths

If LLVM is present but not on `PATH`, the runner adds the compiler directory to the current process `PATH` and uses the full compiler path.

If no usable compiler can build `build\qikvrt_verify.exe`, the runner may attempt Visual Studio Build Tools through `winget` with the C++ workload. If policy, privileges, package source state, or network restrictions block the installation, the result remains `BLOCK`, not false `PASS`.

Boundary: the runner does not scan the network, does not modify remote repositories, and does not silently claim C selftest success without an executable verifier.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
