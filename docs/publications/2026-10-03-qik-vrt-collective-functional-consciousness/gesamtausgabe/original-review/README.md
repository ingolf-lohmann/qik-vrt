# QIK-VRT — Die wirksame Kontinuität

Gesamtausgabe vom 3. Oktober 2026.

## Lieferumfang

Der Fachartikel, die vollständige allgemeinverständliche Prosa, 30 redaktionelle Aussagegruppen, Quellenbindungen, sichtbare Korrekturen, nachgerechnete Rohzahlen, zwei isolierte Methoden-Gegenbeispiele und bytegleich erhaltene historische Quellen werden zusammen ausgeliefert. Es handelt sich um einen neuen Vorpublikationskandidaten, nicht um eine Zenodo-Veröffentlichung.

## Nachrechnung

`python3 calculations/calculate.py`

Python 3 und Git erforderlich. Das Skript startet nur lokale Testprozesse und ein temporäres Git-Repository. Es führt keine Remote-Schreiboperation aus. Es reproduziert die Rechnung und Methoden-Gegenbeispiele, nicht die historischen Zeitversuche.

## Satz

`cd manuscript && xelatex -interaction=nonstopmode -halt-on-error main.tex && xelatex -interaction=nonstopmode -halt-on-error main.tex`

Verwendet: XeLaTeX/TeX Live, Noto Serif, Inter, DejaVu Sans Mono sowie Latin Modern Math. Der dokumentierte Math-Font-Pfad in main.tex kann auf einem anderen System angepasst werden. Schriften sind nicht als Dateien im Paket enthalten. Ein erneuter Satz kann PDF-Metadaten, Font-Subset-Namen und deshalb die PDF-Bytes ändern; die ausgelieferte PDF ist durch ihren Hash gebunden, nicht durch die Behauptung byteidentischer Builds.

## Geltungs- und Rechtehinweis

Ingolf Lohmann lieferte Konzept, Zweck, Anforderungen und Product-Owner-Auftrag. Redaktion, Auswertung, Methodenprüfung und Satz wurden durch QIK-VRT mit OpenAI-Komponente erzeugt. Historische Quellen behalten ihre jeweils vorhandenen Rechte-/Lizenzhinweise. Ihre Beigabe ist Quellenrückgabe an den Auftraggeber, keine pauschale Neulizenzierung zur öffentlichen Weiterverteilung. Die späteren Zenodo-Metadaten und die endgültige Publikationslizenz bedürfen der im Projekt vorgesehenen Prüfung.

Keine Main-Promotion, keine PDF-Verteilung auf alle Nodes und kein neuer Zenodo-Upload werden durch dieses lokale Paket behauptet. Lokale Git-Blob-SHA-1-Berechnung bedeutet nicht, dass das Objekt in einem Remote-Repository materialisiert ist.
