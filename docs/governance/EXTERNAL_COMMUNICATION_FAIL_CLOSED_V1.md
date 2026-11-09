# Externe Kommunikation: fail-closed Versand- und Fehlerstandard (Owner-Anweisung 2026-11-09)

Status: normativer Änderungskandidat, bis Review/Merge nicht als auf main aktiviert behaupten.

## Verpflichtende Zustandsunterscheidung

Für jede externe Korrespondenz die Zustände DRAFT, SUBMISSION_ACCEPTED, SENT_ITEM_VERIFIED, DELIVERY_CONFIRMED, ATTACHMENTS_VERIFIED und RECIPIENT_ACK getrennt führen. Ein API-Ergebnis `null` oder HTTP-Erfolg bestätigt nur die Annahme des jeweiligen Auftrags, nicht die Zustellung. Ein gespeicherter Entwurf ist niemals ein Versandbeleg. Keine Behauptung von Versand, CC, Anhang oder Wirkung ohne passenden Readback.

## Prüf- und Versandfolge

1. Originalkorrespondenz und vollständige Empfänger-/Absenderidentität lesen; keine fremde Absenderadresse erfinden.
2. Betreff, Quellen, Versionsstand, Fakten, Lizenz und externe Aussagen prüfen; unsichere Claims fail-closed kennzeichnen.
3. Originalanhänge bevorzugen; bei fehlenden Dokumenten aus belegten Quellen neu erzeugte Fassungen deutlich als Rekonstruktion ausweisen. Dateinamen, Seitenzahl, Öffnbarkeit, SHA-256, Umfang und inhaltliche Übereinstimmung vor Versand prüfen.
4. Die im Auftrag verlangte CC-Adresse ausdrücklich setzen. Für Outlook ausschließlich Outlook verwenden; Gmail nicht als stillen Ersatz.
5. Nach Versand den Ordner 'Gesendete Elemente' auf exakt diese Nachricht prüfen: Empfänger, CC, Betreff, Zeit, Text und Anhangsnamen. Zustellung nicht aus Sent Items ableiten.
6. Einen separaten Entwurf als DRAFT melden und nicht mit gesendeter Nachricht verwechseln. Keine Dubletten versenden, bevor die gesendete Korrespondenz geprüft ist.

## Fehlerdiagnostik (keine Rätselraten-Berichte)

Jede Blockade enthält: betroffene Aktion, erwartetes Ergebnis, tatsächlich beobachteten Zustand, konkrete Ursache (oder ausdrücklich unbekannt), Quelle/Prüfmethode, kleinsten behebbaren nächsten Schritt und unverändert offene Gates. Keine Erfolgsmeldung bei Teilerfolg. Ein HTTP 504 an einem Quellenlink bedeutet keine verifizierte Dateiverfügbarkeit. Fehlende Dateibytes nicht durch Linknamen ersetzen.

## Abnahme

Dieser Standard regelt externe Kommunikation, nicht QIK-VRT-Release-/Governance-Zulassung, Originalhost-EAP, sicherheitstechnische Pilotabnahme oder EFFECT_ACK_DONE. Änderungen bleiben bis Exact-HEAD-CI, Review und Merge reversibel.
