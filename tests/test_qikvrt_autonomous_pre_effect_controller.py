# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_autonomous_pre_effect_controller",
    ROOT / "tools/qikvrt_autonomous_pre_effect_controller.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AutonomousPreEffectControllerTests(unittest.TestCase):
    @staticmethod
    def command_result(command: tuple[str, ...], stdout: str = "", returncode: int = 0):
        return MODULE.self_heal.CommandResult(command, returncode, stdout, "")

    def test_policy_is_active_and_fail_closed(self) -> None:
        policy = MODULE.load_policy()
        self.assertEqual(policy["mission"], "AUTONOMOUS_UNTIL_FIRST_IRREVERSIBLE_EXTERNAL_EFFECT")
        self.assertEqual(policy["preconditions"], MODULE.EXPECTED_PRECONDITIONS)
        self.assertEqual(policy["fail_closed"]["state"], "HOLD")
        self.assertTrue(policy["fail_closed"]["repair_forbidden"])

    def test_all_preconditions_allow_repository_internal_execution(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        self.assertEqual(MODULE.classify(preconditions, None), "AUTONOMOUS_EXECUTION_ALLOWED")

    def test_missing_precondition_holds_instead_of_repairs(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        preconditions["NO_COMPETING_WRITER"] = False
        self.assertEqual(MODULE.classify(preconditions, None), "HOLD")

    def test_irreversible_effect_requires_exact_owner_authorization(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        for effect in MODULE.IRREVERSIBLE_EFFECTS:
            self.assertEqual(MODULE.classify(preconditions, effect), "REQUIRE_EXACT_PRODUCT_OWNER_AUTHORIZATION")

    def test_unknown_effect_fails_closed(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        with self.assertRaises(MODULE.PreEffectBlock):
            MODULE.classify(preconditions, "UNBOUND_EXTERNAL_EFFECT")

    def test_completion_and_epistemic_claims_remain_prohibited(self) -> None:
        policy = MODULE.load_policy()
        prohibited = set(policy["prohibited_autonomous_effects"])
        self.assertTrue(MODULE.PROHIBITED_CLAIMS.issubset(prohibited))
        self.assertFalse(policy["epistemic_boundaries"]["scientific_confirmation_inferable"])
        self.assertFalse(policy["epistemic_boundaries"]["physical_correspondence_inferable"])
        self.assertFalse(policy["epistemic_boundaries"]["independent_review_fabricable"])
        self.assertFalse(policy["epistemic_boundaries"]["measurement_fabricable"])

    def test_personal_working_copy_uses_bound_canonical_upstream(self) -> None:
        def fake_run(command, timeout=900):
            del timeout
            command = tuple(command)
            if command == ("git", "remote"):
                return self.command_result(command, "origin\nupstream\n")
            if command == ("git", "remote", "get-url", "upstream"):
                return self.command_result(
                    command, "https://github.com/ingolf-lohmann/qik-vrt.git\n"
                )
            raise AssertionError(command)

        with mock.patch.object(MODULE.self_heal, "run", side_effect=fake_run):
            self.assertEqual(MODULE._canonical_source_remote(), "upstream")

    def test_direct_authority_clone_falls_back_to_bound_origin(self) -> None:
        def fake_run(command, timeout=900):
            del timeout
            command = tuple(command)
            if command == ("git", "remote"):
                return self.command_result(command, "origin\n")
            if command == ("git", "remote", "get-url", "origin"):
                return self.command_result(
                    command, "https://github.com/ingolf-lohmann/qik-vrt.git\n"
                )
            raise AssertionError(command)

        with mock.patch.object(MODULE.self_heal, "run", side_effect=fake_run):
            self.assertEqual(MODULE._canonical_source_remote(), "origin")

    def test_mismatched_upstream_url_fails_closed(self) -> None:
        def fake_run(command, timeout=900):
            del timeout
            command = tuple(command)
            if command == ("git", "remote"):
                return self.command_result(command, "origin\nupstream\n")
            if command == ("git", "remote", "get-url", "upstream"):
                return self.command_result(
                    command, "https://github.com/example/not-qik-vrt.git\n"
                )
            raise AssertionError(command)

        with mock.patch.object(MODULE.self_heal, "run", side_effect=fake_run):
            with self.assertRaisesRegex(
                MODULE.PreEffectBlock, "canonical source remote URL mismatch"
            ):
                MODULE._canonical_source_remote()

    def test_remote_main_revision_queries_policy_bound_local_origin(self) -> None:
        expected = "17bf684b08363bdb8ae95775ea5a4ae22ce4f0a9"

        def fake_run(command, timeout=900):
            del timeout
            command = tuple(command)
            if command == ("git", "remote", "get-url", "--all", "origin"):
                return self.command_result(
                    command, "https://github.com/ingolf-lohmann/qik-vrt.git\n"
                )
            if command == (
                "gh", "api", "--hostname", "github.com", "--method", "GET",
                "repos/ingolf-lohmann/qik-vrt/git/ref/heads/main"
            ):
                return self.command_result(command, json.dumps({"object": {"sha": expected, "type": "commit"}}))
            raise AssertionError(command)

        with mock.patch.object(MODULE.self_heal, "run", side_effect=fake_run):
            self.assertEqual(MODULE._remote_main_revision(), expected)

    def test_execution_origin_accepts_only_policy_bound_repository_urls(self) -> None:
        for repository in ("Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt"):
            for suffix in ("", ".git"):
                with self.subTest(repository=repository, suffix=suffix):
                    result = self.command_result((), f"https://github.com/{repository}{suffix}\n")
                    with mock.patch.object(MODULE.self_heal, "run", return_value=result):
                        self.assertEqual(MODULE._execution_source_remote(), "origin")

    def test_unknown_missing_or_ambiguous_execution_origin_fails_closed(self) -> None:
        for urls, returncode in (
            ("https://github.com/example/qik-vrt.git\n", 0),
            ("https://github.com/ingolf-lohmann/qik-vrt.git.evil\n", 0),
            ("https://github.com/ingolf-lohmann/qik-vrt.git\nhttps://github.com/ingolf-lohmann/qik-vrt.git\n", 0),
            ("", 1),
        ):
            with self.subTest(urls=urls, returncode=returncode):
                result = self.command_result((), urls, returncode)
                with mock.patch.object(MODULE.self_heal, "run", return_value=result):
                    with self.assertRaisesRegex(MODULE.PreEffectBlock, "repository-local origin URL mismatch"):
                        MODULE._execution_source_remote()

    def test_execution_origin_rejects_missing_or_malformed_role_policy(self) -> None:
        for payload in ("[]", "{}", "invalid"):
            with self.subTest(payload=payload):
                with mock.patch.object(pathlib.Path, "read_text", return_value=payload):
                    with self.assertRaises(MODULE.PreEffectBlock):
                        MODULE._execution_source_remote()

    def test_local_main_drift_still_holds(self) -> None:
        with mock.patch.object(MODULE.self_heal, "observed_base_revision", return_value="a" * 40), \
             mock.patch.object(MODULE, "_remote_main_revision", return_value="b" * 40), \
             mock.patch.object(MODULE, "load_policy"):
            observed = MODULE.observe_preconditions()
        self.assertFalse(observed["CURRENT_MAIN_REOBSERVED"])
        self.assertFalse(observed["NO_COMPETING_WRITER"])
        self.assertEqual(MODULE.classify(observed, None), "HOLD")


if __name__ == "__main__":
    unittest.main()
