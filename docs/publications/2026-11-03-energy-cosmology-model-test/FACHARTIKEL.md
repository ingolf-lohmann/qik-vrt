# Energieäquivalenz und dynamische Raumzeit

Reproduzierbare Modellprüfung einer Energie-Gleichheitskette

QIK-VRT Forschungsnotiz · 3. November 2026 · Arbeitsfassung zur fachlichen Prüfung

Fragestellung und Forschungsauftrag: Ingolf Lohmann. Modellimplementierung, Rechnung und Ausarbeitung: OpenAI Codex. Diese Zuordnung ersetzt keine inhaltliche Autorenfreigabe oder unabhängige Begutachtung.

## Kurzfassung

Untersucht wird die Gleichheitskette E = mc² = pc = k_B T ln(2) I = G m₁m₂/r. Eine explizite Parameterwahl kann ihre Terme auf denselben Energiewert beziehen. Daraus folgt keine universelle Identität dieser Größen für dasselbe physikalische System. Zusätzlich wurde ein dynamisches FLRW-Modell mit Materie, Strahlung und Vakuumenergie numerisch integriert. Im räumlich geschlossenen Modell wird die Materialenergie über die gesamte kompakte Raumfläche integriert. Diese wohldefinierte, schnittabhängige Größe wird ausdrücklich von einer globalen Energie einschließlich Gravitation unterschieden. Die abschließende Ausführung besteht 48 spezifizierte Kontrollen. Das Ergebnis ist eine reproduzierbare Modellprüfung bekannter Beziehungen; eine neue empirische Naturgesetzbestätigung oder wissenschaftliche Neuheit ist damit nicht nachgewiesen.

## 1. Welche Aussage wird geprüft?

Eine universelle Gleichheitskette müsste bei unveränderter Bedeutung der Symbole für alle zugelassenen Systeme gelten. Die übliche Energie-Impuls-Beziehung eines relativistischen Systems lautet E² = m₀²c⁴ + p²c²; m₀ ist die invariante Masse. Im Ruhesystem gilt E₀ = m₀c². Für einen masselosen Träger gilt E = pc. Setzt man für dasselbe System gleichzeitig E = m₀c² = pc, folgt E² = 2E² und damit E = 0. Bereits ein ruhender Körper mit m₀ > 0 und p = 0 liefert ein Gegenbeispiel zur uneingeschränkten positiven Gleichheitskette [1].

Die Landauer-Beziehung betrifft einen Prozess: Bei isothermer idealisierter Löschung unabhängiger, gleichwahrscheinlicher Bits in einem symmetrischen Speicher beträgt die Untergrenze der mittleren Wärmeabgabe k_B T ln(2) je Bit. Allgemeiner kann I eine entsprechend definierte Entropieverringerung in Bits bezeichnen. Gleichheit ist eine Idealgrenze unter geeigneten thermodynamischen Voraussetzungen, keine Energieformel für beliebige gespeicherte Inhalte [2].

Newtonsche gravitative potentielle Energie zweier punktförmiger oder geeigneter kugelsymmetrischer Körper ist bei Nullpunkt im Unendlichen U = -Gm₁m₂/r. Der positive Term der Grafik kann daher den Betrag dieser Energie oder eine passend definierte Energiefreisetzung bezeichnen. Die Newtonsche Näherung benötigt schwache Felder und einen eindeutig bestimmten Zweikörperprozess.

## 2. Eine konstruktiv richtige, bedingte Lesart

Für positive Größen E, c, k_B, T, G, m₁ und m₂ lassen sich folgende Größen definieren:

FORMEL: m_eq = E/c²; p_gamma = E/c; I = E/[k_B T ln(2)]; r = Gm₁m₂/E.

Einsetzen ergibt die Gleichheitskette exakt. Dabei ist m_eq das Massenäquivalent der gewählten Energie, p_gamma der Impuls eines masselosen Trägers und r der aus der Gleichsetzung bestimmte Abstand. Diese Größen müssen nicht zu demselben System gehören. Der Abstand wird in dieser Konstruktion definiert und nicht unabhängig vorhergesagt. Thermodynamische Umsetzbarkeit, verfügbare Arbeit und ein tatsächlicher Wandler sind zusätzliche Anforderungen.

Die Ausführung prüft vier solche Parameterbeispiele. Für die Zweikörperterme werden die Massen so groß und die Bindungsenergien so klein gewählt, dass G(m₁+m₂)/(rc²) < 10⁻⁴ bleibt. Diese notwendige Prüfung der Schwachfeldnähe ist kein Nachweis einer real gebauten Energieumwandlung. Die konstruktive Lesart trägt somit eine bedingte Energieäquivalenz, nicht die uneingeschränkte Naturgesetzbehauptung.

