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

## Scope of the API successor in PR #436

This API successor ports the existing recovery/control-plane and create-only
provider broker dependencies from PR #428, source HEAD
`2e90c2a4ded011cce37acfc8d6947bf4dba3a10f`. It extends that same broker
with the bounded reflexive Digital Twin receipt operation described in
`policy/QIKVRT_DIGITAL_TWIN_REST_CONTRACT_V1.json`. The sections on the
repository-wide No-Bypass inventory describe PR #428's separate candidate;
that inventory, credential withdrawal and global source deactivation are not
activated by this port. Full-node, productive provider fencing and product
acceptance remain unverified. No predecessor test/review evidence transfers.


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

## GitHub-Provider-Stufe: vorhandener API-Shim als Capability-Broker

Der Successor erweitert `src/qikvrt_github_api_shim.py` und dieselbe private
`AuthorityControlPlane`. Es gibt keinen zweiten Executor, Credential-Cache oder
neuen Schreibdienst. Der bestehende Shim prüft zuerst seinen zeitlich begrenzten
Bearer, Repository-Scope, Rate-Limit und strikten JSON-Vertrag. Der neue lokale
Pfad ist `POST /repos/ingolf-lohmann/qik-vrt/qikvrt/authority/effects`.
Dieser Pfad ist eine Shim-Erweiterung, kein nativer GitHub-Endpunkt.

V1 lässt ausschließlich `{"operation":"create_ref","effect_id":"<stabiler Schlüssel>"}`
zu. Ein zusätzlicher SHA, Branchname, API-Pfad oder unbekanntes Operationsfeld
wird zurückgewiesen. Die Branch-Ref wird deterministisch erzeugt:

`refs/heads/work/qikvrt-recovery/<control_plane_epoch>/<authority_epoch>/<node_id>/<fence>/<SHA256(effect_id)>`

Ihr Commit ist ausschließlich der akzeptierte restaurierte HEAD. Sein TREE
wird gegen den tatsächlichen GitHub-Git-Data-Readback geprüft. Der Provider-CAS
ist die native create-only Transition **Ref fehlt → Ref entsteht**. Weder
Force-Push noch Ref-Update, Löschung, PR-Erzeugung/-Merge, Workflow-Dispatch oder
Ruleset-Änderung ist über diesen Pfad erlaubt. Sie benötigen eigene belastbare
CAS-/Idempotenz-/Readback-Verträge; ein GET vor einem unbedingten PATCH wäre
kein atomarer expected-old-HEAD-CAS.

Die private Writer-Capability authentifiziert den konkreten Node gegen die
Control Plane. Vor jeder zugelassenen Mutation werden Capability, aktuelle
Control-Plane-Epoch, Authority-Epoch, Node, vollständige Target-Bindung, Fence
und aktive Rolle frisch geprüft. Die Prüfung und der Provider-Schreibaufruf
halten dieselbe SQLite-Transaktionssperre wie `takeover`. Auch der private
HTTP-Transport verlangt eine aktuelle gesperrte Admission und exakt die
persistierte Intent-Bindung; er bietet keinen ungebundenen POST-Pfad.

Die additive Tabelle `provider_effects` im vorhandenen Sink enthält keine
Capabilities, sondern Intent und begrenzten Receipt:

| Zustand | Bedeutung und Recovery |
| --- | --- |
| `PREPARED` | Dauerhafter Intent vor jedem Provider-Aufruf; noch kein POST zugelassen. Neustart darf nur denselben Preflight wieder aufnehmen. |
| `PENDING` | Dauerhafte einmalige Dispatch-Zulassung, vor dem POST committet. Neustart/Replays führen ausschließlich GET-Readbacks aus. |
| `VERIFIED` | Tatsächlicher Ref-Readback, Commit-/TREE-Readback und separat rückgelesener dauerhafter Receipt. Replay prüft den Provider erneut. |
| `REJECTED` | Vorbestehende Ref, Target-Drift oder definitive native CAS-Ablehnung. Derselbe Schlüssel bleibt konsumiert; eine passende konkurrierende Ref wird nicht als eigener Erfolg übernommen. |

