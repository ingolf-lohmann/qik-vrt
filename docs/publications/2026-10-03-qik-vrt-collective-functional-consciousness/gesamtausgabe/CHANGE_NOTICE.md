# Sichtbarer Änderungsvermerk: Übernahme der Gesamtausgabe

Die bereits zurückgegebene PDF (SHA-256 c82e9182dc2b6068b2d7a70edbd4c3696557813aa8859e92c72a865a46256cce) und das Quellenprüfpaket (SHA-256 ed6a224db353c7bacb3b24f2231feb2eb4ea992affa10d397937a0ff074246b4) wurden tatsächlich abgerufen und bytegenau geprüft. Alle 36 Archivdateien, einschließlich der historischen Quellen und Entwürfe, werden unverändert unter original-review erhalten. Kein Ersatzbild und keine rekonstruierte PDF wird verwendet.

Die Gesamtausgabe wird als eigene Ausgabe im bestehenden PR-#447-Publikationspfad integriert. Sämtliche bereits bestehenden Drei-Seiten-Paketdateien auf dem Integrationsinput 80e34e4d / TREE ace1e64a bleiben unverändert. Zwischen dem Ausgangsstand a31ebb7e und diesem Input hatte eine separate v3-Migration des Drei-Seiten-Kandidaten stattgefunden; diese Übernahme schreibt weder diese Arbeit noch historische Commit-Bytes um. Beide Zustände bleiben über ihre Git-Historie nachvollziehbar.

Die vorhandenen v3-Prüfer und der vorhandene Publisher werden wiederverwendet. Der strikte v2-Default und sämtliche eingefrorenen v1/v2-Policy-/Schema-Bytes bleiben unverändert. Die native v3-Vertragsregression wurde vor dieser Übernahme mit 88 erfolgreichen Tests geprüft. Das ist technische Konsistenz, keine Produktionsaktivierung. Es werden kein Upload-Request, kein Aktivierungsdokument und keine Owner-Upload-Entscheidung erzeugt.

Die Original-PDF/Prosa bleiben eine historische redaktionelle Aussage. Die folgende korrigierte Disposition und das mitgelieferte METHOD_CLAIM_BOUNDARIES.md gelten für die Übernahme:

- C18: Historischen Credential-HOLD an sein ursprüngliches Run-/HEAD-/TREE-Subjekt gebunden.
- C19: Timergrenze, Binärpfad und Git-Modusgrenze auf den konkret geprüften Quellcode begrenzt.
- C21: Offenen verteilten Speedup ausdrücklich als nicht nachgewiesen formuliert.
- C24: Runtime-Zustand als historische Dateibeobachtung statt beweglichem aktuellem Zustand gebunden.
- C27: Zwischenzeitliche v3-Implementierung von Produktionsaktivierung und späterer Einzelautorisierung getrennt.
- C28: Repository-Übernahme von Zenodo-Publikation und Replikationsabnahme getrennt.
- C30: Absolute Verlustfreiheit als offene Garantie abgegrenzt.

Die Claim-Matrix deckt 30 große Aussagegruppen ab; sie behauptet keine vollständige semantische Zertifizierung aller natürlichen Sprachsätze. Alte DRAFTS werden nicht zu gültigen v3-Receipts umetikettiert. Der neue v2-Return bindet die finalen Kandidatenbytes; der immutable v3-Proof bindet die Readiness und die Upload-Closure. Der detached Paketmanifest bindet Proof/Return/Boundary-Report ohne Selbsthash-Zirkel. Neue Exact-Head-Validierung ist erforderlich; PREDECESSOR_EVIDENCE_TRANSFER=false. Keine Veröffentlichung und kein Verbrauch von AUTHORIZE_EXACT_UPLOAD.

## Zwischenzeitlicher Methoden-Nachfolger

Während dieser Übernahme wurde a6f930bb9c8bad58a10d17cd10c87d94c38f0b25 / TREE fbfdba90e086128b5acd4ce5602f0abefed8fce4 als separater Methodenreparatur-Kandidat materialisiert. Dessen Messcode (Blob 0d8e10d419e453a832453343b8a82b330193c330) verwendet Rohbytes und NUL-Pfade, prüft Git-Modus/Typ/Objekt/Inhalt und trennt lokale Vergleichskosten vom vollständigen Remote-Fetch/isolierte-Replik-Abgleich/frischen-Readback-Zyklus. Die Reconciliation verändert ausschließlich die lokale Wegwerf-Replik. Sie ist keine Mutation der beiden Produktionsremotes und beweist keinen verteilten Produktions-Speedup. Die historischen C18/C19-Befunde in der Original-PDF werden nicht umgeschrieben; die neue technische Prüfung muss den integrierten Nachfolger ausführen.
