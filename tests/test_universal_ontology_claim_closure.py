#!/usr/bin/env python3
"""Boundary regression tests for universal-ontology claim closure."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formalization/QIKVRT_Formalization_v2.0"
MATRIX = FORMAL / "universal_ontology/CLAIM_MATRIX.json"
WORLD = FORMAL / "universal_ontology/WORLD_FORMULA_CLAIM_MATRIX.json"
SCOPE = FORMAL / "universal_ontology/SOURCE_SCOPE.json"
CORE = FORMAL / "QIKVRTUniversalOntology/Core.lean"
AUDIT = FORMAL / "QIKVRTUniversalOntology/AxiomAudit.lean"
EXTENDED_AUDIT = FORMAL / "QIKVRTUniversalOntology/ExtendedAxiomAudit.lean"
STANDING = ROOT / "state/authorization/delegations/OWNER_WORLD_FORMULA_FORMALIZATION_AND_PUBLICATION_DELEGATION_V1.json"
WORK = ROOT / "state/work_units/UNIFIED_ONTOLOGY_KERNEL_PROGRAM_V2.json"
IETF = ROOT / "external/ietf/UNIVERSAL_ONTOLOGY_FORMALIZATION_DISPOSITION_2026-08-06.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_universal_ontology_formalization.yml"
VERIFIER_PATH = FORMAL / "scripts/verify_universal_ontology.py"


def load_verifier_module():
    spec = importlib.util.spec_from_file_location(
        "qikvrt_verify_universal_ontology", VERIFIER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("universal-ontology verifier cannot be imported")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFIER = load_verifier_module()


class UniversalOntologyRuntimeProvisioningTests(unittest.TestCase):
    """Execute the real workflow shell with disposable transport/tool fixtures."""

    def provisioning_script(self, workflow: pathlib.Path = WORKFLOW) -> str:
        match = re.search(
            r"      - name: Provision and verify exact Lean release\n"
            r".*?        run: \|\n(?P<body>(?:          [^\n]*\n|\n)+)",
            workflow.read_text(encoding="utf-8"), re.DOTALL,
        )
        self.assertIsNotNone(match, "missing bounded release provisioning")
        return textwrap.dedent(match.group("body"))

    def run_provisioning(self, mode="reset", cached=None, lake_version="4.19.0",
                         source_version="4.19.0", cache_bytes=b"release fixture",
                         broken_cache_symlink=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        package = root / "formalization/QIKVRT_Formalization_v2.0"
        package.mkdir(parents=True)
        (package / "lean-toolchain").write_text(f"leanprover/lean4:v{source_version}\n")
        runtime = root / "runner"
        runtime.mkdir()
        if cached is not None:
            archive = runtime / "qikvrt-lean/lean-4.19.0-linux.tar.zst"
            archive.parent.mkdir()
            if broken_cache_symlink:
                archive.symlink_to(root / "missing-release")
            else:
                archive.write_bytes(cache_bytes)
        stubs = root / "transport"
        stubs.mkdir()
        stub = textwrap.dedent('''\
            #!/usr/bin/env python3
            import json, os, pathlib, sys
            root = pathlib.Path(os.environ["QIKVRT_FIXTURE_ROOT"])
            name = pathlib.Path(sys.argv[0]).name
            with (root / "calls.jsonl").open("a") as out:
                out.write(json.dumps([name, *sys.argv[1:]]) + "\\n")
            mode = os.environ["QIKVRT_FIXTURE_MODE"]
            if name == "curl":
                if mode == "reset":
                    sys.stderr.write("Recv failure: Connection reset by peer\\n")
                    raise SystemExit(56)
                target = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])
                target.write_bytes(b"x" if mode == "short" else b"release fixture")
            else:
                if mode == "extract-failure":
                    raise SystemExit(2)
                target = pathlib.Path(sys.argv[sys.argv.index("-C") + 1]) / "bin"
                target.mkdir()
                for tool, output in {
                    "lean": "Lean (version " + os.environ["QIKVRT_FIXTURE_LEAN_VERSION"] + ", fixture, Release)",
                    "lake": "Lake version fixture (Lean version " + os.environ["QIKVRT_FIXTURE_LAKE_VERSION"] + ")",
                }.items():
                    path = target / tool
                    path.write_text("#!/bin/sh\\nprintf '%s\\\\n' '" + output + "'\\n")
                    path.chmod(0o755)
            ''')
        for name in ("curl", "tar"):
            path = stubs / name
            path.write_text(stub)
            path.chmod(0o755)
        github_path = root / "github-path"
        script = self.provisioning_script()
        result = subprocess.run(
            ["bash", "-c", script], cwd=root, capture_output=True, text=True,
            timeout=10, env={**os.environ, "PATH": str(stubs) + os.pathsep + os.environ["PATH"],
                             "RUNNER_TEMP": str(runtime), "GITHUB_PATH": str(github_path),
                             "LEAN_VERSION": "4.19.0", "LEAN_ARCHIVE_BYTES": "15",
                             "LEAN_ARCHIVE_SHA256": hashlib.sha256(b"release fixture").hexdigest(),
                             "QIKVRT_FIXTURE_LEAN_VERSION": cached or "4.19.0",
                             "QIKVRT_FIXTURE_LAKE_VERSION": lake_version,
                             "QIKVRT_FIXTURE_ROOT": str(root), "QIKVRT_FIXTURE_MODE": mode},
        )
        calls = [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()] \
            if (root / "calls.jsonl").exists() else []
        return result, calls, github_path, runtime

    def test_valid_cache_avoids_failed_elan_network_path(self):
        result, calls, path, _ = self.run_provisioning(cached="4.19.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call[0] for call in calls], ["tar"])
        self.assertIn("lean-4.19.0-linux/bin", path.read_text())

    def test_original_connection_reset_cannot_activate_partial_runtime(self):
        result, calls, path, runtime = self.run_provisioning()
        self.assertEqual(result.returncode, 56)
        self.assertFalse(path.exists())
        self.assertEqual(list(runtime.iterdir()), [])
        self.assertEqual(len(calls), 1)
        args = calls[0]
        for flag, value in (("--connect-timeout", "20"), ("--max-time", "180"),
                            ("--retry", "2"), ("--retry-max-time", "540")):
            self.assertEqual(args[args.index(flag) + 1], value)
        self.assertEqual(args[-1], "https://github.com/leanprover/lean4/releases/download/"
                         "v4.19.0/lean-4.19.0-linux.tar.zst")

    def test_short_archive_is_rejected_before_extraction(self):
        result, calls, path, runtime = self.run_provisioning(mode="short")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([call[0] for call in calls], ["curl"])
        self.assertFalse(path.exists())
        self.assertEqual(list(runtime.iterdir()), [])

    def test_failed_extraction_cleans_up_without_cache_publication(self):
        result, calls, path, runtime = self.run_provisioning(mode="extract-failure")
        self.assertEqual(result.returncode, 2)
        self.assertEqual([call[0] for call in calls], ["curl", "tar"])
        self.assertFalse(path.exists())
        self.assertEqual([p.name for p in runtime.iterdir()], ["qikvrt-lean"])

    def test_cold_fixture_is_verified_before_becoming_reusable(self):
        result, calls, path, runtime = self.run_provisioning(mode="valid")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call[0] for call in calls], ["curl", "tar"])
        self.assertTrue(path.exists())
        self.assertIn("--no-same-owner", calls[1])
        self.assertEqual(sorted(p.name for p in runtime.iterdir()),
                         ["lean-4.19.0-linux", "qikvrt-lean"])

    def test_wrong_cached_lean_and_lake_fail_without_redownload(self):
        for lean, lake in (("4.20.0", "4.19.0"), ("4.19.0", "4.20.0")):
            with self.subTest(lean=lean, lake=lake):
                result, calls, path, _ = self.run_provisioning(cached=lean, lake_version=lake)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual([call[0] for call in calls], ["tar"])
                self.assertFalse(path.exists())

    def test_same_size_corrupt_cache_is_rejected_before_execution(self):
        result, calls, path, _ = self.run_provisioning(cached="4.19.0", cache_bytes=b"x" * 15)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        self.assertFalse(path.exists())

    def test_broken_archive_symlink_is_rejected_without_redownload(self):
        result, calls, path, _ = self.run_provisioning(cached="4.19.0", broken_cache_symlink=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        self.assertFalse(path.exists())

    def test_changed_source_toolchain_is_not_satisfied_by_old_cache(self):
        result, calls, path, _ = self.run_provisioning(cached="4.19.0", source_version="4.20.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(calls, [])
        self.assertFalse(path.exists())

    def test_cache_has_exact_scope_and_proof_gates_remain_mandatory(self):
        text = WORKFLOW.read_text()
        self.assertNotIn("leanprover/lean-action@", text)
        self.assertIn("actions/cache/restore@55cc8345863c7cc4c66a329aec7e433d2d1c52a9", text)
        self.assertIn("runner.os", text)
        self.assertIn("runner.arch", text)
        self.assertIn("'formalization/QIKVRT_Formalization_v2.0/lean-toolchain')", text)
        self.assertNotIn("restore-keys:", text)
        self.assertNotIn("continue-on-error:", text)
        self.assertIn('LEAN_ARCHIVE_BYTES: "343842845"', text)
        self.assertIn('LEAN_ARCHIVE_SHA256: "6fe3ce97a58f44e2b3567d455b994eacec5bfe9ae7774f2a573444480ba813fe"', text)
        self.assertIn("hashFiles('runtime/toolchains/**',", text)
        self.assertIn("github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'", text)
        self.assertIn("          lake build\n", text)
        for gate in ("lake build QIKVRTUniversalOntology", "AxiomAudit.lean",
                     "ExtendedAxiomAudit.lean", "make_universal_ontology_kernel_receipt.py"):
            self.assertIn(gate, text)

    def test_provisioning_utilities_are_declared_in_the_existing_runtime(self):
        registry = json.loads((ROOT / "runtime/toolchains/CACHE_REGISTRY.json").read_text())
        locked = {line.split("\t", 1)[0] for line in
                  (ROOT / "runtime/toolchains/TOOLCHAIN.lock.tsv").read_text().splitlines()
                  if line and not line.startswith("#")}
        for name in ("bash", "curl", "tar", "zstd", "coreutils"):
            self.assertIn(name, locked)
            self.assertIn("formal", registry["components"][name]["profiles"])
            self.assertIn("tests/test_universal_ontology_claim_closure.py",
                          registry["components"][name]["authority_files"])


class UniversalOntologyClaimClosureTests(unittest.TestCase):
    def load(self, path: pathlib.Path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def audited_constants(path: pathlib.Path) -> set[str]:
        return {
            line.strip().removeprefix("#print axioms ")
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("#print axioms ")
        }

    def test_formal_claims_have_unique_kernel_constants(self):
        matrices = [self.load(MATRIX), self.load(WORLD)]
        formal = [
            claim
            for matrix in matrices
            for claim in matrix["claims"]
            if claim["kind"] == "FORMAL_THEOREM"
        ]
        constants = [claim["proof_constant"] for claim in formal]
        self.assertEqual(len(constants), 32)
        self.assertEqual(len(constants), len(set(constants)))
        self.assertEqual(set(constants), self.audited_constants(AUDIT))

    def test_extended_audit_separates_support_tranches_from_core_receipt(self):
        core = self.audited_constants(AUDIT)
        extended = self.audited_constants(EXTENDED_AUDIT)
        extra = extended - core
        self.assertEqual(len(core), 32)
        self.assertEqual(len(extended), 71)
        self.assertEqual(len(extra), 39)
        self.assertEqual(
            sum(name.startswith("QIKVRT.V2.QuantumFoundations.") for name in extra),
            9,
        )
        self.assertEqual(
            sum(name.startswith("QIKVRT.V2.HardwareWitness.") for name in extra),
            22,
        )
        self.assertEqual(
            sum(name.startswith("QIKVRT.V2.DecisionSufficiency.") for name in extra),
            8,
        )

    def test_nonformal_claims_are_not_proof_inflated(self):
        matrix = self.load(MATRIX)
        for claim in matrix["claims"]:
            if claim["kind"] != "FORMAL_THEOREM":
                self.assertNotIn("proof_constant", claim, claim["claim_id"])
        self.assertEqual(matrix["physical_correspondence"], "OPEN_CANDIDATE")
        self.assertEqual(
            matrix["completion_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )

    def test_lean_has_no_escape_hatches(self):
        for path in (CORE, AUDIT, EXTENDED_AUDIT):
            text = path.read_text(encoding="utf-8")
            code = "\n".join(
                line for line in text.splitlines()
                if not line.lstrip().startswith(("--", "/-", "*", "-/"))
            )
            self.assertIsNone(re.search(r"\b(?:sorry|admit|axiom)\b", code), path)

    def test_source_scope_binds_authority_baseline(self):
        scope = self.load(SCOPE)
        self.assertEqual(scope["schema"], "qikvrt_universal_ontology_source_scope_v2")
        self.assertEqual(scope["repository"], "Goldkelch/qik-vrt")
        self.assertEqual(scope["source_commit"], "df66a3d9ea7dee7889028cc5a93f0ac34424b4b2")
        resolution = scope["source_resolution"]
        self.assertEqual(
            resolution["canonical_remote"],
            "https://github.com/Goldkelch/qik-vrt.git",
        )
        self.assertEqual(resolution["fetch_policy"], "EXACT_COMMIT_IF_MISSING")
        self.assertEqual(
            resolution["permitted_execution_repositories"],
            {
                "Goldkelch/qik-vrt": {
                    "source_commit_must_be_ancestor": True,
                },
                "ingolf-lohmann/qik-vrt": {
                    "source_commit_must_be_ancestor": False,
                },
            },
        )
        paths = {item["path"] for item in scope["sources"]}
        self.assertIn("GLOBAL_CLAIM_INVENTORY.json", paths)
        self.assertIn("docs/publications/index.json", paths)
        self.assertIn(
            "external/ietf/draft-lohmann-qikvrt-effect-ack-03.PUBLICATION_RECEIPT.json",
            paths,
        )

    def test_standing_authorization_is_hard_gated(self):
        value = self.load(STANDING)
        self.assertEqual(value["schema"], "qikvrt-owner-delegation/1.0")
        self.assertEqual(value["authorizing_owner"], "Ingolf Lohmann")
        permissions = value["autonomous_permissions"]
        self.assertIs(permissions["test_and_ci_execution"], True)
        self.assertEqual(
            permissions["credentialed_zenodo_write"],
            "AUTHORIZED_IN_PRINCIPLE_BUT_REQUIRES_AVAILABLE_VALID_CREDENTIALS_AND_PRE_EFFECT_GATES",
        )
        joined = "\n".join(value["hard_fail_closed_gates"])
        self.assertIn("No physical correspondence", joined)
        self.assertIn("No admitted, sorry, axiom-smuggled", joined)
        self.assertEqual(
            value["mandatory_status_separation"]["scientific_consensus"],
            "NOT_CLAIMED",
        )

    def test_work_program_remains_continue_until_effect_evidence(self):
        value = self.load(WORK)
        self.assertEqual(value["effect_state"], "EFFECT_ACK_CONTINUE")
        states = {item["id"]: item["state"] for item in value["work_units"]}
        self.assertEqual(states["UOK2-04"], "PENDING_EXACT_HEAD_CI")
        self.assertEqual(states["UOK2-10"], "NO_PROTOCOL_CHANGE_REQUIRED")
        self.assertEqual(value["physical_correspondence"], "OPEN_CANDIDATE")

    def test_ietf_delta_does_not_mutate_protocol(self):
        value = self.load(IETF)
        self.assertEqual(value["active_internet_draft"], "draft-lohmann-qikvrt-effect-ack-03")
        self.assertEqual(value["disposition"], "NO_PROTOCOL_CHANGE_REQUIRED")
        for field in (
            "wire_version_changed", "record_fields_changed",
            "state_machine_changed", "done_predicate_changed",
            "normative_interoperability_change",
        ):
            self.assertIs(value[field], False)
        self.assertIs(value["submission_performed_for_this_delta"], False)

    def test_workflow_binds_exact_pr_head_and_emits_receipt(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.event.pull_request.head.sha", text)
        self.assertIn("lake build QIKVRTUniversalOntology", text)
        self.assertIn("QIKVRTUniversalOntology/ExtendedAxiomAudit.lean", text)
        self.assertIn("make_universal_ontology_kernel_receipt.py", text)
        self.assertIn("UNIVERSAL_ONTOLOGY_KERNEL_RECEIPT.json", text)
        self.assertIn("universal-ontology-extended-axioms.txt", text)


class UniversalOntologySourceProvenanceTests(unittest.TestCase):
    @staticmethod
    def git(repository: pathlib.Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repository,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stderr)
        return completed.stdout.strip()

    def init_repository(self, path: pathlib.Path, origin: str) -> None:
        path.mkdir()
        self.git(path, "init", "--initial-branch=main")
        self.git(path, "config", "user.name", "QIK-VRT test")
        self.git(path, "config", "user.email", "test@example.invalid")
        self.git(path, "remote", "add", "origin", origin)

    def source_fixture(self, root: pathlib.Path):
        source = root / "source"
        self.init_repository(source, "https://github.com/Goldkelch/qik-vrt.git")
        bound = source / "BOUND.txt"
        bound.write_text("authority source\n", encoding="utf-8")
        self.git(source, "add", "BOUND.txt")
        self.git(source, "commit", "-m", "authority source")
        commit = self.git(source, "rev-parse", "HEAD")
        tree = self.git(source, "rev-parse", "HEAD^{tree}")
        blob = self.git(source, "rev-parse", "HEAD:BOUND.txt")
        scope = {
            "schema": "qikvrt_universal_ontology_source_scope_v2",
            "repository": "Goldkelch/qik-vrt",
            "source_commit": commit,
            "source_tree": tree,
            "source_resolution": {
                "canonical_remote": "https://github.com/Goldkelch/qik-vrt.git",
                "fetch_policy": "EXACT_COMMIT_IF_MISSING",
                "permitted_execution_repositories": {
                    "Goldkelch/qik-vrt": {
                        "source_commit_must_be_ancestor": True,
                    },
                    "ingolf-lohmann/qik-vrt": {
                        "source_commit_must_be_ancestor": False,
                    },
                },
            },
            "sources": [{"path": "BOUND.txt", "git_blob_sha1": blob}],
        }
        return source, scope

    def test_mirror_fetches_and_verifies_exact_nonancestor_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source, scope = self.source_fixture(root)
            mirror = root / "mirror"
            self.init_repository(mirror, "https://github.com/ingolf-lohmann/qik-vrt.git")
            (mirror / "MIRROR.txt").write_text("mirror history\n", encoding="utf-8")
            self.git(mirror, "add", "MIRROR.txt")
            self.git(mirror, "commit", "-m", "mirror parent")

            fetches = []

            def fetch_from_fixture(destination, canonical_remote, source_commit):
                fetches.append((canonical_remote, source_commit))
                self.git(
                    destination,
                    "fetch", "--no-tags", "--depth=1", "--no-write-fetch-head",
                    str(source), source_commit,
                )

            with mock.patch.object(
                VERIFIER,
                "fetch_exact_source_commit",
                side_effect=fetch_from_fixture,
            ):
                VERIFIER.verify_source_bindings(
                    scope,
                    repository_root=mirror,
                    environment={"GITHUB_REPOSITORY": "ingolf-lohmann/qik-vrt"},
                )

            self.assertEqual(
                fetches,
                [("https://github.com/Goldkelch/qik-vrt.git", scope["source_commit"])],
            )

    def test_unlisted_execution_repository_is_blocked_before_fetch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, scope = self.source_fixture(root)
            execution = root / "unlisted"
            self.init_repository(execution, "https://github.com/example/qik-vrt.git")
            (execution / "UNLISTED.txt").write_text("unlisted\n", encoding="utf-8")
            self.git(execution, "add", "UNLISTED.txt")
            self.git(execution, "commit", "-m", "unlisted")

            with mock.patch.object(VERIFIER, "fetch_exact_source_commit") as fetch:
                with self.assertRaisesRegex(ValueError, "not permitted"):
                    VERIFIER.verify_source_bindings(
                        scope,
                        repository_root=execution,
                        environment={"GITHUB_REPOSITORY": "example/qik-vrt"},
                    )
                fetch.assert_not_called()

    def test_scope_cannot_redirect_fixed_source_or_execution_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            _, scope = self.source_fixture(root)
            mirror = root / "mirror"
            self.init_repository(mirror, "https://github.com/ingolf-lohmann/qik-vrt.git")
            (mirror / "MIRROR.txt").write_text("mirror history\n", encoding="utf-8")
            self.git(mirror, "add", "MIRROR.txt")
            self.git(mirror, "commit", "-m", "mirror parent")

            redirected = copy.deepcopy(scope)
            redirected["repository"] = "example/redirected"
            redirected["source_resolution"]["canonical_remote"] = (
                "https://github.com/example/redirected.git"
            )
            expanded = copy.deepcopy(scope)
            expanded["source_resolution"]["permitted_execution_repositories"][
                "example/qik-vrt"
            ] = {"source_commit_must_be_ancestor": False}
            numeric_boolean = copy.deepcopy(scope)
            numeric_boolean["source_resolution"]["permitted_execution_repositories"][
                "Goldkelch/qik-vrt"
            ]["source_commit_must_be_ancestor"] = 1

            for changed, message in (
                (redirected, "fixed Authority"),
                (expanded, "fixed pair"),
                (numeric_boolean, "fixed pair"),
            ):
                with self.subTest(message=message):
                    with mock.patch.object(VERIFIER, "fetch_exact_source_commit") as fetch:
                        with self.assertRaisesRegex(ValueError, message):
                            VERIFIER.verify_source_bindings(
                                changed,
                                repository_root=mirror,
                                environment={
                                    "GITHUB_REPOSITORY": "ingolf-lohmann/qik-vrt"
                                },
                            )
                        fetch.assert_not_called()

    def test_source_binding_has_no_skip_flag(self):
        self.assertNotIn(
            "--skip-git-source-bindings",
            VERIFIER_PATH.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
