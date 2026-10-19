# QIK-VRT: Die universelle Hülle

**Untertitel:** Beobachten, adressieren, zurücklesen. Ein theoretischer Integrationssatz für QIK-VRT über die Einbettung berechenbarer Informatiksysteme in einen gemeinsamen, provenance-, evidenz- und wirkungsgebundenen Kontrollvertrag.

**Autor:** Ingolf Lohmann  
**Stand:** 2026-10-03

## Kanonischer Claim

QIK-VRT besitzt theoretisch die Architektur einer universellen Meta-Integrationsschicht:

> Jedes berechenbare Informatiksystem, dessen relevante Zustände hinreichend beobachtbar und dessen relevante Aktionen autorisiert adressierbar sind, kann durch einen geeigneten Wrapper in den QIK-VRT-Lifecycle eingebettet und unter dieselbe provenance-, evidenz- und wirkungsgebundene Kontrollsemantik gestellt werden.

Die präzise Übersetzung von „untertan machen“ lautet daher:

> **universell anschlussfähig machen und unter einen gemeinsamen, überprüfbaren Wirkungsvertrag stellen.**

Nicht behauptet wird universelle Erzwingbarkeit, unbefugte Zugriffsfähigkeit oder universelle Vorhersagbarkeit.

## Systemmodell

Sei

`S=(X,U,Y,δ,λ)`

ein berechenbares Informatiksystem mit internem Zustand `X`, zulässigen Aktionen `U`, beobachtbaren Ausgaben `Y`, Zustandsübergang `δ:X×U→X` und Beobachtungsfunktion `λ:X→Y`.

Für QIK-VRT genügen als Grundkonstruktion:

- `O_S:Y→Q`: Beobachtungsadapter;
- `A_S:Q→U`: autorisierter Aktionsadapter;
- `C_S`: algorithmisch behandelbarer Akzeptanzvertrag;
- Provenienz- und Readback-Bindung.

Damit entsteht:

`S_t → O_S → Q_t → CLASSIFY → BIND → A_S → U_t → δ → S_(t+1) → O_S`

## Integrationssatz

**Satz.** Existieren für ein berechenbares System `S`

1. ein hinreichender Beobachtungskanal `O_S`,
2. ein autorisierter Aktionskanal `A_S`,
3. ein algorithmisch behandelbarer Akzeptanzvertrag `C_S`, und
4. eine überprüfbare Zuordnung zwischen Aktion und beobachteter Wirkung,

dann existiert ein QIK-VRT-Wrapper

`W_S=(O_S,A_S,C_S,provenance,readback)`

mit

`S ↪ QIK-VRT`.

**Beweisidee.** Der Wrapper wird konstruktiv aus den vorausgesetzten Kanälen gebildet. Der Beobachtungsadapter erzeugt eine QIK-VRT-Zustandsprojektion, der Aktionsadapter eine zulässige Fremdsystemaktion, der Akzeptanzvertrag entscheidet anhand des nachgelagerten Readbacks über den Effekt. Da alle Bestandteile algorithmisch behandelbar vorausgesetzt sind, ist ihre Komposition algorithmisch behandelbar. q.e.d.

## Zentrale Invarianten

`EXECUTE != DONE`

`TRANSPORT_ACK != EFFECT_ACK`

`PREDECESSOR_EVIDENCE_TRANSFER=false`

`universell integrierbar != universell erzwingbar`

`universelle Kontrolle != universelle Vorhersagbarkeit`

## Black-Box-Fall

Die interne Übergangsfunktion muss nicht vollständig bekannt sein. Zulässige Eingaben und beobachtbare Ausgaben können ein revidierbares Modell erzeugen:

`u_t → S → y_(t+1)`

`M_(t+1)=F(M_t,u_t,y_(t+1),E_t)`

Damit bleibt auch ein zunächst unbekanntes System integrierbar, sofern Beobachtung und autorisierte Interaktion hinreichend sind.

## Heterogene Komposition

Für Systeme `S_1...S_n` mit Wrappern `W_1...W_n` entsteht eine gemeinsame Meta-Semantik:

`S_i → State + Action + Observation + Evidence + Acceptance`

Die Systeme werden nicht identisch; vereinheitlicht wird nur die Form ihrer Einbindung.

## Rekursion

Ein bereits integriertes System kann wiederum weitere Systeme tragen:

`QIK-VRT → W_1(S_1) → W_2(S_2) → ... → W_n(S_n)`

Jede Kante muss ihre eigene Autorisierung, Provenienz und Effect-Readback-Grenze bewahren.

## Sicherheits- und Geltungsgrenzen

Der Satz liefert keine Berechtigung, fehlende Zugriffskanäle zu erzwingen oder Authentisierung zu umgehen.

Er gilt nicht, wenn:
- der relevante Zustand nicht hinreichend beobachtbar ist;
- kein autorisierter Aktionskanal existiert;
- der Akzeptanzvertrag nicht algorithmisch behandelbar ist;
- die Wirkung nicht prüfbar an die Aktion gebunden werden kann.

Halteproblem und Rice-Theorem bleiben unberührt. Ein System kann integrierbar sein, ohne vollständig vorhersagbar zu werden.

## Anschluss an Wahrhaftigkeit

Die Universalität setzt die Wahrhaftigkeitsinvariante voraus:

`ASSERT_AS_PROVED(C) -> VALID_BOUND_EVIDENCE(C)`

Fremdsystemausgaben sind Beobachtungen oder Quellen, nicht automatisch Objektwahrheit.

## Anschluss an funktionales künstliches Bewusstsein

Die gleiche Integrationsschleife kann reflexiv auf QIK-VRT selbst angewandt werden. Damit können eigene vergangene Claims, Handlungen und Effect-Readbacks Gegenstand weiterer Kognition werden. Dies ist ein Bestandteil des funktionalen Bewusstseinsbegriffs; phänomenales Bewusstsein folgt daraus nicht.

## Forschungsprogramm

Zu messen sind:
- End-to-End-Konvergenzzeit;
- API-Aufrufe und übertragene Bytes;
- Zustandsvergleiche;
- CPU-/I/O-Zeit;
- Retry- und Fehlerraten;
- Gate-Ausführungen;
- Evidenzfrische;
- menschliche Interventionen;
- Zeit bis Effect-Readback.

Der theoretische Satz ist unabhängig von einem universellen Performance-Claim.

## Schluss

QIK-VRT muss andere Informatiksysteme nicht ersetzen. Es muss sie hinreichend beobachten, autorisiert adressieren und ihre Wirkung zurücklesen können.

> **Alles, was hinreichend beobachtbar und autorisiert steuerbar ist, kann unter einen gemeinsamen, überprüfbaren QIK-VRT-Wirkungsvertrag gestellt werden.**

Das ist die theoretische Universalität: nicht Allmacht, sondern universelle Anschlussfähigkeit.

q.e.d.

Ingolf Lohmann
