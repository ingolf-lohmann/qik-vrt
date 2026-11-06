#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only original QIK-VRT Terminal/Transputer browser cutover probe.

This does not operate a browser, execute EAP, authenticate a user, attest a VM,
disable TinyFish, create a new executor, or promote an effect to DONE.
One deliberately unauthenticated browser request verifies noVNC is NOT exposed
without authorization; any successful anonymous browser response is a BLOCK.
"""
from __future__ import annotations

import argparse
import http.client
import json
import re
import ssl
from urllib.parse import urlsplit

SHA1 = re.compile(r"^[a-f0-9]{40}$")
MAX_BODY = 65536
PATH_HEALTH = "/qik-vrt/mesh/v1/healthz"
PATH_SUBJECT = "/api/temdd/subject"
PATH_BROWSER = "/qik-vrt/mesh/v1/terminal/vnc.html"
PATH_CAPABILITY = "/qik-vrt/mesh/v1/effect-ack/.well-known/effect-ack"
REQUIRED_ROLES = ("terminal", "gateway", "m68k", "live_sse")


def admissible_origin(origin: str, *, allow_loopback: bool = False) -> bool:
    if type(origin) is not str:
        return False
    try:
        url = urlsplit(origin)
        if url.username is not None or url.password is not None:
            return False
        if url.query or url.fragment or url.path not in ("", "/"):
            return False
        if url.scheme == "https":
            return url.hostname == "raumzeitterminal.de" and url.port in (None, 443)
        return (allow_loopback and url.scheme == "http"
                and url.hostname in ("127.0.0.1", "localhost")
                and url.port in (8080,))
    except ValueError:
        return False


def read_path(origin: str, path: str, timeout: int = 5) -> tuple[int, str, bytes]:
    """Exact-origin GET with system TLS validation, no redirects or cookies."""
    u = urlsplit(origin)
    conn = (http.client.HTTPSConnection(u.hostname, u.port or 443,
                                        timeout=timeout, context=ssl.create_default_context())
            if u.scheme == "https" else
            http.client.HTTPConnection(u.hostname, u.port or 80, timeout=timeout))
    try:
        conn.request("GET", path, headers={
            "Accept": "application/json, text/html;q=0.5",
            "Cache-Control": "no-cache",
        })
        response = conn.getresponse()
        data = response.read(MAX_BODY + 1)
        if len(data) > MAX_BODY:
            raise ValueError("RESPONSE_TOO_LARGE")
        return response.status, response.getheader("Content-Type", ""), data
    finally:
        conn.close()


def _json_payload(value: bytes):
    try:
        return json.loads(value.decode("utf-8"))
    except (ValueError, UnicodeError):
        return None


def evaluate(read, origin: str, head: str, tree: str, repository: str,
             pr: int, *, allow_loopback: bool = False) -> dict[str, object]:
    """Bounded public probe. Real authentication is out of scope and stays HOLD."""
    findings: list[str] = []
    def hold(reason: str):
        findings.append(reason)
        return {"schema": "qikvrt_megast_native_browser_probe_v1",
                "classification": "BLOCKED",
                "reason": reason,
                "observed": findings,
                "browser_cutover": False,
                "effect_ack_done": False}
    if not admissible_origin(origin, allow_loopback=allow_loopback):
        return hold("EXACT_ORIGIN_NOT_ALLOWED")
    if (not SHA1.fullmatch(head) or not SHA1.fullmatch(tree)
            or repository != "ingolf-lohmann/qik-vrt"
            or type(pr) is not int or pr <= 0):
        return hold("EXACT_AUTHORITY_SUBJECT_INVALID")
    try:
        hs, ct, raw = read(origin, PATH_HEALTH)
        if hs != 200 or "application/json" not in ct.lower():
            return hold("MESH_HEALTH_NOT_AVAILABLE")
        h = _json_payload(raw)
        if not isinstance(h, dict) or h.get("schema") != "qikvrt_cloud_transputer_mesh_health_v1":
            return hold("MESH_HEALTH_SCHEMA_INVALID")
        if h.get("state") != "READY":
            return hold("MESH_NOT_READY")
        if h.get("commit") != head or h.get("tree") != tree:
            return hold("MESH_EXACT_HEAD_TREE_MISMATCH")
        if (not isinstance(h.get("roles"), dict) or
                any(h["roles"].get(role) != "READY" for role in REQUIRED_ROLES)):
            return hold("REQUIRED_MESH_ROLE_NOT_READY")
        findings.append("MESH_HEALTH_EXACT_SUBJECT_OBSERVED")
        ss, st, body = read(origin, PATH_SUBJECT)
        if ss != 200 or "application/json" not in st.lower():
            return hold("TERMINAL_SUBJECT_UNAVAILABLE")
        sub = _json_payload(body)
        expected = {"repository": repository, "pr": pr, "head": head, "tree": tree}
        if not isinstance(sub, dict) or sub.get("subject") != expected:
            return hold("TERMINAL_EXACT_SUBJECT_MISMATCH")
        if sub.get("dod") is True:
            return hold("UNSUPPORTED_TERMINAL_DOD_CLAIM")
        findings.append("TERMINAL_SUBJECT_READBACK_OBSERVED")
        bs, _, _ = read(origin, PATH_BROWSER)
        if 300 <= bs < 400:
            return hold("BROWSER_REDIRECT_FORBIDDEN")
        if bs == 200:
            return hold("ANONYMOUS_BROWSER_EXPOSURE")
        if bs not in (401, 403):
            return hold("BROWSER_ACCESS_GATE_NOT_VERIFIED")
        findings.append("ANONYMOUS_BROWSER_ACCESS_DENIED")
        cs, _, _ = read(origin, PATH_CAPABILITY)
        if cs != 200:
            return hold("EAP_CAPABILITY_NOT_AVAILABLE")
        findings.append("EAP_CAPABILITY_READABLE")
    except (OSError, TimeoutError, ValueError, ssl.SSLError, http.client.HTTPException):
        return hold("TRANSPORT_OR_TLS_PROBE_FAILED")
    return {"schema": "qikvrt_megast_native_browser_probe_v1",
            "classification": "PUBLIC_TRANSPORT_OBSERVED_ONLY",
            "reason": "VM_ATTESTATION_AUTHENTICATED_BROWSER_AND_NATIVE_EAP_READBACK_REQUIRED",
            "observed": findings,
            "browser_cutover": False,
            "effect_ack_done": False}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="https://raumzeitterminal.de")
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--expected-repository", default="ingolf-lohmann/qik-vrt")
    parser.add_argument("--expected-pr", type=int, required=True)
    parser.add_argument("--allow-loopback", action="store_true")
    args = parser.parse_args(argv)
    result = evaluate(read_path, args.origin, args.expected_head,
                      args.expected_tree, args.expected_repository,
                      args.expected_pr, allow_loopback=args.allow_loopback)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["classification"] == "PUBLIC_TRANSPORT_OBSERVED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
