# QIKVRT Deploy Final Aggregation Repair / Deploy-Finalbewertung-Reparatur

Deutsch: V2.13.4 repariert den PowerShell-StrictMode-Fehler im generischen GitHub-Deploy-Skript. Frühere Versionen prüften gefilterte Zeilen mit einer direkten `.Count`-Eigenschaft; unter PowerShell 5.1 StrictMode kann das bei Null- oder Singleton-Ergebnissen abbrechen. Die finale Bewertung nutzt jetzt `Measure-Object` über `Get-DeployRowCount`.

English: V2.13.4 repairs the PowerShell StrictMode error in the generic GitHub deploy script. Earlier versions inspected filtered rows via a direct `.Count` property; under PowerShell 5.1 StrictMode this can fail for null or singleton results. Final evaluation now uses `Measure-Object` through `Get-DeployRowCount`.

Author / Urheber: Ingolf Lohmann  
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.  
License: CC BY-NC-ND 4.0 for documentation unless otherwise stated.