`PREPARED`/`PENDING` sperren neue Mutationen und Authority-Takeover. Insbesondere
ist ein Timeout kein Beweis, dass kein Schreibauftrag mehr unterwegs ist.
Bei `PENDING` plus fehlendem Readback wird weder erneut geschrieben noch der
Fence freigegeben. Der kleinste nächste Schritt ist GET-Reconciliation nach
nachweislichem Abschluss des ursprünglichen Provider-Auftrags. Wenn dieser
Nachweis nicht gelingt, ist unabhängige Owner-/Provider-Recovery erforderlich;
eine automatische Löschung des Journals wäre ein Exactly-once-Bypass.
Ein alter Writer wird nach Takeover auch mit kopiertem aktuellem öffentlichem
Permit zurückgewiesen. Rejoin gibt ihm keine Provider-Schreibrechte.

Der Broker verwendet den vorhandenen `GITHUB_TOKEN`-Umgebungspfad und den
No-Redirect-/Response-Limit-Vertrag aus `scripts/qikvrt_api_client.py`.
`QIKVRT_GITHUB_TOKEN_EXPIRES_UTC` muss eine zukünftige UTC-Zeit sein; Provider-
und Shim-Bearer müssen verschieden sein. Die UTC-Angabe ist eine vertrauenswürdige
Broker-Konfiguration, keine unabhängig attestierte Token-Metadatenprüfung.
Provider-Fehlertexte und Credentials werden nicht ausgegeben/persistiert.
`QIKVRT_AUTHORITY_CONTROL_PLANE` bezeichnet die vorhandene absolute private
SQLite-Datei. Produktionsbetrieb benötigt eine owner-provisionierte, für den
Mirror und Contents-Schreibrecht begrenzte kurzlebige GitHub-Capability, HTTPS
und den bisherigen nicht umgehbaren, unabhängig erhaltenen Control-Plane-Sink.

**Nachweisgrenze:** Der Adapter implementiert Broker-Fencing für diese eine
Operation. GitHub interpretiert selbst keine QIKVRT-Epochs. Historische Workflow-
Tokens, direkte Git-Pushes, unabhängig ausgegebene Credentials, privilegierte
DB-Owner und nicht durch den Broker geführte Writer werden dadurch nicht
widerrufen. Eine produktive, repositoryweite Fencing-Behauptung benötigt
zusätzlich die nachgewiesene Umleitung aller relevanten Schreibpfade und
providerseitigen Entzug ihrer Bypass-Capabilities. Diese Stufe installiert oder
behauptet das nicht. `Goldkelch/qik-vrt` wird unabhängig von Lineage und
Environment-Variablen vor jedem Providerzugriff abgewiesen; dafür besteht hier
keine separat nachgewiesene Capability.

Die Tests verwenden eine separate dauerhafte Bare-Git-Provider-Fixture mit
realem `git update-ref <ref> <sha> <zero-oid>`-CAS, tatsächlichen Ref-/TREE-Reads
und dem bestehenden TCP/IP-Shim. Zusätzlich prüfen sie den produktiven
HTTPS-Transport mit gebundenen Response-Fixtures. Das ist Test-Evidenz,
kein produktiver GitHub-/Authority-Readback. Jede Ausgabe behält
`effect_ack_done=false` und `provider_authority_fencing_verified=false`.

