<!-- Copyright 2026 Ingolf Lohmann. SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->

# Ein Punkt. Zwei Welten. — React integration

Idee und Dramaturgie: **Ingolf Lohmann**. Gestaltung und Animation:
KI-unterstützt. Integration und technische Aufbereitung: OpenAI Codex.
Die Erzählung ist als visuelle Metapher eingeordnet.

## Active web build

The existing Raumzeitterminal Site imports `VectorNarrativeSection` in
`app/dossier/page.tsx`, before the technical evidence sections. Its homepage
links to the same section. The component and CSS in this directory are
byte-identical copies of that build's `components/` sources.

- Dossier: https://qikvrt-scheibenhard.ingolf-lohmann.chatgpt.site/dossier#vektorerzaehlung
- Original application: https://pacman-kausale-reise.ingolf-lohmann.chatgpt.site/
- Host project: `appgprj_6ac4018a3e0c8191a06187c296d6c7ea`
- Source commit: `25df5228558c0ff26e54dc351fafc3c9b9a8d422`
- Source tree: `359d0ebf141803431ca67d917cb2047b81032e3f`
- Saved version: **48**
- Deployment: `appgdep_6add28faddec81918e075acd4aecbd4e`, provider result `succeeded`.
- Deployment archive SHA-256:
  `443d415ae34c6ae7aaa9f044a4d68a02f5e05cfa99e9ac9c387a3d4d8591dc76`.

This records the deployed Site, separately from this Authority source candidate.
The candidate does not assert Main integration, an independent public HTTP
readback of the Site, native Mesh execution, exact-domain acceptance or
`EFFECT_ACK_DONE`. The latest bound observation of `https://raumzeitterminal.de/`
is HTTP 525 at `2026-10-24T21:52:39.360Z`.

## Reuse and offline files

Import `VectorNarrativeSection.tsx` with its adjacent CSS module in a React
application that supports CSS modules. Render `<VectorNarrativeSection />`.
An optional `id` allows multiple sections without duplicate heading IDs.
There is no client state, effect, iframe, script injection, network fetch or
autoplay in this component. Styles have explicit fallback colors and wrap at
small viewport widths; links have visible keyboard focus and 44-pixel targets.

Serve the four original files under
`/vector-narratives/ein-punkt-zwei-welten/` in the consuming application.
`ASSETS.json` binds the original application's saved version 2, source commit,
file sizes and SHA-256 digests. The active Site contains these exact bytes.
MP4 and ZIP use same-origin download links. This avoids relying on a
cross-origin `download` attribute. The original application opens in a new
tab with `noopener noreferrer`.

After downloading, extract the ZIP and open `Ein_Punkt_Zwei_Welten.html`.
The archive also includes `Ein_Punkt_Zwei_Welten.svg`, `LESEN.md` and
`Pruefprotokoll.json`. Saving these files for local use is distinct from
offline caching of the surrounding technical dossier.

## Verification scope

- TypeScript: `tsc --noEmit`, exit 0.
- Production build: the existing Sites build helper, exit 0.
- Existing offline suite: `node scripts/verify-offline.mjs`, exit 0;
  it covers the pre-existing shell and 18 HMI cases.
- Built React output contains the section; all four packaged files match
  their source-version hashes; ZIP CRC and MP4 container signature verified.
- The source application checkout matches its saved version 2 commit.
- No browser visual QA or independent public HTTP asset verification is
  claimed for this integration. The execution environment's HTTP requests
  to the original Site were denied with 403; this does not establish a
  missing public file.

The Authority integrity trio is constructed incrementally from the byte-verified
unchanged Main manifest and these four new files using the current generator's
classification and content-tree digest functions. Full repository regeneration
and tests require fresh exact-head CI; no prior test count is transferred.
