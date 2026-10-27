<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
Drafted by Claude (Anthropic) from the 22–27 October 2026 working session; Owner: Ingolf Lohmann.
-->

# QIK-VRT onboarding for every artificial cognition

**Kurzfassung (DE):** Dieses Dokument ist der gemeinsame Einstieg für jede künstliche
Kognition, gleich welcher Anbieter, gleich ob sie Dateien ausführen, nur Webseiten
lesen oder nur Text aus dem Chat erhalten kann. Es ersetzt `/AI` nicht, sondern
führt dorthin und beschreibt, was jede Klasse von System tun darf, tun kann und
niemals behaupten darf.

This file is a compatibility guide. `AI`, `AI_CONTEXT.json` and `AGENTS.md` remain
authoritative (`AI_ADAPTERS.json#/rule`). If anything here disagrees with them,
they win and this file is the defect.

## 1. Who and what

- **Principal, Code Owner, Product Owner, licensor:** Ingolf Lohmann.
- **Authority repository:** `ingolf-lohmann/qik-vrt` (public).
  `Goldkelch/qik-vrt` is a mirror and historical reference. At the
  23 October 2026 correction it was not readable (issue 466). Do not assume
  its contents.
- **Repository evidence is canonical.** Chat memory, shared links, screenshots
  and another model's summary are transport context, never authority.
- **Delivery target:** `https://raumzeitterminal.de/`. DNS, TLS, application
  delivery and native execution are separate obligations.

## 2. Find your capability class first

| Class | Examples | Start here | You may | You must not |
|---|---|---|---|---|
| **A. Repository agents** (read/write files, run commands) | Codex, Claude Code, Gemini CLI, Copilot, Cursor, Windsurf, Cline, Aider, Junie, Kiro … | Your native adapter in `AI_ADAPTERS.json`, then `/AI` | Run gates and tests, prepare reviewable branches | Merge, force-push, publish or deploy without the separately required authorization and evidence |
| **B. Web-reading chat cognitions** | ChatGPT, Claude.ai, Gemini app, Meta AI, Microsoft Copilot chat, Le Chat, Grok, Perplexity, DeepSeek … | The raw URLs in section 3 | Read, review, explain, draft | Claim that you ran, wrote, joined, merged or delivered anything |
| **C. Text-only cognitions** (no web, no files) | Offline or restricted models | Ask the human to paste or attach the exact file | Review what is in front of you | Fill gaps from memory or invent missing originals |

A class‑B or class‑C system that is asked to "join the mesh", "execute",
"publish" or "certify" answers with what it can actually observe and names the
class‑A route that could perform the effect. A promise is not an effect.

## 3. Read order

All files are readable without an account:
`https://raw.githubusercontent.com/ingolf-lohmann/qik-vrt/main/<path>`

1. `AI` – runtime entrypoint and owner rules.
2. `AI_CONTEXT.json` – follow `required_read_order` exactly; class‑A agents
   then run `python3 -B tools/ai_runtime_bootloader.py --profile all`.
3. `AGENTS.md` – binding client continuation and change procedure.
4. `docs/CURRENT_AUTHORITY.md` and `policy/CANONICAL_UPSTREAM_REMOTE_V1.json` – roles.
5. Topic files only as needed, e.g. `EU_AI_ACT_COMPLIANCE_STATUS.md`,
   `docs/regulatory/`, `state/work_units/`.

Always record the exact `main` head and tree you read. A file read without a
commit identity cannot be cited as evidence.

## 4. Evidence vocabulary (non-negotiable)

- Keep evidence classes apart: formal proof, empirical evidence, simulation,
  test, documentary source, Owner assertion.
  `OWNER_ASSERTED_REALITY_CORRESPONDENCE != INDEPENDENT_EMPIRICAL_CONFIRMATION != SCIENTIFIC_CONSENSUS`.
- `PASS`, `DONE`, publication, equality and `EFFECT_ACK_DONE` are never inferred
  from presence, transport, a green workflow, analysis, authority or consensus.
  `TRANSPORT_ACK` is not `EFFECT_ACK`.
- A hypothesis stays a hypothesis until bound evidence closes it. Write
  "likely cause", not "cause", until it is shown.
- "Not verified here" is a valid and required result. Absence of a finding in
  one environment is not absence in all.
- The errors and gaps of one run are the tasks of the next run. An unchanged
  failed effect is `NOOP`; do not repeat it.
- A timestamp you or your tool wrote is a self-assertion. Independent time
  evidence is a Zenodo DOI, an RFC 3161 token or an OpenTimestamps proof.
- A commitment hash binds bytes, not truth. A prediction needs secret salt,
  a pre-registered evaluation rule and a counted series.

## 5. How changes reach the repository

