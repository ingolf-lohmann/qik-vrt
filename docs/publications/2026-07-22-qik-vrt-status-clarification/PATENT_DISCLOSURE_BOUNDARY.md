<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Patent disclosure boundary

## Zweck und Nichtberatungs-Hinweis

Dieses Dokument grenzt die technische Veröffentlichung von möglichen
patentrechtlichen Aussagen ab. Es ist keine Rechts- oder Patentanwaltsberatung,
keine Patentanmeldung, kein Claim Chart und kein Rechtsgutachten. Maßgeblich
sind die betroffenen Rechtsordnungen, die konkreten Ansprüche, die vollständige
Chronologie und die Prüfung durch dafür qualifizierte Berater und Behörden.

Die [WIPO](https://www.wipo.int/en/web/patents) beschreibt ein Patent als ein
für eine Erfindung erteiltes Ausschließlichkeitsrecht und verweist für Schutz
auf Anmeldungen bei nationalen oder regionalen Ämtern. Eine technische
Veröffentlichung, ein DOI, ein Git-Tag oder ein Internet-Draft ist daher nicht
selbst die Erteilung eines solchen Rechts.

Für eine europäische Neuheitsprüfung erfasst [Artikel 54
EPÜ](https://www.epo.org/en/legal/epc/2020/a54.html) grundsätzlich den vor dem
Anmelde- oder Prioritätstag öffentlich zugänglich gemachten Stand der Technik.
Welche Wirkung eine konkrete Offenlegung in welcher Rechtsordnung hat, kann
dieses Dokument nicht entscheiden. Insbesondere wird keine Schonfrist,
Prioritätswirkung oder Unschädlichkeit einer Veröffentlichung zugesagt.

Für europäische computerimplementierte Erfindungen behandelt das
[Europäische Patentamt Programme für Datenverarbeitungsanlagen](https://www.epo.org/en/legal/guidelines-epc/2026/g_ii_3_6.html)
nicht schon wegen ihrer Ausführung auf einem Computer als patentfähig; die
Prüfung verlangt einen weiteren technischen Effekt beziehungsweise technischen
Beitrag im konkreten Anspruch. Auch dessen Vorliegen würde Neuheit und
erfinderische Tätigkeit nicht vorwegnehmen.

## Öffentlich dokumentiert

Am 22. Juli 2026 waren jedenfalls folgende technische Primärartefakte
öffentlich adressierbar:

- das [QIK-VRT/EFFECT_ACK Working
  Paper](https://doi.org/10.5281/zenodo.21498773);
- der [versionierte Software-Snapshot](https://doi.org/10.5281/zenodo.21498774);
- der [Internet-Draft
  `draft-lohmann-qikvrt-effect-ack-01`](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/01/);
- die veröffentlichten Quellstände in den verlinkten GitHub-Repositories.

Diese Liste belegt nur die benannten öffentlichen Fundstellen. Sie ist keine
vollständige Prior-Art-Suche und trifft keine Aussage darüber, ob gleiche oder
ähnliche Inhalte früher, anderswo oder durch Dritte offengelegt wurden.

## Keine positive Patentstatus-Aussage

Aus den veröffentlichten Artefakten und dieser Statusklärung folgt keine
Garantie oder Feststellung zu:

- Anmeldung, Anhängigkeit, Erteilung oder territorialer Reichweite eines
  Patents;
- Anmelde-, Prioritäts-, Veröffentlichungs- oder Erfindungsdatum im
  patentrechtlichen Sinn;
- Erfindereigenschaft, Berechtigung, Inhaberschaft oder wirksamer Übertragung;
- Neuheit, erfinderischer Tätigkeit, gewerblicher Anwendbarkeit oder
  Patentfähigkeit;
- ausreichender Offenbarung oder Ausführbarkeit im patentrechtlichen Sinn;
- Rechtsbeständigkeit, Anspruchsauslegung oder Durchsetzbarkeit;
- Freedom to Operate oder Nichtverletzung fremder Patent-, Urheber-, Marken-,
  Geschäftsgeheimnis- oder sonstiger Rechte.

Auch ein positives Ergebnis einer Repository-Prüfung, ein DOI-Status oder
`EFFECT_ACK_DONE` wäre kein Ersatz für diese eigenständigen rechtlichen
Prüfungen.

## Technische Offenlegungsgrenze dieses Bundles

Dieses Statusbundle fasst bereits öffentlich dokumentierte mathematische und
prozessuale Grenzen zusammen. Es fügt bewusst keine neuen enabling
Hardwaredetails hinzu. Nicht beschrieben werden insbesondere:

- Schaltpläne, Masken-, ASIC-, FPGA- oder Leiterplattenentwürfe;
- konkrete Sensor-, Aktor-, Verriegelungs- oder Redundanzarchitekturen;
- Schlüsselablage, Hardware-Root-of-Trust oder sichere Provisionierung;
- produktspezifische Zeit-, Leistungs-, Toleranz- oder Ausfallparameter;
- Fertigungs-, Kalibrierungs-, Zertifizierungs- oder Gefährdungsverfahren;
- eine konkrete Implementierung, die aus abstrakten Bedingungen ein
  betriebsfähiges cyberphysisches Produkt macht.

Die Begriffe „treuer Executor“, „vollständige Mediation“ und „empirisch
validiertes Systemmodell“ sind notwendige Bedingungsgrenzen. Sie sind keine
Behauptung, dass eine bestimmte Hardware diese Bedingungen erfüllt, und keine
Anleitung, wie sie vollständig zu realisieren wäre.

## Keine Totalisierungsbrücke zum Patent

Das mathematische Faser-Kriterium und die endliche Modellprüfung begründen
weder eine universelle technische Lösung noch einen automatischen
Patentanspruch. Insbesondere darf die wissenschaftliche Kennzeichnung
`PASS_WITH_EXPLICIT_BOUNDARIES` nicht in eine positive Garantie für
Patentfähigkeit, Schutzumfang oder Verwertbarkeit umgedeutet werden.

## Copyright-Lizenz ist keine Patentlizenz

Die Texte dieses Bundles stehen unter CC BY-NC-ND 4.0. Nach Abschnitt 2(b)(2)
des [offiziellen Creative-Commons-Lizenztexts](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.en)
werden Patent- und Markenrechte durch diese Lizenz nicht lizenziert. Die
Copyright-Erlaubnisse dürfen deshalb nicht als Patentlizenz, Zusicherung der
Nichtverletzung oder Verzicht auf sonstige Rechte gelesen werden.

## Erforderliche getrennte Prüfung

Wer eine Anmeldung, Lizenzierung, Verwertung oder ein Produkt erwägt, muss vor
einer Wirkung mindestens getrennt prüfen lassen:

1. vollständige Offenlegungs- und Prioritätschronologie;
2. Erfinder-, Inhaber- und Übertragungskette;
3. Anspruchsfassung und jurisdictionsspezifische Patentfähigkeit;
4. einschlägigen Stand der Technik und Freedom to Operate;
5. Software-, Standardisierungs-, Lizenz- und Drittanbieterrechte;
6. Safety-, Security-, Export-, Produkt- und Zulassungsanforderungen.

Bis dahin bleibt jede positive Patent- oder Verwertungsaussage ausdrücklich
offen.

Ein internationales Verfahren nach dem PCT ist kein „Weltpatent“; die
Erteilung bleibt Sache der zuständigen nationalen oder regionalen Ämter. Auch
ein erteiltes europäisches Patent ist nicht „unangreifbar“, sondern kann unter
den Voraussetzungen der [Artikel 99](https://www.epo.org/en/legal/epc/2020/a99.html)
und [100 EPÜ](https://www.epo.org/en/legal/epc/2020/a100.html) Gegenstand eines
Einspruchs sein.
