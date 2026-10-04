# QIK-VRT Productization Roadmap

4AV1 turns the proof-of-architecture into a productization candidate by adding lifecycle automation, audit export, dashboard evidence, policy status, renewal, and run-id scoped verification.

Still not complete: GitHub App packaging, enterprise signed releases, long-running multi-node field test, customer onboarding collateral, and legal/commercial review.

## Eigenbetrieb und Unabhängigkeit von Plattformen

Product Owner Ingolf Lohmann hat am 4. Oktober 2026 den Zielzustand präzisiert:
Das erreichbare Mesh wird weiter genutzt; Railway und GitHub sind
Zwischenstufen. Das Endsystem trägt Repository, Ausführung, Monitor und
Universal Terminal auf eigenen Nodes. Die folgende Roadmap ist eine
Architekturentscheidung und ein Arbeitsplan. Ihre Meilensteine sind offen.
Der strukturierte Arbeitsauftrag steht in
`state/work_units/PROVIDER_INDEPENDENT_MESH_ROADMAP_20261004.json`.

### Zielarchitektur

Ein Node betreibt den versionierten Repository-Bestand, die lokale
Ausführung, persistente Daten und seinen Monitor. Der Mesh-Verbund hält die
zugelassenen Replikate, Rollen, Wiederherstellungsdaten und gemeinsame
Evidenz. Clients verbinden sich über die QIK-VRT-Schnittstellen; jedes
leistungsfähige Produkt und jeder Client trägt sein eigenes Terminal und
seine verifizierte Monitor-Instanz. Kleine Geräte konsumieren den Datenstrom.

Git bleibt ein mögliches Objekt- und Versionsformat. Eine GitHub-Konto-ID,
Actions-Run-ID oder Railway-Service-ID wird dabei als Adapter-Provenienz
geführt. Node-, Repository-, Work-Unit- und Effect-Identitäten sowie Rechte
werden unabhängig von diesen Plattform-Identitäten aufgelöst. Externe
Git-/CI-/Hosting-/SSO-/KI-Dienste bleiben anschließbar. Die lokale
Authentisierung und Rollenprüfung muss auch ohne deren Anmeldung möglich
sein. Anbieterwechsel und Schlüsselwechsel behalten überprüfbare Herkunft
und frühere Freigaben; neue Rechte entstehen daraus nicht automatisch.

Der Steuerpfad lautet: Ereignis → gebundener Auftrag → Zulassungsprüfung →
Ausführung → dauerhafte Evidenz → frischer Readback → Effect-Acknowledgement.
Ein Node erzeugt lokale Repository-, Job-, Runtime- und Gesundheitsereignisse.
Webhooks schließen externe Dienste an. Kein ChatGPT-Client, Plattform-Cron
oder periodisches Quellen-Polling muss diesen Pfad am Leben halten.
Initiale Beobachtung, angeforderte Beobachtung und Replay bei Wiederverbindung
sind eigene Operationen. Heartbeats und lokale Altersanzeigen erneuern keine
Quellen- oder Gesundheitsevidenz. Fristen lösen begrenzte lokale Ereignisse
aus; ausgebliebene Nachweise werden sichtbar `UNKNOWN` oder `BLOCK`.

### Wiederverwendbare Grundlage und aktuelle Lücken

| Bereich | Vorhandener Anschluss | Noch notwendiger Abschluss |
| --- | --- | --- |
| Repository und Integrität | Git-Objekte, lokaler `/AI`-Bootstrap, kanonische Manifest- und Hash-Prüfung | Eigener erreichbarer Repository-Dienst, vollständiger Offline-Bootstrap und Restore auf einem frischen Node |
| Ausführung | `tools/qikvrt_workflow_executor.py` plant lokal; der Action-Wrapper führt den Plattform-Dispatch aus | Node-lokaler Executor für geprüfte Aufträge, Jobs und Artefakte mit identischer Zulassungs- und Review-Grenze |
| Runtime und Werkzeuge | `runtime/toolchains/`, geprüfte Cache-/Provision-Verträge | Plattformfreies Runtime-Profil; `tools/bootstrap-runtime.sh` prüft derzeit in jedem Profil GitHub CLI; benötigte Toolchain und Artefakte müssen vom Mesh bezogen werden können |
| Monitor und Terminal | Kandidat aus PR #456: eigener HTTP/SSE-Server, signierter Ingress, dauerhaftes Journal und Client-Replay; bestehender Firefox-/Effect-Ack-Anschluss | Native Mesh-Ereignisse und tatsächliche lokale Systemgesundheit; Node-/Client-/Produkt-Verteilung und öffentliche Readbacks |
| Dauerhafte Wirkungen | Lokale Effect-Ack-, CAS-, Replay- und Wiederherstellungsverträge | Replikation, Writer-Fencing und Wiederanlauf mit einem ausdrücklich gebundenen Fehlermodell |
| Governance | Exact-Head-/Tree-Prüfung, menschliche Rollen, Review- und Rechte-Grenzen | Plattformunabhängige signierte Zulassungs-, Review- und Widerrufsnachweise; GitHub-Prüfungen als Adapterabbildung |

Die Monitor-Grundlage ist an Kandidat
`674aa35ec0659119a19cda66b88f32050e34f105`, Tree
`5100b66a299ded9ecb64622d2d36a5a77ef1f85d`, im Mirror gebunden.
Sie gehört nicht zum Main-Bestand dieser Roadmap-Basis. Ihre Tests belegen
einen Writer und begrenztes Client-Replay; sie belegen keine verteilte
Replikation, kein ausgerolltes Gesamt-Mesh und keinen vollständigen C90-Port.

