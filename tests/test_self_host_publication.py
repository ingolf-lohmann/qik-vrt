# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Bounded adapter tests; no production credentials or Zenodo effects."""
import contextlib
import datetime
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from tools import qikvrt_self_host as host
from tools import qikvrt_zenodo_publish as publisher


class PublicationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.base.chmod(0o700)
        self.root = self.base / "checkout"
        self.root.mkdir()
        (self.root / "tools").mkdir()
        for name in ("qikvrt_zenodo_publish.py", "qikvrt_zenodo_actions.py", "qikvrt_zenodo_machine_proof.py"):
            (self.root / "tools" / name).write_bytes((host.ROOT / "tools" / name).read_bytes())
        for command in (["init", "-q"], ["config", "user.name", "Fixture"],
                        ["config", "user.email", "fixture@example.invalid"],
                        ["remote", "add", "origin", "https://github.com/Goldkelch/qik-vrt.git"],
                        ["add", "."], ["commit", "-qm", "fixture"]):
            subprocess.run(["git", "-C", str(self.root), *command], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.head = host.git(self.root, "rev-parse", "HEAD").decode()
        self.tree = host.git(self.root, "rev-parse", "HEAD^{tree}").decode()
        self.manifest_path = self.root / "request.json"
        self.manifest_path.write_text("{}")
        self.registry_path = self.base / "credential-references.json"
        self.registry = {"schema": "qikvrt-protected-runtime-credential-references/v1", "credentials": {}}
        expiry = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()
        for name, origin in (("GITHUB_TOKEN", "https://github.com"),
                             ("ZENODO_ACCESS_TOKEN", "https://zenodo.org")):
            secret = self.base / (name + ".private")
            self.write(secret, (name + "_FAKE_CREDENTIAL_ONLY").encode())
            self.registry["credentials"][name] = {"origin": origin, "principal": "fixture-owner",
                "opaque_reference": "facility/" + name, "source_path": str(secret), "scopes": ["declared-publisher-scope"], "expires_at": expiry}
        self.write(self.registry_path, host.raw_json(self.registry))
        self.request_path = self.base / "publication.json"
        self.request = {"schema": "qikvrt-publication-runtime-request/v1", "repository": "Goldkelch/qik-vrt",
            "checkout": str(self.root), "execution_head": self.head, "execution_tree": self.tree,
            "manifest": "request.json", "manifest_sha256": host.digest(self.manifest_path.read_bytes()),
            "publisher_sha256": host.digest((host.ROOT / "tools/qikvrt_zenodo_publish.py").read_bytes()),
            "launcher_sha256": host.digest(Path(host.__file__).read_bytes()),
            "python_sha256": host.digest(Path(sys.executable).resolve().read_bytes()),
            "credential_registry": str(self.registry_path)}
        self.pin = self.save_request()
        self.manifest = {"schema": publisher.SCHEMA_V2, "repository": "Goldkelch/qik-vrt",
            "machine_proof": {"fixture": True}, "owner_authorization": {"fixture": True},
            "evidence_path": self.root / "receipt.json"}
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        self.load = stack.enter_context(mock.patch.object(publisher, "load_manifest", return_value=self.manifest))
        self.source = stack.enter_context(mock.patch.object(publisher, "_validate_repository_source_head", return_value=self.head))

    def write(self, path, raw):
        path.write_bytes(raw)
        path.chmod(0o600)

    def save_request(self):
        raw = host.raw_json(self.request)
        self.write(self.request_path, raw)
        return host.digest(raw)

    def test_admission_has_no_network_effect_and_restores_platform_environment(self):
        with mock.patch.dict(os.environ, {"GITHUB_SHA": "unrelated", "GITHUB_REPOSITORY": "unrelated"}), \
                mock.patch.object(publisher.zenodo, "ZenodoClient") as client:
            admitted = host.publication_request(self.request_path, self.pin)
            self.assertEqual(admitted[0], self.request)
            self.assertEqual(os.environ["GITHUB_SHA"], "unrelated")
            self.assertEqual(os.environ["GITHUB_REPOSITORY"], "unrelated")
            client.assert_not_called()

    def test_mirror_cannot_replace_pinned_authority(self):
        self.request["repository"] = "ingolf-lohmann/qik-vrt"
        with self.assertRaisesRegex(ValueError, "PINNED_PUBLICATION_AUTHORITY"):
            host.publication_request(self.request_path, self.save_request())

    def test_actual_mirror_origin_is_refused_even_with_authority_request(self):
        subprocess.run(["git", "-C", str(self.root), "remote", "set-url", "origin",
                        "https://github.com/ingolf-lohmann/qik-vrt.git"], check=True)
        with self.assertRaises(publisher.zenodo.ZenodoError):
            host.publication_request(self.request_path, self.pin)

    def test_request_pin_and_execution_drift_refused(self):
        with self.assertRaisesRegex(ValueError, "PIN_MISMATCH"):
            host.publication_request(self.request_path, "0" * 64)
        self.request["execution_tree"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "SUBJECT_DRIFT"):
            host.publication_request(self.request_path, self.save_request())

    def test_publisher_and_manifest_drift_refused(self):
        (self.root / "tools/qikvrt_zenodo_publish.py").write_text("changed")
        with self.assertRaisesRegex(ValueError, "PUBLISHER_DRIFT"):
            host.publication_request(self.request_path, self.pin)
        (self.root / "tools/qikvrt_zenodo_publish.py").write_bytes(
            (host.ROOT / "tools/qikvrt_zenodo_publish.py").read_bytes())
        self.manifest_path.write_text("changed")
        with self.assertRaisesRegex(ValueError, "MANIFEST_DRIFT"):
            host.publication_request(self.request_path, self.pin)

    def test_legacy_or_missing_machine_controls_are_refused(self):
        self.manifest["schema"] = publisher.SCHEMA
        with self.assertRaisesRegex(ValueError, "V2_PUBLICATION_CONTROLS"):
            host.publication_request(self.request_path, self.pin)
        self.source.assert_not_called()

    def test_publisher_dependency_drift_is_refused_before_machine_admission(self):
        dependency = self.root / "tools/qikvrt_zenodo_actions.py"
        dependency.write_bytes(dependency.read_bytes() + b"\n# changed\n")
        with self.assertRaisesRegex(ValueError, "DEPENDENCY_DRIFT"):
            host.publication_request(self.request_path, self.pin)
        self.load.assert_not_called()

    def test_oversized_private_input_is_refused_before_dispatch(self):
        self.write(self.registry_path, b" " * 65537)
        with self.assertRaisesRegex(ValueError, "INPUT_TOO_LARGE"):
            host.publication_request(self.request_path, self.pin)

    def test_actual_secret_cannot_be_used_as_reference_metadata(self):
        self.registry["credentials"]["GITHUB_TOKEN"]["principal"] = "GITHUB_TOKEN_FAKE_CREDENTIAL_ONLY"
        self.write(self.registry_path, host.raw_json(self.registry))
        with mock.patch.object(host, "publication_invoke") as run:
            with self.assertRaisesRegex(ValueError, "VALUE_IN_REFERENCE_METADATA"):
                host.publication_resume(self.request_path, self.pin)
            run.assert_not_called()
        self.assertFalse(self.registry_path.with_name(self.registry_path.name + ".interactions.json").exists())

    def test_cli_refusal_is_sanitized_and_nonzero(self):
        child = subprocess.run([sys.executable, "-B", str(host.ROOT / "tools/qikvrt_self_host.py"),
            "publication-resume", "--publication-request", str(self.request_path),
            "--publication-request-sha256", "0" * 64], capture_output=True, text=True)
        self.assertEqual(child.returncode, 2)
        self.assertEqual(json.loads(child.stdout),
            {"state": "HOLD", "cause": "PUBLICATION_GATE_REFUSED", "effect_ack_done": False})
        self.assertNotIn(str(self.base), child.stdout + child.stderr)

    def test_expiry_wrong_provider_plaintext_and_unsafe_permissions_refused(self):
        for key, value in (("expires_at", "2000-01-01T00:00:00Z"), ("origin", "https://example.invalid"),
                           ("token", "UNACCEPTABLE_INLINE_CREDENTIAL")):
            changed = json.loads(json.dumps(self.registry))
            changed["credentials"]["GITHUB_TOKEN"][key] = value
            self.write(self.registry_path, host.raw_json(changed))
            with self.assertRaises(ValueError):
                host.publication_request(self.request_path, self.pin)
        self.write(self.registry_path, host.raw_json(self.registry))
        self.registry_path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "OWNER_ONLY"):
            host.publication_request(self.request_path, self.pin)

    def test_secret_symlink_refused(self):
        source = Path(self.registry["credentials"]["GITHUB_TOKEN"]["source_path"])
        target = self.base / "elsewhere"
        source.rename(target)
        source.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "NOT_SYMLINKED"):
            host.publication_request(self.request_path, self.pin)

    def test_existing_lock_prevents_dispatch(self):
        path = self.request_path.with_name(self.request_path.name + ".lock")
        self.write(path, b"")
        with path.open("rb") as lock, mock.patch.object(host, "publication_invoke") as run:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                host.publication_resume(self.request_path, self.pin)
            run.assert_not_called()

    def test_publisher_failure_and_ambiguous_timeout_never_mark_done_or_retry(self):
        for response in (subprocess.CompletedProcess([], 2), subprocess.TimeoutExpired([], 3600)):
            patch = {"side_effect": response} if isinstance(response, Exception) else {"return_value": response}
            with mock.patch.object(host, "publication_invoke", **patch) as run:
                result = host.publication_resume(self.request_path, self.pin)
                self.assertFalse(result["effect_ack_done"])
                self.assertTrue(result["state"].startswith("HOLD"))
                self.assertEqual(run.call_count, 1)

    def test_only_publisher_receipt_can_confirm_publication_and_no_secret_is_journaled(self):
        self.write(self.manifest["evidence_path"], b"{}")
        evidence = {"state": "published", "phase": "public_verified", "doi": "10.5281/zenodo.123",
                    "record_url": "https://zenodo.org/records/123"}
        seen = {}
        def invoke(root, request, env):
            seen["env"] = env
            self.assertEqual(request["manifest"], "request.json")
            self.assertEqual(env["GITHUB_TOKEN"], "GITHUB_TOKEN_FAKE_CREDENTIAL_ONLY")
            self.assertNotIn("PYTHONPATH", env)
            return subprocess.CompletedProcess([], 0)
        with mock.patch.object(host, "publication_invoke", side_effect=invoke), \
                mock.patch.object(publisher, "_validate_recovery_evidence", return_value=evidence):
            result = host.publication_resume(self.request_path, self.pin)
        self.assertEqual(result["state"], "PUBLICATION_SCOPE_VERIFIED")
        self.assertFalse(result["effect_ack_done"])
        self.assertFalse(result["all_nodes_persisted"])
        self.assertNotIn("GITHUB_TOKEN", seen["env"])
        journal = self.registry_path.with_name(self.registry_path.name + ".interactions.json").read_text()
        self.assertNotIn("FAKE_CREDENTIAL_ONLY", journal)
        self.assertIn("AUTHENTICATED_PUBLICATION_PUBLIC_READBACK_VERIFIED", journal)
        with mock.patch.object(host, "publication_invoke", return_value=subprocess.CompletedProcess([], 0)), \
                mock.patch.object(publisher, "_validate_recovery_evidence", side_effect=publisher.zenodo.ZenodoError("forged")):
            with self.assertRaises(publisher.zenodo.ZenodoError):
                host.publication_resume(self.request_path, self.pin)

    def test_event_adapter_has_no_polling_or_restart_loop_or_journal_self_trigger(self):
        plan = host.publication_supervisor(self.request_path, self.pin, "qikvrt-publication.service")
        self.assertIn("Type=oneshot", plan["unit_text"])
        self.assertIn("Restart=no", plan["unit_text"])
        self.assertIn("WantedBy=multi-user.target", plan["unit_text"])
        self.assertNotIn("interactions.json", plan["path_unit_text"])
        self.assertIn("PathChanged=" + str(self.registry_path), plan["path_unit_text"])
        self.assertNotIn("OnCalendar", plan["path_unit_text"])
        self.assertFalse(plan["supervisor_installed"])
        self.assertFalse(plan["effect_ack_done"])
        directory = self.base / "prepared-supervisor"
        receipt = host.materialize_supervisor(plan, directory)
        self.assertEqual(receipt["state"], "PREPARED_NOT_INSTALLED")
        for name, expected in ((plan["unit_name"], plan["unit_sha256"]),
                               (plan["path_unit_name"], plan["path_unit_sha256"])):
            path = directory / name
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(host.digest(path.read_bytes()), expected)
        self.assertFalse(json.loads((directory / "BINDING.json").read_bytes())["supervisor_installed"])
        with self.assertRaises(FileExistsError):
            host.materialize_supervisor(plan, directory)


if __name__ == "__main__":
    unittest.main()
