<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Formalization and verification: OpenAI Codex. -->
# Seed, Metatransistor und endliche Architekturkomposition

Owner: Ingolf Lohmann, Product Owner. Auftrag vom 30.10.2026:
die beschriebene Seed-/MC68000-Bauform-/Metatransistor-/Transputer-/Terminal-
Architektur mathematisch prüfen und die Beweise in Lean persistieren.

## Geprüftes Ergebnis

Die neue Datei
`formalization/QIKVRT_Formalization_v2.0/QIKVRTEffectAck/SeedArchitecture.lean`
erweitert die vorhandenen Verträge StorageIntegrity.CanonicalCodec,
ConnectabilitySimulation und Physics.EmpiricalBridge. Sie führt kein neues
Wireformat, keinen Hardwaretreiber und keine zweite Laufzeit ein.

Der Hauptsatz `QIKVRT.SeedArchitecture.V1.architecture_closure` besagt:

Für einen deterministischen Übergang, einen gültigen Seed, eine durch jeden
Übergang erhaltene Invariante, einen bereits korrekten kanonischen Codec und
eine nachgewiesene viability-preserving Simulation auf ein Zielsystem gilt
für jede endliche Eingabefolge:

- Die Quellausführung ist eine gültige endliche Spur.
- Eine entsprechend verwandte gültige Zielspur existiert.
- Der Endzustand erfüllt die erklärte Invariante.
- Der Zielendzustand bleibt innerhalb des erklärten Zielvertrags.
- Kodieren und Dekodieren stellen den Quellendzustand exakt wieder her.

Die Hypothesen sind Bestandteil des Satzes. Der Satz konstruiert aus ihnen
keine bislang unbelegte Hardware- oder Containerimplementierung.

## Drei Benchmark-Klassen und Fixpunkte

B1 ist die konkrete Minimalreferenz mit erklärtem Bootmaterial, Codec,
Ganzzahl-/Bitlogik, Speicheranschlüssen und Bausteinschnittstellen. B2 ist
ein vollständiger eingefrorener privater Maximalbestand mit allen zur
Rekonstruktion nötigen Eingaben. B3 umfasst versionierte Arbeits-, Speicher-,
Ruhe-, Wiederanlauf- und Anpassungsschritte.

Die Fixpunktsätze zeigen für jede über den akzeptierten Codec dargestellte
Referenz die feste kanonische Darstellung und die Idempotenz der
Normalisierung. Der Satz für beide Referenzen setzt ihre Bindung als
Parameter voraus. Er beweist weder ein global kleinstes Programm noch die
Vollständigkeit einer bisher nicht inventarisierten privaten Sammlung.

`checkpoint_restart_exact` beweist Gleichheit zwischen durchgehender
Ausführung und Wiederanlauf an jeder endlichen Spurgrenze. Voraussetzung ist
der korrekte Codec und die vollständige Speicherung des modellierten Zustands.
Ein Stromverlust darf in einer konkreten Implementierung nur den tatsächlich
dauerhaft bestätigten Zustand als erhalten behandeln.

## Was die weiteren Sätze leisten

- Komposition bereits geprüfter Codecs bleibt verlustfrei.
- Endlich viele kodierte Werte werden vollständig rekonstruiert.
- Ein vom Decoder abgewiesener Teil verhindert eine vollständige Ausgabe.
- Gleiches Anfangsmodell und gleiche Eingabefolge bestimmen das Ergebnis.
- Die Invariante bleibt in jedem endlichen Netz und bei Hinzufügen einer
  gültigen Zelle erhalten; bestehende Zellzustände bleiben unverändert.
- Die erklärte boolesche Freigabe verlangt Bindung, Befugnis, Unterscheidung
  und Driftfreiheit. Fehlende Befugnis blockiert.
- Das **abstrakte gepufferte** Gate erhält seinen gespeicherten Inhalt,
  auch bei endlicher Wiederholung. Das ist kein Nachweis für Datenerhalt in
  real stromlosem flüchtigem Speicher.
- Dezimale Festkomma-Koeffizienten werden in Int exakt addiert und
  multipliziert; die Nenner 10^s komponieren gemäß der Skalenaddition.
  Int ist hier unbeschränkt. Maschinenwortbreiten, Überlaufkontrolle,
  Division und konkrete Dezimalhardware benötigen eigene Verfeinerung.
