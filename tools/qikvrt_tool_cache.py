#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate deterministic, complete cache coverage for the declared QIK-VRT runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "runtime/toolchains/TOOLCHAIN.lock.tsv"
REGISTRY_PATH = ROOT / "runtime/toolchains/CACHE_REGISTRY.json"
COVERAGE_PATH = ROOT / "runtime/toolchains/CACHE_COVERAGE.json"
WINDOWS_RELEASE_PATH = "runtime/toolchains/python-3.12.10-embed-amd64.release.json"

REQUIRED_COMPONENT_FIELDS = {
    "version",
    "profiles",
    "cache_class",
    "provider",
    "cache_locations",
    "authority_files",
    "verification",
    "trusted_save",
}
FORBIDDEN_CACHE_TOKENS = {
    "gh_token",
    "github_token",
    "credential",
    "cookie",
    ".ssh",
    "private_key",
    "auth login",
}


class ContractError(RuntimeError):
    """Raised when the runtime cache contract is incomplete or inconsistent."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_lock() -> dict[str, dict[str, list[str]]]:
    if not LOCK_PATH.is_file():
        raise ContractError(f"missing toolchain lock: {LOCK_PATH.relative_to(ROOT)}")
    records: dict[str, dict[str, set[str]]] = {}
    for line_number, raw in enumerate(
        LOCK_PATH.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not raw or raw.startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 7:
            raise ContractError(
                f"invalid lock row {line_number}: expected 7 tab-separated fields"
            )
        component, version, platform, _archive, _archive_hash, _license, purpose = fields
        if not component or not version or not platform or not purpose:
            raise ContractError(f"invalid empty field in lock row {line_number}")
        record = records.setdefault(
            component,
            {"versions": set(), "platforms": set(), "purposes": set()},
        )
        record["versions"].add(version)
        record["platforms"].add(platform)
        record["purposes"].add(purpose)

    normalized: dict[str, dict[str, list[str]]] = {}
    for component, record in records.items():
        versions = sorted(record["versions"])
        if len(versions) != 1:
            raise ContractError(f"{component}: multiple versions in lock: {versions}")
        normalized[component] = {
            "versions": versions,
            "platforms": sorted(record["platforms"]),
            "purposes": sorted(record["purposes"]),
        }
    if not normalized:
        raise ContractError("toolchain lock declares no components")
    return normalized


def read_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        raise ContractError(f"missing cache registry: {REGISTRY_PATH.relative_to(ROOT)}")
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid cache registry JSON: {exc}") from exc
    if registry.get("schema") != "qikvrt-tool-cache-registry/1.0":
        raise ContractError("unsupported cache registry schema")
    if registry.get("lock_authority") != str(LOCK_PATH.relative_to(ROOT)):
        raise ContractError(
            "cache registry lock_authority does not identify TOOLCHAIN.lock.tsv"
        )
    if registry.get("coverage_authority") != str(COVERAGE_PATH.relative_to(ROOT)):
        raise ContractError(
            "cache registry coverage_authority does not identify CACHE_COVERAGE.json"
        )
    if not isinstance(registry.get("components"), dict):
        raise ContractError("cache registry components must be an object")
    return registry


def validate_windows_python_payload(registry: dict[str, Any]) -> None:
    """Cross-check the Windows starter against the existing lock and upstream bytes."""
    component = registry['components'].get('python-embed-windows')
    if component is None:
        return
    relative = component.get('payload_manifest')
    if relative != 'runtime/toolchains/python-3.12.10-embed-amd64.payload.json':
        raise ContractError('Windows Python payload authority path mismatch')
    try:
        spec = json.loads((ROOT / relative).read_text(encoding='utf-8'))
        rows = [line.split('\t') for line in LOCK_PATH.read_text(encoding='utf-8').splitlines()
                if line.startswith('python-embed-windows\t')]
        if len(rows) != 1 or rows[0][1:6] != [spec['version'], spec['platform'], spec['archive'],
                                               spec['archive_sha256'], spec['license']]:
            raise ContractError('Windows Python payload differs from toolchain lock')
        if (spec['schema'] != 'qikvrt-windows-python-payload/1.0' or spec['version'] != '3.12.10'
                or spec['platform'] != 'windows-amd64' or spec['network_default'] != 'DENY'):
            raise ContractError('Windows Python payload identity/network policy mismatch')
        for path_key, hash_key in [('license_file', 'license_sha256'),
                                   ('upstream_sbom_file', 'upstream_sbom_sha256'),
                                   ('upstream_sigstore_file', 'upstream_sigstore_sha256')]:
            if sha256_bytes((ROOT / spec[path_key]).read_bytes()) != spec[hash_key]:
                raise ContractError(f'Windows Python provenance hash mismatch: {path_key}')
        sbom = json.loads((ROOT / spec['upstream_sbom_file']).read_text(encoding='utf-8'))
        upstream = [p for p in sbom['packages'] if p['SPDXID'] == 'SPDXRef-PACKAGE-cpython']
        if (len(upstream) != 1 or upstream[0]['versionInfo'] != spec['version']
                or upstream[0]['downloadLocation'] != spec['upstream_url']
                or upstream[0]['licenseConcluded'] != spec['license']
                or {'algorithm': 'SHA256', 'checksumValue': spec['archive_sha256']}
                   not in upstream[0]['checksums']):
            raise ContractError('Windows Python upstream SPDX binding mismatch')
        files = spec['files']
        if len(files) != 35 or files['LICENSE.txt']['sha256'] != spec['license_sha256']:
            raise ContractError('Windows Python complete payload/license binding mismatch')
        for name, record in files.items():
            if (not name or Path(name).name != name or '/' in name or '\\' in name
                    or record['bytes'] <= 0 or len(record['sha256']) != 64
                    or any(c not in '0123456789abcdef' for c in record['sha256'])):
                raise ContractError('Windows Python member identity/hash/size mismatch')
        witness = component.get('native_offline_witness')
        if witness is not None:
            receipts = []
            for path_key, hash_key in [('receipt_path', 'receipt_sha256'),
                                       ('cache_receipt_path', 'cache_receipt_sha256')]:
                raw = (ROOT / witness[path_key]).read_bytes()
                if sha256_bytes(raw) != witness[hash_key]:
                    raise ContractError('Windows Python native offline witness hash mismatch')
                receipts.append(json.loads(raw))
            offline, cached = receipts
            if (offline['schema'] != 'qikvrt-windows-python-offline-start-receipt/1.0'
                    or offline['source_head'] != witness['source_head']
                    or offline['source_tree'] != witness['source_tree']
                    or str(offline['run_id']) != str(witness['run_id'])
                    or offline['archive_sha256'] != spec['archive_sha256']
                    or offline['license_sha256'] != spec['license_sha256']
                    or offline['payload_manifest_sha256'] != sha256_bytes((ROOT / relative).read_bytes())
                    or not offline['native_windows_x64'] or not offline['os_egress_denied']
                    or offline['system_python_candidates_exposed']
                    or offline['upstream_download_during_offline_start']
                    or not offline['dependency_closed_for_materialized_carrier']
                    or offline['cold_offline_restore'] != 'PASS'
                    or offline['fresh_qikvrt_cmd_start'] != 'PASS'
                    or offline['warm_offline_start'] != 'PASS'
                    or not offline['effect_acceptance_retained']
                    or offline['main_activation_verified'] or offline['effect_ack_done']
                    or cached['archive_sha256'] != spec['archive_sha256']
                    or cached['upstream_download_performed']
                    or cached['self_test'] != offline['runtime_self_test']
                    or cached['version'] != spec['version']
                    or cached['self_test']['pointer_bits'] != 64):
                raise ContractError('Windows Python native offline witness identity/scope mismatch')
            expected_controls = {'native-log-contract', 'native-log-owner-dacl', 'missing-cache',
                'tampered-archive', 'missing-archive', 'tampered-executable', 'missing-stdlib',
                'unexpected-module', 'reparse-cache', 'reconstruction-consent-required',
                'final-verification-rollback'}
            controls = offline['negative_controls']
            if set(controls) != expected_controls or any(v['result'] != 'PASS' for v in controls.values()):
                raise ContractError('Windows Python native offline negative controls are incomplete')
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ContractError(f'invalid Windows Python payload authority: {exc}') from exc


def windows_release_candidate(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve the immutable candidate; availability and publication remain unproved."""
    registry = read_registry() if registry is None else registry
    component = registry['components']['python-embed-windows']
    try:
        from tools.qikvrt_integrity import _regular_file_bytes
        raw = _regular_file_bytes(ROOT, WINDOWS_RELEASE_PATH)
        link = component['durable_release_candidate']
        if link['path'] != WINDOWS_RELEASE_PATH or sha256_bytes(raw) != link['sha256']:
            raise ContractError('Windows release candidate registry hash mismatch')
        candidate = json.loads(raw)
        spec = json.loads(_regular_file_bytes(ROOT, component['payload_manifest']))
        archive = candidate['archive']
        name = f"qikvrt-cpython-{spec['version']}-{spec['platform']}-sha256-{spec['archive_sha256']}.zip"
        tag = f"runtime-cpython-{spec['version']}-{spec['platform']}-sha256-{spec['archive_sha256']}"
        if (candidate['schema'] != 'qikvrt-runtime-release-candidate/1.0'
                or candidate['component'] != spec['component']
                or candidate['version'] != spec['version'] or candidate['platform'] != spec['platform']
                or candidate['license'] != spec['license']
                or archive != {'upstream_name': spec['archive'], 'asset_name': name,
                               'bytes': spec['archive_bytes'], 'sha256': spec['archive_sha256']}
                or candidate['repository'] != 'ingolf-lohmann/qik-vrt'
                or candidate['tag'] != tag
                or candidate['download_url'] != f"https://github.com/{candidate['repository']}/releases/download/{tag}/{name}"
                or candidate['state'] != 'PREPARED_NOT_PUBLISHED'
                or candidate['no_clobber'] is not True or candidate['immutable_release_required'] is not True
                or candidate['durable_public_readback_verified'] is not False
                or candidate['main_activation_verified'] is not False
                or candidate['effect_ack_done'] is not False
                or candidate['reconstruction'] != {'url': spec['upstream_url'],
                                                   'requires': spec['reconstruction_requires']}):
            raise ContractError('Windows release candidate identity/effect boundary mismatch')
        witness = component['native_offline_witness']
        expected = {component['payload_manifest'], 'runtime/toolchains/TOOLCHAIN.lock.tsv',
                    spec['license_file'], spec['upstream_sbom_file'], spec['upstream_sigstore_file'],
                    'third_party/python/THIRD_PARTY_PYTHON_RUNTIME_PROVENANCE.json',
                    witness['receipt_path'], witness['cache_receipt_path']}
        bindings = candidate['bindings']
        if {b['path'] for b in bindings} != expected or len(bindings) != len(expected):
            raise ContractError('Windows release candidate binding set mismatch')
        for binding in bindings:
            data = _regular_file_bytes(ROOT, binding['path'])
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if (set(binding) != {'path', 'bytes', 'sha256', 'git_blob_sha1'}
                    or type(binding['bytes']) is not int or binding['bytes'] != len(data)
                    or binding['sha256'] != sha256_bytes(data) or binding['git_blob_sha1'] != blob):
                raise ContractError(f"Windows release candidate bound bytes differ: {binding['path']}")
        if candidate['historical_native_witness'] != witness:
            raise ContractError('Windows release candidate historical witness mismatch')
        return candidate
    except (OSError, KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise ContractError(f'invalid Windows release candidate: {exc}') from exc


def validate_registry(
    locked: dict[str, dict[str, list[str]]],
    registry: dict[str, Any],
) -> list[dict[str, Any]]:
    entries: dict[str, Any] = registry["components"]
    locked_names = set(locked)
    registry_names = set(entries)
    missing = sorted(locked_names - registry_names)
    extra = sorted(registry_names - locked_names)
    if missing:
        raise ContractError(
            f"cache registry misses locked components: {', '.join(missing)}"
        )
    if extra:
        raise ContractError(
            f"cache registry has undeclared components: {', '.join(extra)}"
        )

    allowed_classes = set(registry.get("cache_classes", []))
    if not allowed_classes:
        raise ContractError("cache registry defines no cache classes")

    coverage: list[dict[str, Any]] = []
    for component in sorted(locked):
        entry = entries[component]
        if not isinstance(entry, dict):
            raise ContractError(f"{component}: registry entry must be an object")
        absent_fields = sorted(REQUIRED_COMPONENT_FIELDS - set(entry))
        if absent_fields:
            raise ContractError(
                f"{component}: missing fields: {', '.join(absent_fields)}"
            )
        expected_version = locked[component]["versions"][0]
        if entry["version"] != expected_version:
            raise ContractError(
                f"{component}: registry version {entry['version']!r} "
                f"!= lock {expected_version!r}"
            )
        if entry["cache_class"] not in allowed_classes:
            raise ContractError(
                f"{component}: unsupported cache class {entry['cache_class']!r}"
            )
        for list_field in (
            "profiles",
            "cache_locations",
            "authority_files",
            "verification",
        ):
            value = entry[list_field]
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                raise ContractError(
                    f"{component}: {list_field} must be a non-empty string list"
                )
        if not isinstance(entry["provider"], str) or not entry["provider"].strip():
            raise ContractError(f"{component}: provider must be non-empty")
        if not isinstance(entry["trusted_save"], bool):
            raise ContractError(f"{component}: trusted_save must be boolean")

        for authority in entry["authority_files"]:
            authority_path = ROOT / authority
            if not authority_path.is_file():
                raise ContractError(
                    f"{component}: missing authority file: {authority}"
                )

        joined_locations = "\n".join(entry["cache_locations"]).lower()
        forbidden = sorted(
            token for token in FORBIDDEN_CACHE_TOKENS if token in joined_locations
        )
        if forbidden:
            raise ContractError(
                f"{component}: credential-bearing cache location token(s): "
                f"{', '.join(forbidden)}"
            )

        coverage.append(
            {
                "cache_class": entry["cache_class"],
                "component": component,
                "provider": entry["provider"],
                "version": expected_version,
            }
        )
    validate_windows_python_payload(registry)
    if 'durable_release_candidate' in entries.get('python-embed-windows', {}):
        windows_release_candidate(registry)
    return coverage


def build_coverage() -> dict[str, Any]:
    locked = read_lock()
    registry = read_registry()
    components = validate_registry(locked, registry)
    lock_bytes = LOCK_PATH.read_bytes()
    registry_bytes = REGISTRY_PATH.read_bytes()
    total = len(locked)
    covered = len(components)
    if covered != total:
        raise ContractError(f"cache coverage is incomplete: {covered}/{total}")
    return {
        "schema": "qikvrt-tool-cache-coverage/1.0",
        "status": "PASS",
        "coverage_basis": (
            "unique components in runtime/toolchains/TOOLCHAIN.lock.tsv"
        ),
        "coverage_percent": 100,
        "declared_components": total,
        "covered_components": covered,
        "lock_sha256": sha256_bytes(lock_bytes),
        "registry_sha256": sha256_bytes(registry_bytes),
        "components": components,
        "rules": {
            "all_declared_tools_have_cache_strategy": True,
            "new_tool_must_extend_lock_and_registry_before_use": True,
            "credentials_forbidden_in_cache": True,
            "cold_and_warm_cache_semantics_equal": True,
            "cache_never_replaces_required_checks": True,
        },
    }


def render() -> None:
    document = build_coverage()
    COVERAGE_PATH.write_text(canonical_json(document), encoding="utf-8")
    print(
        f"PASS: rendered {document['covered_components']}/"
        f"{document['declared_components']} tool-cache coverage"
    )


def verify() -> None:
    expected = canonical_json(build_coverage())
    if not COVERAGE_PATH.is_file():
        raise ContractError(
            f"missing coverage authority: {COVERAGE_PATH.relative_to(ROOT)}"
        )
    actual = COVERAGE_PATH.read_text(encoding="utf-8")
    if actual != expected:
        raise ContractError(
            "CACHE_COVERAGE.json is stale; run "
            "'python3 tools/qikvrt_tool_cache.py render'"
        )
    document = json.loads(actual)
    print(
        f"PASS: {document['covered_components']}/"
        f"{document['declared_components']} declared tools have cache strategies "
        f"({document['coverage_percent']}%)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("render", "verify"))
    args = parser.parse_args(argv)
    try:
        if args.command == "render":
            render()
        else:
            verify()
    except ContractError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
