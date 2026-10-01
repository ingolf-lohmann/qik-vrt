<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Vollnode, Wiederherstellung, Authority-Rolle und Projektabstammung

Ingolf Lohmann legt am 1. Oktober 2026 fest: Jeder vollwertige QIK-VRT-Node,
Authority wie Mirror, muss den vollständigen angenommenen Mesh-Zustand aus
seinen eigenen erhaltenen Daten verlustfrei wiederherstellen, die aktive
Authority-Rolle übernehmen und weitere Mirrors sowie eigenständige Projekte
anlegen können. Alle abgeleiteten Projekte bleiben hierarchisch unter der
Wurzel `Goldkelch/qik-vrt`. Das ist eine normative Produktanforderung; ihre
Deklaration ersetzt keinen Ausfallversuch oder Effekt-Nachweis.

Der maschinenlesbare Vertrag ist
`policy/QIKVRT_FULL_NODE_RECOVERY_AND_DERIVATION_V1.json`.

## Vollständigkeit und Verlustfreiheit

Die identische 400-Byte-Gesamtsignatur bindet den kanonischen Vertrag. Sie ersetzt
die Nutzdaten nicht. Ein individueller Node besitzt zusätzlich seine eigene
Identität. Ein Git-Clone des Main-Baums genügt nicht: Er kann Historie, andere
Refs, LFS-Objekte, Submodule, Runtime-Payloads, persistente Zustände, Releases,
Artefakte, Issues/PR-Metadaten, Berechtigungen und Scheduler-Zustand auslassen.

Die V1-Signatur wird unverändert aus `ingolf-lohmann/qik-vrt` PR #424 auf HEAD
`def7a93e7ae36426bebaf7b82519b670025f8f42` wiederverwendet. Ihre 400 Byte haben
SHA-256 `27a84a7e19e1b46f50d3a855b87da65f5fe07b806575b0d15ca0587b7cab5792`.
Auch eine neu gehashte fremde 400-Byte-Signatur wird gesperrt. Damit entsteht
keine zweite Standpunktsignatur; Review-, Merge- und Runtime-Evidenz des
Quell-PRs wird durch Byte-Wiederverwendung nicht auf diesen Successor übertragen.

Ein außerhalb des Checkpoints gepinnter und vom Owner geprüfter Closure-Plan
muss alle erforderlichen Abhängigkeiten und ihre exakten Bytebindungen
inventarisieren. Auch verschlüsselte lokale Recovery-Escrows müssen vorhanden
sein. Ein Digest beweist deren Byteidentität, nicht Entschlüsselbarkeit,
Zugriffsrechte oder die Vollständigkeit des Plans. Laufzeit-Selbsttests und
Capability-Readbacks bleiben deshalb zusätzliche Vollnode-Abnahmekriterien.
Der bestehende Seed-Registrierungspfad prüft diese Live-Effekte noch nicht und
sperrt deshalb eine remote behauptete `full_node: true`-Zulassung. Eine normale
Node-Registrierung erklärt den Node nicht zum Vollnode. Ein künftiger
Zulassungs-Successor muss die unabhängigen Nachweise tatsächlich konsumieren.
Klartextgeheimnisse und authentifizierte Sitzungen gehören nicht in öffentliches
Git oder Tool-Caches. Die erzeugten Checkpoint-Verzeichnisse sind privat und
werden durch dieses Werkzeug nicht veröffentlicht.

Der wiederherstellbare Zustand ist an einen angenommenen konsistenten
Checkpoint und seinen Schreib-Watermark gebunden. Soll bei beliebigem Ausfall
des gesamten übrigen Mesh kein angenommener Write verloren gehen, darf ein
Write erst bestätigt werden, nachdem er auf jedem als Vollnode zugelassenen
Node dauerhaft angekommen ist. Ein rückständiger oder getrennter Node verliert
diesen Zulassungsstatus bis zur nachgewiesenen Aufholung. Nicht replizierte
spätere Information lässt sich aus einer älteren Kopie nicht rekonstruieren.

## Ausführbarer Offline-Pfad

`tools/qikvrt_mesh_recovery.py` nutzt die vorhandenen kanonischen Seed-JSON-
Funktionen, die begrenzte Subprozess-Supervision und die bereits eingesetzte
Git-Runtime. Die vorhandene portable Source-Kapsel bleibt unverändert: Ihre
2-MiB-/128-Objekt-/64-Pfad-Grenzen und ihr expliziter Ausschluss einer gesamten
Historie machen sie für vollständige Node-Backups ungeeignet.

Das neue Werkzeug unterstützt:

