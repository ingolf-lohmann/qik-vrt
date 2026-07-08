# QV2134E Deploy Token Property and AV-Safe Bootstrap Repair

Deutsch: Dieser Hotfix schließt den extern beobachteten Windows-Abbruch nach erfolgreicher Acceptance: `Normalize-GitHubHeaderToken` gab bei leerem Environment-Token bisher einen String zurück, während der nachfolgende StrictMode-Code ein Objekt mit `.token` erwartete. Die Funktion liefert nun immer ein Objekt `{ token, removed }`, auch bei leerer Eingabe.

English: This hotfix closes the externally observed Windows abort after successful acceptance: `Normalize-GitHubHeaderToken` previously returned a string for an empty environment token while the later StrictMode code expected an object with `.token`. The function now always returns an object `{ token, removed }`, including empty input.

Deutsch: Zusätzlich wurde der Windows-Entry-Point AV-sicherer gemacht: keine automatische Elevation, kein `ExecutionPolicy Bypass`, kein `DownloadString`/`Invoke-Expression`-Chocolatey-Installer im Default-Pfad. Vorhandene Compiler werden bevorzugt verwendet; Paketinstallation ist nur noch explizit per `QIKVRT_ALLOW_PACKAGE_INSTALL=1` vorgesehen.

English: The Windows entry point is also more AV-safe: no automatic elevation, no `ExecutionPolicy Bypass`, and no `DownloadString`/`Invoke-Expression` Chocolatey installer on the default path. Existing compilers are preferred; package installation is now explicit through `QIKVRT_ALLOW_PACKAGE_INSTALL=1` only.

Status: SANDBOX_STATIC_VERIFIED; external Windows GitHub upload retest remains pending.
