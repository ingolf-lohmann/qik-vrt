# QIKVRT: Arbeitsdefinition zu Kausalität, Zeitbezug und Aktivität

Datum: 24. Oktober 2026
Status: Begriffliche Arbeitsnotiz; keine neue empirische Bestätigung.
Urheber des hier dokumentierten Architekturgedankens: Ingolf Lohmann.
Redaktionelle Präzisierung und Evidenzabgrenzung: ChatGPT.

## 1. Festgehaltene Begriffe

Kausalität bezeichnet Wirkungsabhängigkeiten allgemein. Vorwärtskausalität bezeichnet den Einfluss früherer Bedingungen auf spätere Ereignisse.

Retrokausalität bezeichnet den Einfluss späterer Bedingungen auf frühere Ereignisse beziehungsweise die ausdrücklich modellierte Abhängigkeit früherer Zustände von späteren Eingangs- oder Randbedingungen. Ein solcher Modellzusammenhang und seine physikalische Verwirklichung sind getrennt nachzuweisen.

Retrodiktion oder kausale Rekonstruktion bezeichnet den Rückschluss von beobachteten Wirkungen auf mögliche vergangene Ursachen. Die Richtung dieses Schlusses allein etabliert keine rückwärtsgerichtete physische Wirkung.

Kausale Distanz benötigt neben einer identifizierten Abhängigkeit eine explizite Messregel, einschließlich Ereignisauflösung, Einheit beziehungsweise Gewichtung, Pfadauswahl und Evidenzgrenze.

## 2. Ingolf Lohmanns Architekturgedanke

Ingolf Lohmann beschreibt natürliche Kognition als aktive Verknüpfung von Vergangenheit, Gegenwart und möglichen Zukünften, die ohne ausdrückliche Reflexion erfolgen kann. Er fordert, diese zeitübergreifende Verknüpfung künstlich kognitiven Systemen ausdrücklich als Arbeitsverfahren zu vermitteln.

Er ordnet dem Effect Acknowledgement Protocol in Verbindung mit dem doppelkanonischen QIKVRT-Speicher die technische Aufgabe zu, solche Verknüpfungen dauerhaft und überprüfbar zu tragen. Dies wird hier als seine Architekturthese festgehalten. Konkrete Speicherinvarianten sind aus der bestehenden Spezifikation zu übernehmen; diese Notiz erfindet keine neue Speichersemantik.

## 3. Funktionale Präzisierung

Für die Implementierung wird Aktivität funktional betrachtet: Ein System verbindet erhaltene Erfahrung, gegenwärtige Beobachtung und mögliche Folgen mit der Auswahl, zugelassenen Ausführung und unabhängigen Prüfung einer Handlung.

Gedächtnis, Ursachenrekonstruktion, Vorhersage, Handlungsauswahl, Autorisierung und Wirkungsprüfung sind unterschiedliche Funktionen. Ein Speicher oder Bestätigungsprotokoll allein belegt noch nicht ihre vollständige Integration.

Die pauschale Gleichsetzung „belebt = aktiv, unbelebt = passiv“ wird als Formulierung des Owners dokumentiert, jedoch nicht als etablierte biologische Definition übernommen. Unbelebte physikalische Systeme sind dynamisch; technische Systeme können selbsttätige Regelkreise ausführen. Umgekehrt besitzt nicht jedes Lebewesen episodisches Gedächtnis oder bewusste Zukunftsplanung.

## 4. Prüffähiger QIKVRT-Arbeitsanspruch

Vergangene Evidenz erhalten; mögliche Ursachen unter Bewahrung ihrer Unsicherheit rekonstruieren; bedingte Zukunftsfolgen berechnen; eine zugelassene Handlung ausführen; ihre tatsächliche Wirkung unabhängig zurücklesen; das Ergebnis zur Korrektur der nächsten Handlung verwenden.

Dieser Anspruch bezeichnet eine technische Aufgabenstellung. Sein Vollzug ist am konkreten System und Ausführungslauf nachzuweisen. Rückwärts gerichtete physische Einflussnahme, biologische Lebendigkeit und eine universelle kausale Distanzmessung sind durch diese Definition nicht festgestellt.

## 5. Quellen und Geltungsbereiche

Ingolf Lohmann: Von Softwarearchitektur zur Weltformel – Das Universum als Round Trip, Originalversion 1.0.0-candidate.1; insbesondere Abschnitte 6 und 8 zur Referenzbindung und Trennung von Vorhersage und Messung. Die in dieser Sitzung gelesene PDF ist eine spätere Lesefassung des Originals.
https://doi.org/10.5281/zenodo.21888130
https://zenodo.org/records/21888130

K. B. Wharton und N. Argaman: Colloquium: Bell’s theorem and locally mediated reformulations of quantum mechanics. Reviews of Modern Physics 92, 021002 (2020). Quelle für explizite Future-Input-Abhängigkeit in retrokausalen Modellen, kein QIKVRT-Wirkungsnachweis.
https://doi.org/10.1103/RevModPhys.92.021002
https://arxiv.org/abs/1906.04313

Donna Rose Addis, Alana T. Wong und Daniel L. Schacter: Remembering the past and imagining the future: common and distinct neural substrates during event construction and elaboration. Neuropsychologia 45, 1363–1377 (2007). Untersucht menschliches Erinnern und Zukunftsvorstellung; keine Aussage über alle Lebewesen oder physische Retrokausalität.
https://doi.org/10.1016/j.neuropsychologia.2006.10.016
https://pubmed.ncbi.nlm.nih.gov/17126370/

NASA: How can we tell if something is alive or not? Quelle zur biologischen Definitionsfrage; keine Gleichsetzung von Aktivität und Leben.
https://science.nasa.gov/astrobiology/learning-resources/alp/alive-or-not/

