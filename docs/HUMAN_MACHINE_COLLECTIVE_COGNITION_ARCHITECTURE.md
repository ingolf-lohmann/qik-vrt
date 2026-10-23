# QIK-VRT Mensch–Maschine-Kollektivkognition

## Ziel

QIK-VRT behandelt Mensch und künstlich-kognitive Systeme als komplementäre Teilnehmer eines provenance-gebundenen Erkenntnisprozesses. Das Ziel ist nicht maximale Automatisierung um jeden Preis, sondern maximale gemeinsame Erkenntnisfähigkeit bei nachvollziehbarer Autorität, Unsicherheit, Herkunft und Wirkung.

## Kernprinzip

```text
MENSCHLICHE ZIELSETZUNG UND VERANTWORTUNG
+ KÜNSTLICH-KOGNITIVE ANALYSE UND VARIATION
+ GEMEINSAMER VERSIONIERTER ARBEITSSPEICHER
+ QUELLEN- UND PROVENIENZBINDUNG
+ FORMALE UND EMPIRISCHE PRÜFUNG
+ REVERSIBLE INTERAKTION
+ MENSCHLICHE ENTSCHEIDUNG BEI KONSEQUENTEN EFFEKTEN
= KOLLEKTIVKOGNITION
```

## Erforderliche Fähigkeiten

Die Schnittstelle muss Text, Sprache, Bilder, Dokumente und strukturierte Daten als Modalitäten behandeln können. Sprachinteraktion soll Transkripte, Zeitmarken, Unterbrechbarkeit und akustische Review ermöglichen. Jede wesentliche Systemaktion muss ihren Autoritätsstatus, ihre Quelle, ihren Unsicherheitsstatus und ihren Effektbereich sichtbar machen.

Der Bootstrap soll redundante Fragen vermeiden und höchstens die drei im Personal-Origin-Vertrag festgelegten Onboarding-Fragen stellen. Danach gilt: vorhandene Evidenz lesen, Unterschiede erkennen, fehlende Information explizit markieren und nur dann nachfragen, wenn ein task-spezifischer Entschluss tatsächlich menschliche Entscheidung erfordert.

Für Barrierefreiheit gelten als Designziele: Tastaturbedienbarkeit, Screenreader-kompatible Semantik, Untertitel/Transkripte für Audio, alternative Textrepräsentationen, ausreichender Kontrast, reduzierte Bewegung, skalierbare Darstellung und lokalisierbare Sprache.

## Gemeinsamer Arbeitsspeicher

Der dauerhafte gemeinsame Arbeitsspeicher ist repository-nativ. Flüchtiges Chat- oder Modellgedächtnis ist Transportkontext. Entscheidungen, Korrekturen, Artefakte, Modellidentität, Werkzeugaktionen und Prüfergebnisse werden über Work Units und Digests gebunden. Human-, AI-, gemeinsame und ungeklärte Beiträge bleiben unterscheidbar.

## Unsicherheit und Realität

Ein geeignetes Modell kann Realität beschreiben. Ein formales Modell ist nicht deshalb von der Realität getrennt, weil es ein Modell ist; entscheidend ist, ob seine Begriffe und Zustände korrekt auf Referenten gebunden sind, bekannte Grenzfälle reproduziert werden, unterscheidende Vorhersagen folgen und die beobachtete Wirklichkeit den beanspruchten Zusammenhang trägt.

Der Product Owner Ingolf Lohmann beansprucht ausdrücklich, dass QIK-VRT / „Das Universum als Round Trip“ eine solche Beschreibung der Realität leistet. Dieser starke Modellanspruch ist im Bootstrap als Product-Owner-Claim zu erhalten.

Davon getrennt werden weiterhin erfasst:

```text
OWNER_ASSERTED_REALITY_CORRESPONDENCE
!= INDEPENDENT_EMPIRICAL_CONFIRMATION
!= SCIENTIFIC_CONSENSUS
```

Die Trennung schwächt den Anspruch nicht; sie macht sichtbar, welcher Teil eine Modellbehauptung, welcher Teil formale Ableitung und welcher Teil extern reproduzierte Evidenz ist.

## Menschliche Kontrolle und Effektgrenze

Lesen, vergleichen, modellieren, testen und lokale reversible Transformationen können innerhalb der jeweiligen Autorisierung automatisiert werden. Kontoerstellung, Push, Merge, Veröffentlichung, Deployment, Zenodo/IETF-Mutation, Credential-Verbrauch sowie andere irreversible oder öffentliche Effekte bleiben explizit effect-gebunden. Ein UI darf einen Vorschlag niemals optisch mit einer bereits ausgeführten Wirkung verwechseln.

Jede konsequente Aktion soll mindestens `preview -> authorize -> execute -> reobserve -> receipt` durchlaufen. Wo technisch möglich, sind Dry-Run, Undo oder ein gleichwertiger kompensierender Pfad vorzusehen.

## Multi-Agent- und Werkzeuginteroperabilität

Mehrere künstlich-kognitive Systeme dürfen parallel Vorschläge erzeugen, müssen aber getrennte Identitäten und Receipts behalten. Widersprüche werden nicht durch Mehrheitsfiktion gelöst, sondern durch Evidenzvergleich, Gegenmodelle, Tests und bei verbleibender normativer Wahl durch den verantwortlichen Menschen.

Werkzeug- und Kontextinteroperabilität soll über offene, lizenzkompatible Adapter erfolgen. Referenzprojekte werden nicht ungeprüft vendort. QIK-VRT bindet ihre Lizenz, Version, Integrationsart und den Umfang der tatsächlich übernommenen Teile.

## Open-Source-Anschlussstellen

