# Local verification summary

**Snapshot date:** 2026-07-20

**Public baseline inspected:** `8ae1884116221087bdcc75eed9905bb80bdd9e95`

**Verified object:** the repair-set content tree carried by the repository
commit that publishes this summary

## Result

```text
LOCAL_TEST_RESULT = PASS
TEST_MODULES_DISCOVERED = 9
TESTS_RUN = 102
TESTS_PASSED = 102
TESTS_FAILED = 0
TESTS_SKIPPED = 0
PYTHON_SYNTAX = PASS
SHELL_SYNTAX = PASS
WORKFLOW_YAML_PARSE = PASS
OPENAPI_YAML_PARSE = PASS
JSON_PARSE = PASS (historical UTF-8 BOM accepted)
LICENSE_TRANSITION = PASS
GIT_DIFF_CHECK = PASS
CANONICAL_INTEGRITY = PASS
MAKE_TEST = PASS
MASTER_GATE = PASS
```

The reproducible test command was:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 \
  python3 -B -m unittest discover -s tests -p 'test_*.py' -v
```

The 102 tests cover:

| Module | Tests |
|---|---:|
| API client | 4 |
| five-state effect protocol and conformance | 41 |
| handler security | 17 |
| handler unit behavior | 6 |
| repository-integrity generator | 1 |
| launcher and publication planner | 15 |
| license transition and exact official text | 5 |
| seed/import workflows | 12 |
| TCP/IP end-to-end adapter | 1 |

The tests establish local behavior for the bounded reference implementation,
including all five normative `EFFECT_ACK` states and DONE-only ordinary
release. The repaired runtime also bounds subprocess output and time, binds
restored workflow state to an authenticated successful run of the same
repository/workflow/commit, uses unique per-run logs, and journals publication
effects durably. Planned release assets are additionally bound to tracked
`HEAD` bytes and require post-effect agreement with GitHub's reported SHA-256
and size. The subprocess bound covers descendant process groups; integrity
locking is crash-recoverable; authorization inputs and records are bounded and
symlink-safe; and arbitrary captured bytes remain valid JSONL. These properties
are covered by local tests or static workflow
inspection. The local results do not themselves establish remote publication, a live GitHub Actions run,
Zenodo ingestion, external adoption, production certification, or the truth of
scientific, legal, medical, psychological, historical, religious, or personal
claims stored in repository documents.

The current reference publisher performs no direct Zenodo effect and rejects
an attempt to enable that unsupported path. Commit, push, release, remote
workflow and archival effects are outside this local test result and require
their own remote-head, tag, run, release or DOI evidence.

All 1,179 non-runtime JSON files parse as JSON. Some retained historical
Windows-era artifacts begin with a UTF-8 BOM; the archive-wide check therefore
uses `utf-8-sig`. Current active JSON contracts are emitted without a BOM.

See `STATUS.md` and `HISTORICAL_ARTIFACT_BOUNDARIES.md` for the exact claim and
archive boundaries.
