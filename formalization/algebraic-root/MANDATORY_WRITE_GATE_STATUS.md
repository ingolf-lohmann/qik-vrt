# Mandatory mathematics gate — enforcement and compatibility status

This branch adds a **candidate** workflow `.github/workflows/qikvrt-math-premerge-gate.yml`
which runs for every pull request without path filters. It checks a strictly
ISO C90 finite-state refinement checker, queries Lean's latest release, and
rechecks the mathematical foundation with the six independent Lean kernels.

**This does not yet enforce every GitHub write.** Required branch rulesets /
status checks, restrictions on direct pushes, force pushes, workflow edits,
token permissions, admin bypasses, tags, other branches, API writes and
external automation must be independently configured and verified.
Until then, direct writes can bypass the candidate workflow. A PR check is
not a pre-write gate: the PR branch is necessarily already persisted on GitHub.
A truly pre-write check requires local/staging-only computation followed by
an authenticated, non-bypassable gateway to the remote writer.

The C90 program `c90_math_verifier.c` checks **concrete finite-state
permutation certificates** (at most 256 states). It is not a replacement for
the Lean kernel, cannot verify arbitrary Lean proof terms, and cannot prove
the soundness of an arbitrary application. The independent Lean kernels
remain the proof authorities. No unsupported claim of C90/Lean feature parity.

Each run calls `check_lean_version.py` against the official latest GitHub
release, retaining the pinned Lean 4.35.0 for reproducibility. Discovery of a
new release is recorded as an upgrade obligation. Automatically generating
and approving a new Lean verifier from an untrusted release is prohibited:
a new implementation must be version-pinned, built, cross-tested with the
retained old implementation, reviewed and separately approved before use.
The older verifier must remain available for historic evidence.

Acceptance gates still outstanding:
- Require the mathematical premerge status in an effective main ruleset
  and independently read back enforcement and bypass behavior.
- Cover all write-capable actors and paths with a non-bypassable
  pre-persistence gateway, or state a narrower protected scope.
- Bind every candidate artifact and exact proof specification to a
  machine-verifiable verdict, not merely a repository-wide theorem check.
- Implement and verify any newly discovered Lean version separately,
  preserving historical compatibility.