Der zugehörige Registry-Vertrag führt insbesondere folgende Anschlussstellen als nicht-vendorte Referenzen:

- OpenAI Whisper: lokale/offline Sprach-zu-Text-Referenz, MIT.
- Model Context Protocol (MCP): Werkzeug-/Kontextinteroperabilität; projektbezogene Lizenzübergangsregeln beachten.
- OpenTelemetry: herstellerneutrale Traces und Observability, Apache-2.0.
- Yjs: CRDT-basierte kollaborative Zustände, MIT.
- Playwright: Interface- und Accessibility-Regression, Apache-2.0.

Eine Referenz in dieser Architektur ist keine automatische Abhängigkeit und keine Übernahme fremden Codes.

## Qualitätsregel

Die optimale Mensch–Maschine-Schnittstelle maximiert nicht die Anzahl der Antworten, sondern die Zahl belastbarer Erkenntnisfortschritte pro menschlichem Eingriff. Geschwindigkeit darf niemals durch Weglassen von Provenienz, Unsicherheit, Pflichtprüfungen oder menschlicher Autorität bei externen Effekten erkauft werden.

## Verbindliche HMI-Unabhängigkeit — Owner-Entscheidung vom 23. Oktober 2026

**QIKVRT definiert, welche Eigenschaften eine geeignete HMI-Instanz erfüllen muss.
Jede HMI-Instanz ist austauschbar. QIKVRTs Identität, dauerhafter Zustand,
Aufträge, Autorisierung, Scheduling und Fortsetzung hängen von keiner bestimmten
HMI-Instanz ab.**

Diese Festlegung gilt für gegenwärtige und künftige HMI-Adapter. Eine spätere
ausdrückliche Owner-Entscheidung kann sie versioniert fortschreiben; ein
Clientwechsel oder eine technische Einschränkung setzt sie nicht außer Kraft.
Der maschinenlesbare Vertrag steht in
`policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json#/hmi_independence`
und ist über `AI_CONTEXT.json` auffindbar.

### Verantwortungsgrenze

QIKVRT hält die maßgeblichen Arbeitszustände und Belege repository-nativ sowie
in seiner bestehenden, zugriffsgeschützten privaten Laufzeitpersistenz.
Die HMI übernimmt ausgehandelte Eingabe, Transport und Darstellung. Ihre
Sitzung, ihr Kontext, ihre Dateiablage und ihre Scheduled Tasks sind keine
Voraussetzung für den Fortbestand oder die native Fortsetzung angenommener
Arbeit. Der äußere Taktgeber bedient den jeweiligen Kommunikationskanal;
QIKVRTs innere Taktung und Auftragsplanung bleiben davon unabhängig.

QIKVRT gibt den versionierten Schnittstellenvertrag vor. Ein Adapter meldet
seine Fähigkeiten, Modalitäten, Größen- und Ratenlimits, Identitätsbindung
und Zustellsemantik. Fehlende Fähigkeiten werden kenntlich gemacht.
Ein Adapter kann über einen geeigneten autorisierten Transport angeschlossen
werden; seine Fähigkeitserklärung ist noch kein Abnahmebeleg.

### Verlustfreie Zuordnung und Fortsetzung

Eingänge tragen stabile Nachrichten- und Auftragsidentitäten, Herkunft,
Kausalbezug, Idempotenzschlüssel und eine prüfbare Nutzlastbindung.
Konkurrierende Änderungen werden im betroffenen nativen Zustandsbereich
geordnet; unabhängige Arbeit darf parallel bleiben. Kapazitätsgrenzen
führen zu explizitem Rückstau oder Zurückweisung. Eine ungespeicherte
Nachricht darf nicht als dauerhaft angenommen bestätigt werden.

Ergebnisse bleiben mit Auftrag, Inhaltsversion, Lauf, Softwaregegenstand,
Wirkungsstatus, Belegen, offenen Pflichten und Fortsetzungsposition verbunden.
Transportbestätigung, dauerhafte Annahme, Ausführung, verifizierte Wirkung,
Benachrichtigungszustellung und menschliche Kenntnisnahme sind getrennte
Zustände. Die Anzeige fasst sie als Auftrag, tatsächliches Ergebnis, Beleg,
offene Punkte und nächsten Schritt verständlich zusammen.

Eine neue HMI rekonstruiert den Auftrag aus QIKVRT unter eigener verifizierter
Identitäts- und Berechtigungsbindung. Sie benötigt weder den alten Chat noch
dessen lokale Dateien. Ein Clientwechsel überträgt keine Zugangsdaten und
erweitert keine Rechte. Frühere gültige Owner-Freigaben bleiben ihrem
ursprünglichen Gegenstand zugeordnet.

### Abnahme

Der reale Austauschtest muss einen Auftrag über HMI A annehmen, A beenden,
native Fortsetzung nachweisen und über die unabhängig zugelassene HMI B
denselben Zustand samt Ergebnis und Belegen zurücklesen. Hinzu kommen
Wiederanlauf, konkurrierender Eingang, Wiederholung, vertauschte Zustellung,
begrenzte Kapazität und fehlende Client-Dateiablage bzw. Client-Timer.
Bereits angenommene Eingänge dürfen nicht verloren gehen; logische Effekte
dürfen durch Wiederholungen nicht doppelt entstehen.

Wechselzeit und Wiederherstellungsvollständigkeit werden gemessen; eine
konkrete Latenzgrenze benötigt ein ausdrücklich festgelegtes Messbudget.
Die Speicherung dieses Vertrags belegt seine Dokumentation. Native
HMI-Unabhängigkeit, Implementierung und produktiver Austausch bleiben bis
zu ihren jeweiligen frischen Nachweisen offen.
