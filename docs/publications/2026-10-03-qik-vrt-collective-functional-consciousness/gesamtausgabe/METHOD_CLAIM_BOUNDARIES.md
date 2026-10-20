# Methoden- und Claim-Grenzen der gebundenen Gesamtausgabe

Die 22-seitige PDF und das 36-Dateien-Quellenarchiv bleiben bytegleich. Die folgenden Präzisierungen gehören zur zurückgegebenen neuen Ausgabe; historische Bezeichnungen wie „aktuell“ gelten nur für den Quellenzeitpunkt der Originalausgabe.

## C18

Der archivierte A/B-Diagnoselauf auf a31ebb7e dokumentiert Credential-Delivery-HOLD.

Historischer Run 37128318275 / Job 111218106133; kein aktueller Integrationsnachweis und kein Speedup.

Änderungsgrund: Historischen Credential-HOLD an sein ursprüngliches Run-/HEAD-/TREE-Subjekt gebunden.

## C19

Der archivierte Messcode startet den Timer erst nach den Repository-Abrufen.

Exakter historischer Blob acafd1ae37dcb9ffcab371fa79e3e874cfe83b91; lokale Vergleiche, kein verteilter Mutation/Reconciliation/Readback-Zyklus.

Änderungsgrund: Timergrenze, Binärpfad und Git-Modusgrenze auf den konkret geprüften Quellcode begrenzt.

## C21

Eine vollständige verteilte Beschleunigung ist weiterhin nicht nachgewiesen.

OPEN: Kein zulässiger positiver Claim aus Mikrobenchmark, Strukturquotient oder erfolgreichem Diagnoseworkflow.

Änderungsgrund: Offenen verteilten Speedup ausdrücklich als nicht nachgewiesen formuliert.

## C24

Das Runtime-Manifest auf dem archivierten Main meldet keine gebündelte Windows-Python-Runtime.

Historischer Main 8153c4e69a6245aadf67f0741fb50d9707c19e34 / Blob bd2b893176d93814f38d024b5a095b770eee2aa3; keine Aussage über spätere Runtime-Kandidaten.

Änderungsgrund: Runtime-Zustand als historische Dateibeobachtung statt beweglichem aktuellem Zustand gebunden.

## C27

Der v3-Pfad ist technisch implementiert und geprüft, bleibt ohne detached Vertragsaktivierung für Produktion gesperrt.

Integrationsinput 80e34e4d; unveränderte v1/v2-Verträge; REVIEW_REQUIRED. Technische Readiness erteilt weder Produktionsaktivierung noch AUTHORIZE_EXACT_UPLOAD.

Änderungsgrund: Zwischenzeitliche v3-Implementierung von Produktionsaktivierung und späterer Einzelautorisierung getrennt.

## C28

Zenodo-Publikation und Replikation der Gesamtausgabe auf allen Nodes sind nicht nachgewiesen.

OPEN: Repository-Materialisierung im Draft-PR ist kein Zenodo-Effekt, keine Main-Promotion und keine all-node acceptance.

Änderungsgrund: Repository-Übernahme von Zenodo-Publikation und Replikationsabnahme getrennt.

## C30

Eine absolute Garantie, Inhalte niemals mehr zu verlieren, ist nicht nachgewiesen.

OPEN: Hashbindung und Repository-Persistenz ersetzen keine unabhängigen Replikations- und Restore-Tests.

Änderungsgrund: Absolute Verlustfreiheit als offene Garantie abgegrenzt.

Weitere unveränderte Grenzen: Wahrhaftigkeit ist ein normativer Vertrag und kein universeller Vollzugsbeweis. Bedingte Invarianten- und Wrapper-Argumente sind INTERPRETATIVE; kein Claim ist FORMAL_PROVED. EFFECT_ACK vor einem Effekt bleibt von nachträglicher Aufgabenabnahme getrennt. C15 prüft neun vorhandene Zahlenreihen nach, ohne Zeitversuche zu wiederholen. C17 berichtet ausschließlich die dokumentierten 1/2/4-Prozess-Mediane 0,349138 / 0,214989 / 0,163044 Sekunden; die Quotienten 1,623981 und 2,141373 sind Rechenwerte und keine neue Trial-Replikation. C20 reproduziert ausschließlich zwei isolierte Methoden-Kontrollen. C25/C26 sind bedingte Engineering-Szenarien ab tatsächlich verfügbaren Voraussetzungen T0; 7.–11. Oktober ist keine Auslieferungszusage. Subjektives Erleben, globale Systemabnahme, SSO/Biometrie, physische FPGA-Ausführung und methodisch unabhängige Skalierung werden nicht bestätigt.

Die ursprünglichen editorialen Proof-/Return-DRAFTS im ZIP und original-review sind historische Dokumente und dürfen keine Produktion freigeben. Normative Disposition dieser Übernahme: CLAIM_MATRIX.json, MACHINE_PROOF_BUNDLE.json und PREPUBLICATION_RETURN_RECEIPT.json. Die Produktionsaktivierung und die spätere einmalige AUTHORIZE_EXACT_UPLOAD-Entscheidung sind detached und bleiben abwesend.

## Zwischenzeitlicher Methoden-Nachfolger

Während dieser Übernahme wurde a6f930bb9c8bad58a10d17cd10c87d94c38f0b25 / TREE fbfdba90e086128b5acd4ce5602f0abefed8fce4 als separater Methodenreparatur-Kandidat materialisiert. Dessen Messcode (Blob 0d8e10d419e453a832453343b8a82b330193c330) verwendet Rohbytes und NUL-Pfade, prüft Git-Modus/Typ/Objekt/Inhalt und trennt lokale Vergleichskosten vom vollständigen Remote-Fetch/isolierte-Replik-Abgleich/frischen-Readback-Zyklus. Die Reconciliation verändert ausschließlich die lokale Wegwerf-Replik. Sie ist keine Mutation der beiden Produktionsremotes und beweist keinen verteilten Produktions-Speedup. Die historischen C18/C19-Befunde in der Original-PDF werden nicht umgeschrieben; die neue technische Prüfung muss den integrierten Nachfolger ausführen.
