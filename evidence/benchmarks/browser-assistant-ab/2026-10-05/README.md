<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Ausführungs- und Nachweisstand

**Produktvergleich nicht ausgeführt. Keine Kundennutzenbehauptung.**

`PREFLIGHT.json` bindet den tatsächlich geprüften Main-Ausgangspunkt,
Arbeitskopie-Flag, aktuelle Harness-/Terminal-/Toolchainbytes und die beobachtete
Python-/OS-Umgebung. Der fehlende ausführbare persönliche Rechercheassistent,
die ungebundene gewöhnliche Baseline, die fehlende Firefox-Installation und der
nicht nachgewiesene authentifizierte Personal-Runtime-Pfad sind getrennt erfasst.

`prepared-run/manifest.json` enthält 12 vorab geplante identische Paare,
also 24 Einzelversuche. `prepared-analysis/` hält alle 24 als `NOT_EXECUTED`
fest. Es gibt keine Produktrohwerte; `product_metrics=null` und
`product_trials_executed=0`. Die eingefrorenen Fixtures sind vollständig
synthetisch. Die Quellen- und Aufgabenbytes sind keine Nutzerbeobachtungen.

`self-test-run/` enthält einen separat bezeichneten `HARNESS_SELF_TEST` mit
acht geskripteten Trials, synthetischen Uhren, Rohereignissen, Hashketten und
Oracle-Ausgaben. Beide Arme erhalten absichtlich dieselben geskripteten
Antworten. `SELF_TEST_ANALYSIS.json` ist nur die reproduzierbare Auswertung
dieser Messmechanik. Ein Armname „qikvrt“ macht diese Testdaten nicht zu
QIK-VRT-Produktdaten. Kein Zeitgewinn oder Nutzen wird daraus behauptet.

`TERMINAL_SMOKE.json` ist ein tatsächlicher isolierter HTTP-Referenzpfadtest
mit Prepare, vollständigem Record-Readback, Commit, frischem State-Readback
und Replay-409. Er verwendet unverändert den vorhandenen Loopback-Träger;
Firefox und ein Rechercheassistent wurden dabei nicht ausgeführt. Die
Trace-Digests binden die beobachteten HTTP-Antwortbytes, ohne lokale
Einmal-Tokens zu veröffentlichen. Das ist keine Produktmessung.

Reproduktion aus dem enthaltenen Kandidatencheckout:

```bash
python3 -B tools/qikvrt_browser_assistant_ab.py analyze --run evidence/benchmarks/browser-assistant-ab/2026-10-05/prepared-run
python3 -B tools/qikvrt_browser_assistant_ab.py analyze --run evidence/benchmarks/browser-assistant-ab/2026-10-05/self-test-run
make browser-assistant-ab-test
```

Auswertungen verlangen unveränderte gebundene Harness-/Runtime-/Toolchaindateien.
Die Git-Revision, die dieses Paket enthält, bindet die vollständigen
Nachweisbytes. In-file HEAD/TREE in den Rohmanifesten bezeichnen ausdrücklich
den beobachteten Ausgangspunkt mit Dirty-Flag; sie werden nicht nachträglich
auf einen späteren Commit umetikettiert. Die Rohereignisse und das ursprüngliche
Manifest bleiben unverändert.

Nächster Produktbaustein: einen tatsächlich aufrufbaren authentifizierten
Personal-Assistentenadapter in den bestehenden Firefox-/Terminal-Pfad
integrieren und die gewöhnliche Baseline mit ihrer normalen Persistenz binden.
Danach den Messvertrag um dessen reale Kontroll- und Beobachtungsspuren
erweitern und sämtliche geplanten Paare frisch ausführen.
