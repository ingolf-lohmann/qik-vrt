#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Pure, fail-closed shape check for *proposed* external-account bindings.

NO network, OAuth token issuance, Apple/iCloud access, host mutation, EAP
prepare/commit or effect release. An accepted shape is NOT evidence of consent.
Trusted runtime authentication, authorization and EAP are separate gates.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

HEX64 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED = {
    ("linkedin", "identity.read"): "OAUTH_2_0_OIDC",
    ("linkedin", "posts.write"): "OAUTH_2_0",
    ("apple_account", "identity.signin"): "SIGN_IN_WITH_APPLE",
    ("icloud_drive", "files.read_selected"): "OS_FILE_PROVIDER_PICKER",
    ("icloud_drive", "files.write_selected"): "OS_FILE_PROVIDER_PICKER",
}
REQUIRED = {
    "schema", "binding_ref", "provider", "capability", "consent_method",
    "subject_digest", "evidence_digest", "exact_scope", "consent_expiry",
    "source_ref", "revocation_ref", "original_host_ref",
}
SECRET_KEYS = {
    "password", "access_token", "refresh_token", "id_token",
    "client_secret", "cookie", "session_cookie", "private_key",
    "authorization_code", "apple_id_password", "security_scoped_bookmark",
}


def _has_secret(value: Any) -> bool:
    if isinstance(value, dict):
        return any(k.lower() in SECRET_KEYS or _has_secret(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_has_secret(x) for x in value)
    return False


def preflight(record: Any) -> dict[str, str]:
    """Only report rejection or readiness for *independent* review, never DONE."""
    def block(reason: str) -> dict[str, str]:
        return {"classification": "BLOCKED", "reason": reason,
                "effect_ack_done": "NOT_CLAIMED"}
    if not isinstance(record, dict):
        return block("RECORD_NOT_OBJECT")
    if _has_secret(record):
        return block("SECRET_FIELD_FORBIDDEN")
    if set(record) != REQUIRED:
        return block("FIELDS_NOT_EXACT")
    if any(not isinstance(value, str) or not value.strip() for value in record.values()):
        return block("VALUE_INVALID")
    if record["schema"] != "qikvrt_external_binding_preflight_v1":
        return block("SCHEMA_UNSUPPORTED")
    capability = (record["provider"], record["capability"])
    if capability not in ALLOWED:
        return block("CAPABILITY_NOT_ALLOWED")
    if record["consent_method"] != ALLOWED[capability]:
        return block("CONSENT_METHOD_MISMATCH")
    if any(not HEX64.fullmatch(record[k])
           for k in ("subject_digest", "evidence_digest")):
        return block("EVIDENCE_DIGEST_INVALID")
    if record["exact_scope"] not in {
        "openid profile email", "w_member_social", "identity",
        "user_selected_file_read", "user_selected_file_write",
    }:
        return block("SCOPE_UNRECOGNIZED")
    scopes = {
        ("linkedin", "identity.read"): "openid profile email",
        ("linkedin", "posts.write"): "w_member_social",
        ("apple_account", "identity.signin"): "identity",
        ("icloud_drive", "files.read_selected"): "user_selected_file_read",
        ("icloud_drive", "files.write_selected"): "user_selected_file_write",
    }
    if record["exact_scope"] != scopes[capability]:
        return block("SCOPE_CAPABILITY_MISMATCH")
    # Never parse untrusted strings as authorization: no real provider or OS
    # grant is proven by these structural checks.
    return {"classification": "STRUCTURALLY_COMPLETE_UNTRUSTED",
            "reason": "PROVIDER_AND_ORIGINAL_EAP_READBACK_REQUIRED",
            "effect_ack_done": "NOT_CLAIMED"}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: qikvrt_external_account_binding_preflight.py RECORD.json", file=sys.stderr)
        return 2
    try:
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"classification": "BLOCKED", "reason": type(exc).__name__,
                          "effect_ack_done": "NOT_CLAIMED"}))
        return 2
    decision = preflight(data)
    print(json.dumps(decision, sort_keys=True))
    return 0 if decision["classification"] == "STRUCTURALLY_COMPLETE_UNTRUSTED" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
