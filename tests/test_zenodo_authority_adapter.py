#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Production authority and compact-grant boundaries, without network effects."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

TESTS = pathlib.Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))
import test_zenodo_machine_proof_policy as fixtures
from tools import qikvrt_zenodo_publish as publisher
from tools import qikvrt_zenodo_actions as zenodo

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUTHORIZATION = "release/OWNER_ZENODO_AUTHORIZATION_brief-2610.json"
FROZEN = "release/brief-2610/FROZEN_UPLOAD_CANDIDATE.json"


class ZenodoAuthorityAdapterTests(unittest.TestCase):
    def compact_fixture(self, root: pathlib.Path) -> None:
        for relative in ("policy", "schemas", "release/brief-2610"):
            shutil.copytree(ROOT / relative, root / relative)
        fixtures.write(root, AUTHORIZATION, (ROOT / AUTHORIZATION).read_bytes())

    def inspect(self, root: pathlib.Path) -> dict:
        return publisher.inspect_compact_authorization(
            pathlib.Path(AUTHORIZATION), pathlib.Path(FROZEN), root
        )

    def test_original_grant_verifies_exact_bytes_without_effects_or_new_consent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            self.compact_fixture(root)
            before = (root / AUTHORIZATION).read_bytes()
            with mock.patch.object(publisher, "_github_api_request") as github, \
                    mock.patch.object(zenodo, "ZenodoClient") as client:
                result = self.inspect(root)
            github.assert_not_called()
            client.assert_not_called()
            self.assertEqual(result["state"], "BLOCK")
            self.assertEqual(result["first_blocker"], "COMPACT_AUTHORIZATION_NOT_EFFECT_ATTESTATION")
            self.assertEqual(result["authority_candidate"], "ingolf-lohmann/qik-vrt")
            self.assertEqual(result["exact_bytes"], {
                "aggregate_sha256": "830e6df6153c901890669a0cd2d2af650ad84f36cf46726854c4314e88ab8ddd",
                "content_file_count": 11, "content_total_bytes": 177418,
            })
            self.assertFalse(result["owner_authorization_created"])
            self.assertFalse(result["single_use_lock_acquired"])
            self.assertFalse(result["zenodo_mutation_attempted"])
            self.assertFalse(result["authority_main_activation_verified"])
            self.assertEqual((root / AUTHORIZATION).read_bytes(), before)
            self.assertEqual(result["original_authorization"]["sha256"], hashlib.sha256(before).hexdigest())

    def test_tampered_content_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            self.compact_fixture(root)
            path = root / "release/brief-2610/QIK-VRT_Der_Brief_an_das_Jahr_2610_DE.pdf"
            path.write_bytes(path.read_bytes() + b"changed")
            with self.assertRaisesRegex(zenodo.ZenodoError, "byte identity differs"):
                self.inspect(root)

    def test_duplicate_file_and_wrong_aggregate_are_rejected(self) -> None:
        for mutation in ("duplicate", "aggregate"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = pathlib.Path(temporary)
                self.compact_fixture(root)
                path = root / FROZEN
                value = json.loads(path.read_text())
                if mutation == "duplicate":
                    value["files"].append(copy.deepcopy(value["files"][0]))
                else:
                    value["aggregate_sha256"] = "0" * 64
                path.write_bytes(zenodo._json_bytes(value))
                with self.assertRaises(zenodo.ZenodoError):
                    self.inspect(root)

    def test_schema_rename_is_not_an_authorization_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            self.compact_fixture(root)
            path = root / AUTHORIZATION
            value = json.loads(path.read_text())
            value["schema"] = publisher.OWNER_AUTHORIZATION_SCHEMA
            path.write_bytes(zenodo._json_bytes(value))
            with self.assertRaisesRegex(zenodo.ZenodoError, "unsupported compact"):
                self.inspect(root)

    def test_compact_schema_cannot_start_production(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, manifest_path = fixtures.MachineProofBeforeZenodoTests().fixture(root)
            manifest = json.loads(manifest_path.read_text())
            path = root / manifest["owner_authorization"]["path"]
            value = json.loads(path.read_text())
            value["schema"] = publisher.COMPACT_OWNER_AUTHORIZATION_SCHEMA
            path.write_bytes(zenodo._json_bytes(value))
            manifest["owner_authorization"] = fixtures.identity(root, path.relative_to(root).as_posix())
            manifest_path.write_bytes(zenodo._json_bytes(manifest))
            with mock.patch.object(publisher, "_github_api_request") as github, \
                    mock.patch.object(zenodo, "ZenodoClient") as client:
                with self.assertRaises(zenodo.ZenodoError):
                    publisher.publish(manifest_path, root)
            github.assert_not_called()
            client.assert_not_called()

    def test_current_policy_binds_origin_and_prevents_historical_role_transfer(self) -> None:
        # Historical consumers keep their import; it cannot select production.
        self.assertEqual(publisher.PRODUCTION_REPOSITORY, "Goldkelch/qik-vrt")
        self.assertEqual(publisher._production_authority(ROOT), "ingolf-lohmann/qik-vrt")
        with mock.patch.object(publisher, "_git", return_value=(0, "https://github.com/ingolf-lohmann/qik-vrt.git")):
            publisher._validate_origin_repository(ROOT, "ingolf-lohmann/qik-vrt")
            with self.assertRaises(zenodo.ZenodoError):
                publisher._validate_origin_repository(ROOT, "Goldkelch/qik-vrt")
        for origin in ("https://github.com.evil/ingolf-lohmann/qik-vrt.git",
                       "https://token@github.com/ingolf-lohmann/qik-vrt.git",
                       "https://github.com/Goldkelch/qik-vrt.git"):
            with self.subTest(origin=origin), self.assertRaises(zenodo.ZenodoError):
                publisher._origin_repository_identity(origin, "ingolf-lohmann/qik-vrt")

    def test_api_cannot_send_authority_token_to_mirror_or_foreign_repository(self) -> None:
        for repository in ("Goldkelch/qik-vrt", "other/repository"):
            with mock.patch.object(publisher.urllib.request, "build_opener") as opener:
                with self.assertRaises(zenodo.ZenodoError):
                    publisher._github_api_request("GET", f"/repos/{repository}/git/ref/tags/x", "g" * 32,
                                                  repository="ingolf-lohmann/qik-vrt")
                opener.assert_not_called()

    def test_candidate_head_or_wrong_tree_cannot_activate_authority(self) -> None:
        for remote_head, remote_tree in (("b" * 40, "c" * 40), ("a" * 40, "d" * 40)):
            with mock.patch.object(publisher, "_git", return_value=(0, "c" * 40)), \
                    mock.patch.object(publisher, "_github_api_request", return_value=(200, {
                        "sha": remote_head, "commit": {"tree": {"sha": remote_tree}}
                    })), self.assertRaisesRegex(zenodo.ZenodoError, "AUTHORITY_ROLE_BINDING_NOT_ACTIVE"):
                publisher._validate_active_authority(ROOT, "ingolf-lohmann/qik-vrt", "a" * 40, "g" * 32)

    def test_new_authority_uses_same_create_only_lock_and_independent_readback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, path = fixtures.MachineProofBeforeZenodoTests().fixture(root)
            manifest = json.loads(path.read_text())
            repository = "ingolf-lohmann/qik-vrt"
            (root / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json").write_bytes(
                (ROOT / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json").read_bytes())
            manifest["repository"] = repository
            authorization = root / manifest["owner_authorization"]["path"]
            value = json.loads(authorization.read_text())
            value["repository"] = repository
            authorization.write_bytes(zenodo._json_bytes(value))
            manifest["owner_authorization"] = fixtures.identity(root, authorization.relative_to(root).as_posix())
            path.write_bytes(zenodo._json_bytes(manifest))
            _, head = fixtures.materialize_git_history(root, path)
            fixtures.run_git(root, "remote", "set-url", "--push", "origin", f"https://github.com/{repository}.git")
            github = fixtures.FakeGitHubGitData(root)
            with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": repository}, clear=True), \
                    mock.patch.object(publisher, "_github_api_request", side_effect=github):
                normalized = publisher.load_manifest(path, root)
                first = publisher._acquire_remote_consumption_lock(root, normalized, head, "g" * 32)
                second = publisher._acquire_remote_consumption_lock(root, normalized, head, "g" * 32)
            self.assertEqual(first["tag_object"], second["tag_object"])
            self.assertEqual(second["recovery_mode"], "EXISTING_EXACT_REF_NO_CREATE")
            self.assertEqual(len(github.refs), 1)
            self.assertEqual(sum(method == "POST" and path.endswith("/git/refs") for method, path in github.calls), 1)
            self.assertTrue(all(path.startswith(f"/repos/{repository}/") for _, path in github.calls))


if __name__ == "__main__":
    unittest.main()
