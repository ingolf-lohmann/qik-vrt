# QIK-VRT Homepage Deployment

Dieses Paket publiziert eine GitHub-Pages-faehige Homepage unter `docs/`.

## Standardziel

- Repository: `Goldkelch/qik-vrt`
- Branch: `main`
- Pfad: `docs/`
- Startseite: `docs/index.html`

## GitHub Pages

Repository Settings -> Pages -> Source: Deploy from a branch -> Branch `main` -> Folder `/docs`.

### Frische Abnahme und Authority-Zugriff

Der kanonische Produkt-URL bleibt `https://goldkelch.github.io/qik-vrt/`.
Die Konfiguration ist am Repository `Goldkelch/qik-vrt` zu lesen; Schreibrechte
auf `ingolf-lohmann/qik-vrt` belegen keinen Authority-Pages-Zugriff.
Vor einer Reparatur die tatsächliche Pages-Quelle und den letzten Build/Deploy
gegen die vorhandene `main:/docs`-Site prüfen. Ein Build-Artefakt des
Seed-Dashboard-Workflows ist keine öffentliche Pages-Veröffentlichung.

Der bestehende Personal-Firefox-Windows-Witness erzeugt für seinen exakten
Kandidaten `PUBLIC_URL_READBACK.json`, `PUBLIC_URL_HTTP.html` und
`PUBLIC_URL_BROWSER.png`. HTTP 200, identische Kandidatenbytes von
`docs/index.html` und die echte Produktseite im Browser vor Extension-Injektion
sind getrennt vom lokalen Extension-Test nachzuweisen. Ein 404 oder ein anderer
Host erfüllt diese Abnahme nicht. Die Root-Seite belegt nicht die Veröffentlichung
des gesamten Kandidaten-Trees oder einen akzeptierten Personal-Release.

Falls Authority-Pages-Lesen oder -Schreiben nicht verfügbar ist, den genauen
Capability-HOLD erhalten. Die Diagnose für PR #438 steht in
`state/work_units/QIKVRT_FIREFOX_WINDOWS_SCOPE_20261001.json` unter
`public_pages_continuation`; die tatsächliche Authority-Konfiguration bleibt
unbekannt, bis sie authentifiziert zurückgelesen wurde. Erst dann die belegte
Ursache reparieren und den kanonischen URL am selben Kandidaten frisch prüfen.

## Kognitionskonsole

- Lokaler Modus: funktioniert direkt im Browser ohne Token.
- GitHub-Models-Modus: Nutzer gibt eigenen Token mit `models:read` ein.
- Oeffentlicher No-Token-KI-Betrieb: naechste Stufe ueber GitHub App oder Server-Proxy.

## Status

Version: `QIKVRT_V2_13_4AX1`
Referenzlauf: `4AV1_20260708T174034Z_709544`
