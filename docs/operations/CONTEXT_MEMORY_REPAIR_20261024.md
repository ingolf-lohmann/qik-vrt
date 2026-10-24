<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Speicherengpass: belegte Ursachen und vorhandener Ersatzpfad

Owner-Ziel und Implementierungsfreigabe: Ingolf Lohmann, 24. Oktober 2026. Diagnose und Implementierung: Codex im autorisierten Auftrag. Dies ist eine technische Reparaturquittung mit begrenztem Messumfang.

Die maßgeblichen Zustände bleiben im originalen SQLite-Journal und in versionierten Work Units. Der austauschbare HMI-/Modellkontext erhält nur benötigte Ausschnitte und geprüfte Identitäten. Ein Digest ermöglicht eine Integritätsprüfung vorhandener Daten; er rekonstruiert keine verlorenen Originalbytes allein. Die bereits geltende HMI-Unabhängigkeitsregel bleibt unverändert.

## Zwei nachgewiesene Materialisierungen

Die MCP-HEAD-Abfrage verlangte das vollständige Commit-JSON mitsamt Dateidiffs. Am beobachteten Main-Commit a1a2204f waren dies 561856 Bytes für 68 Dateien. Die reparierte bestehende GET-Verbindung löst zuerst den Ref als 40-Byte-SHA auf und liest danach den unveränderlichen Git-Commit mit Baumkennung: im selben Fall weitere 3295 Bytes, zusammen 3335 Bytes. Beide ursprünglichen Antwortdigests bleiben gebunden. Ein Server, der statt des SHA wieder das volle JSON liefert, wird abgewiesen. Keine automatische Voll-Diff-Ausweichroute. Ref-, Tag- und Commit-Auflösung bleibt beim ursprünglichen Commit-Ref-Endpunkt; ein veränderlicher Branch wird nicht als unveränderlicher Commit ausgegeben.

Offizieller Medienvertrag: https://docs.github.com/en/rest/commits/commits#get-a-commit
Git-Commit-Objekt: https://docs.github.com/en/rest/git/commits#get-a-commit-object

Die Prüfung des TEMDD-Historienstandes und die lokale Writer-Übergabe materialisierten vollständige SQL-Ergebnislisten. Der Ersatz liest dieselben Originalzeilen nacheinander, validiert weiterhin jedes Ereignis aller Subject-Partitionen und erzeugt denselben ursprünglichen kanonischen Frontier-Digest. Die Übergabe vergleicht beide Historien weiterhin zeilenexakt und widerruft den alten Writer vor der Zielzulassung. Kein neues Datenbankschema, kein Journalreset und keine Aufweichung von Eigentümerlock, Writer-Seal oder Admission. Der Python-Speicherbedarf dieser Prüfphase hängt damit von der Größe eines zugelassenen Ereignisses ab statt von der Länge der ganzen Historie. Der vollständige Integritätsscan benötigt weiterhin Zeit proportional zur Historienlänge.

## Reproduktion und Grenzen

DIAGNOSIS.json und die Originalmessungen unter evidence/context-memory/2026-10-24/ binden die Ausgangsquelle. Drei abwechselnde Vergleichsläufe bei 64 und 1024 Ereignissen verwenden dieselbe private SQL-Fixture. Bei 1024 Ereignissen: maximal 20876228 Bytes Python-Allokation zuvor, 32927 Bytes danach; alle Frontier-Digests identisch. Gemessen wurde tracemalloc, weder Prozess-RSS noch SQLite-C-Allokation noch produktive Host-Auslastung. Der alte Reader bleibt als ausschließlich diagnostische Originalquelle erhalten. REPRODUCE_MEMORY_COMPARISON.py wiederholt den Vergleich in frischen privaten Fixtures; es wird nicht als Runtime oder neuer Executor installiert.

20 gezielte datei-/transportbezogene Tests und 132 API-Client-Regressionen bestehen lokal. Der alte lokale Socket-Suitelauf scheiterte in zehn Fällen an gesperrter Socket-Erzeugung; das ist kein reparierter Netzwerkfehler. Die bestehende native QIKVRT CI führt deshalb die vollständigen Wire-, Ledger-, Packaging- und Repository-Gates auf dem tatsächlichen neuen HEAD aus. Die bestehende Self-Host-Paketliste enthält src/qikvrt_temdd_event_ledger.py; der Original-Packager lädt diesen Laufzeitträger.

Diese Reparatur verändert weder den Anbietergrenzwert des Modell-Kontextfensters noch Kontospeicherquoten. Ein allgemeiner physischer OOM als Fehlerursache wurde nicht beobachtet. Rekonstruktion, Nutzerrechte, vollständige Peer-Antworten und produktive Domain-/Runtime-Abnahme behalten ihre eigenen Nachweispflichten. React darf eine Darstellung aus geprüften Daten anpassen; daraus folgt keine Zulassung beliebigen empfangenen ausführbaren Codes.

## Erhaltene offene Veröffentlichung

PR 598 hat den aktualisierten Fachartikel, die Prosa-PDF, Prosaartikel.txt, den reinen Vorlesetext und das 36-Theorem-Beweispaket dauerhaft integriert. Der unveränderte v2-Publisher verlangt für die nach der allgemeinen Aufgabenfreigabe erzeugten neuen Bytes noch das genaue nachfolgende Owner-Ereignis aus release/causal-distance-lean-2026-10-24/EXACT_UPLOAD_DECISION_REQUEST.txt. Es wird kein solches Ereignis erfunden. Nach dessen Eingang ist der vorhandene Editorial-Queue-/Publisher-Pfad zu verwenden; öffentliche Datei- und DOI-Rückprüfung sowie Katalogfortschreibung gehören zum selben Auftrag.

Die erste native Vollprüfung erkannte eine noch auf den alten Ledger- und Testquelltext gebundene Self-Host-Nachfolgerquittung. Der gesamte bisherige Nachweis ist byteidentisch unter evidence/self_host/original-recovered/SOURCE_RECOVERY_SUCCESSOR_before_CONTEXT_MEMORY_20261024.json erhalten. Die vorhandene Nachfolgerquittung bindet die beiden veränderten Träger neu und enthält den gehashten Übergang; keine historische PASS-Übertragung. Der ursprüngliche Fehlerfall und ein zusätzlicher Erhaltungstest bestehen lokal. Die vollständige native Prüfung wird auf dem dadurch tatsächlich geänderten Nachfolger erneut erforderlich.
