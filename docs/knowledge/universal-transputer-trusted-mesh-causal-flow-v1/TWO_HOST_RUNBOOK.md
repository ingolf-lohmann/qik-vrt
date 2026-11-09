# QIK-VRT – Zwei-Host-mTLS-Round-Trip, reversibler Operatorpfad

**Stand 09.11.2026.** Dies ist ein experimenteller, nichtproduktiver und ohne externe Hostzulassung nicht ausführbarer Host-übergreifender Transportpfad. Zwei unabhängige, zugelassene Hosts wurden **nicht** verifiziert. Die Befehle sind ein vorbereitetes Ausführungsprofil, kein behaupteter Deploy. Der ursprüngliche lokale 17-Test-Nachweis bleibt eine separate historische Version.

## Bindungsregeln

1. Ausschließlich Authority `ingolf-lohmann/qik-vrt` und derselbe **40-stellige Exact-Commit-SHA** für beide Hosts. Die Dateien `two_way_reference.py` und `mtls_transport.py` müssen bytegenau aus dem gepinnten Commit stammen. Nicht durch eine ungebundene GitHub-Branchspitze ersetzen.
2. Host A (Sender) und Host B (Empfänger) müssen separat kontrollierte Sicherheits- und Persistenzdomänen sein. `localhost` und `127.0.0.0/8` genügen nicht. Auch getrennte Container auf demselben Host liefern noch keinen unabhängigen Originalhostnachweis.
3. Vom Operator getrennt provisionierte kurzlebige Zertifikate und private Schlüssel bleiben **außerhalb** von Git. Host-B-Serverzertifikat enthält den per DNS aufgelösten Hostnamen als SAN; Host-A-Clientzertifikat besitzt die zugelassene Identität `CN=node-a`. Beide Prozesse vertrauen nur der absichtlich provisionierten CA. CA-Schlüssel gehören auf keinen Host.
4. Host B hat eine vom zuständigen Operator nachgewiesene Ingress-Firewall mit Allowlist für Host A; Host A hat das erwartete DNS und eine überprüfte Route. Es darf kein TLS- oder Admission-Bypass verwendet werden.
5. Vor dem Transport sind die unabhängige Hostidentität, das Exact-Head, die tatsächlich laufenden Prozesse, die persistierten State-Pfade und die Admission nachzuweisen. Der CLI-Schalter `--admitted` ist **nur ein lokales Simulationsgate**; er erteilt selbst keine Mesh- oder produktive Hostzulassung.
6. HTTP-Empfangsreceipt und `effect_ack_done=false` sind Transportbelege. Produktive EAP-Wirkung setzt einen eigenständigen, aktuell geprüften Originalhost-Readback voraus.

## Reproduzierbare Offline-Regressionsprüfung

```sh
python3 -B -m unittest discover -s docs/knowledge/universal-transputer-trusted-mesh-causal-flow-v1 -p 'test_mtls_transport.py' -v
python3 -B -m unittest discover -s docs/knowledge/universal-transputer-trusted-mesh-causal-flow-v1 -p 'test_two_host_admission.py' -v
```

Im lokalen Kandidaten wurden 17 bisherige und 17 zusätzliche Tests (34/34) erfolgreich ausgeführt. Die zweite Gruppe überprüft insbesondere Remote-Bind- und Routing-Sperren, unbekannte beziehungsweise lokale Ziele, falsche Node-Health, fehlenden Receipt-Status und Replay-Voraussetzungen. Der lokale Test nutzt keinen externen Host.

## Einmalige Testausführung (erst nach Host-/Zertifikatszulassung)

**Host B – separater Empfänger.** Das folgende Beispiel bindet explizit an eine externe Schnittstelle. Diese Freigabe darf nur nach der tatsächlichen Firewall-/Host-Abnahme erfolgen. `--remote-test-bind` aktiviert ausschließlich das begrenzte Testprofil, nicht die produktive Mesh-Runtime.

```sh
python3 mtls_transport.py server \
  --ca /secure/trust/ca.pem --cert /secure/node-b/cert.pem --key /secure/node-b/key.pem \
  --state /srv/qikvrt-two-host/node-b --head <EXACT_40_HEX_COMMIT> \
  --port 8443 --bind-host 0.0.0.0 --remote-test-bind --admitted
```

**Host A – separater Sender.** `node-b.example.invalid` ist lediglich ein Platzhalter. Ein tatsächlicher, zugelassener DNS-Name muss im Serverzertifikat als SAN enthalten sein. TLS prüft CA und Hostname, der Server prüft die Client-Zertifikatsidentität. `--require-remote-peer` lehnt Loopback-/unauflösbare Ziele ab und überprüft die fremde, experimentelle Health-Identität, bevor eine Outbox erstellt wird.

```sh
python3 mtls_transport.py client \
  --ca /secure/trust/ca.pem --cert /secure/node-a/cert.pem --key /secure/node-a/key.pem \
  --state /srv/qikvrt-two-host/node-a --head <EXACT_40_HEX_COMMIT> \
  --port 8443 --connect-host node-b.example.invalid --require-remote-peer \
  --event-id claim-1 --kind CLAIM --payload 'QIK-VRT remote test'
```

**Host A – Replay derselben Persistenzbytes nach Neustart** (kein zweites Ereignis):

```sh
python3 mtls_transport.py client \
  --ca /secure/trust/ca.pem --cert /secure/node-a/cert.pem --key /secure/node-a/key.pem \
  --state /srv/qikvrt-two-host/node-a --head <EXACT_40_HEX_COMMIT> \
  --port 8443 --connect-host node-b.example.invalid --require-remote-peer \
  --event-id claim-1 --replay-existing
```

## Externe Abnahmematrix

| Gate | erforderlicher unabhängiger Beleg | Stand |
|---|---|---|
| A und B | unabhängige laufende Hosts samt getrennten State-Volumes und Operatoridentitäten | **OPEN** |
| Netzwerk | echte, zugelassene TCP/TLS-Route und Firewall-Freigabe | **OPEN** |
| mTLS | beidseitiger Zertifikats-/SAN-/Client-CN-Nachweis, CA-Bindung | **OPEN** |
| Originalbytes | SHA-256-gebundener Transport über zwei reale Hosts | **OPEN** |
| Replay | Neustart, Doppelzustellung, unveränderter Ledger-Digest und kalter Receipt-Readback | **OPEN** |
| CI/Governance | Exact-HEAD-Lauf, vollständige Integrität, unabhängiges Review | **OPEN** |
| Originalhost/EAP | IONOS-Admission, HTTPS, native Runtime und `EFFECT_ACK_DONE=true` | **OPEN / BLOCKED** |

Kein erfolgreicher lokaler oder experimentell externer Transport hebt diese Gates automatisch auf. Die gesonderte QIK-VRT/IONOS-Produktivabnahme bleibt fail-closed.
