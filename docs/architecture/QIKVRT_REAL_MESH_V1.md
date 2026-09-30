# QIK-VRT Real Multi-Pair Mesh V1

## Warum die Authority/Mirror-Paarprojektion noch kein echtes Mesh war

`QIKVRT_AUTHORITY_MIRROR_MESH_V1` bindet eine einzelne Authority/Mirror-Beobachtung korrekt und fail-closed. Sie erzeugt jedoch nur ein kanonisches Beobachtungsobjekt. Ein statischer Envelope-Builder besitzt weder unabhängige Node-Laufzeiten noch einen Transport, keine Weiterleitung zwischen mehreren Paaren, keinen zurücklaufenden Ack-Pfad und keine restartfeste node-lokale Persistenz. Deshalb gilt:

```text
PAIR_OBSERVATION != RUNTIME_MESH
STATIC_TERMINAL_PROJECTION != NODE_TO_NODE_EXECUTION
```

V1 ergänzt genau diesen fehlenden Laufzeitkern, ohne die Paarbeobachtung umzudeuten oder `DIVERGED` mit Synchronisation zu verwechseln.

## Minimal echtes Mesh

Der ausführbare Akzeptanzpfad startet vier voneinander unabhängige Python-Prozesse:

```text
pair-a-authority  <->  pair-a-mirror
       |                  |     \
       |                  |      \
       v                  v       v
pair-b-authority  <->  pair-b-mirror
```

Die deklarierte Peer-Graphstruktur ist zusammenhängend, zyklisch und gibt jedem Node mindestens zwei Peers. Zwei verschiedene vier-Hop-Routen werden über echte TCP-Verbindungen auf `127.0.0.1` ausgeführt. Damit ist nicht nur eine Liste von Nodes materialisiert, sondern tatsächliche Node-zu-Node-Kommunikation mit einem durch die Route zurückkehrenden terminalen Receipt.

Jedes Authority/Mirror-Paar enthält genau eine `AUTHORITY`- und eine `MIRROR`-Rolle. Mehrere Laufzeitinstanzen dürfen dieselben Repository-Rollen binden; daraus wird weder ein weiteres GitHub-Repository noch eine neue kanonische Authority erfunden.

## Ereignismodell

Node-Arbeit beginnt ausschließlich durch einen eingehenden Socket-Frame. Es gibt keinen fachlichen Timer und kein periodisches Polling. Socket- und Prozess-Timeouts sind nur begrenzte Watchdog-/Lease-Grenzen und lösen keine neue fachliche Arbeit aus.

```text
SOCKET_EVENT
-> exact envelope validation
-> append-only ACCEPTED receipt
-> next-hop relay or terminal receipt
-> returning acknowledgement
-> append-only COMPLETED receipt
-> host reobservation of every node ledger
-> bounded Effect-Acknowledgement
```

## Kanonischer Envelope und Routing

Jede Nachricht bindet:

- Mesh-ID und Topologie-Digest;
- eindeutige Message-ID und Route-ID;
- vollständige Node-/Pair-/Role-/Repository-/Tree-Bindung;
- eine explizite Route über mindestens zwei Paare;
- Hop-Index und hashverkettete Vorgänger-Receipts;
- Payload-Bytes durch SHA-256;
- `external_effect=NONE`.

Ein Hop ist nur zulässig, wenn die Kante in der deklarierten Peer-Topologie vorhanden ist. Wiederverwendung derselben Message-ID mit anderen Bytes endet in `EFFECT_ACK_BLOCK`. Ein unerreichbarer Next Hop bleibt retry-fähig in `EFFECT_ACK_CONTINUE`; daraus entsteht weder `DONE` noch ordinary release.

## Persistenz und Restart

Jeder Node führt ein eigenes append-only JSONL-Ledger. Jeder Datensatz bindet Sequenz, Vorgänger-Digest, Node-ID und Record-Digest. Nach einem Prozessneustart wird die gesamte Hashkette verifiziert und der idempotente Message-Index rekonstruiert. Ein exakt wiederholter bereits abgeschlossener Input liefert dasselbe terminale Receipt, ohne einen weiteren Ledger-Datensatz anzuhängen.

