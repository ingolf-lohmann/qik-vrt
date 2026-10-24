<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->

# Spur halten: Quality Gates für einen portablen Universal Transputer

Softwarebefund, Zustandsübertragung und prüfbare Hardware-Anschlussfähigkeit im QIK-VRT Mesh

Ingolf Lohmann - Konzeption, Anforderung und Verantwortung. Technische Erhebung, Ausarbeitung und Satz: OpenAI Codex im Auftrag von Ingolf Lohmann. Technischer Bericht, Version 0.1, 28. September 2026. Nicht begutachtet.

## Zusammenfassung

Diese Fallstudie untersucht einen exakt gebundenen Quellstand von QIK-VRT anhand von zehn Quality Gates für Linux-Distribution, Docker-Container, Universal Transputer und Universal Terminal. Die Untersuchung trennt vorhandenen Code, tatsächlich ausgeführte Teilprüfungen und den Nachweis am ausgelieferten Ziel. In der frischen lokalen Auswahl bestehen 103 Tests; ein weiterer wird wegen fehlender Systemwerkzeuge übersprungen. C90-Kern und daraus erzeugte Assembly bestehen ihre Prüfungen. Ein Vier-Prozess-Mesh führt zwei lokale TCP-Paare aus. Der innere Kern umfasst in der untersuchten x86-64-Übersetzung 394 Byte Code und schreibgeschützte Daten.

Auf der hier ausdrücklich vorgeschlagenen ordinalen Evidenzskala 0 bis 4 ergibt sich für die vollständigen Gates der Vektor (2, 1, 2, 2, 2, 2, 2, 1, 0, 2). Kein vollständiges Gate erreicht in diesem begrenzten Audit den Nachweis am ausgelieferten Ziel. Dies ist keine Aussage, dass die Software nicht existiere: Ausführbare Komponenten sind unmittelbar beobachtet. Es begrenzt die darüber hinausgehende Behauptung eines vollständig freigabefähigen Gesamtprodukts.

Serialisierung und Deserialisierung ermöglichen die Übertragung expliziter Zustände, sofern Identität, Semantik, Integrität und Autoritätsgrenzen erhalten bleiben. Daraus folgt weder die beliebige Migration eines laufenden Betriebssystemprozesses noch ein Nachweis physischer Hardware. Die Verbindung zu einem von Ingolf Lohmann als Meta-Transistor bezeichneten Hardware-Anteil wird als offene Verfeinerungsaufgabe formuliert. Ethik ist ein verbindlicher normativer Rahmen; technische Ungefährlichkeit muss dennoch jeweils begründet und geprüft werden.

## Leseschlüssel

Die Claim-IDs [Q01] bis [Q18] verweisen auf die maschinenlesbare Anspruchsmatrix. Messwerte gelten ausschließlich unter den angegebenen Bedingungen. OFFEN bedeutet fehlenden Nachweis im erhobenen Umfang und nicht automatisch einen Produktfehler. Ein Zenodo-Eintrag wäre ein archivierter Forschungsstand und keine Produktfreigabe. [Q01, Q02, Q03]


# 1. Untersuchungsgegenstand und Methode

Untersucht wird Goldkelch/qik-vrt, Main-Commit f2fa5a5e11dafe6d9579301c2a479e0eaa02d16c, TREE 956c16b291c05243437b1f018321936e4438949a. Der Stand ist der Messgegenstand; der spätere Dokumentations-Commit ist ein eigener Subject. Die Quellenbindungen enthalten Dateigröße, SHA-256 und Git-Blob. Die Tests wurden vor dem Hinzufügen dieses Berichts im sauberen Checkout ausgeführt. [Q01]