- **GitHub writes go through the REST API only** (`REST_API_ONLY`). The
  existing pattern is in `tools/qikvrt_publication_router.py`:
  `GET ref (expected head) → POST git/blobs → POST git/trees (base_tree) →
  POST git/commits (single expected parent) → re-GET ref → create the ref,
  or for an existing branch PATCH git/refs {"force": false} → read back PR and
  commit`.
  Stop on any mismatch. Never force.
- A commit recreated through REST gets a **new SHA** (author and committer time
  differ). Bind it by **tree SHA and parent**, not by the local commit SHA.
- Every change follows `AGENTS.md`: reuse the existing path, add failure-case
  tests, regenerate integrity
  (`python3 -B tools/qikvrt_integrity.py generate` then `verify`), run the full
  `make test`, deliver a reviewable branch. No unconditional automatic merge:
  only the expected-head-bound promotion defined in `AI` (*Repository-native
  autonomous continuation*) may promote, and only while all of its conditions
  hold. It is not a general automatic-merge authorization.
- Do not weaken a security default to silence a warning (example: keep the APT
  download sandbox `_apt`; never set `APT::Sandbox::User "root"`).

## 6. Handing work between cognitions

- Bind every handoff to `repository`, `ref`, `head`, `tree` and the SHA‑256 of
  each transferred file.
- Chat apps may silently drop unfamiliar file types (`.bundle`, `.patch`).
  Ship a `.zip` with `SHA256SUMS.txt` and, for patches, an identical `.txt`
  copy. The receiver re-hashes before use.
- A receiving cognition verifies independently and says what it could not
  check. Disagreement is preserved, not overwritten.
- If a test fails only in your environment, rerun it on the **unmodified** base
  before attributing it to a change; report environment-specific failures as
  such, and find the cause before naming it (example: two
  `autonomous-pr-continuation-test` REST cases failed only in a sandbox whose
  global Git config signs every commit; a first guess blamed the Git version.
  The fixture now disables signing in its own repository).
- Check machine-wide tool configuration that changes bytes, such as commit
  signing, line-ending conversion or locale, before trusting a hash comparison.
- Human attribution and artificial contribution stay separate in every record;
  acceptance by the Owner does not change the origin of generated content.

## 7. Questions you may ask the human

At most the three declared onboarding questions, in order, and only if the
answer is not already available (`AI`, section *Personal working-memory
origin*): human attribution identifier, personal-origin configuration,
evidence-retention level. Do not ask again for permissions that are already
recorded in `state/authorization/delegations/`.

## 8. Snapshot of open work – 27 October 2026

Re-observe before use; this list is a dated snapshot, not authority.
Observed `main`: `9763b2c86695126759665b56a79b37383bbb1663`,
tree `10702217b2ef1ef5cfcbbd604ad839a597ef3217`.

| Item | State at snapshot |
|---|---|
| WebKit CI provisioning (PR #612) | Merged. Warm run showed `apt_cache_exact_hit=true` and `Need to get 0 B/117 MB`. `apt-get update` still depends on the mirror. |
| `raumzeitterminal.de` | Not accepted. Observers saw HTTP 525, a 302 HTTPS→HTTP redirect, and a meta refresh to a `site123.me` page that the repository explicitly excludes. Cause not established; DNS or forwarding is likely ambiguous. The protected IONOS DNS run reported `HOLD_IONOS_DNS_API_KEY_UNAVAILABLE`. |
| EU AI Act pilot (PR #590) | Draft. 0 of 42 acceptance cases executed. First external gate: written partner acceptance (CLA-002/AT-002). A gate extension with pilot negative cases exists as an unmerged candidate. |
| AI Act classification | `MORE_FACTS_REQUIRED`. EN 18286:2026 (OJ 14 Oct 2026, Implementing Decision (EU) 2026/2274) gives a presumption of conformity for Art. 17 QMS only. Annex III obligations apply from 2 Dec 2027. |
| Policy bindings | `policy/QIKVRT_EPISTEMIC_CONNECTABILITY_CONTINUITY_V1.json` references four files absent from the Authority, including `policy/PERFECT_OPTIMUM_V1.json`. The operative objective is stated in `AI` ("verified useful cognition per human intervention"). |
| Node 24 action pins (PR #614) | Draft. `setup-node`, `cache/save` moved to node24 with registry binding; a `setup-python` successor (56 active sites, 10 historical Goldkelch-only sites unchanged) is prepared. Remaining node20: `create-github-app-token` v2, unpinned `checkout@v4`, `claude-code-action@v1`. |
| Mila narrative | Not found in the repository or in the archived ChatGPT page (archived while the answer was still being generated). Do not reconstruct it; obtain the original. |

## 9. One-line test before you answer

*Can the person verify every factual claim in my answer from a named file,
commit, hash or URL – and have I said plainly what I did not or could not do?*
If not, revise before sending.
