#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Fixed-target, GET-only Authority diagnosis through the existing R11 transport."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.qikvrt_r11_read_only_observation_dispatch_v2 import (
    MAX_RESPONSE, NoRedirect, RetryingGitHubAPI,
)

AUTHORITY = "Goldkelch/qik-vrt"
AUTHORITY_ID = 1271407206
OWNER_ID = 293941403
MIRROR = "ingolf-lohmann/qik-vrt"
MIRROR_ID = 1273784147
QR_URL = "https://github.com/Goldkelch/qik-vrt/blob/main/AI"
RAW_URL = "https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/AI"
SHA = r"[0-9a-f]{40}"
WORKFLOW = ".github/workflows/qikvrt_mesh_authority_edge.yml"
CREDENTIALS = (
    "QIKVRT_RULESET_ADMIN_TOKEN", "QIKVRT_GITHUB_ADMIN_TOKEN",
    "QIKVRT_MESH_TOKEN", "QIKVRT_AUTHORITY_APP_TOKEN", "GITHUB_TOKEN",
)


class AuthorityURLAPI(RetryingGitHubAPI):
    @staticmethod
    def _validate_path(path):
        fixed = {
            "/user", f"/repos/{MIRROR}", f"/repos/{AUTHORITY}",
            f"/repositories/{AUTHORITY_ID}", f"/repos/{AUTHORITY}/commits/main",
        }
        if path in fixed or re.fullmatch(
            rf"/repos/{AUTHORITY}/contents/AI\?ref={SHA}", path
        ):
            return
        raise ValueError("GET path is outside the fixed Authority URL probe")


def utc():
    return datetime.now(timezone.utc).isoformat()


def credential(environment):
    present = {name: bool(environment.get(name)) for name in CREDENTIALS}
    for name in CREDENTIALS:
        if present[name]:
            return environment[name], name, present
    return "", None, present