Die Auswahl umfasst zehn Testmodule zu Distribution, öffentlichem Readback, MegaST-Profil, Cloud-Transputer, Subject-Bindung, Live-SSE, Repository-Terminal, HTTP-EFFECT_ACK und Netzwerkgrenzen. Der Standardbibliotheksrunner entdeckt 104 Fälle: 103 bestanden, einer übersprungen, Dauer 3,822 Sekunden. Der übersprungene Fall benötigt nginx/runuser. Ein zunächst versuchter pytest-Aufruf war mangels installiertem pytest nicht ausführbar; anschließend wurde der im Repository unterstützte unittest-Pfad benutzt. [Q02]

C90 wurde mit GCC 13.3.0, x86-64, -std=c90, -pedantic-errors und -Os übersetzt. Ein separater Aufruf assembliert den erzeugten Kern und linkt denselben Testkorpus erneut. Beide Ausführungen bestehen. Zusätzlich wurde tools/qikvrt_real_mesh.py frisch mit dem exakten HEAD und TREE ausgeführt. Der resultierende Scope lautet LOOPBACK_TCP_ONLY. Ein bloßer grüner Workflowname wird nicht als Wirkungsbeleg übernommen. [Q03, Q04]

Als ergänzende CI-Evidenz wurde Run 36346727864, Job 108697217922, am selben HEAD gelesen. Das Audit-ZIP 10940821417 wurde heruntergeladen und gegen den GitHub-SHA-256 geprüft. Seine Diagnose meldet MAKE_TEST_EXIT=0 und einen unveränderten Worktree. Diese Erhebung ersetzt weder einen ISO-Boot noch eine Messung an einem physischen Chip. [Q05]

## Geltungsgrenzen

Docker, QEMU, Cargo und GHDL standen im lokalen Messpfad nicht als ausführbare Programme bereit. Deshalb wurden hier kein Containerstart, kein vollständiger Rust-/GHDL-Roundtrip und kein physischer Boardtest neu ausgeführt. Die GitHub-Abfrage umfasste die ersten Seiten der auf diesen HEAD gefilterten Push- und workflow_dispatch-Läufe; sie war keine Vollerhebung sämtlicher workflow_run-Ereignisse. Höhere historische Nachweise werden ohne erneute exakte Bindung nicht übertragen. [Q06]


# 2. Eine berechenbare Evidenzskala

Eine zuvor vereinbarte numerische Skala war im zugänglichen Kontext nicht auffindbar. Deshalb wird folgende Skala als offengelegte Operationalisierung vorgeschlagen. Sie misst Nachweisstufen des geprüften Scopes, weder wirtschaftliche Fertigstellung noch statistische Sicherheit. [Q07]

| Stufe | Evidenzstatus |
|---|---|
| 0 | Noch nicht operationalisiert im erhobenen Nachweisstand |
| 1 | Spezifiziert; vollständige Implementierung nicht belegt |
| 2 | Implementierungspfad vorhanden; vollständiger Ausführungsnachweis fehlt |
| 3 | Vollständiger Gate im gebundenen Test bestätigt |
| 4 | Vollständiger Gate frisch am ausgelieferten Ziel bestätigt |

Ein Gate erhält nur die höchste vollständig begründbare Stufe. Besteht beispielsweise der HTTP-Test, während die frische Firefox-Beobachtung fehlt, erhält der gesamte Terminal-Gate keine Stufe 3. Teilprüfungen werden gesondert genannt. Das Verfahren enthält sachkundige Bewertungsentscheidungen; die anschließende Zählung ist rein mechanisch und in QUALITY_GATES.json nachvollziehbar. [Q07]

Für QG-01 bis QG-10 ergibt sich (2, 1, 2, 2, 2, 2, 2, 1, 0, 2). Damit liegen ein Gate auf Stufe 0, zwei auf Stufe 1 und sieben auf Stufe 2; keines liegt auf Stufe 3 oder 4. Das Minimum ist 0. Die Zahl vollständig am ausgelieferten Ziel bestätigter Gates ist 0 von 10. Ein Mittelwert wird bewusst nicht als Freigabemaß verwendet: Die Skala ist ordinal, und ein starkes Teilgebiet kompensiert keinen offenen Pflicht-Gate. [Q08]