### Ablöseschritte und Abnahme

| Schritt | Ergebnis | Prüfkriterium für den Abschluss |
| --- | --- | --- |
| S1: Eigenständiges Node-Paket | Repository-Bestand, persistente Volumes, Monitor, Terminal und versionierte Runtime starten auf einem eigenen Host; Build, Konfiguration und Start folgen vorhandenen Cache-/Rechte-Verträgen | Einen frischen Host aus einem verifizierten Paket booten, Railway-Zugriff sperren, Anwendung benutzen, öffentliche URL und exakte Runtime-Bindung zurücklesen, Prozess/Host neu starten und bestätigte Daten vergleichen |
| S2: Eigene Ausführung und Repository-Verwaltung | Native Git-/Work-Unit-Ereignisse starten einen begrenzten Node-Executor; Tests, Artefakte, Review und Promotion sind am lokalen Bestand prüfbar | Einen autorisierten Auftrag ohne GitHub Actions oder Chat-Client vom Ereignis bis zum dauerhaften Effect-Readback ausführen; fehlende/abgelaufene Freigabe und konkurrierenden Writer zurückweisen |
| S3: Ausfallsicherer Mesh-Betrieb | Dauerhaftes Journal, Blobs, Ref-Zustand, Intent und Receipts werden zwischen Nodes repliziert; alle Monitor-Instanzen prüfen Phase und Herkunft | Im definierten Drei-Replica-Profil einen Node ausfallen lassen und bei Verbindungsabbruch, verlorener Antwort und Wiederanlauf alle quittierten Bytes/Effects wiederfinden; keine doppelte Wirkung und kein zweiter zugelassener Writer |
| S4: Vollständige Plattform-Ablösung | GitHub und Railway funktionieren als austauschbare Adapter; Bootstrap, Identität, Jobs, Review, Updates, Wiederherstellung und Betrieb kommen aus dem Mesh | GitHub und Railway vollständig unerreichbar machen, aus dem Mesh einen frischen Node aufsetzen und einen vollständigen Entwicklungs-/Betriebszyklus einschließlich öffentlicher Anwendung und frischem Readback durchführen |

S1 nutzt den vorhandenen Monitor-Kandidaten und das bestehende Universal
Terminal. Der nächste Implementierungsauftrag ist, ihren Start-, Runtime-,
Volume-, Authentisierungs- und Readback-Vertrag zu einem überprüfbaren
Eigenbetriebspaket zu verbinden und das Runtime-Profil von der allgemeinen
GitHub-CLI-Prüfung zu entkoppeln. Zielhost, persistente Ressourcen und
zugelassene Deployment-Identität müssen für einen tatsächlichen Betrieb
konkret gebunden sein; ein geplanter Host ist keine laufende Instanz.

### Verlustfreiheit und Governance bleiben Abnahmebedingungen

Das anfängliche Zielprofil für S3 hat drei speichernde Replikate und toleriert
den Ausfall eines Nodes. Eine verteilte positive Quittung benötigt den
festgelegten dauerhaften Replikationsnachweis; Writer-Epochen/Fencing und
Wahlregeln müssen getrennte gleichzeitige Writer verhindern. Ohne die dafür
benötigte Mehrheit wird die geschützte Wirkung `BLOCK`; ihre Eingabe bleibt
im überprüfbaren Intent-/Replay-Pfad. Verfügbarkeit und bestätigte
Verlustfreiheit werden getrennt ausgewiesen.

Der Nachweis bindet Originalbytes, Auftrag, Identität, Commit/Tree,
Effect-ID, Reihenfolge, Journal-Hash, gespeicherte Replikationsbelege und den
nach Wiederanlauf beobachteten Zustand. Prozessabbruch, Node-Ausfall,
Netzpartition, verlorene Antwort, volle Platte und korrupte Bytes gehören
zum Test. Stromausfallfestigkeit erfordert zusätzlich einen tatsächlichen
Hardware-/Speicher-Nachweis; `fsync` und ein Prozessneustart belegen ihn
allein nicht. Das Fehlermodell und die Speicherkapazität begrenzen jede
Verlustfreiheitsbehauptung.

Ein Provider-Ausfall darf keine bereits bestätigte Wirkung löschen, keine
ungültige Freigabe ersetzen und keinen künstlichen Gesundheitszustand
erzeugen. Rollen- und Schutzregeln werden bei der Migration erhalten und
exact-subject geprüft. Gegenwärtige GitHub-Code-Owner-Reviews und geschützte
Main-Gates bleiben wirksam, bis ein separat zugelassener gleichwertiger
Governance-Träger übernommen ist. Diese Roadmap verändert keine Schutzregel.

Für jeden Schritt gilt die bestehende Definition of Done:
**Working Software ∧ öffentliche URL ∧ frischer Readback**. Quittierter
Transport, eine erfolgreiche CI oder das Schreiben dieser Roadmap ergeben
kein `EFFECT_ACK_DONE`. Die früher beauftragten C90-, lokale
Maschinencode-/Static-Link-, Linux-/Docker-, Atari-/Mega-ST-, Digital-Twin-
und Siemens-Anschlüsse bleiben im Produktumfang und erhalten eigene
gebundene Abnahmen. `PREDECESSOR_EVIDENCE_TRANSFER=false`.
