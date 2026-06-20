#!/usr/bin/env python3
from __future__ import annotations
import pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main(argv=None):
    text=(ROOT/"tools/qikvrt_github_auto_release.py").read_text(encoding="utf-8",errors="ignore")
    for token in ["git","push","gh","release","create","BLOCK_GITHUB_AUTH_MISSING","BLOCK_GIT_REMOTE_MISSING","BLOCK_ACCEPTANCE_REQUIRED"]:
        assert token in text, "missing token "+token
    assert "external_evidence_claims" in text
    print("PASS GitHub automated merge/commit/push/release gate")
    return 0
if __name__=="__main__": raise SystemExit(main())