Für den hier geforderten Gesamtumfang lautet die Freigabebedingung: G01 UND G02 UND ... UND G10, jeweils mit erfülltem Zielscope. Der Audit unterstützt diese Konjunktion derzeit nicht. Das ist ein prüfbarer HOLD wegen unvollständiger Evidenz. Ein Release einer enger begrenzten experimentellen Komponente hätte einen eigenen, vorab deklarierten Scope. [Q07, Q08]


# 3. Quality Gates: Identität bis Terminal

## QG-01 Exakte Produktidentität - Stufe 2
HEAD und TREE sowie Build-/Subject-Bindungen sind implementiert.

Schließungskriterium: Ein gemeinsames eingefrorenes Manifest mit ISO-Hash, OCI-Digest, Distribution, ISA, Paket- und Toolversionen für beide Profile.

## QG-02 Reproduzierbare Builds - Stufe 1
Buildpfade existieren; Docker nutzt bookworm-slim und nicht vollständig versionierte apt-Pakete.

Schließungskriterium: Zwei saubere Builds je Profil mit fixierten Inputs; identische Digests oder vorab begründete, separat gebundene Normalisierung.

## QG-03 Boot und Containerstart - Stufe 2
ISO-Boot-, Container- und Health-Prüfpfade sind vorhanden.

Schließungskriterium: Frischer BIOS-/gegebenenfalls UEFI-Boot des veröffentlichten ISO sowie OCI-Start auf jeder zugesagten ISA; keine übersprungenen Pflichtchecks.

## QG-04 Transputer-Konformität - Stufe 2
C90 und Assembly bestehen frisch; LUT, Guards, Bindungen, Replay und Backpressure werden ausgeführt.

Schließungskriterium: Derselbe Konformanzkorpus für C90, Smalltalk und MC68000, Hin- und Rückweg, beschädigte und falsch adressierte Nachrichten; exakte Zielartefakte.

## QG-05 Interaktives Terminal - Stufe 2
HTTP-Terminal samt Prepare/Commit/Readback wird lokal getestet. Firefox-/Fensterprüfung ist implementiert.

Schließungskriterium: Sichtbares frisches Firefox-Fenster, echte Eingabe, gebundene Ausführung und beobachtetes Ergebnis im ausgelieferten Profil.


# 4. Quality Gates: Mesh bis Auslieferung

## QG-06 Cloud-Mesh - Stufe 2
Vier lokale Prozesse und zwei Paare kommunizieren frisch über TCP; begrenzte Receipts liegen vor.

Schließungskriterium: Mindestens zwei getrennte Hosts/Runtimes: authentifizierte Adressierung, Versionsbehandlung, Abbruch, Wiederanschluss und frischer Ergebnis-Readback.

## QG-07 Persistenz und Wiederherstellung - Stufe 2
Store-/Quellen-Recovery und Container-Profile sind implementiert; lokales Mesh-Replay nach Neustart wird beobachtet.

Schließungskriterium: Neuer Container und anderer Host erhalten Identität, Store und Historie; anschließender frischer End-to-End-Roundtrip aus dem übertragenen Zustand.

## QG-08 Fehler und Autorität - Stufe 1
Mehrere Negativpfade bestehen; der bekannte Installation-403-Fehler ist auf diesem Main nicht als vollständig reparierter Produktpfad belegt.

Schließungskriterium: Rate-Limit-, Permission- und andere 403 getrennt; sichere Reset-/Request-Metadaten, Subject bleibt erhalten, keine Blind-Retries, keinerlei Review/PASS/EFFECT_ACK aus 403; Isolation und Secrets.

## QG-09 Ressourcen und Last - Stufe 0
Codegrößen sind gemessen. Vorab eingefrorene Leistungsbudgets für den gesamten zugesagten Betrieb sind hier nicht nachgewiesen.

