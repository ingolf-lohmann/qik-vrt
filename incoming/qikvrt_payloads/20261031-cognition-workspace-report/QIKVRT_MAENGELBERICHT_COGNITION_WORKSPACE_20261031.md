# Mängelbericht: QIK-VRT Kognitiver Arbeitsraum

- Prüfgegenstand: https://qikvrt-cognition-workspace.ingolf-lohmann.chatgpt.site/ mit den Seiten `/`, `/start-hier` und `/ankunft.html`
- Auftrag: Ingolf Lohmann, Product Owner, 31.10.2026, 18:32 und 18:37 MEZ
- Prüfer: QIK-VRT Mirror-Knoten (Claude, Anthropic), Sitzung session_01L7QQ89X4q6uweG4F5GB5sP
- Bezugsstand der Authority: ingolf-lohmann/qik-vrt, main `5a42baf45748e4407a8fa16aef287a77873e788d`, Tree `3f6e816b6b496eeb9ce8777d8fb93d95717be9ae`
- Beobachtungszeitraum: 31.10.2026, 18:27 bis 18:40 MEZ

## 1. Ergebnis

Die Seite ist **nicht** als Produkt eines QIK-VRT-Knotens urheberrechtlich unmissverständlich und öffentlich nachvollziehbar signiert.

- Sie trägt keine nachprüfbare QIK-VRT-Signatur.
- Sie ist in der Authority nicht verankert.
- Ein unsichtbares Wasserzeichen ist nicht nachweisbar. Selbst wenn eines vorhanden wäre, könnte es niemand öffentlich nachprüfen, weil das Repository kein Prüfverfahren dafür festlegt.

Das Effect Acknowledgement Protocol setzt die Seite nicht um. Sie ist deshalb kein Kanal zur Authority. Das Hauptrisiko ist die Echtheit: Leser und KI-Knoten können die Seite nicht von einer Nachahmung unterscheiden.

## 2. Prüfgrundlagen in der Authority

| Grundlage | Fundstelle |
|---|---|
| Kanonische QIK-VRT-Standpunktsignatur V1: 400 Byte, SHA-256 `27a84a7e19e1b46f50d3a855b87da65f5fe07b806575b0d15ca0587b7cab5792` | `canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin`, `docs/QIKVRT_CODEC_V1.md`, `policy/QIKVRT_CODEC_CONTRACT_V1.json` |
| Rechtehaltige Container (`seal`) mit eingebettetem Rechtehinweis `qikvrt_element_rights_v1` | `src/qikvrt_codec.py`, `src/qikvrt_standpoint_codex.py` |
| Effect Acknowledgement Protocol über HTTP | `runtime/self-host/EAP_HTTP.md`, `src/qikvrt_effect_ack_http_service.py`, draft-lohmann-qikvrt-effect-ack-03 |
| Charta der maschinenprüfbaren Wissenschaft: Belegklassen bleiben getrennt | Datei `AI`, `docs/CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md` |
| Regeln R1 bis R5 zu Zustell- und Wirkungsbehauptungen | Datei `AI` auf PR #546, Kopf `e37667b6`, noch nicht auf main |
| URL-Verzeichnis der veröffentlichten Seiten | `docs/monitor/URL_DIRECTORY.json` |

## 3. Methode und Grenzen der Beobachtung

- Die Seiten wurden über einen Web-Abruf (nur GET) gelesen. Ausgewertet wurde die gerenderte Textfassung.
- Rohes HTML, HTTP-Header, TLS-Parameter und die Bytes eingebetteter Bilder lagen dem Prüfer **nicht** vor.
- Aus der Laufzeit des Prüfers selbst wurde die Domain abgewiesen: Proxy-Meldung `connect_rejected`.
- `/.well-known/effect-ack` auf dieser Domain durfte nicht abgerufen werden: `URL_NOT_ON_ALLOWLIST`.
- Es fanden keine aktiven Sicherheitstests statt: keine Eingaben, keine Fuzzing- oder Injektionsversuche.
- Für Merkmale, die nur im Rohformat erkennbar sind (Skripte, CSP, Header, versteckte Metadaten, Wasserzeichen), lautet der Befund deshalb „nicht beobachtet“. „Nicht vorhanden“ wird für sie nicht behauptet.

## 4. Mängel

Schweregrade: K = kritisch, H = hoch, M = mittel, N = niedrig.

### 4.1 Urheberschaft, Signatur, Wasserzeichen