def public_get(url):
    if url not in {QR_URL, RAW_URL}:
        raise ValueError("public read escaped the two fixed entrypoints")
    request = urllib.request.Request(url, method="GET", headers={
        "User-Agent": "qikvrt-authority-url-probe/1", "Cache-Control": "no-cache",
    })
    try:
        response = urllib.request.build_opener(NoRedirect()).open(request, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError("public body exceeds its byte bound")
        return int(response.status), raw


def probe(token, source, executor, *, transport=None, public_reader=public_get):
    report = {
        "schema": "qikvrt_authority_url_probe_v1", "observed_at": utc(),
        "executor": executor, "target": {
            "repository": AUTHORITY, "repository_id": AUTHORITY_ID,
            "owner_id": OWNER_ID, "qr_url": QR_URL,
        },
        "credential_source": source, "observations": [],
        "first_blocker": None, "state": "CONTINUE", "source_read_verified": False,
        "public_url_effect_verified": False, "effect_ack_done": False,
        "mutation_count": 0, "predecessor_evidence_transfer": False,
    }
    if not token:
        report.update(state="BLOCK", first_blocker="AUTHORITY_CREDENTIAL_NOT_DELIVERED")
        return report
    api = AuthorityURLAPI(token, transport=transport)

    def get(label, path):
        # Accept every HTTP status once: 403/429 is recorded, never blindly retried.
        status, headers, raw = api.raw_get(path, tuple(range(100, 600)))
        if token.encode() in raw:
            raise ValueError("response contains credential material; refusing persistence")
        item = {"label": label, "path": path, "method": "GET", "status": status,
                "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "observed_at": utc()}
        if headers.get("x-ratelimit-remaining") == "0":
            item["rate_limit_exhausted"] = True
        report["observations"].append(item)
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            value = None
        return item, value if isinstance(value, dict) else {}

    def blocked(reason):
        report.update(state="BLOCK", first_blocker=reason)
        return report

    control, value = get("mirror_control", f"/repos/{MIRROR}")
    if control["status"] == 200 and value.get("id") != MIRROR_ID:
        return blocked("EXECUTOR_CONTROL_IDENTITY_MISMATCH")
    principal, value = get("credential_principal", "/user")
    report["principal"] = {
        "status": principal["status"], "identity_verified": principal["status"] == 200,
    }
    if principal["status"] == 200:
        report["principal"].update(id=value.get("id"), login=value.get("login"))
    named, repository = get("authority_by_name", f"/repos/{AUTHORITY}")
    numeric, by_id = get("authority_by_id", f"/repositories/{AUTHORITY_ID}")
    for item, value in ((named, repository), (numeric, by_id)):
        if item["status"] == 200 and (
            value.get("id") != AUTHORITY_ID or value.get("full_name") != AUTHORITY
            or value.get("owner", {}).get("id") != OWNER_ID
        ):
            return blocked("AUTHORITY_IDENTITY_MISMATCH")
    if named["status"] != 200 or numeric["status"] != 200:
        reason = "AUTHORITY_READ_REJECTED_CAUSE_UNDETERMINED"
        if source == "GITHUB_TOKEN":
            reason = "AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED"
        return blocked(reason)
    report["repository_visibility"] = repository.get("visibility")
    report["target_permissions"] = {
        key: value for key, value in repository.get("permissions", {}).items()
        if key in {"pull", "push", "admin", "maintain", "triage"} and isinstance(value, bool)
    }
    commit, value = get("authority_main", f"/repos/{AUTHORITY}/commits/main")
    head = value.get("sha", "")
    tree = value.get("commit", {}).get("tree", {}).get("sha", "")
    if commit["status"] != 200 or not re.fullmatch(SHA, head) or not re.fullmatch(SHA, tree):
        return blocked("AUTHORITY_MAIN_SUBJECT_NOT_VERIFIED")
    item, value = get("authority_AI", f"/repos/{AUTHORITY}/contents/AI?ref={head}")
    if item["status"] != 200 or value.get("encoding") != "base64":
        return blocked("EXACT_AUTHORITY_AI_NOT_READABLE")
    encoded = value.get("content")
    if not isinstance(encoded, str):
        return blocked("EXACT_AUTHORITY_AI_INVALID_ENCODING")
    try:
        raw = base64.b64decode(encoded.replace("\n", ""), validate=True)
    except (ValueError, TypeError):
        return blocked("EXACT_AUTHORITY_AI_INVALID_ENCODING")
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if value.get("type") != "file" or value.get("path") != "AI" or value.get("size") != len(raw) or value.get("sha") != blob:
        return blocked("EXACT_AUTHORITY_AI_BINDING_MISMATCH")
    if token.encode() in raw:
        raise ValueError("AI contains credential material; refusing persistence")
    report.update(source_read_verified=True, authority_subject={
        "head": head, "tree": tree, "AI_blob": blob,
        "AI_bytes": len(raw), "AI_sha256": hashlib.sha256(raw).hexdigest(),
    })
    public = []
    for url in (QR_URL, RAW_URL):
        status, body = public_reader(url)
        public.append({"url": url, "method": "GET", "authentication": "anonymous",
                       "status": status, "bytes": len(body),
                       "sha256": hashlib.sha256(body).hexdigest(), "observed_at": utc()})
    report["public_readbacks"] = public
    final, value = get("authority_main_reobservation", f"/repos/{AUTHORITY}/commits/main")
    if final["status"] != 200 or value.get("sha") != head:
        return blocked("AUTHORITY_MAIN_CHANGED_DURING_PROBE")
    if public[0]["status"] == 200 and public[1]["status"] == 200 and public[1]["sha256"] == report["authority_subject"]["AI_sha256"]:
        report.update(public_url_effect_verified=True, state="URL_READBACK_VERIFIED")
    else:
        return blocked("PUBLIC_QR_URL_EFFECT_NOT_VERIFIED")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    expected = os.environ.get("GITHUB_SHA", "")
    if os.environ.get("GITHUB_REPOSITORY") != MIRROR or not re.fullmatch(SHA, expected):
        raise SystemExit("BLOCK: native Mirror event binding is missing")
    def git(*parts):
        return subprocess.check_output(["git", "-C", str(ROOT), *parts], text=True).strip()
    if git("rev-parse", "HEAD") != expected:
        raise SystemExit("BLOCK: checkout does not match the native event head")
    executor = {
        "repository": MIRROR, "head": expected, "tree": git("rev-parse", "HEAD^{tree}"),
        "run_id": os.environ.get("GITHUB_RUN_ID"), "attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "ref": os.environ.get("GITHUB_REF"), "actor": os.environ.get("GITHUB_ACTOR"),
        "event": os.environ.get("GITHUB_EVENT_NAME"), "workflow_path": WORKFLOW,
        "workflow_sha256": hashlib.sha256((ROOT / WORKFLOW).read_bytes()).hexdigest(),
    }
    token, source, present = credential(os.environ)
    try:
        report = probe(token, source, executor)
    except (ValueError, TypeError, KeyError, OSError, SystemExit):
        report = {"schema": "qikvrt_authority_url_probe_v1", "executor": executor,
                  "observed_at": utc(), "state": "BLOCK", "first_blocker": "PROBE_TRANSPORT_OR_RESPONSE_VALIDATION_FAILED",
                  "credential_source": source, "mutation_count": 0, "effect_ack_done": False}
    report["credential_names_present"] = present
    app_inputs = {
        name: bool(os.environ.get(name)) for name in
        ("QIKVRT_RULESET_APP_ID", "QIKVRT_RULESET_APP_PRIVATE_KEY")
    }
    report["app_credential_names_present"] = app_inputs
    report["app_token_issuance_outcome"] = os.environ.get("QIKVRT_APP_TOKEN_ISSUANCE_OUTCOME", "skipped")
    if report.get("first_blocker") == "AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED" and all(app_inputs.values()) and report["app_token_issuance_outcome"] != "success":
        report["first_blocker"] = "AUTHORITY_APP_TOKEN_ISSUANCE_NOT_VERIFIED"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("QIKVRT_AUTHORITY_URL_READBACK=" + json.dumps(report, sort_keys=True))
    return 0 if report.get("public_url_effect_verified") else 2


if __name__ == "__main__":
    raise SystemExit(main())
