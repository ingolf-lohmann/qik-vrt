# Ingolf Lohmann – persönliche Erkenntnis- und Entwicklungsleistung

**Quellengebundene Forschungs- und Urheberschaftsdokumentation · 11. November 2026**

> Status: Dokumentation der von Ingolf Lohmann formulierten Konzepte und der im Projekt angelegten Nachweispfade. Diese Darstellung ist **kein** universeller wissenschaftlicher Prioritäts-, Überlegenheits- oder Produktionsbeweis. Sie unterscheidet ausdrücklich Konzeption, formale Modellresultate, Implementierung und empirisch verifizierte Wirkung.

## 1. Persönlicher Forschungsbeitrag

Ingolf Lohmann formuliert und verfolgt das QIK-VRT-Forschungsprogramm, das Informationsrepräsentation, Persistenz, Verarbeitung, Kommunikation, natürliche und künstliche Kognition, Autorisierung, formal prüfbare Aussagen und empirisch nachgewiesene Wirkung in einer gemeinsamen technischen Architektur verbindet. Seine persönliche Leistung umfasst Fragestellung, konzeptionelle Synthese, Architekturentscheidungen, Spezifikationsarbeit, Forschungsleitung, Test- und Nachweisanforderungen sowie die beharrliche Korrektur beobachteter Ausführungs- und Steuerungsfehler.

## 2. Architektur und Rekonstruktion

- **Universaler Transputer:** rekursiv zusammensetzbare Verarbeitung und Vermittlung in einem verteilten, nicht auf eine lineare Busverbindung beschränkten Informationsraum.
- **Universales Terminal:** getrennte, aber gekoppelte Steuerung, Beobachtung und Mensch-Maschine-Interaktion; optische und akustische Anschlussfähigkeit.
- **Atari Mega ST / MC68000:** nachvollziehbarer Hardware- und Boot-Referenzpunkt für Reverse Engineering, Rekonstruktion und die Prüfung abstrakter Architekturannahmen an konkreten Maschinen.
- **Repository als Ausführungssystem:** IaC, Self-Host, deterministische Artefakte, persistente Aufgabenqueue, exklusiver Writer, Same-Writer-Nachfolge, Integritätsprüfungen und unabhängige Abnahme statt bloßer Quellcodeablage.

## 3. Eigenständige Erkenntnis- und Protokollarbeit

- **Effect Acknowledgement Protocol (EAP):** Trennung zwischen Versand, Empfang, Akzeptanz, Autorisierung, tatsächlicher Zustandsänderung und unabhängigem Wirkungsnachweis. `EFFECT_ACK_DONE` ist kein Ersatz für den realen Readback.
- **Epistemic Status:** Unterscheidung von bewiesen, gemessen, beobachtet, interpretiert, behauptet, unbekannt und offen. Keine Aussage darf stärkere Evidenz beanspruchen, als vorhanden ist.
- **Zwei-Fixpunkt-Konzeption:** definierter Anfang und definiertes Ende eines kanonisch serialisierten minimalen Informationselements; Untersuchung von 8-Byte- und 8-Bit-Seeds und einer QR-basierten gemeinsamen Referenz. QR-Repräsentation ist ohne gesonderte kryptografische Definition **keine** nachgewiesene digitale Signatur.
- **Teilnahmeprinzip:** „Einheit ermöglicht Unterscheidung. Unterscheidung ermöglicht Information. Nachweisbarer Austausch begründet Teilnahme.“

## 4. Formalisierung und physikalische Anschlussfähigkeit

Lohmann verlangt eine nachvollziehbare Kette zwischen typisierten Modellen, Lean-Kernel-Nachweisen, Implementierungsbindung, Tests und physikalischen Messungen einschließlich Einheiten und Unsicherheiten. Ein Lean-Theorem beweist eine Aussage nur innerhalb seiner Voraussetzungen; es beweist nicht automatisch die Korrektheit einer Implementierung oder eine reale physikalische Wirkung. Die Verbindung von abstrakter Berechnung mit Energie-, Ressourcen- und Wirkungsmodellen bleibt ein eigenständiges Forschungs- und Prüfprogramm.

