# QIKVRT 2.13.4G Windows AllSigned Inline Host Repair

DE: Externer Windows-Retest zeigte: `QIKVRT_MOTW_UNBLOCK` meldete SKIP, trotzdem blockierte PowerShell `tools\license_acceptance.ps1` als nicht digital signiert. Ursache: lokale ExecutionPolicy/Sicherheitsrichtlinie erzwingt faktisch signierte Skriptdateien; MOTW-Entfernung allein reicht nicht.

EN: External Windows retest showed: `QIKVRT_MOTW_UNBLOCK` reported SKIP, yet PowerShell blocked `tools\license_acceptance.ps1` as unsigned. Cause: local execution/security policy effectively requires signed script files; MOTW removal alone is insufficient.

Repair:
- `QIKVRT.cmd` no longer invokes local `.ps1` files with `powershell -File`.
- Local PS1 content is read from the extracted repository and executed as an inline PowerShell `ScriptBlock` with `-RepoRoot`.
- No default `ExecutionPolicy Bypass` flag is used.
- No automatic elevation is used.
- No default remote installer download/`Invoke-Expression` path is restored.
- Package installation still requires explicit `QIKVRT_ALLOW_PACKAGE_INSTALL=1`.

Boundary: This is a sandbox/static/POSIX-verified repository repair. External Windows Defender, PowerShell 5.1 policy, and GitHub upload retest remain owner-side.
