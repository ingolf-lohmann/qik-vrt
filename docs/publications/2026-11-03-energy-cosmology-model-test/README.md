# Energieäquivalenz und dynamische Raumzeit - Einstieg

Stand: 3. November 2026. Auftrag und Fragestellung: Ingolf Lohmann; Implementierung, Rechnung und Ausarbeitung: OpenAI Codex.

## Sofort wiederfinden

1. ENTRY_INDEX.json: Einstieg, Ergebnis, Originalquellen und Aufgaben-IDs.
2. FACHARTIKEL.md / QIKVRT_Energie_Raumzeit_Forschungsnotiz.pdf: wissenschaftliche Arbeitsfassung, fünf Seiten.
3. PROSAARTIKEL.md / QIKVRT_Virtuelles_Universum_Prosa.pdf: allgemein verständliche Arbeitsfassung, vier Seiten einschließlich eigenem Quellenanhang.
4. CLAIM_MATRIX.json: jede Aussage mit Nachweis und Grenze.
5. run_experiment.py, results/RESULTS.json und results/closed_mixed_trajectory.csv: neue Ausführung, 48/48 Kontrollen.
6. prior_sources/: die sechs bytegleich wiedergewonnenen ursprünglichen Lean-Dateien.
7. production_evidence/: separat geprüfter Original-Debian-Pfad und tatsächliche Hostgrenze.
8. REVISION_2.json und SOURCE_GATE_PENDING.json: dokumentierte Ergänzung der Quellenanzeige und weiterhin offene Publikationsprüfung. Die wissenschaftliche PDF und die numerischen Ergebnisse bleiben bytegleich zum Vorgänger.

## Ergebnis und Reproduktion

    python3 -B run_experiment.py --output results

Python 3.12 oder neuer, nur Standardbibliothek; Exit 0 ist erforderlich. Vier FLRW-Modelle, 800 Schritte je Hauptlauf, drei analytische Lösungen, zwei ODE-Formulierungen, Koordinatenkontrolle, Konvergenz und Negativkontrollen. Die komplette Haupttrajektorie enthält 801 Zustände. stdout/stderr und beide Quelliterationsstände bleiben erhalten. Die erste Ergebnisdatei wurde nach Pfadwiederverwendung aus dem erhaltenen ersten Quelltext bytegleich reproduziert und als Reproduktion protokolliert.

Die universelle Posteridentität ist unter den üblichen Bedeutungen nicht bestätigt. Eine bedingte Gleichheit durch Parameterdefinitionen ist konstruiert. Eine dynamische virtuelle FLRW-Geometrie wurde tatsächlich gerechnet. Die Gesamtgröße ist die Materialenergie des vollständigen kompakten räumlichen Schnitts; keine beobachterunabhängige globale Gravitationsenergie wird behauptet. Innere physikalische Raumzeitentstehung, neue Messungen und wissenschaftliche Neuheit sind nicht nachgewiesen.

## Vorherige Ergebnisse und fehlende Belege

Quellencheckpoint: 9a6a3f9d-967b-5bb2-a065-20261102e002, Version 1. Der decodierte Quellen-JSON hatte 5151 Bytes und SHA-256 a9a11d2a9dddd8b577f905a445659048a1e2e7177ffe264e1e1dbec1a60fc95e. Das ursprüngliche Hauptmodul hat SHA-256 8c0ff578be57f0b18435189d711f11e94990e434fb31f9e00f1666ad0ddc1a23. Historische Lean-Erfolge sind dokumentierte Vorgängerberichte; hier wurde kein neuer Lean-Kernel gestartet. Das alte Vollarchiv und seine kompletten Rohlogs bleiben offen. Die neuen Läufe ersetzen diese historische Lücke nicht.

## Ablage und Wirkungsgrenzen

Vorgesehener Repositorypfad: docs/publications/2026-11-03-energy-cosmology-model-test. Ausgangs-Main 40fa8eb1a6b413801ba8554dca35f915d54316c7, Tree cd81338b400104452a666873d1fe6c02e996b3a3. Arbeitsauftrag d385b867-360a-5794-8428-2df4b90c53fb; Nachprüfung edc3fb2e-4ac3-5d42-8bd9-1aab83406801. Die spätere Fernrücklesung bindet den tatsächlichen Kandidatencommit außerhalb dieses selbstreferenzfreien Inhalts.

Quellenpersistenz ist keine Main-Integration, Zenodo-Veröffentlichung oder produktive IONOS-/EAP-Abnahme. Die Zenodo-Arbeitsfassung beansprucht weder DOI noch Publikation; der Ownerauftrag nennt eine Bestätigung der Gleichung als Voraussetzung, die in dieser allgemeinen Form nicht vorliegt. Der separate R2-Stopp bleibt unberührt. Die fünf Original-Debian-Pakete und 199 Quellen sind am exakten Main geprüft, aber nicht auf einem Host installiert. Der Original-SSO-/Hostanschluss bleibt konkret offen; es werden keine Ersatzschlüssel oder neuen Identitäten erzeugt.

## Lizenz und Attribution

Neue Artikeltexte und Metadaten: CC-BY-NC-ND-4.0. run_experiment.py: PolyForm-Noncommercial-1.0.0. render_articles.py übernimmt den Apache-2.0-Renderer des bestehenden QIK-VRT-Pfads und erweitert ihn um Tabelle, Grafik und Quellenanhänge. Originale Lean-Dateien werden unverändert und mit ihrer im Vorgänger dokumentierten Provenienz erhalten. Die neue Rechnung weist keine wissenschaftliche Neuheit aus.

Der erste Remote-Stand ist ein Forschungsarchiv-Kandidat mit [skip ci], um die bekannte selectorlose workflow_run-Publisher-Kaskade nicht neu zu starten. Die nativen Gesamtprüfungen dieses Kandidaten bleiben ausdrücklich offen; daraus wird keine Merge- oder Produktionszulassung abgeleitet. ARCHIVE_MODE.json bindet diese Entscheidung.