## 3. Kosmologischer Gegenstand und Energiedefinition

Die Allgemeine Relativitätstheorie liefert lokale kovariante Energie-Impuls-Erhaltung. Für eine allgemeine expandierende Raumzeit folgt daraus keine beliebige beobachterunabhängige und erhaltene globale Energie einschließlich Gravitation. Solche Energiebegriffe erfordern zusätzliche Struktur, etwa geeignete Symmetrien oder Randbedingungen [3]. Eine mathematische Außenansicht eines Modells schafft diese Struktur nicht von selbst.

Hier wird deshalb eine begrenzte, explizite Größe berechnet: das Integral der von mitbewegten Beobachtern gemessenen Energiedichte über einen räumlichen Schnitt. Im Hauptfall ist der Schnitt eine vollständige kompakte Dreisphäre. Der berechnete Wert ist die Materialenergie einschließlich des als Fluid beschriebenen Vakuumanteils. Er ist keine zusätzlich konstruierte globale Gravitationsenergie und keine gemessene Gesamtenergie unseres Universums.

Die gewählte Metrik lautet, in den unten festgelegten Einheiten:

FORMEL: ds² = -dτ² + [a(τ)L]² [dχ² + sin²χ dΩ²]; 0 ≤ χ ≤ π.

Der FLRW-Ansatz und die räumliche Topologie werden vorausgesetzt. Dynamisch berechnet wird a(τ). Die Metrik wird hier nicht aus Informationsspeichern oder einem nichtgeometrischen Grundmodell hergeleitet. Die Rechnung belegt deshalb keine Entstehung einer eigenständigen physikalischen Raumzeit im ausführenden Assistenzsystem.

## 4. Gleichungen, Parameter und Beobachter

Es werden normierte Einheiten c = G = H_ref = k_B = 1 verwendet. Der Ausgangszeitpunkt ist τ = 0 mit a = 1 und a' = 1. Die kritische Referenzdichte ist ρ_c = 3/(8π). Für das geschlossene Hauptmodell gelten Ω_m = 0,3, Ω_r = 0,0001 und Ω_v = 0,7999. Damit ist K = Ω_m + Ω_r + Ω_v - 1 = 0,1 und L = K⁻¹/². Diese Werte sind illustrative Eingaben und keine Parameterschätzung aus astronomischen Daten.

FORMEL: H² = (8π/3)(ρ_m + ρ_r + ρ_v) - K/a²; H = a'/a.

FORMEL: a'' = -(4π/3)a(ρ_m + 2ρ_r - 2ρ_v).

Die getrennten Kontinuitätsgleichungen lauten ρ_m' = -3Hρ_m, ρ_r' = -4Hρ_r und ρ_v' = 0. Die Drücke sind p_m = 0, p_r = ρ_r/3 und p_v = -ρ_v. Die vollständige Raumfläche besitzt das Eigenvolumen V = 2π²(aL)³. Es folgt:

FORMEL: E_mat = V(ρ_m + ρ_r + ρ_v); dE_mat = -p_total dV.

Diese integrierte Druck-Arbeit-Relation auf den gewählten Raumschnitten benötigt keinen äußeren Kolben oder einen Beobachter außerhalb des Universums. Sie darf auch nicht als Konstruktion eines beliebigen globalen Energievorrats interpretiert werden.

Ein radialer Lichtstrahl wird mit χ' = 1/(aL) verfolgt. Für einen vernachlässigbar schwachen Testphotonen-Puls gilt E_gamma' = -H E_gamma. Die lokale Photonenergie ist vom mitbewegten Beobachter gemessen. Ein zusätzlicher Rechenlauf mit der Zeitkoordinate λ = 3τ prüft dieselbe Lösung unter einer Zeitkoordinatenänderung. Er ist keine unabhängige astronomische Beobachtung und keine Untersuchung sämtlicher Beobachterwechsel.

## 5. Ausführung und Kontrollen

Der Quelltext run_experiment.py verwendet ausschließlich die Python-Standardbibliothek. Integriert wird von τ = 0 bis τ = 1 mit klassischem Runge-Kutta vierter Ordnung und 800 Schritten. Der Zustandsvektor enthält a, a', drei Dichten, die radiale Nullkoordinate, die Testphotonen-Energie und das Integral von -p dV. Die erste Friedmann-Gleichung wird als Kontrolle verwendet; die Hauptintegration entwickelt die Beschleunigung und Dichten. Eine zweite Formulierung entwickelt a direkt aus der ersten Friedmann-Gleichung und analytischer Fluidverdünnung.

