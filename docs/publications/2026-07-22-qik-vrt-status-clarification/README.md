<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT status clarification

Dieses textuelle Publikationsbundle präzisiert den wissenschaftlichen,
technischen und patentrechtlichen Aussageumfang der am 22. Juli 2026
veröffentlichten QIK-VRT/EFFECT_ACK-Artefakte.

```text
PASS_WITH_EXPLICIT_BOUNDARIES
```

Es handelt sich um eine erklärende Ergänzung, nicht um eine rückwirkende
Änderung des Working Papers, des Software-Snapshots oder des Internet-Drafts.

## Inhalt

| Datei | Rolle |
|---|---|
| `STATUSERKLAERUNG_DE.md` | vollständige deutschsprachige Status- und Anspruchsklärung |
| `WHATSAPP_RELEASE_KOMMENTAR_DE.md` | kurze, direkt versendbare Veröffentlichungsfassung |
| `RELEASE_NOTES_WHATSAPP_DE.md` | persönliche, offenbarende und zugleich evidenzgebundene WhatsApp-Release-Notes |
| `EVIDENCE_BOUNDARY.md` | Beleg-, Bedingungs- und Nichtbeleggrenzen |
| `EVIDENCE_INDEX.json` | maschinenlesbare SHA-256-Bindung der maßgeblichen Primärevidenz |
| `BUILD_PROVENANCE.json` | PDF-Build-, Hash- und visuelle QA-Provenienz |
| `PATENT_DISCLOSURE_BOUNDARY.md` | Grenze zwischen technischer Veröffentlichung und Patentstatus |
| `LICENSE_NOTICE.md` | Copyright- und Lizenzhinweise |
| `CITATION.cff` | maschinenlesbare Zitationsmetadaten |
| `QIK-VRT_EFFECT_ACK_Statusklaerung_2026-07-22.pdf` | gerenderte, visuell geprüfte A4-Fassung der Statuserklärung |
| `ZENODO_FILESET.md` | exakter, audiofreier Uploadumfang des eigenständigen Reports |
| `ZENODO_PUBLIC_INVENTORY.md` | geprüfte Inventur der 14 vorhandenen Versionsrecords in fünf Concept-Linien |
| `README.md` | Übersicht und Primärquellen |

## Kernaussage

QIK-VRT/EFFECT_ACK belegt in einem benannten endlichen Modell eine
reproduzierbare Kontrollstruktur. Semantische Rekonstruktion ist genau dann
wohldefiniert, wenn die Zielsemantik auf den Beobachtungsfasern konstant ist;
exakte historische Inversion benötigt Injektivität. Cyberphysische Geltung
bleibt von vollständiger Mediation, frischer authentisierter Prüfung, treuer
Ausführung und empirischer Systemvalidierung abhängig.

Das Ergebnis ist keine universelle Totalisierungs-, Sicherheits- oder
Patentgarantie. Die vollständige Draft-01-Wire-Implementierung bleibt
`CONTINUE_DRAFT01_WIRE_IMPLEMENTATION`.

## Offizielle Primärquellen

- [Working-Paper-DOI 10.5281/zenodo.21498773](https://doi.org/10.5281/zenodo.21498773)
- [Software-DOI 10.5281/zenodo.21498774](https://doi.org/10.5281/zenodo.21498774)
- [IETF Datatracker: `draft-lohmann-qikvrt-effect-ack-01`](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/01/)
- [IETF-Archiv: Revision `-01`](https://www.ietf.org/archive/id/draft-lohmann-qikvrt-effect-ack-01.html)
- [Goldkelch-Veröffentlichungstag](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0)
- [Ingolf-Lohmann-Veröffentlichungstag](https://github.com/ingolf-lohmann/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0)
- [WIPO: Patents](https://www.wipo.int/en/web/patents)
- [Europäisches Patentübereinkommen, Artikel 54](https://www.epo.org/en/legal/epc/2020/a54.html)
- [Creative Commons BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode.en)

## Abgrenzung dieses Bundles

Das Bundle ist absichtlich dokumentarisch; die in `LICENSE_NOTICE.md`
ausgewiesenen datei- und komponentenbezogenen Lizenzhinweise gelten. Es enthält
keine Audioaufnahmen oder Transkripte, keine Kopie des Internet-Drafts, keine
ausführbare Software und keine neuen enabling Hardwaredetails. Aussagen werden
aus den verlinkten öffentlichen Primärartefakten abgeleitet; nichtöffentliche
Kommunikation ist kein Evidenzanker.

Die PDF-Fassung wurde aus `STATUSERKLAERUNG_DE.md` mit Pandoc und XeLaTeX in
A4 gesetzt, mit Poppler in vier Seitenbilder gerendert und visuell geprüft.
`EVIDENCE_INDEX.json` bindet die ausgewertete Primärevidenz per SHA-256; das
Veröffentlichungsmanifest bindet zusätzlich alle vorgesehenen Uploaddateien
mit Größe, MD5 und SHA-256.

## Zitieren

Die empfohlene Zitation steht in [`CITATION.cff`](CITATION.cff). Das
Veröffentlichungsverfahren reserviert den eigenständigen DOI in einem
getrennt autorisierten Schritt und bettet exakt diesen Wert vor der
Finalisierung in die Zitationsdatei ein. Die DOIs der Primärquellen dürfen
nicht als DOI dieses Ergänzungsbundles ausgegeben werden.

## Lizenz

Copyright 2026 Ingolf Lohmann. Dieses Bundle steht unter CC BY-NC-ND 4.0;
Einzelheiten und Patentvorbehalt stehen in
[`LICENSE_NOTICE.md`](LICENSE_NOTICE.md) und
[`PATENT_DISCLOSURE_BOUNDARY.md`](PATENT_DISCLOSURE_BOUNDARY.md).