| Operation | Nachgewiesener Umfang |
| --- | --- |
| `create` | Gepinnter Closure-Plan, exakte 400-Byte-Signatur, alle inventarisierten Refs und erforderlichen Assets; eigenständig restaurierbares Git-Bundle |
| `verify` | Bytebindungen, kanonisches JSON, Kategorien, Abstammung und tatsächlicher Git-Restore in einer leeren temporären Umgebung |
| `restore` | Bare-Repository mit identischem HEAD/TREE und Refs, identische Assets und Signatur, erhaltene Node-Identität; Writer deaktiviert |
| `clone` | Derselbe geprüfte Datenstand, neue Identität aus 256 Zufallsbits, gebundener Parent und Quellcheckpoint; Runtime-Rebinding erforderlich |
| `plan-authority` | Gebundener Recovery-Plan samt noch zu erfüllenden Fencing-, Capability-, CAS- und Readback-Anforderungen |
| `plan-project` | Neue `Goldkelch/<Projekt>`-Identität mit erhaltener Wurzel, Parent und Checkpointbindung; noch zu erfüllende Erzeugungs- und Registrierungsanforderungen |

Beispielaufrufe mit extern verifizierten Digests:

```sh
python3 -B tools/qikvrt_mesh_recovery.py create \
  --repository /node/repository --payload-root /node/checkpoint-payload \
  --plan /node/owner-reviewed-closure.json --expect-plan-sha256 "$PLAN_SHA256" \
  --output /recovery/checkpoint-new
python3 -B tools/qikvrt_mesh_recovery.py restore \
  --checkpoint /recovery/checkpoint-new --expect-manifest-sha256 "$MANIFEST_SHA256" \
  --output /recovery/restored-node-new
```

Der Payload enthält `QIKVRT_SIGNATURE.bin` mit exakt 400 Byte und die im Plan
vollständig inventarisierten Dateien. `validate_plan` ist die ausführbare
V1-Feldsemantik: unbekannte Felder, doppelte JSON-Schlüssel, nichtkanonisches
JSON, unsichere Pfade, fehlende Kategorien und uneindeutige Identitäten werden
zurückgewiesen. Der Digest des Manifests ist dessen Checkpoint-Identität und muss
vor der Wiederherstellung aus einer vertrauenswürdigen Quelle vorliegen.

Das Werkzeug führt weder Network-Fetch noch den restaurierten Programmcode aus.
Es deaktiviert Lazy-Fetch, Replacement-Objekte, Hooks und globale Git-Konfiguration.
Shallow-/Partial-Clones, externe Alternates, Grafts und symbolische Non-HEAD-Refs
werden gesperrt. Ein Bundle wird in einer leeren Umgebung restauriert und mit
`fsck` geprüft; inkrementelle Bundles mit fehlenden Vorläufern bestehen diese
Prüfung nicht. Bestehende Ausgabeziele werden nicht überschrieben. Unvollständige
Ausgaben und überschüssige Dateien bestehen die Prüfung nicht.
`git.required_objects` bindet außerdem historische Git-Objekte außerhalb der
aktuellen Main-Historie. Diese müssen vor dem Export an dauerhafte Recovery-Refs
gebunden werden und nach dem leeren Restore mit identischem Typ verfügbar sein.
Bloße Verfügbarkeit im Quell-Object-Store oder `FETCH_HEAD` genügt nicht.

Die V1-Kapazitätsgrenzen stehen in der Policy. Größere Zustände benötigen einen
versionierten Kapazitäts-Successor; die Grenzen dürfen nicht durch eine falsche
Vollnode-Erklärung umgangen werden. Geschützte Secret-Backups werden lediglich
als opake Bytefolgen transportiert. Der Restore erzeugt ein Bare-Repository;
Bootstrap, Runtime-Start und Secret-Unseal sind separate, noch zu prüfende Schritte.

## Authority-Rolle und bleibende Wurzel

Die aktive Authority ist eine übernehmbare Betriebsrolle. Die historische und
organisatorische Wurzel bleibt `Goldkelch/qik-vrt`, auch wenn ein Mirror die
aktive Rolle übernimmt. Ein Verbindungsfehler beweist keinen Gesamtausfall und
erlaubt keine konkurrierende Authority. Recovery benötigt eine exklusive
Writer-Sperre oder eine bereits delegierte Owner-Recovery-Freigabe mit technisch
durchgesetztem Single-Writer-Verhalten, ein frisches Control-Plane-Epoch,
targetgebundene nutzbare Rechte, atomaren Epoch-CAS und frischen Effekt-Readback.
Ein aus dem Backup stammendes Epoch ist keine Beobachtung des aktuellen Epochs.

Eine zurückkehrende alte Authority wird vor Schreibzugriff vom alten Epoch
ausgeschlossen und als Mirror wieder angeschlossen. Die Wiederherstellung darf
keine History überschreiben oder frühere Reviews auf einen neuen Head übertragen.

