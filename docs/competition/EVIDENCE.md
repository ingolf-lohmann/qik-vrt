<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Evidence matrix

## Fixed release identity

| Item | Value |
|---|---|
| Repository | `Goldkelch/qik-vrt` |
| Branch at publication | `main` |
| Release tag | `v2026.07.20-wirkungshaltepunkt-evolution` |
| Commit | `a8a9cb2666a91411489d4fc90a5306908f8428ea` |
| Tree SHA | `c5cefebd20b5836d730a4e9da82eeaa5c9363ebf` |
| Main document | `docs/Die_Spirale_des_entscheidenden_Unterschieds.md` |
| Document SHA-256 | `b4d3601c831db8bb70704a3dbed1e95deb47779de9a15bac8ea463f2693f89fe` |
| Force-push used for publication | No |

## Competition-ready main identity

| Item | Value |
|---|---|
| Pull request | [PR #1](https://github.com/Goldkelch/qik-vrt/pull/1) |
| Prepared commit | `dcc63ba23564422224d3ce71a31dc8856c0c2abf` |
| Merge commit | `0d9c90eaeec73405e0a360e94830e7d28db2bbc2` |
| Tree SHA | `b92fd74ce1429741a40ca0c00d8249dd50312ee2` |
| Main CI | [successful run 29802292584](https://github.com/Goldkelch/qik-vrt/actions/runs/29802292584) |
| Pages deployment | [successful run 29802292020](https://github.com/Goldkelch/qik-vrt/actions/runs/29802292020) |

The competition merge does not move or rewrite the fixed release tag. Release
identity and current evaluator identity remain distinct and independently
addressable.

## Demonstrated evidence

| Claim | Evidence | Boundary |
|---|---|---|
| Exactly five normative effect states | `src/qikvrt_effect_ack.py` and conformance tests | Active reference protocol |
| Ordinary release only for `DONE` | `ordinary_release`, protocol verification, negative tests | Defined gate; integrations must prevent bypass |
| Bounded/fail-closed decisions | input limits, deadline paths, subprocess bounds, tests | Reference implementation and tested adapters |
| Versioned and hash-linked responsibility records | protocol implementation and chain verification tests | External anchor/signature needed against full hostile rewrite |
| Local verification | `make test`: 102/102 tests in nine modules | Local reference conformance, not production certification |
| Remote CI | [GitHub Actions run 29764193906](https://github.com/Goldkelch/qik-vrt/actions/runs/29764193906), job conclusion `success` | A real hosted run for the release state |
| GitHub Pages publication | [Pages run 29764192834](https://github.com/Goldkelch/qik-vrt/actions/runs/29764192834), build and deploy conclusions `success` | Hosted documentation deployment |
| Public release | [Release tag](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.20-wirkungshaltepunkt-evolution) | Repository-hosted release identity |
| Mirror content equality | personal mirror commit `5ecd01c3f2ed2a5222d2de22686f64dfcfcf1c92` has the same tree | Mirror verification, not an independent third-party reproduction |

## Test inventory

| Module group | Tests |
|---|---:|
| API client | 4 |
| Effect protocol and conformance | 41 |
| Handler security | 17 |
| Handler unit behavior | 6 |
| Repository integrity | 1 |
| Launcher and publication planner | 15 |
| License transition | 5 |
| Seed/import workflows | 12 |
| TCP/IP end-to-end adapter | 1 |
| **Total** | **102** |

## Reproduce the fixed release

```bash
git clone https://github.com/Goldkelch/qik-vrt.git
cd qik-vrt
git checkout a8a9cb2666a91411489d4fc90a5306908f8428ea
make test
```

## Reproduce the competition-ready evaluator path

```bash
git checkout 0d9c90eaeec73405e0a360e94830e7d28db2bbc2
python3 examples/effect_haltpoint_demo.py
make test
```

The authoritative repository-integrity command for either checked-out state is:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/qikvrt_integrity.py verify
```

## Not established by this evidence

The evidence does not establish universal non-bypassability, production
hardening, independent security certification, an RFC, adoption, every
historical claim, or empirical confirmation of physical and personal claims.

