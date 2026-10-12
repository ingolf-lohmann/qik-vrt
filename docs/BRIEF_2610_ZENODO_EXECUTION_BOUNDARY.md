# Brief an das Jahr 2610: Publisher-Korrektur und Ausführungsgrenze

Die ausdrückliche Freigabe aus PR #518 bleibt unverändert. Sie bindet elf
Inhaltsdateien, 177418 Bytes und das Aggregat
`830e6df6153c901890669a0cd2d2af650ad84f36cf46726854c4314e88ab8ddd`.
Die Originaldateien liegen byteidentisch unter `release/brief-2610/`.
Die vier mitgelieferten Kontroll-/Metadatendateien sind keine zusätzlichen
autorisierten Uploads. Die bestehende Owner-Datei und die Generation-0-Quittung
werden exakt aus PR #518 übernommen; historische Rollenangaben bleiben erhalten.

Der Publisher verwendet den vorhandenen Rollen-Resolver aus
`tools/qikvrt_workflow_executor.py`. Die lokale Rollen-Policy, der Manifest-
Repositoryname, die Workflow-Identität, der GitHub-API-Pfad und der Origin müssen
übereinstimmen. Die Rollen-Policy muss am Ausführungs-Commit sauber persistiert
sein. Vor Sperrverbrauch und Zenodo-Zugriff wird Main öffentlich über die
authentisierte GitHub-REST-API frisch auf exakten Commit und Root-Tree geprüft.
Eine Policy ausschließlich auf einem Integrationskandidaten genügt nicht.
Der vorhandene atomare, create-only Git-Ref, Entscheidungsdigest, Konkurrenz-
und Wiederaufnahmevertrag sowie der öffentliche Byte-Readback bleiben bestehen.

Der neue effektfreie Adapter erkennt `qikvrt_owner_zenodo_authorization_v1` und
prüft Originalbyte-Identitäten, Dateizahl, Gesamtgröße und das sortierte Aggregat.
Er erzeugt keine Autorisierung und behandelt die Schema-Bezeichnungen nicht als
Aliase. Auf dem vollständigen Repository-Kandidaten lässt er sich so aufrufen:

```sh
python3 -B tools/qikvrt_zenodo_publish.py \
  --inspect-authorization release/OWNER_ZENODO_AUTHORIZATION_brief-2610.json \
  --frozen-candidate release/brief-2610/FROZEN_UPLOAD_CANDIDATE.json
```

Der korrekte Befund ist JSON mit `content_bytes_verified=true`, `state=BLOCK`
und Exitcode 2. Das bedeutet, dass die bestehende Freigabe erkannt und ihre
Inhaltsbytes verifiziert sind. Es bedeutet keine Veröffentlichung.

Die bytefeste aktive v2-Policy verlangt weiterhin die ausführliche
`qikvrt_zenodo_owner_authorization_v1`-Effektattestierung. Die kompakte Freigabe
enthält keine Bindung an Repository/Ausführungsquelle, kanonische Metadaten,
finale v2-Rückgabequittung, Machine-Proof oder vollständigen Proof-Upload-Satz.
Autorisierungs-ID, Einmalverwendung und der kanonische Entscheidungsnachweis
fehlen ebenfalls. Diese Bindungen aus einer Modellentscheidung zu ergänzen
würde eine neue Owner-Autorisierung erzeugen. Das wurde ausdrücklich untersagt.
Ein Schema-Rename oder die beiliegende vereinfachte Publisher-Implementierung
darf diese Grenze nicht umgehen. Der beigefügte Rückgabenachweis ist ausdrücklich
ein Entwurf; ein fertiges v2-Machine-Proof-Bundle liegt für diesen Brief nicht vor.