- Aus einer extern begründeten unteren Wärmegrenze pro Löschvorgang folgt
  die entsprechende untere Grenze für deren endliche Summe in erklärten
  exakten Ganzzahleinheiten.
- Unterschiedliche externe Eingaben können trotz deterministischem
  Übergang verschiedene Ergebnisse liefern.
- Die vorhandene empirische Brücke verlangt weiterhin Beobachtungsevidenz.

## Physikalische und produktive Anschlussverpflichtungen

Diese Einträge bleiben **OPEN**, bis ein eigener gegenstandsgebundener
Nachweis vorliegt:

1. Konkretes MC68000-kompatibles Gehäuse und elektrischer Pinvertrag,
   Schaltung/Netzliste, Fertigungsparameter, Synthese, Timing und Boardbetrieb.
2. Implementierung des Seed-/Codec-Vertrags durch die tatsächlichen
   C90-/RTL-/Maschinencode-Datenpfade einschließlich aller Grenzen und Fehlerfälle.
3. Vollständige Rechen-, Speicher-, Betriebssystem- und Containerfunktionen
   bis zum tatsächlich gestarteten Universal Transputer und Terminal.
4. Vollständige private Quell-/Daten-/Laufzeit-/Rechte- und
   Wiederherstellungs-Closure des angegebenen Maximalstands.
5. Temperatur, Löschprotokoll, physikalisches Zustandsmodell, Kalibrierung
   und tatsächliche Energiebilanz. Die Landauer-Beziehung k_B T ln(2)
   wird durch diese Std-only-Datei nicht aus Mikroelektronik hergeleitet.
6. Gemessene Ressourcenverbesserung oder globale Minimalität.
7. Physikalischer Superdeterminismus und universelle Realitätskorrespondenz.
8. Produktive Host-, Peer-, Domain- und EFFECT_ACK_DONE-Abnahme.

Der Owner bezeichnet die Zielarchitektur als „Superdeterministische
Maschine“. Die hier geprüfte mathematische Eigenschaft ist deterministische
Ausführung bei gebundenem Zustand und gebundenen Eingaben. Diese Formulierung
wird nicht stillschweigend in einen Beweis des physikalischen
Superdeterminismus umgedeutet.

## Kernel, Vertrauensbasis und Gegenkontrollen

Lean 4.19.0 ist die bestehende Projekt-Toolchain. Der Audit nennt die exakten
Abhängigkeiten aller 30 Sätze: 17 ohne Axiome; die übrigen verwenden nur
propext und teilweise Quot.sound. Es gibt keine projektspezifischen Axiome,
kein sorry, admit, unsafe oder native_decide in der neuen Beweisquelle.

Vier absichtlich falsche Lean-Behauptungen testen:
Freigabe ohne Befugnis, Rekonstruktion trotz abgewiesenem Teil,
gleiche Ergebnisse aus unterschiedlichen externen Eingaben und null
Gesamtwärme trotz positivem Beispielbeitrag. Akzeptiert der Kernel eine
dieser Behauptungen, scheitert die CI. Fehlende Importe zählen nicht als
erfolgreiche Negativkontrolle.

Die lokale /proc-App-Pfad-Kompatibilität verwendet die bereits vorhandene
APP_PATH_COMPAT.c. Sie ändert weder Kernel noch Lean-Bibliotheksbytes.
Die Receipt bindet Quelle, Compiler/Lean, tatsächliche Befehle, Exitcodes,
Axiomliste und Gegenkontrollen. Ein lokaler Receipt ist keine native
GitHub-CI- oder Main-Integrationsbestätigung.

## Reproduktion

Im vorhandenen Lean-Projekt:

    lake build QIKVRTEffectAck.SeedArchitecture QIKVRTEffectAck.SeedArchitectureAxiomAudit
    lake env lean QIKVRTEffectAck/SeedArchitectureAxiomAudit.lean

Der bestehende Manuskript-Workflow baut und auditiert das Modul, gleicht
jede Axiomliste mit CLAIM_MATRIX.json ab und verlangt die vier erwarteten
inhaltlichen Zurückweisungen. Das neue Modul wird im vorhandenen Manuskript-Workflow ausdrücklich gebaut;
der bestehende Bibliothekseinstieg und seine historischen Quellbindungen bleiben erhalten.

Formaler Beweis, Implementierungsverfeinerung, physikalische Messung und
Repository-/Produktionsintegration behalten ihre eigenen Nachweise.