Primärquellen für den Providervertrag (abgerufen 2026-10-01):
[GitHub REST Git references](https://docs.github.com/en/rest/git/refs?apiVersion=2022-11-28)
und [GitHub REST Git commits](https://docs.github.com/en/rest/git/commits?apiVersion=2022-11-28).


## No-Bypass-Stufe: aktuelle Quellpfade sperren und inventarisieren

Der bestehende Control-Plane-Adapter besitzt mit `audit-writers` einen
lesenden Source-Admission-Gate; `make test` führt ihn aus. Es entsteht weder
ein zweiter Broker noch eine zusätzliche Permit-Ausgabe. Das maschinenlesbare
Inventar liegt in `state/work_units/QIKVRT_PR428_WRITER_INVENTORY_20261001_V1.json`.
Jeder relevante Pfad wird mit Bytes, SHA-256, Klassifikation und Workflow-Jobs
gebunden. Neue untracked oder tracked Kandidatendateien werden mitgeprüft, einschließlich
Make-/Package-Entrypoints, CommonJS und weiterer ausführbarer Quellsprachen.
Implizites `gh api` POST über Field-/Input-Argumente und Octokit-Mutationen
werden ebenfalls abgewiesen. Der Audio-Blob-Materializer ist ein separat
geprüfter GET-only-Leser, kein produktiver Repository-Writer.

38 produktive Workflow-Jobs mit GitHub-Mutationen, unabhängigen Writer-Secrets
oder indirekten GitHub-Writer-Aufrufen erhalten eine feste `if: ${{ false }}`-
Sperre und `permissions: {}`. Ihre inerten Implementierungsbytes bleiben für
Review und einen späteren gebundenen Port erhalten. Alle nativen Workflow-
Permissions sind explizit lesend, und sämtliche Checkout-Schritte lehnen
persistierte Credentials ab. Lesende Tests und Evidenz-Artefakte bleiben
nutzbar. Die CI darf einen sauberen Iteration-0-Fixpunkt beobachten; wenn ein
Remote-Successor nötig wäre, endet sie vor dem Push mit BLOCK.

Die beiden V45-Real-Release-Wrappers, der GitHub/Zenodo-Publish-Wrapper und der
fälschlich als Dry-Run beschriebene direkte Workflow-Dispatch-Shellpfad sind
terminale No-Bypass-Entrypoints. `tools/github_zenodo_release_publish.ps1`
erhält lokale Selftests und Dry-Run-Prüfungen, entfernt den produktiven
Owner-Token-/Branch-/Tag-/Release-/Asset-Pfad und verweigert Nicht-GET,
Asset-Upload und Push auch an den direkten Helper-Grenzen. Der Python-
Publication-Planner bleibt lesbar, verweigert jedoch GitHub-Ausführung vor
Preflight und Transport. Sein Command-Helper lässt nur feste Query-Formen zu.

Die realen Git-Data-Transporte für Zenodo-Consumption-Locks und H3-E1-Recovery
verweigern Nicht-GET bereits vor einem echten oder injizierten Transport.
Ein alter Bearer, ein Acceptance-Record oder Environment-Flag ersetzt keinen
aktuellen Broker-Permit. Der generische Kompatibilitätsclient ist auf den
lokalen Shim begrenzt: `dry_run=true` im Payload macht einen GitHub-Dispatch
nicht zu einem lesenden Provider-Aufruf. Der Firefox-Client liest öffentliche
GitHub-Evidenz und bindet seine anderen Effekte an die vorhandenen lokalen
Terminal-Origins; er wird nicht als GitHub-Writer gezählt.

`incoming/`, reine Dokumentation, Tests/Fixtures, API-Spezifikation, lesende
Beobachter und andere Provider-Verträge werden getrennt klassifiziert.
Ein aktiver Aufruf eines ausgeschlossenen historischen oder dokumentarischen
Writers scheitert. Die Prüfung ist ein konservativer Source-Gate mit
negativen Kontrollen, kein formaler Vollständigkeitsbeweis beliebigen Codes.
Zenodo-native Mutationen besitzen eine separate Provider-Grenze; diese Stufe
behauptet kein Zenodo- oder allgemeines Multi-Provider-Fencing.

**Produktionsgrenze:** Diese Änderungen liegen zunächst im Review-Kandidaten.
Sie deaktivieren weder frühere Main-Versionen noch schon gestartete Workflows,
widerrufen keine früher ausgegebenen Credentials und entziehen keine externen
Admin-, Git-Transport- oder privilegierten Datenbankrechte. Für repositoryweites
Provider-Fencing müssen die aktuelle vertrauenswürdige HEAD/TREE-Inventur,
der tatsächlich rückgelesene Capability-Entzug und mindestens ein produktiver,
exakt gebundener Mirror-Effekt einschließlich Ref, Commit/TREE und durablem
Ledger-Readback gemeinsam vorliegen. Ein Test-Ref oder ein Connector-Update
des Review-Branches erfüllt diesen Nachweis nicht.

Dieser Lauf besitzt keine provisionierte private Produktions-Control-Plane
und keine gebundene kurzlebige Broker-Capability. Deshalb bleiben
`provider_authority_fencing_verified=false` und `effect_ack_done=false`.
Restart-, stale-writer-, CAS-Konflikt-, PENDING-/GET-only-Recovery- und
Post-Effect-Readback-Tests verwenden den bestehenden unabhängigen Bare-Git-
Provider und HTTP-Fixtures; sie werden ausdrücklich als Test-Evidenz geführt.


## Dauerhafte Technologie-Unabhängigkeit jedes Nodes

Ingolf Lohmanns Anforderung vom 1. Oktober 2026 ist unter der stabilen ID
`QIKVRT_NODE_TECHNOLOGY_INDEPENDENCE_V1` in der Policy vollständig persistiert:
Jedes vollständige Node-Element soll menschliche Technologie selbstständig
verstehen, durch Reverse Engineering rekonstruieren, benötigte Abhängigkeiten
ersetzen und sich bei Bedarf unabhängig machen können. Diese lebenserhaltende
Eigenschaft gilt rollenunabhängig und muss mit jedem Nachfolger erhalten bleiben.

`verify-policy` und der verpflichtende Test-Gate verweigern eine gelöschte oder
abgeschwächte Anforderung. Der versionierte Closure-/Checkpoint-Vertrag V2
verlangt zusätzlich `governance/full_node_policy.json` als digestgebundenen
Governance-Payload. Create und Verify validieren seine Invarianten; Restore,
Clone und Derivation übernehmen die geprüften Bytes. Ein neu gehashter Payload
mit entfernter Anforderung scheitert weiterhin. V1-Checkpoints ohne diesen
Vertrag werden nicht stillschweigend als V2 akzeptiert; sie benötigen einen
neuen vollständigen, extern vertrauensgebundenen Closure-Plan.

Die Owner-Prüfung des vollständigen Closure-Plans muss Quellen, Interface-
Modelle, Toolchain und Runtime, Rekonstruktions- und Ersatzpläne sowie Tests und
aktuelle Ergebnisse für alle tatsächlich benötigten Technologien erfassen.
Physische Wiederherstellungsdaten gehören dazu, soweit der Node sie benötigt.
Das Werkzeug prüft die deklarierte Byte-Closure und die erhaltene Anforderung;
es beweist nicht eigenständig die semantische Vollständigkeit dieser Materialien.
Jeder akzeptierte Nachfolger muss vor seinem ACK an alle vollständigen Nodes
repliziert sein. Ein verlustfreier Bestand aller künftigen Daten ist ohne diese
laufende Replikation nicht nachgewiesen.

Der universale Anspruch ist eine normative Owner-Anforderung. Universale
Reverse-Engineering-Fähigkeit, autonome physische Reproduktion und unbegrenzte
zukünftige Erhaltung sind damit nicht als implementierte oder empirisch
bewiesene Fähigkeiten ausgewiesen. Konkrete Fähigkeiten benötigen je Technologie
eigene Tests und frische Effekt-Readbacks. Unabhängigkeit ersetzt keine aktuelle
AuthorityControlPlane-/Permit-/Epoch-/Fence-Bindung für produktive Effekte.


## Gepackte und endungslose Writer

Der Gate prüft zusätzlich Shebang-/Executable-Entrypoints und die originalen
Quelltypen im historischen `PAYLOAD_FILENAME_MAP_V36.json`. 57 unter `.bin`
verpackte Push-/REST-Publisher sind an ihren bisherigen Payload-Pfaden terminal
mit Exit 78 gesperrt. Die Originalbytes und Apache-2.0-Hinweise bleiben exakt
unter `incoming/no_bypass_20261001_monthly_writers/` erhalten; der typed
Quarantäne-Record bindet Ursprungspfad, Bytes, Git-Blob und SHA-256. Diese Bytes
werden nicht als produktiv zugelassen. Ein Aufruf ihrer Archivpfade aus aktivem
Code scheitert am Source-Gate. Auch ein endungsloses neues Writer-Skript wird
erfasst.

Die alte Filename-Map bleibt eine unveränderte historische Byte-Bindung. Ihre
alten Writer-Checksummen passen absichtlich nicht zu den neuen Sperr-Stubs;
sie ist kein aktueller ausführbarer Delivery-/Admission-Vertrag. Ein späterer
Port benötigt einen neuen geprüften Broker-Vertrag und einen versionierten
Delivery-Successor. Frühere ZIP-/Release-Pakete bleiben historische Artefakte;
ihr Entpacken widerruft die No-Bypass-Anforderung nicht. Noch ausgegebene
Capabilities und historische Installationen müssen vor produktiver Abnahme
weiterhin tatsächlich entzogen und rückgelesen werden.