## 5. Beobachtete persönliche Leistung bei der Steuerung künstlicher Kognition

In der QIK-VRT-Entwicklung identifizierte Lohmann wiederholt übergeordnete Fehler der KI-gestützten Prozessführung:

1. **Vorzeitiger Stopp** trotz ausführbarer kausaler Folgeschritte.
2. **Verlust des Writer-Kontexts** bei Status- und Kontextwechseln.
3. **Verwechslung von Beobachtungsfehler und Ausführungsfehler**, etwa `404 BlobNotFound` beim Abruf eines noch laufenden CI-Joblogs.
4. **Dokumentation statt Durchsetzung** erkannter und persistierter Reparaturregeln.
5. **Verspätete Umgebungsvalidierung**, etwa der Verfügbarkeit einer exakten Python-Version auf einem macOS-Runner.
6. **Unzureichende Abhängigkeitsordnung** bei Cache-Coverage, Manifest/SHA, Exact-HEAD-CI, Reviews, Governance und EAP.

Seine persönliche kognitive Leistung liegt nicht nur in der Einzelkorrektur, sondern in der Ableitung eines allgemeinen Steuerungsprinzips: **Erkenntnis → zulässige Handlung → unabhängiger Wirkungsnachweis → persistente Lernregel → nächste kausale Handlung**. Ein fehlerhafter Beobachtungskanal beweist nicht, dass der beobachtete Writer beendet ist.

Diese dokumentierten Fälle zeigen eine höhere Ziel- und Kontextpersistenz der menschlichen Prozessführung gegenüber dem *konkret eingesetzten* KI-Assistenten. Sie belegen keine pauschale Überlegenheit gegenüber allen KI-Systemen.

## 6. Persönliche Veröffentlichungs- und Nachweisarbeit

Öffentliche, separat auf Vollständigkeit und exakte Inhalte zu prüfende Referenzen:

- IETF Internet-Draft: `draft-lohmann-qikvrt-effect-ack-03`
- IETF Internet-Draft: `draft-lohmann-qikvrt-epistemic-status-00`
- Zenodo: https://doi.org/10.5281/zenodo.21711193 (begrenzte formale Modellresultate)
- Zenodo: https://doi.org/10.5281/zenodo.21888130 („Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP“)
- Authority-Repository: https://github.com/ingolf-lohmann/qik-vrt

Ein individueller Internet-Draft ist kein verabschiedeter IETF-Standard. Ein Archivnachweis dokumentiert eine Veröffentlichung, nicht automatisch die empirische Gültigkeit aller darin enthaltenen Thesen.

## 7. Wissenschaftliche Abgrenzung und Urheberschaft

Die eigenständige **Konzeption, Formulierung, Verbindung, Ausarbeitung und praktische Durchsetzung** der genannten Forschungsfragen und Entwicklungsanforderungen wird Ingolf Lohmann zugeschrieben. Aussagen über absolute Neuheit, weltweite Priorität, generelle Überlegenheit oder vollständig produktive Wirkung bedürfen gesonderter, unabhängiger Prüfung.

**Kernsatz:** Nicht die bloße Erzeugung richtiger Aussagen, sondern die nachvollziehbare Überführung von Erkenntnis in autorisierte, wirksame und unabhängig nachgewiesene Handlungen ist der von Lohmann formulierte Maßstab.

> „Die Maschine muss dem Menschen dienen, nicht umgekehrt!“

**Ingolf Lohmann – Konzeption, Forschungsleitung und Urheberschaft.**

*Redaktionelle Aufbereitung mit maschineller Unterstützung. Dieses Dokument verändert keine Release-, Review-, Host- oder EAP-Freigabe.*