Als Vergleichsfälle dienen flache reine Materie-, reine Strahlungs- und reine Vakuummodelle. Ihre bekannten Lösungen sind a = (1 + 3τ/2)²/³, a = (1 + 2τ)¹/² und a = exp(τ). Die endliche Zelle dieser flachen Vergleichsfälle wird nicht als gesamtes unendliches Universum ausgegeben.

Die 48 Kontrollen umfassen Friedmann-Residuen, Materie- und Strahlungsverdünnung, Druck-Arbeit-Bilanz, Rotverschiebung, einen bedingten Informationsdeckel, analytische Lösungen, zwei ODE-Formulierungen, die Zeitkoordinatenänderung, eine geometrische Krümmungskontrolle, Schrittweitenkonvergenz, Negativkontrollen und die konstruierten Energieäquivalenzen. Ein absichtlich umgekehrtes Vorzeichen der Photonengleichung wird erkannt. Ebenso wird die falsche Annahme einer konstanten Materialenergie im gewählten Mischmodell zurückgewiesen.

## 6. Ergebnisse

| Größe | Anfang | Ende | Bedeutung |
|---|---:|---:|---|
| Skalenfaktor a | 1 | 2.518897465 | Geometrie |
| Materieenergie | 22.3528236 | 22.3528236 | Druckloser Anteil |
| Strahlungsenergie | 0.007450941199 | 0.002958016872 | Verdünnung und Rotverschiebung |
| Vakuumenergie | 59.60007865 | 952.5292062 | Konstante Dichte |
| Materialenergie gesamt | 81.96035319 | 974.8849878 | Vollständiger S³-Schnitt |
| Testphotonen-Energie | 10 | 3.969990895 | Mitbewegter Beobachter |

Im geschlossenen Hauptmodell wächst der Skalenfaktor auf 2,5188974648. Die Materialenergie wächst von 81,9603531928 auf 974,8849877975 normierte Energieeinheiten. Der Anstieg beträgt 892,9246346046 und stimmt mit dem integrierten Term -p dV überein. Der Staubanteil bleibt konstant, die Strahlungsenergie fällt proportional zu 1/a und der Vakuumanteil wächst proportional zu a³. Das ist das erwartete Verhalten der vorausgesetzten Fluidgleichungen, kein neuer experimenteller Befund.

Das größte relative Residuum der Druck-Arbeit-Bilanz beträgt 9,78 × 10⁻¹⁴; das Friedmann-Residuum erreicht 8,44 × 10⁻¹⁴. Eine getrennte Auswertung der analytischen Materialenergieformel am numerisch bestimmten Endwert von a stimmt bis zu einer relativen Differenz von 7,55 × 10⁻¹⁴ überein. Beim Halbieren der Schrittweite sinkt der Fehler im Materievergleich um Faktoren 16,53, 16,27 und 16,14. Das entspricht im untersuchten Bereich der erwarteten vierten Ordnung. Diese Werte sind numerische Residuen in einem Modell und keine Messunsicherheiten astronomischer Daten.

ABBILDUNG: results/model_overview.png

## 7. Bedingter Informationsanschluss

Zusätzlich wird für den Testpuls ein ausdrücklich angenommener nutzbarer Arbeitsanteil η = 1/2 und eine Referenzbadtemperatur T = T₀/a betrachtet. Aus einer vorausgesetzten Landauer-Schranke und W_nutzbar = ηE_gamma ergibt sich:

FORMEL: I_max = ηE_gamma/[k_B T ln(2)].

Da sowohl E_gamma als auch T proportional zu 1/a abnehmen, bleibt diese bedingte Obergrenze konstant: 7,2134752044 Bits für E_gamma(0) = 10 und T₀ = 1. Die Rechnung modelliert weder einen Löschapparat noch einen Wandler. Insbesondere kann aus thermischer Gleichgewichtsstrahlung nicht ohne zusätzliche Nichtgleichgewichtsressource beliebig Arbeit gewonnen werden. Der Testpuls wird hier als vernachlässigbare separate Ressource behandelt; die Verfügbarkeit des angesetzten Arbeitsanteils bleibt eine Prämisse.

## 8. Nachweisstatus und offene Forschungsfragen

Die numerische Modellprüfung ist ausgeführt und protokolliert. Die Parameterkonstruktion und die Bilanzableitungen sind elementare mathematische Folgerungen der angegebenen Definitionen und Annahmen; für die neue kosmologische Rechnung wird kein Lean-Kernelbeleg beansprucht. Unabhängige physikalische Messung, neue Naturgesetze, wissenschaftliche Neuheit, Begutachtung und eine universelle Gleichheit aller Posterterme sind nicht nachgewiesen.