Schließungskriterium: Vor der Messung CPU/RAM/Startzeit/p95/p99/Durchsatz sowie Last und Hostprofil festlegen; Überlast bleibt begrenzt und fail-closed.

## QG-10 Öffentliche Auslieferung - Stufe 2
Download-, Hash- und Boot-Readback sind im Repository vorgesehen und getestet.

Schließungskriterium: Unabhängiger Client lädt ISO und Container per festem Digest und wiederholt Terminal-/Transputer-Pfad; öffentliche Referenz und vollständige Receipts.


# 5. Wie klein kann der ausführbare Kern sein?

Der Begriff Kernel bezeichnet hier zunächst den inneren QIK-VRT-Berechnungskern, nicht den Linux-Kernel und nicht die gesamte vertrauenswürdige Systembasis. Die C90-Schnittstelle verwendet 14 Eingabebytes und 6 Ausgabebytes. Der Kern benötigt laut Quellvertrag weder Betriebssystem, Netzwerk noch Heap; seine Annahmen umfassen acht Bit pro Byte und einen exakten vorzeichenlosen 32-Bit-Typ. [Q09]

| Abgrenzung | Umfang |
|---|---|
| Eine LUT-Funktion | .text: 86 Byte |
| Inneres Kernobjekt | .text + .rodata: 394 Byte |
| Sechs C90-Objekte zusammen | Code + schreibgeschützte Daten: 7.174 Byte |
| stdio-Adapter als ELF-Datei | 26.792 Byte Dateigröße |
| Adapter: text + data + bss | 80.512 Byte, ohne Stack und externe Laufzeit |

Die 86 Byte sind die gemessene Maschinenfunktion qikvrt_boolean_lut. Sie allein realisiert nicht den ganzen Transputer. Für das Kernobjekt ergeben sich 384 Byte .text plus 10 Byte .rodata. Mit Wire, SHA-256, Exchange, Bus und EFFECT_ACK summieren sich die entsprechenden Abschnitte auf 7.174 Byte. Der ausführbare stdio-Adapter ist 26.792 Byte groß; seine Abschnitte text/data/bss umfassen zusammen 80.512 Byte. Stack, dynamische Bibliotheken und Betriebssystem kommen hinzu. Objektdateigröße, geladenes Abbild und RAM-Bedarf sind deshalb verschiedene Größen. [Q03]

Diese Werte sind reproduzierbare Punktmessungen einer konkreten Übersetzung, keine bewiesenen Minimalgrößen und keine Transistorzahlen. Ein anderer Compiler, eine andere ISA oder andere Prüfanforderungen kann andere Größen erzeugen. Für Linux-Distribution, Browser und Cloud-Träger wurde hier keine Gesamtgröße ermittelt. Ein Docker-Container nutzt den Kernel seines Hosts; ein kleiner Container enthält deshalb nicht automatisch einen ebenso kleinen unabhängigen Kernel. [Q09, Q10]


# 6. Serialisierung, Deserialisierung und Invarianten

Der vorhandene Transputer speichert explizite Identität, Objekte, Ereignisse, Anker und Checkpoints. Die Quellwiederherstellung bindet Originalbytes und Git-Blobs; Store-Snapshots referenzieren alle benötigten Objekte. Ein Neustart kann daraus einen kontrollierten logischen Zustand rekonstruieren. Das ist etwas anderes als ein universeller Dump von CPU-Registern, offenen Sockets, Dateideskriptoren und beliebigen Fremdbibliotheken eines laufenden Prozesses. [Q11]

