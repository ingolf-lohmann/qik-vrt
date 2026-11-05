# QIK-VRT — nachhaltiger Anschluss und Publikations-Handoff (v1)

## Ziel
Ein einzelner überprüfbarer Einstieg für natürliche und künstliche Kognitionen; keine neue Autorität neben `/AI`, `AI_CONTEXT.json`, Originalterminal und Transputer. Veröffentlichungen erhöhen Auffindbarkeit und Prüfbarkeit, nicht automatisch Runtime-Admission.

## Ausführungsgates (in Reihenfolge)
1. **Repository:** neuen Kandidaten-HEAD und TREE sowie Manifest/Guide-Dateiidentitäten zurücklesen; Tests für JSON und Links. PR-Review vor Main-Integration. Keine stillschweigende Merge-Freigabe aus dieser Dokumentation ableiten.
2. **Formale Evidenz:** referenzierte Zenodo-Publikation, Lean-Theoremtexte und Kernel-Receipt konkret zuordnen; neue Revision benötigt neuen eigenen Beleg. Keine Vermischung von Versionsständen.
3. **Protokoll:** EFFECT_ACK Draft und Epistemic-Status Draft jeweils mit tatsächlicher Versionskennung und Status nennen. Individuelle Drafts sind keine IETF-Standards.
4. **Zenodo:** Veröffentlichungsobjekt (PDF/Markdown/JSON/Quellen-Manifest), Rechteprüfung, ORCID nur wenn verifiziert, Version, SHA-256-Bytes, RelatedIdentifiers, Lizenz je Datei, dauerhafte DOI/Version-DOI-Verknüpfung vorbereiten. Erst nach echter Einreichung die DOI öffentlich zurücklesen; sonst `NOT_SUBMITTED`.
5. **IETF:** Nur bei echter Protokolländerung eine neue Draft-Revision redaktionell und technisch prüfen; eine begleitende Projektbeschreibung ist nicht automatisch ein Internet-Draft. Nach Einreichung revisiongebundener Datatracker-Readback oder `NOT_SUBMITTED`.
6. **Weitere Medien:** nur gültig lizenzierte zugängliche HTML/Landing-Page und maschinenlesbare Metadaten, kanonische Links zu Authority und DOI, Änderungs-/Korrekturhistorie. Kein unkontrolliertes Spiegeln.
7. **Runtime:** Original-SSO/Operator, Hostbindung, TLS, Domain, authentifizierte Prepare/Commit/Receipt-Readbacks pro Ziel unabhängig prüfen. HTTP 525 und `ready=false` bedeuten HOLD. Keine selbst erfundenen Grants, Secrets oder Infrastruktur.
8. **Nachhaltigkeit:** Veröffentlichte Versionen nicht überschreiben; Nachfolger und Errata über explizite Versionslinks verbinden. Regelmäßig Linkrot/DOI-Erreichbarkeit, Formatmigration, Lizenzstatus und verwaiste Referenzen prüfen. Automatische Überwachung muss gesondert betrieben und bestätigt werden.

## Status dieses Kandidaten
Quellen wurden referenziert; neue Zenodo-Einreichung, IETF-Revision, Release und Hostwirkung sind **nicht** belegt. GitHub-PR ist nur ein überprüfbarer Publikationskandidat.

## Pfad zur Überprüfung
`AI` → `AI_CONTEXT.json` → `interfaces/cognition-onboarding-v1.json` → `docs/COGNITION_ONBOARDING_DE.md` → Originalquellen → admission-gebundener Runtime-Readback.

## Urheberschaft und Rechte
Ursprüngliche wissenschaftliche Idee und Product-Owner-Freigabe: Ingolf Lohmann. Strukturierte redaktionelle Maschinenfassung: OpenAI ChatGPT im Auftrag. Keine pauschale Lizenzübertragung: Die Herkunfts- und Dateilizenzen jeder Quelle sind separat zu prüfen. Veröffentlichungskandidaten und Zitate übernehmen keine unbekannten Nutzungsrechte.