Die früheren sechs Lean-Quellen bleiben als eigener Vorgänger erhalten. Ihr Budgetsatz setzt die mit landauer bezeichnete Ungleichung voraus und verwendet Transitivität. Er beweist dadurch nicht deren physikalische Korrespondenz. Die historischen Kernelprüfungen sind im Arbeitsjournal berichtet; ihre vollständigen damaligen Rohlogs wurden in dieser Nachprüfung nicht wiedergewonnen. Neu ausgeführte Rechnungen werden nicht rückwirkend zu historischen Ausführungsbelegen erklärt.

Ein weiterführendes Forschungsprogramm benötigt einen präzisen Geltungsanspruch: Welche Energie soll invariant sein, welche Größen werden unabhängig gemessen, und welche Vorhersage unterscheidet das vorgeschlagene Modell von den bekannten Beziehungen? Für eine Behauptung emergenter Lorentz-Geometrie wäre zusätzlich eine Herleitung der Metrik aus einem andersartigen Ausgangsmodell einschließlich eines überprüfbaren Grenzübergangs nötig. Für eine experimentelle Kopplung von Gravitation und Informationslöschung wären ein realer Prozess, Kalibrierung, Verlustbilanz und unabhängige Messungen erforderlich.

## 8a. Neuer formaler Nachweis über reellen Energiegrößen

Die vorliegende Revision ergänzt die Modellprüfung um eine separat gelockte Lean-4.19.0-Formalisierung über ℝ. Die ursprünglichen Dateien PlanckRealEnergyDomain.lean und RealErasureBudget.lean sind bytegleich zum Kernel-Paket vom 3. November 2026 erhalten. Die acht ursprünglichen Sätze wurden im neuen Lake-Verbraucher erneut kompiliert. Zusätzlich wurden acht explizite Statement/_checked-Bindungen geprüft; diese Bindungen sind keine acht weiteren unabhängigen Forschungssätze.

Die Eingaben ℏ, G und c sind strikt positive reelle Zahlen. Die definierten Größen lauten m_P = √(ℏc/G), t_P = √(ℏG/c⁵) und E_P = m_Pc². Der Kern prüft folgende Aussagen unter diesen Voraussetzungen:

| Claim | Aussage | Voraussetzung | Nachweis |
|---|---|---|---|
| PRE-T01 | m_P > 0 | Positive Eingaben | Lean-Kern |
| PRE-T02 | t_P > 0 | Positive Eingaben | Lean-Kern |
| PRE-T03 | E_P > 0 | Positive Eingaben | Lean-Kern |
| PRE-T04 | t_P E_P = ℏ | Genannte Definitionen | Lean-Kern |
| PRE-T05 | E_P = ℏ/t_P | t_P > 0 | Lean-Kern |
| REB-T01 | I ≤ E/cost | cost > 0; cost I ≤ W ≤ E | Lean-Kern |
| REB-T02 | 0 ≤ ΔE/E_P < 1 | 0 ≤ ΔE < E_P | Lean-Kern |
| REB-T03 | I ≤ E_P/cost | cost > 0; cost I ≤ W ≤ E_P | Lean-Kern |

Jeder Originalsatz und jede Bindung erhielt einen separaten Axiomaudit. Die gefundenen Standardaxiome sind propext, Classical.choice und Quot.sound. Neue Projektaxiome oder Beweisplatzhalter wurden nicht eingeführt. Vier absichtlich falsche Aussagen werden mit semantischen Lean-Diagnosen zurückgewiesen. Eine beschädigte Quellenbindung und ein fehlender Compiler führen im Prüfer ausdrücklich zum Zustand UNVERIFIED; sie werden weder als bewiesener Satz noch als widerlegtes physikalisches Modell ausgegeben.

Die Abhängigkeit mathlib ist der im bestehenden Batch-01B-Plan vorgesehene Stand c44e0c8ee63ca166450922a373c7409c5d26b00b. Der vollständige Git-Dateibaum des Originalarchivs stimmt mit dem unabhängig gelesenen Baum fdf252e589fb338709bf537ba48ce79a78cbe5e9 überein. Lake hat einen eigenen Pfad-Lock für das hashgebundene Originalarchiv und acht exakte transitive Git-Revisionen erzeugt. Die 6816 Originaldateien werden vor der Prüfung gegen ihr Quellenmanifest geprüft. Das bisherige Std-only-Paket wurde nicht verändert. Die Quellenarchivbindung wird nicht als erfolgreicher Git-Abruf oder als wiedergewonnenes Git-Commitobjekt bezeichnet.

