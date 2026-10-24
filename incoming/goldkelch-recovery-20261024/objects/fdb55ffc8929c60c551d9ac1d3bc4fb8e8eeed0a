# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
import base64
import hashlib
import json
from pathlib import Path
import unittest

from tools import qikvrt_authority_url_probe as p

TOKEN = "fixture-credential-never-persist-123456"
HEAD = "a" * 40
TREE = "b" * 40
AI = b"QIK-VRT AI fixture\n"
BLOB = hashlib.sha1(f"blob {len(AI)}\0".encode() + AI).hexdigest()


class AuthorityURLProbeTests(unittest.TestCase):
    def transport(self, overrides=None):
        values = {
            f"/repos/{p.MIRROR}": (200, {"id": p.MIRROR_ID}),
            "/user": (200, {"id": p.OWNER_ID, "login": "Goldkelch"}),
            f"/repos/{p.AUTHORITY}": (200, {"id": p.AUTHORITY_ID, "full_name": p.AUTHORITY,
                "owner": {"id": p.OWNER_ID}, "visibility": "public", "permissions": {"pull": True}}),
            f"/repositories/{p.AUTHORITY_ID}": (200, {"id": p.AUTHORITY_ID,
                "full_name": p.AUTHORITY, "owner": {"id": p.OWNER_ID}}),
            f"/repos/{p.AUTHORITY}/commits/main": (200, {"sha": HEAD, "commit": {"tree": {"sha": TREE}}}),
            f"/repos/{p.AUTHORITY}/contents/AI?ref={HEAD}": (200, {
                "type": "file", "path": "AI", "size": len(AI), "sha": BLOB,
                "encoding": "base64", "content": base64.b64encode(AI).decode()}),
        }
        values.update(overrides or {})
        self.paths = []
        def read(path):
            p.AuthorityURLAPI._validate_path(path)
            self.paths.append(path)
            status, value = values[path]
            return status, {}, json.dumps(value).encode()
        return read

    def run_probe(self, **kwargs):
        return p.probe(TOKEN, "QIKVRT_GITHUB_ADMIN_TOKEN", {
            "repository": p.MIRROR, "head": "c" * 40, "tree": "d" * 40,
        }, public_reader=lambda url: (200, AI if url == p.RAW_URL else b"GitHub AI page"), **kwargs)

    def test_exact_source_and_public_bytes_are_both_required(self):
        result = self.run_probe(transport=self.transport())
        self.assertTrue(result["source_read_verified"])
        self.assertTrue(result["public_url_effect_verified"])
        self.assertEqual(result["authority_subject"]["AI_blob"], BLOB)
        self.assertEqual(result["mutation_count"], 0)
        self.assertFalse(result["effect_ack_done"])
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertNotIn(base64.b64encode(AI).decode(), json.dumps(result))

    def test_missing_credential_never_invokes_transport(self):
        def forbidden(_):
            self.fail("transport invoked without a delivered credential")
        result = p.probe("", None, {}, transport=forbidden)
        self.assertEqual(result["first_blocker"], "AUTHORITY_CREDENTIAL_NOT_DELIVERED")

    def test_existing_app_output_precedes_mirror_workflow_token(self):
        token, source, present = p.credential({"QIKVRT_AUTHORITY_APP_TOKEN": TOKEN, "GITHUB_TOKEN": "mirror-fixture"})
        self.assertEqual((token, source), (TOKEN, "QIKVRT_AUTHORITY_APP_TOKEN"))
        self.assertTrue(present["GITHUB_TOKEN"])

    def test_only_mirror_token_does_not_prove_authority_delivery(self):
        read = self.transport({f"/repos/{p.AUTHORITY}": (404, {}),
                              f"/repositories/{p.AUTHORITY_ID}": (404, {})})
        result = p.probe(TOKEN, "GITHUB_TOKEN", {}, transport=read)
        self.assertEqual(result["first_blocker"], "AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED")
        self.assertFalse(result["source_read_verified"])

    def test_404_with_named_credential_remains_cause_undetermined(self):
        result = self.run_probe(transport=self.transport({f"/repos/{p.AUTHORITY}": (404, {})}))
        self.assertEqual(result["first_blocker"], "AUTHORITY_READ_REJECTED_CAUSE_UNDETERMINED")
        self.assertNotIn("suspended", json.dumps(result))
        self.assertNotIn("deleted", json.dumps(result))

    def test_authority_only_credential_is_not_rejected_by_mirror_control(self):
        result = self.run_probe(transport=self.transport({f"/repos/{p.MIRROR}": (404, {})}))
        self.assertTrue(result["source_read_verified"])

    def test_wrong_repository_identity_stops_before_source_read(self):
        result = self.run_probe(transport=self.transport({f"/repositories/{p.AUTHORITY_ID}": (200, {
            "id": 123, "full_name": p.AUTHORITY, "owner": {"id": p.OWNER_ID}})}))
        self.assertEqual(result["first_blocker"], "AUTHORITY_IDENTITY_MISMATCH")
        self.assertFalse(any("contents/" in path for path in self.paths))

    def test_exact_AI_blob_mismatch_is_rejected(self):
        result = self.run_probe(transport=self.transport({f"/repos/{p.AUTHORITY}/contents/AI?ref={HEAD}": (200, {
            "type": "file", "path": "AI", "size": len(AI), "sha": "0" * 40,
            "encoding": "base64", "content": base64.b64encode(AI).decode()})}))
        self.assertEqual(result["first_blocker"], "EXACT_AUTHORITY_AI_BINDING_MISMATCH")

    def test_response_containing_bearer_is_never_persisted(self):
        with self.assertRaisesRegex(ValueError, "credential material"):
            self.run_probe(transport=self.transport({"/user": (200, {"login": TOKEN})}))

    def test_main_movement_invalidates_public_readback(self):
        read = self.transport()
        calls = 0
        def moving(path):
            nonlocal calls
            result = read(path)
            if path.endswith("/commits/main"):
                calls += 1
                if calls == 2:
                    return 200, {}, json.dumps({"sha": "e" * 40}).encode()
            return result
        result = self.run_probe(transport=moving)
        self.assertEqual(result["first_blocker"], "AUTHORITY_MAIN_CHANGED_DURING_PROBE")
        self.assertFalse(result["public_url_effect_verified"])

    def test_scope_escape_and_write_are_rejected(self):
        for path in ["https://evil.example/repos/Goldkelch/qik-vrt", "/repos/other/repo",
                     f"/repos/{p.AUTHORITY}/contents/AI?ref=main", "/user?token=value"]:
            with self.assertRaises(ValueError):
                p.AuthorityURLAPI._validate_path(path)
        api = p.AuthorityURLAPI(TOKEN)
        with self.assertRaises(SystemExit):
            api.request("POST", f"/repos/{p.AUTHORITY}", payload={})

    def test_rate_limit_status_is_read_once_without_sleep(self):
        read = self.transport({f"/repos/{p.AUTHORITY}": (403, {})})
        result = self.run_probe(transport=read)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(self.paths.count(f"/repos/{p.AUTHORITY}"), 1)

    def test_workflow_separates_probe_from_admission_and_keeps_read_permissions(self):
        source = (Path(__file__).resolve().parents[1] / p.WORKFLOW).read_text()
        probe, admit = source.split("  authority-url-probe:", 1)[1].split("  admit:", 1)
        self.assertIn("contents: read", source)
        self.assertIn("persist-credentials: false", probe)
        self.assertIn("github.repository == 'ingolf-lohmann/qik-vrt'", probe)
        self.assertIn("inputs.operation == 'authority_url_probe'", probe)
        self.assertIn("github.event_name != 'push'", admit)
        self.assertIn("inputs.operation == 'admit'", admit)
        self.assertNotIn("/approve", probe)
        self.assertNotIn("permission-administration", probe)
        self.assertIn("owner: Goldkelch", probe)
        self.assertIn("repositories: qik-vrt", probe)
        self.assertIn("permission-contents: read", probe)
        self.assertLess(probe.index("Verify probe boundaries"), probe.index("RULESET_ADMIN_TOKEN:"))


if __name__ == "__main__":
    unittest.main()
