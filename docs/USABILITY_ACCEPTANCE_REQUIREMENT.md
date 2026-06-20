# Product Owner Usability Acceptance Requirement

The Product Owner's usability acceptance test is authoritative.

A machine-generated PASS is not sufficient if the observed user workflow fails.

V45.12 specifically repairs the Windows local verification failure:

```text
Python was not found ... Exit code: 9009
```

The primary Windows verify wrapper must not invoke Python directly. It must run
PowerShell-only checks and return a controlled local verification result.

Expected local result without GitHub remote evidence:

```text
LOCAL_VERIFY = PASS
REAL_GITHUB_RELEASE = BLOCK_UNTIL_LIVE_GITHUB_EVIDENCE
```

This is not a contradiction. The repository can be locally well-formed while the
real GitHub release requirement remains blocked until live evidence exists.