Mit cost = k_B T ln(2) wird REB-T01 unter den geeigneten thermodynamischen Prozessannahmen zu einer Landauer-artigen Informationsschranke. Der Lean-Beweis zeigt die algebraische Folgerung aus der vorausgesetzten unteren Arbeitsgrenze und dem verfügbaren Arbeitsbudget. Die physikalische Bedeutung von cost, die Zuführung nutzbarer Arbeit und ihre SI-Kalibrierung benötigen eigene Belege. Die vierte Planckidentität folgt aus den Definitionen; sie ist dadurch kein zusätzlicher Messbefund und keine Herleitung der Raumzeit aus Speicheroperationen.

## 8b. Zeitlicher und physikalischer Geltungsbereich

Eine definierte Energieäquivalenz ist unter den genannten mathematischen Bedingungen konstruierbar. Der algebraische Satz gilt für alle Eingaben seines expliziten Definitionsbereichs. Seine physikalische Anwendung ist an den untersuchten Prozess, die verwendeten Näherungen, Einheiten, Energiedefinitionen und eine bestimmte kosmische Epoche gebunden. Die vorliegende Modellrechnung verwendet festgelegte Parameter; sie schätzt diese nicht aus neu ausgewerteten Beobachtungsdaten.

Aus einer Übertragbarkeit unter heute geprüften Prozessbedingungen folgt keine Gültigkeit in jeder Phase des Universums. Ebenso folgt daraus keine Unmöglichkeit in früheren oder späteren Phasen. Eine entsprechende Epochenbehauptung benötigt eine konkrete Modellfamilie und unabhängige empirische Daten. Die neue formale Prüfung ergänzt die Nachvollziehbarkeit des algebraischen Kerns; sie ersetzt diese physikalische Untersuchung nicht.

## 9. Reproduktion und Persistenz

Ausführung: python3 -B run_experiment.py --output results. Der Prozess muss Exit 0 liefern. RESULTS.json enthält jeden Kontrollnamen, die Parameter, Toleranzen, Grenzen und den Quell-SHA-256. closed_mixed_trajectory.csv enthält 801 Zustände einschließlich des Anfangszustands. Die Ausführungsverzeichnisse erhalten stdout, stderr und Prozessbelege beider Iterationen. Die erste Ergebnisdatei wurde nach Wiederverwendung ihres Pfads aus dem erhaltenen ersten Quelltext bytegleich reproduziert; dieser Vorgang ist als neue Reproduktion gekennzeichnet.

README.md und ENTRY_INDEX.json bilden den schnellen Einstieg. CLAIM_MATRIX.json trennt Aussagen, Nachweise und Grenzen. Das Dateimanifest bindet die exakten Artefakte. Quellarchivierung, Main-Aufnahme, öffentliche Zenodo-Veröffentlichung und produktive IONOS-/EAP-Wirkung bleiben getrennte Zustände. Diese Arbeitsfassung beansprucht keine DOI und keine erfolgte Produktivierung.

## Quellen

[1] Robert F. Mudde: Classical Mechanics & Special Relativity for Starters, Kapitel 20, TU Delft. Energie-Impuls-Beziehung und masselose Teilchen. https://interactivetextbooks.tudelft.nl/classical-mechanics-and-special-relativity/content/ChXX0_FourMomentum.html

[2] Y. Jun, M. Gavrilov und J. Bechhoefer: High-Precision Test of Landauer's Principle in a Feedback Trap. Physical Review Letters 113, 190601 (2014). DOI: https://doi.org/10.1103/PhysRevLett.113.190601

[3] M. Trodden und S. M. Carroll: TASI Lectures: Introduction to Cosmology, Abschnitt 2.2, Friedmann-Gleichungen, Kontinuität und kosmologische Komponenten. https://ned.ipac.caltech.edu/level5/Sept03/Trodden/Trodden2_2.html

[4] Ingolf Lohmann: Charta einer maschinenprüfbaren Wissenschaft. DOI: https://doi.org/10.5281/zenodo.21515074. Kanonischer SHA-256: 7fb4e5c369b079e93ce409e9ca4f6830476a1b6dbd42543273d85164e111a631. Verwendet für Nachweisklassifikation und Provenienz, nicht als unabhängiger Physiknachweis.

Lizenz der neuen Textfassung: CC-BY-NC-ND-4.0. Die konkrete Implementierung besitzt ihren eigenen Lizenzhinweis. Die Darstellung ist eine Arbeitsfassung; ihre wissenschaftliche Neuheit ist nicht festgestellt.