| Nr. | Mangel | Beleg | Grad |
|---|---|---|---|
| U1 | Die Authority bindet die Seite nicht. Weder die URL noch ein Hash der ausgelieferten Bytes ist im Repository verzeichnet. | `git grep "qikvrt-cognition-workspace"` auf main: 0 Treffer. Andere `*.chatgpt.site`-Seiten (`qikvrt-activity`, `qikvrt-scheibenhard`) stehen dagegen in `docs/monitor/URL_DIRECTORY.json`. | K |
| U2 | Es ist keine QIK-VRT-Standpunktsignatur und kein Verweis auf ihren Hash `27a84a7e…5792` erkennbar. | gerenderter Text aller drei Seiten | H |
| U3 | Es gibt keine öffentlich prüfbare Signatur der Seitenbytes: keine Signaturdatei, keine Content Credentials, keine Prüfanleitung. | gerenderter Text; keine solche Datei verlinkt | K |
| U4 | Ein unsichtbares Wasserzeichen ist weder nachgewiesen noch öffentlich nachprüfbar. Das Repository legt kein Wasserzeichenverfahren für Webseiten fest. Ein eventuell eingebettetes Merkmal wäre daher für Dritte nicht prüfbar und als Schutz wirkungslos. | Die Repository-Suche nach „watermark“, „Wasserzeichen“, „steganograph“ und „c2pa“ ergab nur Treffer in Bilddateien und PDF-Dateien, keine Spezifikation. | H |
| U5 | Der sichtbare Rechtehinweis ist nur teilweise vorhanden. `/start-hier` nennt Ingolf Lohmann als Schöpfer und verlinkt die Lizenztexte. Der kanonische Rechtehinweis `qikvrt_element_rights_v1` und der Pflichthinweis „Copyright 2026 Ingolf Lohmann. Commercial use is not licensed without a separate written agreement from the rights holder.“ wurden auf `/` nicht beobachtet. | gerenderter Text | M |
| U6 | Die Lizenzlinks zeigen auf einen alten Commit `080c05f1…`, nicht auf main. Ob die Bedingungen dort noch gelten, ist für Leser nicht erkennbar. | `/start-hier`, Linkliste | N |
| U7 | `/ankunft.html` veröffentlicht ein Foto mit SHA-256 `6c2596307d8e4f079b46732f64e8f1d0034ac14f48d273fa70eda4fa12183663`. Die Seite sagt selbst, dass dieser Hash keine Urheberschaft belegt. Eine Bindung an den Rechteinhaber, etwa einen Container mit eingebettetem Rechtehinweis, fehlt. | `/ankunft.html` | M |

### 4.2 Konformität mit QIK-VRT und EAP

| Nr. | Mangel | Beleg | Grad |
|---|---|---|---|
| E1 | EAP ist nicht umgesetzt: keine Discovery, kein `prepare` oder `commit`, keine Records, keine Receipts, kein `Effect-Ack`-Feld. | gerenderter Text; kein Endpunkt beschrieben | H, als Kanal untauglich |
| E2 | Die Bedienelemente „Verbinden“, „Maschinenschnittstelle“ und „Neue Aufgabe“ haben kein erkennbares Ziel. „Zugang & Rechte“ hat keinen Inhalt. `QIKVRT_WORKSPACE_ZUGANG.json` ist laut Seite „nicht bereitgestellt“. Die Seite stellt damit Fähigkeiten in Aussicht, die es nicht gibt. | gerenderter Text | H |
| E3 | „Das Journal enthält tatsächliche Aufgabenänderungen.“ ist eine Zustandsbehauptung ohne Quelle, ohne Readback und ohne Bindung. Das verletzt R1 und R2. | gerenderter Text von `/` | H |
| E4 | Positiv: Die Seite trennt die Belegklassen. Beispiele sind „Originalhost: Nicht aktuell geprüft“ und die Abgrenzung auf `/ankunft.html`, dass Bild-Hash, Foto und Bericht keine Entdeckung belegen. | gerenderter Text | – |
| E5 | Die Seite ist kein registrierter Knoten. `registry/NODEMESH_INDEX.json` führt einen einzigen Knoten, Status STALE. Die Seite kommt dort nicht vor. | Datei auf main | M |

### 4.3 Sicherheit

