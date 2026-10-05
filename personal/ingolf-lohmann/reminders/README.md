<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright (c) 2026 Ingolf Lohmann. -->

# Persönliche Erinnerungen

Owner-Auftrag vom 5. Oktober 2026: Erinnerungen werden grundsätzlich im
Repository hinterlegt und durch dessen Laufzeit ausgeführt. Keine neue lokale
ChatGPT-Automation anlegen. Diese Regel gilt für künftige Erinnerungsaufträge,
solange Ingolf Lohmann nichts anderes bestimmt; bestehende fremde Aufgaben
werden dadurch nicht geändert oder übernommen.

`OWNER_REMINDERS_V1.json` ist die versionierte Auftragsquelle. Der bestehende
`.github/workflows/qikvrt_workflow_executor.yml` ruft den kleinen Reminder-Adapter
auf. Ein GitHub-Kommentar mit Owner-Erwähnung ist der Benachrichtigungskanal;
der Controller sendet weder E-Mails noch Zahlungen. Die persönlichen Details
liegen ausschließlich hinter authentifizierten privaten Datei-Verweisen.

## Annahme und Idempotenz

- Der Auftrag bindet Repository, Owner, Zeitpunkt mit Zeitzone, Version,
  private Artefaktidentitäten, Inhalts-Hashes und Annahmekriterium.
- Vor Fälligkeit und bei `COMPLETED`/`CANCELLED` wird nichts zugestellt.
- Nur ein `main`-Ereignis mit genau ausgechecktem Event-Commit darf zustellen.
  Der aktuelle `main`-Head wird vor Zulassung erneut gelesen.
- Der Hash des vollständigen Auftrags bindet einen ausschließlich neu
  anlegbaren Ref `receipts/owner-reminders/<hash>`. Ein bestehender Ref ohne
  zurückgelesenen Kommentar bedeutet `HOLD`; kein blinder zweiter Versand.
- Nur ein bytegleich zurückgelesener Kommentar von `github-actions[bot]` am
  gebundenen Commit zählt als technisch zugestellt. Seine ID und URL werden
  im Laufartefakt gesichert. Das beweist weder Lesen noch Aufgabenerledigung.
- Neue Inhalte erhalten eine neue Version und neu geprüfte Evidenz. Eine
  erneute Zustellung bedarf eines konkreten erneuerten Owner-Auftrags.
- Erledigung benötigt Ingolfs Bestätigung samt geeignetem Beleg. Eine
  Zahlung bleibt bis zu ihrer persönlichen Freigabe und Bankbestätigung offen.
- Nach Abschluss werden erledigte Einträge geschlossen. Der bestehende
  Executor bleibt für seine bisherigen Aufgaben bestehen.

## Datenschutz und Wiederverwendung

Das Repository ist öffentlich. Keine Gesundheitsdaten, Zahlungsdaten,
Privatadressen, Rechnungen, Telefonlisten oder fremden Projektunterlagen
einchecken. Nur neutrale Labels und private authentifizierte Verweise zulassen.
Der bestehende Executor und seine Provisionierung werden wiederverwendet;
es entsteht kein zusätzlicher Scheduler. Die bestehenden no-effect Mesh- und
Watchdog-Verträge bleiben unverändert. Die Owner-Erinnerung ist ein separat
gebundener Effekt und keine Aktivierung eines Mesh-Nodes.

Der zusätzliche tägliche Termin ist 08:30 `Europe/Paris`; die bestehende
stündliche Prüfung holt überfällige offene Einträge nach. GitHub kann geplante
Läufe verzögern. Aktivierte Konfiguration, erfolgreicher Lauf, tatsächliche
Benachrichtigung und menschliche Annahme müssen gesondert belegt werden.

## Tagesplan

Der persönliche Tagesplan ist über `DAY_PLAN_2026-10-06.md` mit seinem privaten
Endartefakt gebunden. Uhrzeit und Treffpunkt offener Termine werden nur nach
Bestätigung als fest vereinbart bezeichnet. Keine technische Entwicklungsarbeit
wird als persönliche Reisevorbereitung ausgegeben.

Prüfen: `make owner-reminders-test`; vollständiges Gate: `make test`.
Vorschau ohne Wirkung: `python3 -B tools/qikvrt_owner_reminders.py`.
