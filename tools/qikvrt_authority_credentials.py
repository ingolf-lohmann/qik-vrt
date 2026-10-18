# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Existing #446 credential resolver, extracted without priority changes.

Source: 3e8530f2beb158cdfebd3fa74d25498e7ac2aa4a,
tools/qikvrt_authority_url_probe.py. An unverified workspace GITHUB_TOKEN
does not establish Authority scope; Authority consumers exclude that fallback
from the input mapping. Repository roles follow the current canonical policy.
"""
CREDENTIALS = (
    "QIKVRT_RULESET_ADMIN_TOKEN", "QIKVRT_GITHUB_ADMIN_TOKEN",
    "QIKVRT_MESH_TOKEN", "QIKVRT_AUTHORITY_APP_TOKEN", "GITHUB_TOKEN",
)

def credential(environment):
    present = {name: bool(environment.get(name)) for name in CREDENTIALS}
    for name in CREDENTIALS:
        if present[name]:
            return environment[name], name, present
    return "", None, present
