#!/usr/bin/env python3
from tests.helpers import repo_path
def test_github_auto_release_tool_materialized():
    text=repo_path("tools/qikvrt_github_auto_release.py").read_text(encoding="utf-8")
    assert "git" in text and "push" in text and "gh" in text and "release" in text
def test_github_auto_release_blocks_without_acceptance_remote_or_auth():
    text=repo_path("tools/qikvrt_github_auto_release.py").read_text(encoding="utf-8")
    assert "BLOCK_ACCEPTANCE_REQUIRED" in text
    assert "BLOCK_GIT_REMOTE_MISSING" in text
    assert "BLOCK_GITHUB_AUTH_MISSING" in text
def test_no_false_release_claim_boundary():
    text=repo_path("tools/qikvrt_github_auto_release.py").read_text(encoding="utf-8")
    assert "external_evidence_claims" in text
    assert "PASS_RELEASE_CREATED" in text