Für einen Encoder E und Decoder D lautet die gewünschte Bedingung: D(E(s)) ist unter der vereinbarten Beobachtungsrelation äquivalent zu s. Zusätzlich muss die relevante Invariante I nach Wiederherstellung gelten. Gleiche Bytes genügen nur dann, wenn die Zielumgebung denselben Vertrag interpretiert. Bei einer neuen ISA braucht es eine kompatible Implementierung oder Emulation; Host-APIs, Endianness, Rechte und externe Ressourcen bleiben explizite Voraussetzungen. WebAssembly verdeutlicht diese Grenze: Ein portables Binärformat legt nicht automatisch die verfügbaren Host-APIs fest. [Q12]

Für QIK-VRT sind mindestens Subject, Quell- und Zielidentität, Protokollversion, Längen, Integrität, Anfragekorrelation und die Trennung zwischen Transportbestätigung und Wirkungsbestätigung zu erhalten. Persistierte Daten dürfen keine beliebige neue Autorität verleihen. Der Decoder muss unbekannte Versionen, ungültige Längen, beschädigte Bindungen und widersprüchliche Zustände ablehnen. HMAC liefert Authentizität im Schlüsselmodell, aber keine Verschlüsselung und keinen eigenständigen Identitätsnachweis einer natürlichen Person. [Q11, Q12]

Der frische Mesh-Receipt beobachtet Neustart und Replay ohne zusätzliche Ledger-Einträge innerhalb seines lokalen Modells. Er meldet ausdrücklich keine Authority-/Mirror-Synchronisation und keinen allgemeinen EFFECT_ACK. Die im Test verwendeten Repository-Rollen und Mirror-Baumwerte sind Topologiedaten dieses Experiments; sie sind keine frische Live-Synchronisationsmessung des entfernten Mirror-Repositories. [Q04]

Für eine Hardware-Verfeinerung wird eine Relation R zwischen Software- und Hardwarezuständen benötigt: initial passende Zustände, erhaltende Übergänge und übereinstimmende beobachtbare Ergebnisse. Ein endlicher digitaler Zustandsautomat lässt sich unter passenden technischen Annahmen in Logik beschreiben. Ob die konkrete Schaltung Timing, Reset, Taktübergänge, Fehlerfälle und Ressourcenbudgets einhält, bleibt durch Synthese und Messung zu schließen. Eine solche Beweiskette wurde hier nicht ausgeführt. [Q12, Q13]


# 7. Umsetzung, Hardware und verantwortbarer Betrieb

Die Aussage „in Software bereits umgesetzt“ trifft auf die hier identifizierten und teilweise ausgeführten Komponenten zu. Ein fertiges Gesamtprodukt lässt sich daraus erst mit vollständigen Gates ableiten. Der nächste Software-Schritt ist konkret: den Rate-Limit-Fix auf seinem exakten Kandidaten prüfen und integrieren, den neuen Main neu binden, Build-Inputs einfrieren, beide Zielprofile booten, getrennte Hosts und Recovery prüfen und erst danach öffentliche Artefakte zurücklesen. [Q06, Q14]

Die vorher erstellte Reparatur liegt separat in Goldkelch/qik-vrt PR 1265, HEAD 1b50aab45e44f87058730605ed850c1f7fa10020. Sie gehört nicht zum hier vermessenen Main. Insbesondere darf kein 403 als Review-Erfolg, PASS oder EFFECT_ACK gelten. Installation-Limits erfordern sichere Rate-/Reset-Metadaten, Request-ID, erhaltene Subject-Bindung und den Verzicht auf erneute Versuche im erschöpften Fenster. Permission-403 und andere HTTP-Fehler bleiben eigenständige Blocker. [Q14]

Eine belastbare Lieferfrist braucht ein festgelegtes Zielprofil, verfügbare Runner, den Integrationsstand und Ergebnisse dieser Prüfungen. Die gemessenen 3,822 Sekunden für die Testauswahl sind keine Release-Dauer. Für Hardware folgt auf einen festgelegten Vertrag zunächst überprüfbare RTL-Simulation, dann Synthese und Platzierung, Board-/FPGA-Messung und gegebenenfalls ASIC-Entwicklung. Aus dem Softwarebefund allein folgt kein seriöser Kalendertermin. [Q15]