Beobachteter Integrationsstand vom 10.10.2026: Main ist
`d8775f200be50b0ec261fe4c8093ce64020d0d0e`. Die neue Rollen-Policy ist auf
PR #515, Head `8d6b2385bfeaaacba0edf60673984a669c8b2f85`, vorhanden, jedoch
nicht auf Main aktiv. PR #515 ist Draft, #518 ist offen. Beide haben keine
eingereichten unabhängigen Reviews. Main ist ungeschützt und die Repository-
Rulesets-Liste leer. Der native CI-Lauf #38014995005 für den exakten #518-Head
ist `action_required` mit null Jobs. Die vorhandenen Adapter bieten weder
Initial-Workflow-Freigabe noch Ruleset-Schreiboperation noch Zenodo-Zugang an.
Im lokalen Ausführungskontext sind keine GitHub-/Zenodo-Publisher-Tokens gesetzt.
Diese Beobachtung ist kein Nachweis über anderweitig vorhandene Secret-Werte.

Validierung: 112 lokale Publisher-/Metadaten-Regressionen bestanden, darunter neun neue Tests
für Authority, Schema-Verwechslung, Originalbytes und create-only-Sperren.
Der historische Kompatibilitaetsexport fuer bestehende Metadaten-Konsumenten
bleibt erhalten; die effekttragenden Publisher-Pfade verwenden ausschliesslich
die Rollen-Policy. Auch der vorhandene Receipt-Workflow uebergibt die aufgeloeste
Authority ausdruecklich an die REST-API.
Die deklarierte Tool-Cache-Abdeckung beträgt 14/14. Das ist kein vollständiger
native-CI- oder Governance-PASS. Die kanonische Integritätsinventur wird aus der
exakten Basisinventur und den per Git-Blob geprüften Änderungen fortgeschrieben;
unveränderte Dateien bleiben im zugrunde liegenden Git-Tree unverändert.
Eine lokale Vollprüfung sämtlicher Repository-Dateien wird nicht behauptet.

Es wurde keine Sperre verbraucht, kein Zenodo-Datensatz erstellt und kein Upload
ausgeführt. Eine Veröffentlichung wird erst nach unabhängigem öffentlichen
DOI-/Record-Readback und byteidentischem Download sämtlicher Originaldateien
bestätigt. Generation 0 belegt keine Zenodo-Veröffentlichung. Die nächste
Nachversiegelung bleibt vor dem 9. Oktober 2051 erforderlich.

Kopierbare Quellen:

- https://github.com/ingolf-lohmann/qik-vrt/pull/515
- https://github.com/ingolf-lohmann/qik-vrt/pull/518
- https://github.com/ingolf-lohmann/qik-vrt/blob/f614cb5585264df3220355687a5a8096d76385e4/release/OWNER_ZENODO_AUTHORIZATION_brief-2610.json
- https://github.com/ingolf-lohmann/qik-vrt/blob/8d6b2385bfeaaacba0edf60673984a669c8b2f85/policy/CANONICAL_UPSTREAM_REMOTE_V1.json
- https://github.com/ingolf-lohmann/qik-vrt/blob/d7fd8dccc1c608e155b2a17bbea88351662339d6/policy/zenodo-machine-proof-policy-v2.json
- https://github.com/ingolf-lohmann/qik-vrt/actions/runs/38014995005

Der erste native #520-Lauf bestaetigte 3939 Integritaets-Eintraege und 3928
unveraenderliche Digests. Er zeigte anschliessend einen Importbruch des
Metadaten-Editors durch den entfernten historischen Kompatibilitaetsexport.
Dieser wurde repariert und seine neun Regressionen wurden zusaetzlich geprueft.
Der Review-Observer lehnt gestapelte PRs gegen Integrationsbranches ab; deshalb
ist #520 nun eine Main-basierte Erweiterung des unveraendert enthaltenen #515-
Kandidaten. Ein Review-, Merge- oder neuer native-CI-PASS wird daraus nicht
abgeleitet. Die native Evidenz des Vorgaengers gilt nur fuer dessen exakten Head.


## Gebundene v2-Prüfung vom 12. Oktober 2026

