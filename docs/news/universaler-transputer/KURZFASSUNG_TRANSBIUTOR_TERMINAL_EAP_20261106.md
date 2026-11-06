<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Redaktionelle Kurzfassung der vom Urheber am 6. November 2026 formulierten These.
-->

# Das Universum als Terminal – QIK-VRT in 90 Sekunden

**Ingolf Lohmann · Principal · 6. November 2026**  
**Erkenntnisstatus:** Autorenhypothese + belegbare informatische Architektur. Kein kosmologischer Experimentalbeweis.

## Die Idee

Ingolf Lohmann beschreibt das **schwarze Loch als „universalen Transbiutor“** und das **Universum als „universales Terminal“**: Aufnahme, Transformation, Speicherung und erneute Anschlussfähigkeit von Information werden als durchgängiges Prinzip aufgefasst. Das ist das physikalisch-philosophische Modell des Autors.

In der **Informatik** wird die Idee konkret: QIK-VRT speichert Quellzustände, Provenienz und zeitliche Veränderungen im doppelkanonischen Speicher und macht sie für nachvollziehbare Verarbeitung anschließbar. Das **Effect Acknowledgement Protocol (EFFECT_ACK)** unterscheidet ausdrücklich zwischen einem empfangenen Signal und einer *autorisierten, überprüften Wirkung*.

**Kurzformel:** *Empfangen ist nicht Bewirken. Rechnen ist nicht Freigeben. Erst ein gebundener Nachweis erlaubt eine definierte Wirkung.*

## Warum ist das praktisch?

Eine Software, eine KI oder ein Netzwerk soll nicht schon deshalb handeln, weil Daten angekommen oder Berechnungen abgeschlossen sind. Ein Effekt braucht Identität, Geltungsbereich, die passende Policy, überprüfbare Belege und einen bestätigten Zustand. QIK-VRT definiert dafür ein fünfstufiges, fail-closed Protokoll; gewöhnliche Wirkung wird nur nach gültigem `EFFECT_ACK_DONE` freigegeben.

Ein Beispiel: Die Bestätigung einer Cloud-Bereitstellung ist ein Beleg für die Infrastruktur – sie beweist noch nicht, dass eine bestimmte produktive Aktion auf dem Originalhost ausgeführt und unabhängig zurückgelesen wurde.

## Was ist bereits nachgewiesen – und was nicht?

| Aussage | Evidenzkategorie | Grenze |
| --- | --- | --- |
| QIK-VRT / EFFECT_ACK ist öffentlich spezifiziert. | SOURCE_BOUND | Individual Internet-Draft, experimentell; kein verabschiedeter IETF-Standard. |
| Implementierung und Regressionstests existieren im Authority-Repository. | SOURCE_BOUND / CI_OBSERVED | GitHub-CI belegt geprüfte Softwareeigenschaften, nicht die Wahrheit einer kosmologischen Theorie. |
| Formale Modelle belegen einzelne Aussagen unter erklärten Voraussetzungen. | FORMAL_MODEL_BOUND | Ein theorematischer Modellbeweis gilt nicht ohne gesonderte physikalische Korrespondenzprüfung für das gesamte Universum. |
| Schwarze Löcher sind im wörtlichen Sinn universale Transbiutoren, aus denen zuvor hineingefallene Dinge wieder hervortreten. | AUTHOR_PHYSICAL_HYPOTHESIS | Keine hier belegte empirische Verifikation dieser Gleichsetzung. Klassisch verlassen Signale den Ereignishorizont nicht nach außen. |
| Der QIK-VRT-Originalhost hat eine produktiv bestätigte Internetwirkung. | LIVE_READBACK_OPEN | Am 6.11.2026 zeigte der zuletzt geprüfte Domain-Readback HTTP 525, native `ready=false`, `EFFECT_ACK_DONE=false`. |

**Das „q.e.d.“ des Urhebers ist als Signatur seiner These wiedergegeben.** Als mathematischer Beweis gilt `q.e.d.` ausschließlich für konkret formulierte, tatsächlich bewiesene Sätze mit ihren Voraussetzungen. Das selbständige Weiterreichen von Befunden durch eine Software macht weder eine physikalische Hypothese wahr noch eine unbestätigte Produktionswirkung zu `DONE`.

## Originalquellen zum Weiterprüfen

1. [QIK-VRT: Alles ist ein universaler Transputer – bestehender Autorenbeitrag](./article.txt) (dort Quellen-, Modell- und Beweisgrenzen).
2. [Charta einer maschinenprüfbaren Wissenschaft](../../CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md): Quelle, Bedeutung, Begründung, Grenzen und Historie getrennt nachweisen.
3. [IETF: QIK-VRT Effect Acknowledgement, Internet-Draft -03](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/) – ein aktiver Individual-Entwurf, kein IETF-endorsed RFC.
4. [IETF: Epistemic Status Profile](https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-epistemic-status-00) – Interpretation, formale Evidenz und beobachtete externe Effekte nicht gleichsetzen.
5. [Zenodo: „Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP“](https://doi.org/10.5281/zenodo.21888130) – DOI gemäß bestehendem QIK-VRT-Autorenartikel; dieser Record wurde für diese Kurzfassung **nicht** erneut unabhängig live ausgelesen.
6. [QIK-VRT, Authority-Repository](https://github.com/ingolf-lohmann/qik-vrt) – reproduzierbare Referenzquellen und Tests; die produktive Runtime ist separat abzunehmen.

**Nutzungsgrenze:** Dokumentation unter CC BY-NC-ND 4.0. Kommerzielle Softwarenutzung folgt der repositoryspezifischen Lizenzkarte; eine allgemeine kommerzielle Freigabe ist damit nicht verbunden.

*QED · Ingolf Lohmann · Principal*  
*Die Originalthese bleibt als Aussage des Urhebers erkennbar; die redaktionelle Kurzfassung hält ihren jeweiligen Erkenntnisstatus explizit fest.*