Ein Zusammenspiel kann wiederholte Zustandsprüfung, Hashing und Protokollübergänge auf spezialisierte Logik verlagern. Die mögliche Beschleunigung hängt vom Anteil dieser Arbeit ab. Als reine Modellrechnung gilt bei Anteil p und Beschleunigung s ohne zusätzliche Übergabekosten: S = 1 / ((1 - p) + p/s). Für p = 0,1 und s = 100 ergibt sich rund 1,11; für p = 0,9 rund 9,17. Das sind illustrative Rechenwerte, keine QIK-VRT-Benchmarks. Serialisierung, Kommunikation und neue Prüfungen können den Gewinn reduzieren. [Q16]

Ingolf Lohmann benennt den kategorischen Imperativ als ethisches Credo und beabsichtigt Patentanmeldungen für den Hardware-Anteil. Beides wird hier als Erklärung des Auftraggebers festgehalten. Ein ethisches Credo ersetzt keine Isolation, Autorisierung, Grenzprüfung oder Fehleranalyse. „Völlig ungefährlich“ ist aus diesen Befunden nicht ableitbar. Der Bericht legt keine neue konkrete Meta-Transistor-Schaltung offen und bestätigt weder Anmeldung noch Patentierbarkeit. Vor einer Offenlegung noch unveröffentlichter Erfindungsdetails ist die Neuheit mit patentfachlicher Unterstützung zu prüfen; Art. 54 EPÜ erfasst vor dem Anmeldetag öffentlich Zugängliches. [Q13, Q17]


# 8. Chronologie, Publikation und Schlussfolgerung

Der frühere Aufsatz „Abgeschlossen und anschlussfähig“ vom 15. September 2026 wird bytegleich als historische Fassung erhalten. Zwei Katalogeinträge vom 15. September, 05:39:52, und 27. September, 22:14:51 UTC enthalten dieselben 160.673 PDF-Bytes mit SHA-256 d767a3423099acf70ce6fd509bc332c93835725071d8f57cb4d8e9fd70752ba4. Der Zeitabstand beträgt zwölf Tage, 16 Stunden, 34 Minuten und rund 59 Sekunden. Das belegt zwei zeitlich getrennte Einträge derselben Datei. Die tatsächliche erste Sichtbarkeit beim Nutzer wurde damit nicht gemessen. [Q18]

Aus DevOps-Sicht lässt sich daran eine Frage nach Artefaktverfügbarkeit, Provenienz und Auslieferungsverzögerung untersuchen. Die Datierung belegt weder physikalische Zeitverschiebung noch eine Vorhersagefähigkeit. Der historische Aufsatz formuliert eine bedingte Schließungs- und Fortsetzungsargumentation. Sein eigener Stand lautet FORMAL_PENDING_KERNEL; ein Lean/Lake-Kernelbeleg wird durch die heutige Archivierung nicht nachträglich erzeugt. [Q18]

Für diese Studie ist eine Veröffentlichung als technischer Nachweisbericht angemessen, sobald die exakten Kandidaten samt Anspruchsmatrix zurückgeliefert und nach dem vorhandenen Repository-Verfahren freigegeben wurden. Ein Zenodo-DOI würde den dokumentierten Stand zitierbar machen. Ein Software-Produktrelease benötigt dagegen die vollständige Konjunktion der Gates. Beide Entscheidungen haben unterschiedliche Gegenstände. [Q07, Q18]

