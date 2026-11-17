# Energieäquivalenz, dynamische Raumzeit und reeller Energiekern - Revision 3

Fragestellung und Auftrag: Ingolf Lohmann. Berechnung, Implementierung und Ausarbeitung: OpenAI Codex. Stand 03.11.2026.

## Einstieg

- `FACHARTIKEL.md` bzw. `QIKVRT_Energie_Raumzeit_Forschungsnotiz.pdf`: sieben Seiten mit den ursprünglichen Modellresultaten und dem neuen formalen Nachweis.
- `PROSAARTIKEL.md` bzw. `QIKVRT_Virtuelles_Universum_Prosa.pdf`: fünf Seiten mit allgemein verständlicher Einordnung und zeitlichem Geltungsbereich.
- `CLAIM_MATRIX.json`: mathematische, numerische, bedingte und offene Aussagen.
- `../../../formalization/QIKVRT_RealEnergy_v1/README.md`: separates Lake-Paket, acht ursprüngliche Sätze, acht Statement/_checked-Bindungen und genaue Reproduktion.

Die PDFs enthalten neun bytegleich eingebettete Quellen bzw. Prüfnachweise. Alle zwölf Seiten wurden gerendert und visuell geprüft. Die vier externen Quellenadressen sind sichtbar und anklickbar. Der originale Quellenprüfer wurde unverändert aus der bestehenden Versionshistorie zurückgewonnen und ausgeführt. Die vier externen Quellen bestehen die Prüfung in allen fünf Formaten. Das vollständige Gate wartet auf die eigene öffentliche Quellenarchivierung.

## Erhaltene Modellrechnung

`python3 -B run_experiment.py --output results` reproduziert das konkrete FLRW-Modell. Der bestehende, unveränderte Lauf prüft 48 Kontrollen mit 800 Hauptschritten: analytische Vergleichslösungen, zwei ODE-Formulierungen, Zeitkoordinatenänderung, Konvergenz, Druck-Arbeit-Relation, Rotverschiebung und absichtliche Fehler. `results/RESULTS.json` und die CSV enthalten die unveränderten Zahlen. Die Originalausgaben beider Iterationen bleiben unter `execution/` erhalten. Diese neue formale Ergänzung wird nicht rückwirkend als ein neuer damaliger Lauf bezeichnet.

Die Materialenergie des gewählten geschlossenen Modells ist eine explizite schnittabhängige Größe. Die Metrik und die Parameter werden vorausgesetzt. Die Rechnung belegt keine physikalische Raumzeitentstehung und enthält keine neu geschätzten astronomischen Parameter.

## Neue Ergänzung

Die acht reellen PRE-/REB-Sätze sind in einem tatsächlich von Lake gelockten eigenen Verbraucher erneut geprüft. Die Axiommap ist vollständig. Die falschen mathematischen Aussagen werden zurückgewiesen; Quellen- und Compilerfehler führen zu UNVERIFIED. Die drei Prüferselbsttests stehen im Paket.

Die beiden Artikel behandeln jetzt ausdrücklich den zeitlichen Geltungsbereich: Eine mathematisch definierte Äquivalenz hat angegebene Prämissen. Ihre physikalische Anwendung auf eine bestimmte kosmische Epoche verlangt zusätzliche Belege. Weder universelle Gültigkeit noch eine zeitlich andere Unmöglichkeit wird unterstellt.

## Offene Wirkungsschritte

Native Exact-HEAD-CI, sieben unabhängige Checker, technische Review-/Main-Aufnahme, das originale Quellen-/Archivgate und eine bytegenau öffentlich verifizierte Zenodo-Veröffentlichung sind offen. Die Änderung der Forschungsfassung ist in `../../../CHANGE_NOTICE.md` dokumentiert. Die bestehende allgemeine Ownerfreigabe bleibt erhalten; dieser Entwurf erzeugt keinen neuen DOI und ersetzt keine kandidatengebundene Publikationsentscheidung.

Originalhost-/SSO-, Domain-, Installations-/Restart-/Persistenz-, Mirror-, R2- und Publisher-/Quota-Pflichten bleiben erhalten. Die jüngste unabhängige Domain-Beobachtung zeigt HTTP 525. `EFFECT_ACK_DONE` bleibt unbestätigt. Das alte vollständige November-2-Rohlogarchiv ist eine gesonderte Pflicht; die vorhandenen damaligen Quellen und die neu gesicherten Kernelbelege werden nicht als dieses verlorene Vollarchiv ausgegeben.

Die neue Fassung verändert keine frühere Beobachtung. Quellenarchivierung, Repositorykandidat, Main-Aufnahme, Veröffentlichung und produktive Wirkung sind eigene Nachweisgegenstände.

Native Manuskriptprüfung: Die Läufe41616011235 (7a67d924) und41616823386 (c71f0699) waren erfolgreich. PR679 und die vollständige CI sind getrennt zu beurteilen. Der Beweisumschlag für das zunächst erforderliche Quellenarchiv ist unter source_archive/ im Repository vorbereitet; Original-v2-Prüfer:11 Aussagen,16 Upload-Dateien. Noch keine Zenodo-Veröffentlichung und kein DOI. Die allgemeine Owner-Freigabe ist erhalten, ein späteres kanonisches Upload-Ereignis für diesen neu zurückgegebenen Archivkandidaten ist nicht erfunden worden.
