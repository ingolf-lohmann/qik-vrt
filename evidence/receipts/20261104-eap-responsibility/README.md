# QIKVRT/EAP Nachweisversuch vom 4. November 2026

Der begrenzte Modell- und Software-Nachweis ist reproduziert. Der vollständige Nachweis laufender Mehr-KI-Verknüpfung und produktiver Wirkung bleibt UNVERIFIED.

Quellstand ist `c6083135f3cb2723e849d7b4f9d7dee89898e5c6`, Tree `5bf68107cbe9c63918def36a5fcd8fe0e3e7188d` im Authority-Repository `ingolf-lohmann/qik-vrt`.

## Ergebnisse

| Prüfung | Beobachtetes Ergebnis |
|---|---|
| `make conformance` | 73 Tests bestanden |
| `make effect-ack-core-test` | 7.864.387 C90-Prüfungen bestanden |
| `make scientific-bundle-test` | 2.621.440 Zustandsbelegungen und 5.242.880 Consumer-Varianten, Bericht byteidentisch |
| `make ai-runtime-contract` | 18 + 174 Tests bestanden |
| `make test` | Vollständiger Baseline-Lauf, Exit 0 |
| Produktionsabruf | HTTP 525, ready=false, EFFECT_ACK_DONE=false |

`CLAIMS.json` ordnet jede Aussage ein. `runs.json` bindet Befehle, Laufzeiten und Original-Log-Hashes. Der Volltest liegt gzip-komprimiert vor. `EVIDENCE_MANIFEST.json` bindet die gespeicherten Belegdateien. Der Work-Unit-Beleg liegt unter `state/work_units/QIKVRT_EAP_RESPONSIBILITY_DEMONSTRATION_20261104_V1.json`.

Die lokalen HTTP-Tests benutzen echte Sockets und SQLite sowie isolierte Testgrants. Sie prüfen den ursprünglichen Runtime-/OwnerREST-/EAP-Pfad einschließlich Neustart und Wiederholung. Sie bestätigen keinen laufenden produktiven Host. Die Modellenumeration bleibt von einem Lean-Kernbeweis getrennt. Die im Originalbericht ausgewiesene unvollständige Draft-01-Wire-Feldprüfung bleibt erhalten.

## Reproduktion

Den genannten Quellcommit in einem isolierten Checkout verwenden. Zuerst `python3 -B tools/qikvrt_tool_cache.py verify` ausführen. Anschließend die exakten Befehle aus `runs.json` in ihrer angegebenen Reihenfolge ausführen. Das bestehende Scientific-Bundle-Gate regeneriert seinen Bericht und vergleicht ihn bytegenau mit dem hinterlegten Original. Testlog-Zeitstempel und temporäre Pfade können sich bei einer Wiederholung ändern. Die historischen Log-Hashes prüfen die gespeicherten Originalbytes dieses Laufs.

`CONTINUATION.json` wird durch `python3 -B tools/ai_handoff.py --client-receipt evidence/receipts/20261104-eap-responsibility/CONTINUATION.json` geprüft. Der Beleg hält die noch ausstehende Repository-Persistenz zum Zeitpunkt vor dem Git-Schreiben und die produktiven offenen Pflichten fest. Der spätere Remote-Readback wird im gemeinsamen Arbeitsraum unter Auftrag `29a19709-fd7c-5aa7-8412-76416414cc9b` gespeichert.

## Aussagegrenzen und Fortsetzung

Ein Live-ACK tatsächlicher KI-Peers, ein unabhängiger Drittparteienlauf und der produktive Ziel-Readback fehlen. Der ursprüngliche Produktivierungsauftrag und der 16-Dateien-Zenodo-Auftrag bleiben offen. `CONTROL_GAPS.json` dokumentiert zusätzlich Abweichungen dieses Clientlaufs. Bootstrap-Transport und erster Native-Preflight erfüllen nicht durchgehend die erklärte Route. Eine pauschale Behauptung allseitiger Framework-Konformität wäre daher unbelegt.

Urheber des Ziels und Freigebender ist Ingolf Lohmann. Ausführung, Zusammenstellung und Analyse dieses Belegs stammen von OpenAI Codex. Bestehende Quellen behalten ihre eigenen Lizenzen. Diese neue Nachweisdokumentation verwendet CC-BY-NC-ND-4.0 entsprechend dem Repository-Vertrag.