Die 15/30/60-Sekunden-Roadmap dient der Antwortsuche: nach etwa 15 Sekunden einen brauchbaren Ansatz bewerten, bei Tragfähigkeit bis etwa 30 Sekunden eine Ausgabe beginnen; andernfalls eine weitere begrenzte Suchphase und spätestens um 60 Sekunden eine konkrete Verfeinerung anbieten. Sie ist eine Arbeitsheuristik, kein Zeitbeweis und keine pauschale Garantie für Builds, Tests oder Veröffentlichungen. Im Mesh-Repository liegt ihre Umsetzung separat als PR 415 vor; daraus folgt keine Main-Aktivierung. [Q17]

## Befund

Die technische Substanz liegt in vorhandenen, messbar ausführbaren Softwarekomponenten und ausdrücklich gebundenen Übergängen. Der kleine Kern erklärt, warum mehrere Träger dieselbe Semantik implementieren können. Für ein anschlussfähiges Gesamtprodukt müssen jedoch auch Umgebung, persistierter Zustand, Autorität und Readback zusammenpassen. Diese Studie macht die noch offenen Nachweise überprüfbar, ohne sie durch eine allgemeine Erfolgsbehauptung zu ersetzen. [Q01-Q18]


# Quellen und Reproduktionshinweise

[1] Goldkelch/qik-vrt, Commit f2fa5a5e11dafe6d9579301c2a479e0eaa02d16c. Exakte Dateibindungen, Befehle, Umgebung und Resultate: MEASUREMENTS.json. https://github.com/Goldkelch/qik-vrt/tree/f2fa5a5e11dafe6d9579301c2a479e0eaa02d16c

[2] QIKVRT CI, Run 36346727864, Job 108697217922, Artefakt 10940821417. https://github.com/Goldkelch/qik-vrt/actions/runs/36346727864. Artefakt-SHA-256: c94cb06d16be00219a058c2bd89bac6b1c6d77df69fd4a5ccc78151ac6819d69.

[3] Docker Documentation: What is a container? Abgerufen am 27.09.2026. https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/

[4] WebAssembly: Portability. Abgerufen am 27.09.2026. https://webassembly.org/docs/portability/

[5] seL4: What the Proofs Assume. Abgerufen am 27.09.2026. https://sel4.systems/Verification/assumptions.html. Als methodische Referenz für Beweisvoraussetzungen; keine Übertragung von seL4-Verifikation auf QIK-VRT.

[6] Europäisches Patentamt: EPÜ, Artikel 54, Neuheit. Abgerufen am 27.09.2026. https://www.epo.org/en/legal/epc/2020/a54.html. Rechtliche Einzelfallbewertung und konkrete Schutzrechtsstrategie sind nicht Gegenstand dieses Berichts.

[7] Ingolf Lohmann / OpenAI Codex: Abgeschlossen und anschlussfähig. 15.09.2026, Version 0.1, historische nicht begutachtete PDF-Fassung. Byteidentität und Katalogdaten: PROVENANCE.json im begleitenden Archiv.

[8] Getrennte Arbeitsstände: https://github.com/Goldkelch/qik-vrt/pull/1265 (Requested-Review-Reparatur); https://github.com/ingolf-lohmann/qik-vrt/pull/415 (Zeit-Roadmap). Ihre Existenz ist kein Integrationsnachweis.

## Reproduktion

Auf dem gebundenen Quellstand die Befehle in MEASUREMENTS.json mit externem Evidenzverzeichnis ausführen. Alle zehn Testmodule und die konkrete C90-Übersetzung sind dort genannt. QUALITY_GATES.json enthält die ordinale Bewertungsentscheidung je Gate, deren Zählung und die Freigaberegel. Die Veröffentlichung enthält Logs und den frischen Mesh-Receipt. Um Stufe 4 zu erreichen, sind zusätzlich die in den Tabellen benannten vollständigen Zielprüfungen erforderlich.

Lizenz dieses Berichts: CC BY-NC-ND 4.0. Copyright 2026 Ingolf Lohmann. Die Lizenz macht aus dem Bericht keinen unabhängigen Peer-Review, kein Patent und keinen Produkt-Sicherheitsnachweis.