## Klonen und eigenständige Projekte

Ein neuer Mirror erhält eine eigene Node-Identität; ein neues Projekt zusätzlich
eine neue Repository- und Projektidentität. Beide erhalten dieselbe globale
Signatur und dieselben geltenden Wurzel-Invarianten. Das neue Projekt wird vor
Aktivierung create-only im Graphen der Goldkelch-Wurzel registriert. Zu binden
sind Parent-Repository, Parent-Node und Quellcheckpoint. Die Abstammung bleibt
bei späterer eigenständiger Entwicklung erhalten.

Die logische Hierarchie liegt im versionierten Projektgraphen; konkrete GitHub-
Projektziele haben die Form `Goldkelch/<Projekt>`. Das Werkzeug erzeugt einen
entsprechenden Plan und prüft die Wurzelbindung. Es behauptet weder Root-
Registrierung noch Existenz eines GitHub-Repositories durch das Vorliegen des
Plans. Diese Effekte benötigen einen ausführbaren autorisierten Erzeugungspfad
und frischen Readback von Root-Register und neuem Repository.

## Scheduling im Digital Twin

Der Scheduler gehört zur wiederherzustellenden Datenmenge: Definition, Zeitzone,
Owner/Target, nächster Termin, letzter abgeschlossener Cursor, offene Work Units
und Idempotenzschlüssel. Nach dem Restore muss der neue Authority-Writer diesen
Zustand mit dem tatsächlichen Provider abgleichen, damit erledigte Wirkungen
nicht doppelt ausgeführt und ausstehende Aufgaben nicht vergessen werden.
Identische Scheduler-Dateien sind noch kein gestarteter Provider-Schedule.

## Evidenzgrenze

Die Regressionen zerstören den Fixture-Quellnode nach dem Checkpoint und
restaurieren aus dem allein verbleibenden Paket. Sie prüfen außerdem
Manipulation, fehlende Daten, inkrementelle Bundles, neue Clone-Identitäten,
Scheduler-Byteidentität und Wurzelverletzungen. Das ist technische Evidenz für
den Offline-Vertrag innerhalb dieser Fixtures. Der reale Produktionsnode wird
damit nicht automatisch als Vollnode zugelassen. Seine gesamte Closure,
kanonische Signatur, Runtime, Recovery-Capabilities, Authority-Übernahme,
Scheduler-Wirkungen und GitHub-Projekterzeugung brauchen eigene frische Evidenz.

## Ausführbarer, gefenceter Rollenwechsel (PR #428 Successor)

`tools/qikvrt_authority_transition.py` ergänzt den Offline-Pfad mit einer
persistenten lokalen Control Plane und einem tatsächlich schreibenden Effekt-Sink.
Die Wiederverwendungssuche fand im bisherigen Recovery-, Seed- und Workflow-Pfad
keinen atomaren Authority-Epoch-/Writer-Fence-Sink. Der Adapter verwendet deshalb
die bestehenden Recovery-Prüfer, den strikten kanonischen Seed-JSON-Vertrag und
Python `sqlite3`; ein zusätzliches CLI oder Drittanbieterpaket ist nicht nötig.

Die aktive Rolle steht ausschließlich in der Control Plane. `node.json` bleibt
ein unveränderter Offline-Restore-Nachweis mit `writer_enabled=false`. Der Adapter
ändert weder die permanente Wurzel noch historische Policies und Receipts.

| Operation | Tatsächlicher Effekt / Sperre |
| --- | --- |
| `init` | Separates create-only Owner-Bootstrap eines privaten Sinks mit explizitem Anfangsepoch; keine automatische Recovery fehlender Control Planes |
| `grant` | Authentifizierter Owner-Grant für tatsächlich geprüfte Node-Identität, Manifest, Repository, HEAD/TREE und Scheduler; aktuelles Epoch, noch kein Writer |
| `observe` | Authentifizierte, 30 Sekunden gültige, einmalig konsumierbare aktuelle Epoch-/Revision-/Target-Beobachtung; Backup-Epoch ist kein Ersatz |
| `takeover` | Atomarer CAS des vollständigen beobachteten Zustands; Epoch + 1, neuer Fence, bisherige Authority als Mirror gesperrt, Successor `PENDING_READBACK` |
| `activate` | Frische Prüfung der restaurierten Bytes und dauerhaften Post-CAS-Rolle samt Scheduler; erst dann aktive Authority am angegebenen Sink |
| `write` | Persistiert tatsächliche Nutzbytes mit Idempotenzschlüssel; Capability, Epoch, Fence und aktive Rolle werden im selben Commit-Lock geprüft; anschließender frischer Byte-Readback |
| `rejoin` | Alte Authority bleibt Mirror, Writer gesperrt; Catch-up erforderlich, keine implizite Vollnode-Zulassung |
| `readback` | Authentifizierter aktueller Rollen-/Epoch-/Target-Zustand |

