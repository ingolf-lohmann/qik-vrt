# GT | GitHub Token Runtime Prompt / GitHub-Token-Laufzeitabfrage

Version: 2.13.4

DE: Der GitHub-Token wird nicht im Batch-Wrapper erfasst, sondern ausschließlich in `tools/gh_deploy.ps1` bzw. `tools/gh_deploy.sh`. Dadurch gehen Token-Eingaben nicht mehr durch `cmd.exe`/`for /f` verloren. Der Token wird sanitisiert, auf Nicht-Leerheit geprüft, nur im laufenden Prozess verwendet und nicht persistiert.

EN: The GitHub token is no longer captured in the batch wrapper. It is captured only inside `tools/gh_deploy.ps1` or `tools/gh_deploy.sh`. This prevents token input from being lost through `cmd.exe`/`for /f`. The token is sanitized, checked for non-emptiness, used only in the current process, and never persisted.

Footer / Fusszeile: QIKVRT V2.13.4 | Token prompt in deploy process | Token not persisted.