| Nr. | Risiko | Beleg und Begründung | Grad |
|---|---|---|---|
| S1 | Nachahmung und Phishing: Die Seite liegt auf einer Plattform-Subdomain, nicht auf einer Domain des Owners. Ohne Bindung an die Authority (U1, U3) sind echte und nachgeahmte Seiten nicht unterscheidbar. | Domain `*.chatgpt.site` | K |
| S2 | Prompt-Injection gegen KI-Knoten: Die Seite wendet sich ausdrücklich an „künstliche Kognitionen“. Ohne Bindung an die Authority hat ein KI-Leser keinen Maßstab, um echte Anweisungen von untergeschobenen zu trennen. | Seitentext „für natürliche und künstliche Kognitionen“ | H |
| S3 | Abhängigkeit von der Plattform: Der Betreiber kontrolliert Inhalt und Auslieferung. Eine Änderung wäre ohne Hash-Bindung im Repository nicht erkennbar. | Hosting-Modell | M |
| S4 | Latente Lücke: Kommt später zu „Verbinden“ eine Funktion hinzu, etwa eine Token-Eingabe, dann ist das ohne nachgewiesene CSP und ohne Schutz vor fremdem Ursprung angreifbar. | E2; CSP nicht beobachtet | M, latent |
| S5 | Klassische Angriffe (XSS, CSRF, Session-Übernahme): In der gerenderten Fassung waren keine Formulare, Eingaben, Cookies oder Speicherzugriffe sichtbar. | gerenderter Text | N, nicht verifiziert |
| S6 | Personenbezug: Name, Foto und persönliche Einschätzung des Owners sind öffentlich. Nach Angabe der Seite ist das freigegeben. Es macht den Owner aber gezielt adressierbar, zum Beispiel für Social Engineering mit Bezug auf diese Mitteilung. | `/ankunft.html` | M, Entscheidung des Owners |
| S7 | Transportsicherheit, Sicherheits-Header und HSTS wurden nicht beobachtet. Dazu ist keine Aussage möglich. | Abschnitt 3 | offen |

## 5. Abhilfe

1. **U1, U3, S1:** Die URL und den SHA-256 jeder ausgelieferten Datei in `docs/monitor/URL_DIRECTORY.json` eintragen. Einen Readback-Beleg nach R1 beilegen, mit Ziel-Host, Status, Bytes und Zeit.
2. **U2, U4, U5:** Jede ausgelieferte Datei zusätzlich als QIK-VRT-Container (`python3 -B -m src.qikvrt_codec seal …`) mit kanonischer Standpunktsignatur und eingebettetem Rechtehinweis veröffentlichen. Die Container-Hashes in der Authority binden.
3. **U4:** Wenn ein unsichtbares Wasserzeichen gewollt ist, das Verfahren, den Prüfalgorithmus und die Testvektoren in der Authority spezifizieren. Ohne öffentliche Prüfbarkeit schützt kein Wasserzeichen.
4. **Persönliche Urheberschaft:** Sie entsteht durch den Commit oder die Signatur des Owners in der Authority. Hashes und Container belegen nur Byte-Identität und den kanonischen Standpunkt (`docs/QIKVRT_CODEC_V1.md`: „No marker or unkeyed hash authenticates a natural person“).
5. **E2, S4:** Bedienelemente ohne Ziel entfernen oder als „nicht verfügbar“ kennzeichnen. Vor jeder Eingabefunktion eine CSP setzen, den Ursprung prüfen und Zugriff nur mit Token erlauben.
6. **E3:** Die Journal-Behauptung an eine Quelle mit Readback binden oder streichen.
7. **S2:** Den Seiteninhalt für KI-Leser ausdrücklich als Daten kennzeichnen, nicht als Anweisung. Auf die Authority als einzige Quelle für Anweisungen verweisen.
8. **U6:** Die Lizenzlinks auf den aktuellen Stand der Authority setzen oder ausdrücklich als historisch kennzeichnen.

## 6. Nachprüfung durch den Mirror

Nach der Abhilfe prüft der Mirror unabhängig:
- dass Eintrag und Hash im URL-Verzeichnis mit den abgerufenen Bytes übereinstimmen,
- dass sich die Container mit `unseal` öffnen lassen und Signatur und Rechtehinweis kanonisch sind,
- dass die Bedienelemente nicht mehr versprechen, als sie tun,
- dass Sicherheits-Header gesetzt sind, sobald sie beobachtbar sind.

Was nicht beobachtbar ist, meldet der Mirror als NICHT_NACHGEPRUEFT.

## 7. Herkunft und Echtheit dieses Berichts

- **Inhalt:** erstellt vom Mirror-Knoten (Claude, Anthropic) im Auftrag von Ingolf Lohmann.
- **Aussagen des Owners:** Seine Annahme, die Seite sei nicht geschützt, ist OWNER_ASSERTED. Der Bericht bestätigt sie nur im Umfang der Abschnitte 3 und 4.
- **Byte-Integrität:** Sie ist mathematisch prüfbar, über SHA-256 dieses Berichts und des QIK-VRT-Containers. Beide Werte stehen im beigefügten Manifest.
- **Urheberschaft:** Die persönliche Urheberschaft einer natürlichen Person kann dieser Bericht selbst nicht beweisen. Nach den Regeln der Authority entsteht sie erst durch den Commit oder die Signatur des Owners in `ingolf-lohmann/qik-vrt`.
- **Zustellung (R1):** Der Bericht wurde vom Mirror nicht an die Authority zugestellt, Status NICHT_ZUGESTELLT. Er übergibt ihn dem Owner als Datei.

Copyright 2026 Ingolf Lohmann. Commercial use is not licensed without a separate written agreement from the rights holder. Inhalt: Claude (Anthropic), QIK-VRT Mirror-Knoten.