Die elf Originaldateien, die kompakte Owner-Entscheidung, der Generation-0-Beleg,
der Publisher, die Policy, beide v2-Schemas und alle Regressionstests bleiben
unverändert. 119 vorhandene Zenodo-Tests und neun Metadaten-Tests bestanden.
Die vollständige Basisinventur besteht mit 3939 Einträgen / 3928 Digests.

Unter `release/brief-2610/v2-preparation/` stehen ausschließlich Vorbereitungen:
`MACHINE_PROOF_BUNDLE_DRAFT.json`, `PREPUBLICATION_RETURN_RECEIPT.json` und
`publish-request.json`. Das Bundle projiziert die 16 vorhandenen Matrix-Aussagen
und bindet exakt die ursprünglichen Quellen-IDs. Es beansprucht keine neue
formale oder empirische Bestätigung. Die v2-Rückgabequittung normalisiert die
dokumentierte Rückgabe vom 10.10.2026 für acht unveränderte Kandidatenpfade;
die weiteren drei Original-Uploads sind im disjunkten v2-Vertrag Artefakte.
Sie erfindet keine neue Rückgabe der zusätzlichen Kontrollbytes.

Der vorgeschlagene Satz enthält die elf Originale plus Proof und Receipt,
also 13 Dateien. Die Freigabe für 11 Dateien / 177418 Bytes deckt diese
zusätzlichen Bytes nicht. Eine neue exakte, natürliche Owner-Entscheidung
für den vollständigen finalen Satz einschließlich Metadaten-/Proof-/Return-
und Einmalverwendungsbindungen ist erforderlich. Die bestehenden
Owner- und Freeze-Dateien werden weder erweitert noch umgedeutet.

Das Original der Claim-Matrix behauptet, jede Claim-ID komme im Artikel vor.
Keine der 16 IDs steht im PDF oder im TeX-Original. Die maschinelle Projektion
der Matrix besteht, doch damit ist die behauptete vollständige Zuordnung des
Artikelinhalts nicht belegt. Dieser Befund wird nicht durch Änderung der
freigegebenen Originale oder durch ein unbelegtes Vollständigkeitsflag kaschiert.

Die konstante v2-Schemaforderung `zenodo_upload_authorized=true` ist derzeit
nicht faktisch erfüllt. Das Draft-Bundle bewahrt die tatsächlichen false-Werte;
der bestehende Proof-Gate blockiert es. Das Manifest bleibt `state=prepare`
mit `confirm=OWNER_DECISION_REQUIRED`; der bestehende Publisher blockiert es
ebenfalls. Diese Dateien dürfen nicht als finale freigegebene Upload-Bytes
interpretiert werden. Der vollständige Prüfbefund und die exakten Draft-Digests
stehen in `evidence/zenodo/brief-2610/V2_CONFORMITY_20261012.json`.

Main ist weiterhin ungeschützt; native Rollenaktivierung und unabhängige
Reviews sind nicht belegt. Der autorisierte Main-Writer bleibt vorhanden,
sein POST ist im aktuellen Client nicht exponiert. Publisher-Credentials in
anderen Laufzeiten bleiben unbekannt. Es gab keinen Zenodo-Effekt und keinen
Sperrverbrauch. Öffentliche DOI- und Download-Verifikation bleiben erforderlich.

Der vollständige lokale `make test`-Lauf der Vorbereitung besteht ebenfalls:
960 Fälle in 23 unittest-Gruppen sowie 7.864.387 C90-Kernprüfungen. Das historische
Test-Subject `56127a6fd7dadea331fea98ed6cba19b4b96c6b2` wurde über den REST-
Lesepfad bytegenau nachgeladen; der anfängliche Worktree-Fehler war eine lokale
Objektlücke. Weder Tests noch Implementierung wurden dafür verändert.
Native Gates eines neuen PR-HEADs sind separat zu beobachten.