## Effect-Acknowledgement

Der Mesh-Laufzeitkern führt keine zweite Ack-Zustandsmaschine ein. Nach dem Transport reobserviert der Host die `ACCEPTED`- und `COMPLETED`-Receipts aller vier Nodes und übergibt die Hop-Digests an `src/qikvrt_effect_ack.py`. Nur diese bestehende Fünf-Zustands-Maschine darf den begrenzten Effekt schließen.

```text
TRANSPORT_ACK != EFFECT_ACK_DONE
BOUNDED_LOOPBACK_MULTI_PAIR_MESSAGE_DELIVERY_ONLY != GENERAL_EFFECT_ACK_DONE
```

Der beobachtete Effekt ist ausschließlich die angenommene, persistierte und nach Neustart rekonstruierbare Loopback-Nachrichtenzustellung. Es gibt keinen Repository-Write, keine Publikation, kein Deployment und keinen geschützten externen Effekt.

## Divergenz bleibt sichtbar

Die beiden Laufzeitpaare binden getrennte Authority- und Mirror-Root-Trees. Unterschiedliche Trees werden als `DIVERGED` ausgegeben. Transportfähigkeit erzeugt keine Inhaltsgleichheit und keine Synchronisationsautorität.

```text
DIVERGED = OBSERVED_PAIR_STATE
DIVERGED != SYNC_REQUEST
MESSAGE_DELIVERED != TREES_EQUAL
TREES_EQUAL != RECIPROCAL_RECEIPT_BOUND
```

## Verifizierbare V1-Aussage

Bei erfolgreichem Exact-Head-Workflow ist folgende Aussage zulässig:

```text
FOUR_INDEPENDENT_NODE_PROCESSES_OBSERVED
TWO_AUTHORITY_MIRROR_PAIRS_OBSERVED
REAL_LOOPBACK_TCP_MULTI_HOP_DELIVERY_OBSERVED
RETURNING_ACK_PATH_OBSERVED
APPEND_ONLY_RESTART_PERSISTENCE_OBSERVED
BOUNDED_LOOPBACK_EFFECT_ACK_DONE
```

Ausdrücklich nicht abgeleitet werden:

```text
GENERAL_INTERNET_REACHABILITY
PRODUCTION_DEPLOYMENT
AUTHORITY_MIRROR_SYNCHRONIZATION
AUTHORITY_MIRROR_EQUALITY
PHYSICAL_HARDWARE_EXECUTION
GENERAL_EFFECT_ACK_DONE
MERGE
PASS
FINAL_PASS
```

## Repository multitasking successor (2026-09-30)

The node-wide lock formerly spanned a downstream network await. A controlled
blocked hop prevented an unrelated message from progressing on both Authority
and Mirror roles. Message-scoped locks preserve exactly-once replay while
letting independent routes progress. Holder/waiter accounting prevents a
cancelled waiter from splitting one identity across two locks. Synchronous
ledger appends retain one event-loop writer and the existing hash chain.

The existing system verifier now exposes `multitasking`. On an exact clean
committed checkout, provide `--repository`, `--source-head`, `--source-tree`,
`--counterpart-head`, `--counterpart-tree`, a NEW `--workdir` and `--output`.
It runs three trials each at 4, 8 and 16 independent TCP node processes, with
one concurrent route per node, then restarts every node and replays the exact
messages. It verifies overlapping unfinished tasks from actual node ledgers,
all-hop fresh readback, zero lost/duplicated effects, and exact-byte archive
reconstruction. Original ledgers remain retained beside each archive.

The direct Python test API marks supplied source bindings unverified. The CLI
verifies actual Git HEAD/TREE and a clean worktree before and after execution.
Counterpart identities are references only: every process in one experiment
executes that checkout. Both repositories require separate exact-checkout
executions. Neither a logical Mirror process nor a copied implementation proves
remote Mirror execution, live Main integration, protected review, general Mesh
completion, all TEMDD layers, deployment or unlimited scalability. Only the
measured finite workload and declared ledger corpus may receive its scoped
result. Failed and open work remains distinct from completed messages.