Der Sink muss unabhängig von der bisherigen Authority erhalten bleiben. Seine
SQLite-Datei liegt in einem owner-exklusiven POSIX-Verzeichnis (0700), die Datei
ist 0600 und darf keine Symlinks/Hardlinks haben. Alle Mutationen dieses Sinks
müssen die Adapterprüfung durchlaufen. Datenbank-Owner/Admin-Zugriff ist die
Vertrauensgrenze. Ein Rollback, eine Kopie des Sinks oder eine Wiederherstellung
des Control-Plane-Epochs aus einem Backup ist unzulässig. Ohne diese
Voraussetzungen gibt es keinen Split-Brain-Schutz; ein fehlender Sink wird
gesperrt und nicht selbstständig neu initialisiert. Das Werkzeug behauptet
keinen Schutz vor einem privilegierten Administrator oder einem externen
Writer mit unabhängigen GitHub-/Provider-Rechten.

Der Owner provisioniert den Sink und den separaten Recovery-Grant vor dem
Ausfall oder aus einer erhaltenen unabhängigen Administrationsroute. Eingabe
ist eine tatsächlich nutzbare, targetgebundene, privat entschlüsselte Capability
als 0600-Datei. Der Adapter verifiziert deren Verwendung gegen den tatsächlichen
Sink. Er implementiert keine allgemeine Escrow-Entschlüsselung und akzeptiert
keinen behaupteten Unseal-Erfolg. Ein Grant gilt ausschließlich für das beim Owner-Grant frisch gelesene Epoch;
ein konkurrierender Verlierer benötigt für einen späteren Wechsel einen neuen
Owner-Grant. Tokens werden weder ausgegeben noch in Git
geschrieben. Im Sink stehen nur ihre SHA-256-Bindungen.

Beispiel nach Provisionierung/Grant; `$NODE` bezeichnet den verifizierten
Restore, `$CP` den erhaltenen privaten Sink, `$CAP` dessen private Capability:

```sh
python3 -B tools/qikvrt_authority_transition.py observe \
  --control-plane "$CP" --token-file "$CAP" --node "$NODE" \
  --expect-manifest-sha256 "$MANIFEST_SHA256" > observation.json
python3 -B tools/qikvrt_authority_transition.py takeover \
  --control-plane "$CP" --token-file "$CAP" --node "$NODE" \
  --expect-manifest-sha256 "$MANIFEST_SHA256" --observation observation.json > takeover.json
```

`activate` konsumiert das `permit`-Objekt aus dem Takeover-Resultat als
kanonische JSON-Datei zusammen mit demselben Node/Manifest/Capability-Target.
Ein Prozessabbruch zwischen CAS und Aktivierung lässt beide Writer gesperrt.
Nach Neustart wird derselbe dauerhafte Successor frisch gelesen und aktiviert;
bei konkurrierendem Successor wird das alte Permit zurückgewiesen. Ein Write,
der vor dem CAS committen konnte, verändert die Revision und macht die alte
CAS-Beobachtung ungültig. Nach dem CAS kann kein alter Writer committen.

HEAD/TREE und Scheduler-Cursor dürfen gegenüber dem akzeptierten Sink-Zustand
nicht zurückfallen. Der Rollenwechsel bindet Scheduler-Owner neu, erhält
Cursor, offene Work Units und Idempotenzschlüssel und bewahrt alle bereits
committeten Sink-Effekte. Derselbe Schlüssel mit anderen Bytes wird gesperrt.
Dies ist lokale Scheduler-/Ledger-Reconciliation, kein behaupteter Kalender-
oder Provider-Schedule-Erfolg. Restore-Dateien müssen unter dem vertrauenswürdigen
lokalen Owner während der Abnahme unveränderlich gehalten werden.

Der neue Test zerstört frühere Authority, Quelle, Payload und Checkpoint-Pakete
vor dem Takeover. Er prüft konkurrierende Takeovers und Writes, stale Epochs,
Observation-Replay/Timeout/Clock-Rollback, Capability- und Target-Drift, Rejoin,
Old-Writer-Rejection, Scheduler-Rebinding, Prozessneustart und tatsächliche
CLI-Sink-Effekte. Das ist ausführbare Evidenz für den lokalen POSIX-Sink.
Remote-GitHub-Fencing, Runtime-/Provider-Unseal, globale Replikation/Vollnode-
Zulassung und Root-Projekterzeugung bleiben separat zu integrieren und frisch
zu beweisen. Alle Resultate führen `effect_ack_done=false`; Test-/CI-Erfolg
und lokaler Sink-Erfolg ergeben kein globales `EFFECT_ACK_DONE`.
