<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 | Copyright 2026 Ingolf Lohmann. -->

# QIK-VRT-Speicher: Rechteprofil, Lean-Modell und Effect Acknowledgement

Autorenprüffassung vom 30.10.2026. Ingolf Lohmann: Anforderungen, Konzept, Product Ownership und Freigabe. OpenAI Codex: Code, Formalisierung, Prüfung und Artikelentwürfe.

- [Informatik-Fachartikel](FACHARTIKEL.md) · [PDF](QIKVRT_Speichertechnologie_Fachartikel_2026-10-30.pdf)
- [Allgemein verständlicher Prosaartikel](PROSAARTIKEL.md) · [PDF](QIKVRT_Speichertechnologie_Prosaartikel_2026-10-30.pdf)
- [Claim-Matrix](CLAIM_MATRIX.json)
- [Lokaler Kernelbeleg](LOCAL_KERNEL_RECEIPT.json)
- Lean: `formalization/QIKVRT_Formalization_v2.0/QIKVRTEffectAck/StorageIntegrity.lean`
- Implementierung: `src/qikvrt_standpoint_codex.py` und `src/qikvrt_codec.py`

## Profil und Kompatibilität

Die unveränderte öffentliche 400-Byte-V1-Protokollsignatur ist keine geheime kryptografische Unterschrift. Das neue explizite Rechteprofil verwendet einen getrennten Snapshot-Präfix und den vorhandenen V1-Codec. Jedes Element darin trägt den vollständigen PolyForm-Softwarelizenztext, einen Rechtehinweis auf Ingolf Lohmann, den Dokumentlizenzverweis und eine getrennte kanonische Nutzdatenherkunft. Entfernte oder geänderte Rechtebytes werden auch nach Neuberechnung der öffentlichen Hashes abgewiesen. Alte rohe V1-Elemente werden nicht stillschweigend zu Rechteprofilen erklärt. Eine Migration sämtlicher bestehender Laufzeit- und Hardwarepfade ist offen.

`inspect_licensed` unterscheidet VERIFIED (Profilprüfung), REJECTED (erkannte Abweichung) und UNVERIFIED (kein prüfbarer Eingang). Optional kann ein vorhandener zugelassener Meldesink aufgerufen werden. SUBMITTED_UNCONFIRMED ist keine Zustellbestätigung; SIGNAL_FAILED bleibt sichtbar. `effect_ack_done` ist immer false. Für aktive Nutzdatenersetzung braucht es einen unabhängig vertrauenswürdigen Inhaltshash oder eine geprüfte kryptografische Signatur; bloße gültige Profilstruktur authentifiziert keine Nutzdaten.

## Reproduktion

```sh
python3 -B -m unittest -v tests.test_qikvrt_codec tests.test_qikvrt_standpoint_codex
cd formalization/QIKVRT_Formalization_v2.0
lake build QIKVRTEffectAck.StorageIntegrity
lake env lean QIKVRTEffectAck/StorageIntegrityAxiomAudit.lean
```

Die drei Dateien unter `negative/` müssen mit Lean jeweils fehlschlagen. Der vorhandene Ontologie-CI-Workflow prüft diese neue Speicherschicht separat, bindet HEAD/TREE, Source-/Objekt-/Audit-Hashes und veröffentlicht den Beleg vor den unveränderten historischen Goldkelch-Quellprüfungen. Ein späterer Fehler jener Prüfungen bleibt ein Workflowfehler; der getrennte Speicherbeleg erklärt ihn nicht zum Erfolg.

Beispiel mit vorhandener Datei und dauerhaft vergebener Kennung:

```sh
python3 -B -m src.qikvrt_codec seal input.bin output.qikvrt \
  --stable-id 0000000000000000000000000000000000000000000000000000000000000001 \
  --payload-attribution 'Tatsächliche Urheber laut Quelldokumentation' \
  --payload-license 'Tatsächlich geltende Lizenz oder explizit ungeklärter Status' \
  --payload-source 'urn:lokale-quellreferenz:1'
python3 -B -m src.qikvrt_codec unseal output.qikvrt restored.bin
```

Die Beispielkennung ist kein globaler Kennungsgenerator. Der Erzeuger muss die Zuordnung seiner Kennungen selbst dauerhaft verwalten. Unklare Nutzdatenrechte werden durch Verpackung nicht geheilt. Ein unbekannter Lizenzstatus erlaubt keine sonst unzulässige Nutzung. Das Profil führt keine Zahlung, Installation, Nutzdatenausführung, externe Alarmübertragung oder Produktivfreigabe aus. Eingabe und vorhandenes Ausgabeziel werden bei abgewiesener Extraktion nicht überschrieben.

## Ausprobieren

`BEISPIEL_SPEICHERELEMENT.qikvrt` enthält bewusst erzeugte Binärdaten und das vollständige Rechteprofil. Mit dem vorhandenen `unseal`-Befehl kann es lokal wiederhergestellt werden. `DEMO_MANIFEST.json` beschreibt den tatsächlich geprüften Roundtrip; ein Manifest aus demselben Paket ist kein unabhängiger Herkunftsnachweis.

## Beweisgrenze

22 Lean-Sätze, alle ohne Axiomenabhängigkeiten: exakter Vergleich endlicher Bitfolgen, Rechte-/Signaturentfernung, getrennte Beobachtungszustände, Verfügbarkeitsgrenzen, Algebra eines als korrekt vorausgesetzten inversen Codecs und Invariantenerhaltung über endlich viele korrekte Adaptationsschritte. Kein formaler Nachweis des Python-Parsers, von SHA-256, kryptografischer Personenzuordnung, automatischer Adapterexistenz, physikalischem Superdeterminismus oder konkreter Hardware/QPU/Analogintegration. Ein erfolgreicher Selbstanwendungstest ist keine allgemeine reflexive Wahrheitsgarantie.

69 lokale Codec-Testfälle einschließlich zwölf neuer Rechteprofiltests sind im lokalen Nachweis gebunden. Die bestehenden Lizenzen und Drittrechte bleiben maßgeblich. Dieser Kandidat veröffentlicht weder auf Zenodo noch auf der produktiven Domain.
