#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fail-closed static IaC package contract check; does not deploy or admit production."""
from __future__ import annotations
import argparse
import json
import pathlib
import re

POLICY = pathlib.Path("policy/QIKVRT_SELF_CONTAINED_SERVICE_IAC_V1.json")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
SECRET_NAMES = {"password", "token", "secret", "private_key", "api_key", "client_secret", "credential"}
PROHIBITED_STATES = {"EFFECT_ACK_DONE", "PRODUCTION_ADMITTED"}

def check(root: pathlib.Path, instance: object) -> list[str]:
    problems = []
    policy_path = root / POLICY
    if not policy_path.is_file():
        return ["POLICY_MISSING"]
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return ["POLICY_INVALID"]
    if policy.get("schema") != "qikvrt_self_contained_service_iac_v1":
        problems.append("POLICY_SCHEMA_INVALID")
    if policy.get("effect_ack_done") is not False or policy.get("productive_admission") is not False:
        problems.append("POLICY_UNSAFE_ADMISSION")
    for path in policy.get("required_package_paths", []):
        rel = pathlib.PurePosixPath(path)
        if rel.is_absolute() or ".." in rel.parts or not (root / rel).is_file():
            problems.append("CARRIER_MISSING:" + path)
    if not isinstance(instance, dict):
        return problems + ["INSTANCE_NOT_OBJECT"]
    required = policy.get("required_descriptors", [])
    if not isinstance(required, list) or any(not isinstance(k, str) for k in required):
        return problems + ["POLICY_DESCRIPTOR_INVALID"]
    for key in required:
        if key not in instance or instance[key] in (None, "", [], {}):
            problems.append("DESCRIPTOR_MISSING:" + key)
    for key in ("source_head", "source_tree"):
        if key in instance and (not isinstance(instance[key], str) or not HEX40.fullmatch(instance[key])):
            problems.append("BAD_GIT_ID:" + key)
    if "package_digest_sha256" in instance and (
        not isinstance(instance["package_digest_sha256"], str) or
        not HEX64.fullmatch(instance["package_digest_sha256"])
    ):
        problems.append("BAD_PACKAGE_DIGEST")
    roles = instance.get("runtime_roles")
    if not isinstance(roles, list) or not set(policy.get("required_roles", [])).issubset(set(str(x) for x in roles)):
        problems.append("REQUIRED_ROLES_MISSING")
    refs = instance.get("secret_refs")
    if not isinstance(refs, dict) or any(
        not isinstance(v, str) or not v.startswith(("env://", "vault://", "provider-secret://"))
        for v in refs.values()
    ):
        problems.append("SECRET_REFERENCE_INVALID")
    for k in instance:
        if k.upper() in PROHIBITED_STATES:
            problems.append("EFFECT_STATE_IN_DECLARATION")
    def inspect(node: object, path: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(key, str) and key.lower() in SECRET_NAMES and path != "secret_refs":
                    problems.append("SECRET_VALUE_FIELD:" + key)
                inspect(value, key if not path else path + "." + key)
        elif isinstance(node, list):
            for item in node:
                inspect(item, path)
    inspect(instance)
    return sorted(set(problems))

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument("--instance", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        instance = json.loads(args.instance.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print("BLOCK INSTANCE_UNREADABLE", type(exc).__name__)
        return 2
    errors = check(args.root, instance)
    print("PASS STATIC_IAC_STRUCTURE_ONLY" if not errors else "BLOCK " + " ".join(errors))
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
