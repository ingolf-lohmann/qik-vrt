# QIK-VRT: separat gelockter Verbraucher für reelle Energiegrößen

Stand: 03.11.2026. Auftrag und Fragestellung: Ingolf Lohmann. Implementierung und Prüfung: OpenAI Codex.

## Tatsächlich geprüft

Lean 4.19.0 hat im separat aufgebauten Lake-Paket die unveränderten fünf PRE- und drei REB-Sätze erneut geprüft. Acht zusätzliche `Statement`/`_checked`-Bindungen ordnen dieselben acht Aussagen ihren Beweisen zu. Beide Axiomaudits sind vollständig; die Abhängigkeiten sind `propext`, `Classical.choice`, `Quot.sound`. Vier falsche Aussagen wurden mit semantischen Lean-Diagnosen abgewiesen.

Das Originalarchiv `QIKVRT_RealEnergy_Kernel_20261103.zip` hatte 18410 Bytes und SHA-256 `3de2e360f401123b121def22765c8cc6fe0c6e53f2b5ad5d7ef98d103f744ddf`. Alle 33 Nutzdateien stimmen mit ihrem Originalmanifest überein. Die ursprünglichen Lean-Quellen wurden unverändert übernommen. Der neue Prüfer kompiliert sie ausdrücklich erneut; er übernimmt keinen alten PASS und keinen hartcodierten erfolgreichen Compilerstatus.

`SOURCE_LOCK.json` bindet die Projektquellen und den tatsächlich von Lake erzeugten `lake-manifest.json`. mathlib wird als Pfadabhängigkeit aus dem unveränderten Originalquellarchiv des bereits vorgesehenen Commits `c44e0c8ee63ca166450922a373c7409c5d26b00b` bereitgestellt. `MATHLIB_SOURCE_MANIFEST.json` enthält die 6816 Dateihashes. Der vollständige Git-Dateibaum stimmt mit dem unabhängig gelesenen Originalbaum `fdf252e589fb338709bf537ba48ce79a78cbe5e9` überein. Acht transitive Git-Abhängigkeiten sind im Lake-Manifest auf exakte Revisionen fixiert.

Der frühere Git-Abruf scheiterte mit `Proxy CONNECT aborted`. Das vollständige Quellenarchiv ist vorhanden und bytegeprüft. Das fehlende originale Git-Commitobjekt wurde nicht rekonstruiert; ein Ersatzcommit wird nicht als Original ausgegeben. Der tatsächlich geprüfte Verbraucher verwendet deshalb den ausdrücklich dokumentierten Archiv-/Pfad-Lock. Der ursprüngliche Std-only-Verbraucher bleibt unverändert.

## Reproduktion

Voraussetzungen: Linux x86-64, Git, Python 3 und die originale Lean-4.19.0-Toolchain. Der Prüfer bindet das konkrete Linux-Compilerbinary zusätzlich an seinen SHA-256. Auf einer anderen Plattform muss eine gesonderte Binärbindung geprüft werden.

```bash
python3 bootstrap_mathlib.py
lake exe cache get Mathlib.Data.Real.Sqrt
lake build
python3 check_real_successor.py \
  --lean "$(lake env which lean)" \
  --lake "$(command -v lake)"
```

Das bereits vorhandene Originalarchiv kann beim ersten Schritt mit `--archive /absoluter/pfad/mathlib-c44e0c8.tar.gz` verwendet werden. Sowohl die frische Extraktion als auch die Wiederverwendung vorhandener Quellen wurden geprüft. `vendor/` und `.lake/` sind rekonstruierbare Abhängigkeiten und kein Teil dieses Quellpakets.

Der Prüfer schreibt pro Lauf ein neues Verzeichnis mit chronologischen Prozesslogs, Rückgabecodes, Loghashes, Quellenbindung und Axiommap. Er unterscheidet `VERIFIED_LOCAL_KERNEL`, eine erkannte falsche Aussage und `UNVERIFIED` bei unzuverlässiger Prüfung. Beschädigte Quellen und ein fehlender Compiler wurden als Negativfälle des Prüfers tatsächlich getestet. Die vier falschen mathematischen Beispiele stehen unter `negative/`.

## Aussageumfang

Die Definitionen setzen positive reelle Eingaben voraus. `cost * information ≤ work ≤ available` und `cost > 0` liefern die bedingte Informationsschranke. Die physikalische Interpretation als Landauer-Kosten und ein tatsächlich verfügbarer Arbeitsbetrag bleiben Voraussetzungen. SI-Kalibrierung, neue Messdaten, Entstehung physikalischer Raumzeit oder Produktivbetrieb werden nicht aus dem Kernel-PASS abgeleitet.

Die Erweiterung des bestehenden Manuskript-Workflows liegt als Quellenkandidat vor. Native CI am späteren Repository-HEAD, sieben unabhängige Checker, Review-/Main-Aufnahme und Zenodo-Veröffentlichung sind offen. Das Forschungspaket enthält eigene Fach- und Prosafassungen mit den genauen Grenzen. `EFFECT_ACK_DONE` bleibt unbestätigt.

## Rechte und Herkunft

Copyright 2026 Ingolf Lohmann. Neue QIK-VRT-Hilfsprogramme: PolyForm-Noncommercial-1.0.0; Forschungs- und Dokumentationstexte: CC-BY-NC-ND-4.0. Unveränderte Vorläuferdateien behalten ihre Herkunft. Drittkomponenten, insbesondere Lean und mathlib, behalten ihre eigenen Lizenzen. Die Standardlizenztexte liegen unter `LICENSES/`; das durch den Bootstrap unverändert bereitgestellte mathlib enthält seine eigenen Originalhinweise. Eine Architekturveröffentlichung erteilt keine pauschale kommerzielle Implementierungslizenz.
