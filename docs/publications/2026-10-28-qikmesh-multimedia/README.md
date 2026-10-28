# QIKVRT: Einmal speichern, verlustfrei wiederfinden

Veröffentlichungsentwurf vom 28.10.2026.

- Lesefassung: QIKVRT_Codec_verstaendlich.pdf, ARTICLE_DE.md und ARTICLE_DE.txt.
- Unveränderte gelieferte Ausgangsdatei: OWNER_ORIGINAL.txt.
- Sichtbare Präzisierungen: CHANGE_NOTICE.md.
- Aussagen und offene Geltungsbereiche: CLAIM_MATRIX.json.
- Produktionsstatus: MACHINE_PROOF_PREPARATION.json (PENDING; kein vorgetäuschtes gültiges Produktionsbundle).
- Evidenz: lokaler Codec-Readback, schreibgeschützt zurückgelesenes Journal, öffentliche Zenodo-Quellen samt Hashes.

Reproduktion mit Node 24, im Verzeichnis evidence:

```sh
node verify-carrier.mjs QIKVRT_Rekursive_Selbstdemonstration_20261028.qikmesh mesh-file-codec.js ./independent-verification
```

Die Ausgabe schreibt nur in independent-verification. Originalbytes und das historische Journal werden nicht geändert. Die Prüfung verwendet dieselbe Originalcodec-Implementierung und ist kein zweiter unabhängiger Decoder.

Urheberschaft: Ingolf Lohmann (Idee, Architektur, Originalaussage und Freigabe); OpenAI Codex (Ausarbeitung und Nachprüfung). Bestehende konkrete Dateilizenzen gelten weiter. Dieses Paket bestätigt keine neue Zenodo-Veröffentlichung, kein Main-Merge und keinen entfernten EAP-Abschluss.
