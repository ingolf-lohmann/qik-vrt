<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Author/Rights holder: Ingolf Lohmann.
-->
# Determinismus, Reversibilität, Entropie und Superdeterminismus
## Wissenschaftliche Diskussionsgrundlage — 31. Oktober 2026

**Urheber und Rechteinhaber:** Ingolf Lohmann.  
**Kontext:** QIK-VRT und Effect Acknowledgement Protocol (EAP).  
**Status:** Diskussionsbeitrag; keine behauptete experimentelle Widerlegung physikalischer Theorien.  
**Lizenz:** CC-BY-NC-ND-4.0, vorbehaltlich ausdrücklich anders gekennzeichneter Komponenten.  
**Required Notice:** Copyright 2026 Ingolf Lohmann. Commercial use is not licensed without a separate written agreement from the rights holder.

### 1. Präzise Begriffe

Eine diskrete Zustandsmaschine besteht aus einem Zustandsraum S und einer Übergangsfunktion F:S→S. Determinismus bedeutet, dass F für jeden zulässigen Zustand einen eindeutigen Nachfolger bestimmt. Das allein garantiert keinen eindeutigen Vorgänger: Die konstante Abbildung F(s)=0 ist deterministisch, aber nicht injektiv.

Ist F injektiv, besitzt jeder Zustand im Bild von F höchstens einen Vorgänger. Auf einem endlichen Zustandsraum S mit F:S→S ist Injektivität äquivalent zu Bijektivität; dann existiert F⁻¹ und F⁻¹(F(s))=s für alle s∈S. Für unendliche Zustandsräume erfordert eine globale inverse Abbildung S→S zusätzlich Surjektivität.

Ein reversibles digitales Modell setzt die vollständige Erhaltung der zur Umkehr notwendigen Information voraus. Ein Prüfnachweis über die Modellfunktion ist nicht automatisch ein Nachweis über reale Hardware, Speicherung oder äußere Wirkungen.

### 2. Entropie und physikalische Dynamik

Makroskopische thermodynamische Irreversibilität darf nicht mit einer generellen Nichtinvertierbarkeit aller mikroskopischen physikalischen Bewegungsgleichungen gleichgesetzt werden. Statistische Beschreibung, Anfangsbedingungen, Grobkörnigkeit und Zugänglichkeit von Information sind für den Zeitpfeil relevant. Die Behauptung, Reversibilität existiere ausschließlich in der Informatik, wird nicht erhoben.

### 3. Superdeterminismus ist nicht gleich Rückwärtsberechenbarkeit

Der physikalische Begriff Superdeterminismus betrifft insbesondere die Unabhängigkeit der Messgeräteinstellungen von verborgenen Variablen in Bell-Szenarien. Er ist nicht synonym mit Determinismus, Invertierbarkeit oder rückwärts ausführbarer Berechnung. Die hier dargestellte digitale Konstruktion beweist oder widerlegt daher weder physikalischen Superdeterminismus noch eine konkrete Position von Sabine Hossenfelder.

### 4. QIK-VRT und EAP: begrenzter technischer Anspruch

QIK-VRT kann reversible Zustandsübergänge modellieren, kanonische Zustandsrepräsentationen und Herkunftsnachweise prüfen sowie — soweit implementiert und unabhängig verifiziert — frühere logische Zustände rekonstruieren. EAP trennt geplante, beobachtete und bestätigte externe Wirkungen. Ein Acknowledgement ist kein physikalischer Umkehroperator: Ein bestätigter irreversibler Effekt wird durch die Rückwärtsausführung eines Modells nicht rückgängig gemacht.

Formale Beweise beziehen sich ausschließlich auf die spezifizierten Annahmen und Modelle. Empirische Tests, Produktions-Readbacks und unabhängige Effektbestätigungen bleiben getrennte Nachweise.

### 5. Forschungsprogramm

1. Endliche Zustandsräume, Bijektivität und inverse Übergänge formal spezifizieren und im Lean-Kernel prüfen.
2. Den C90-Prüfer gegen dieselben exakt definierten Testvektoren und Negativkontrollen laufen lassen; einen Lean-Beweis nicht mit einem C90-Test verwechseln.
3. Die Grenze zwischen logisch rekonstruierbaren Zuständen und nicht umkehrbaren externen Effekten anhand des EAP präzisieren.
4. Physikalische Aussagen nur mit expliziten Zusatzannahmen, unterscheidbaren Vorhersagen und geeigneter Fachliteratur zur Diskussion stellen.
5. Bei öffentlicher Veröffentlichung Quellenlage, Urheberrecht, Lizenz und den Unterschied zwischen These, Beweis und empirischer Evidenz erhalten.

### 6. Offene wissenschaftliche Frage

Unter welchen zusätzlichen, physikalisch gerechtfertigten Annahmen lässt sich ein informationsbewahrendes, reversibles digitales Modell sinnvoll auf physikalische Systeme abbilden? Die Existenz eines solchen Modells allein beantwortet diese Frage nicht.

### 7. Nachweiskriterien

- Negativkontrolle: deterministische, nicht injektive Funktion wird nicht als reversibel zugelassen.
- Positivkontrolle: bijektive endliche Funktion mit expliziter Inverser.
- Trennung von logischer Invertierbarkeit, Entropie und Bell-Messunabhängigkeit.
- Trennung von EAP-Effektbestätigung und Effektumkehr.
- Beibehaltung des Copyright- und Lizenzhinweises in allen abgeleiteten Publikationsartefakten.
- Kein Status „physikalisch bewiesen“ ohne eigenständigen physikalischen Nachweis.

*Quod erat demonstrandum* gilt nur für tatsächlich bewiesene mathematische Sätze unter den genannten Voraussetzungen, nicht für die offene physikalische Interpretation.
