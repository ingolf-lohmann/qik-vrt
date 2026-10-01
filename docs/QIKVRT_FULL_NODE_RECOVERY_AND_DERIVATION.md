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
