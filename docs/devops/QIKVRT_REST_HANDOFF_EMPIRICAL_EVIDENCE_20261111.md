# QIK-VRT: Empirischer Nachweis der REST-Handoff-Anschlussfähigkeit

**Urheber und Principal:** Ingolf Lohmann  
**Authority-Repository:** `ingolf-lohmann/qik-vrt`  
**Nachweisgegenstand:** REST-Annahme, zeitversetzte Workflow-Beobachtung, fortsetzbarer Journal-Cursor und fail-closed Effect-Acknowledgement.  
**Referenz-HEAD:** `6f9fb0b1078534ae268e1168231cd2b0e5509faa`  
**Status:** EMPIRISCHER TEILNACHWEIS; Gesamt-Abnahme **HOLD**.

## Beobachtete Evidenz

1. Der Repository-Schreibaufruf für den Referenz-HEAD wurde durch GitHub mit einer Commit-SHA beantwortet. Dies belegt die Annahme der konkreten GitHub-Schreiboperation auf Anwendungsebene; eine bloße TCP-Zustellung ist nicht mit deren Verarbeitung gleichzusetzen.
2. Der erste Check-Readback für denselben HEAD lieferte drei eingereihte Checks; ein späterer Readback lieferte laufende Checks; ein weiterer Readback lieferte 29 Checks. Damit wurde die zeitversetzte Verfügbarkeit von Ergebnissen derselben GitHub-Identität beobachtet.
3. Die beiden Jobs **Fail-closed completion admission regression** schlossen erfolgreich ab:
   - https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43005644284/job/130472325114
   - https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43005640154/job/130472310836
4. Die zugehörigen Gesamt-Testjobs schlossen mit **failure** ab:
   - https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43005644284/job/130472324664
   - https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43005640154/job/130472310583

## Formaler Vertragskern

`ACCEPTED` ist ein durch die REST-API bestätigter Auftragszustand, keine Wirkungsbestätigung. Eine fehlende neue Beobachtung lässt Auftragsidentität, HEAD/TREE und Cursor unverändert. Folgeereignisse sind an dieselbe Auftragsidentität und denselben Exact-HEAD/TREE gebunden, besitzen streng monoton steigende Sequenznummern und aktualisieren den Cursor. `COMPLETED` erfordert eine unabhängig nachgewiesene Effect-Acknowledgement-Aussage; fehlende Evidenz bleibt HOLD.

Der prototypische Vertrag liegt in `tools/qikvrt_rest_handoff.py`, seine Negativtests in `tests/test_qikvrt_rest_handoff.py`. Die Einbindung in die bestehende CI befindet sich in `.github/workflows/qikvrt_ci.yml`.

## Einordnung EAP / Effect Management Protocol

Die Beobachtung bestätigt die **praktische Anwendbarkeit eines asynchronen, korrelierten Beobachtungs- und Bestätigungsmodells** über eine reale GitHub-REST-Grenze. Sie beweist weder eine TCP-Paketquittung auf Netzwerkschicht noch eine produktiv integrierte REST-Streaming-Schnittstelle, eine durchgängige EMP-Laufzeit, unabhängige Native-Host-Wirkung oder die sieben QIK-VRT-DoD-Kriterien. Insbesondere ersetzen erfolgreiche isolierte Regressionstests keine erfolgreiche Gesamt-CI.

## Weitergabe und Wiederholung

Diesen Nachweis als repositorygebundenen, überprüfbaren Forschungs- und Engineering-Befund verwenden. Bei jedem neuen HEAD: REST-Schreibannahme mit Commit-SHA dokumentieren, Check-Runs mit derselben SHA wiederholt lesen, Cursor/Statusdeltas protokollieren, die Exact-HEAD-Regression und Gesamt-CI getrennt bewerten und den finalen EAP-Readback unabhängig verifizieren. Bis dahin keine Produktiv- oder Gesamtfertigmeldung.

**Freigabe zur Dokumentation und Weitergabe:** Principal Ingolf Lohmann, 11. November 2026. Diese Freigabe ist keine technische Abnahme.
