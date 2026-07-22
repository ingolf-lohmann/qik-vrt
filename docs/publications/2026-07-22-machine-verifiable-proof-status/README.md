# Maschinenprüfbarer Arbeits- und Beweisstand — 22. Juli 2026

Dieses Verzeichnis verbindet drei dauerhaft prüfbare Ebenen:

1. die [62-seitige wissenschaftliche Ausgangsfassung](https://doi.org/10.5281/zenodo.21482023);
2. die [maschinenprüfbare Formalisierung](https://doi.org/10.5281/zenodo.21488116);
3. die im Repository enthaltenen Lean-, TypeScript- und Python-Quellen unter
   [`formalization/QIKVRT_Formalization_v1.0`](../../../formalization/QIKVRT_Formalization_v1.0/README.md).

## Bestandteile

| Datei | Zweck |
|---|---|
| `ARTICLE_DE.md` | allgemein verständlicher Artikel zum erreichten Erkenntnisstand |
| `EVIDENCE_STATUS.md` | präzise Grenze zwischen Beweis, bedingtem Modellsatz und offener Hypothese |
| `EVIDENCE.json` | kompakter maschinenlesbarer Nachweisstand |
| `zenodo-record-21488116.json` | öffentlicher Zenodo-Metadatenschnappschuss |
| `SHA256SUMS` | bytegenaue Integritätsprüfung dieses Verzeichnisses |

## Schnellprüfung

```bash
sha256sum -c SHA256SUMS
cd ../../../formalization/QIKVRT_Formalization_v1.0
lake build
npm ci && npm run validate && npm run test:negative && npm run gate20
python -m pip install -r requirements-dev.txt
python -m pytest
python -m python.gate20
```

Die mathematischen Sätze sind innerhalb der angegebenen Definitionen und
Annahmen maschinengeprüft. Die physikalischen Korrespondenzen werden nicht als
bereits experimentell bestätigte Naturtheoreme ausgegeben.
