# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import sys

from tools import qikvrt_authority_url_probe as p

TOKEN = "fixture-credential-never-persist-123456"
HEAD = "a" * 40
AI = b"QIK-VRT AI fixture\n"
BINARY = b"\x00\xff\xfe\x80\r\n\x00"


def blob(raw):
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


BLOB = blob(AI)
BIN_BLOB = blob(BINARY)
TREE_RAW = (b"100644 AI\0" + bytes.fromhex(BLOB)
            + b"100755 binary.bin\0" + bytes.fromhex(BIN_BLOB))
TREE = hashlib.sha1(f"tree {len(TREE_RAW)}\0".encode() + TREE_RAW).hexdigest()
BINDING = {
    "kind": "EXISTING_APP_ACTION_OUTPUT", "action": p.APP_ACTION,
    "installation_id": 123456, "repository": p.AUTHORITY,
    "repository_id": p.AUTHORITY_ID, "owner_id": p.OWNER_ID,
    "requested_permissions": {"contents": "read"},
}
REPOSITORY = {"id": p.AUTHORITY_ID, "full_name": p.AUTHORITY,
              "owner": {"id": p.OWNER_ID}}
REF = {"ref": "refs/heads/main", "object": {"type": "commit", "sha": HEAD}}
INVENTORY = {
    "sha": TREE, "truncated": False,
    "tree": [
        {"path": "AI", "type": "blob", "mode": "100644", "sha": BLOB},
        {"path": "binary.bin", "type": "blob", "mode": "100755", "sha": BIN_BLOB},
    ],
}


def blob_response(raw):
    return {"sha": blob(raw), "size": len(raw), "encoding": "base64",
            "content": base64.b64encode(raw).decode()}


class AuthorityURLProbeTests(unittest.TestCase):
    def transport(self, overrides=None):
        values = {
            "/installation/repositories?per_page=100":
                (200, {"total_count": 1, "repositories": [REPOSITORY]}),
            f"/repos/{p.AUTHORITY}": (200, REPOSITORY),
            f"/repositories/{p.AUTHORITY_ID}": (200, REPOSITORY),
            f"/repos/{p.AUTHORITY}/git/ref/heads/main": (200, REF),
            f"/repos/{p.AUTHORITY}/git/matching-refs/": (200, [REF]),
            f"/repos/{p.AUTHORITY}/git/commits/{HEAD}":
                (200, {"sha": HEAD, "tree": {"sha": TREE}, "parents": []}),
            f"/repos/{p.AUTHORITY}/git/trees/{TREE}?recursive=1": (200, INVENTORY),
            f"/repos/{p.AUTHORITY}/git/blobs/{BLOB}": (200, blob_response(AI)),
            f"/repos/{p.AUTHORITY}/git/blobs/{BIN_BLOB}": (200, blob_response(BINARY)),
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
        kwargs.setdefault("binding", copy.deepcopy(BINDING))
        kwargs.setdefault("public_reader", lambda url: (
            200, AI if url == p.RAW_URL else b"GitHub AI page"))
        return p.probe(TOKEN, "QIKVRT_AUTHORITY_APP_TOKEN", {
            "repository": p.MIRROR, "head": "c" * 40, "tree": "d" * 40,
        }, **kwargs)

    def test_source_closure_reads_binary_bytes_and_reconstructs_tree_modes(self):
        result = self.run_probe(transport=self.transport())
        self.assertTrue(result["git_object_closure_verified"])
        self.assertTrue(result["public_url_effect_verified"])
        self.assertEqual(result["authority_subject"]["AI_blob"], BLOB)
        self.assertEqual(result["blob_proofs"][BIN_BLOB]["sha256"],
                         hashlib.sha256(BINARY).hexdigest())
        self.assertFalse(result["latest_complete_authority_closure_verified"])
        self.assertFalse(result["effect_ack_done"])
        self.assertEqual(result["mutation_count"], 0)
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertNotIn(base64.b64encode(BINARY).decode(), json.dumps(result))

    def test_missing_delivery_has_zero_network_calls_and_one_resume_pointer(self):
        def forbidden(_):
            self.fail("transport invoked without a delivered Authority credential")
        result = p.probe("", None, {}, transport=forbidden)
        self.assertEqual(result["first_blocker"], "AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED")
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["resume_pointer"], p.RESUME_PATH + "#/source_closure_resume")

    def test_only_app_output_is_selected_from_existing_inputs(self):
        env = {name: TOKEN for name in p.CREDENTIALS}
        self.assertEqual(p.credential(env)[:2], (TOKEN, "QIKVRT_AUTHORITY_APP_TOKEN"))
        del env["QIKVRT_AUTHORITY_APP_TOKEN"]
        self.assertEqual(p.credential(env)[:2], ("", None))

    def test_unbound_credentials_stop_before_any_authority_request(self):
        for binding in [None, {}, dict(BINDING, installation_id=0),
                        dict(BINDING, installation_id=True),
                        dict(BINDING, repository=p.MIRROR),
                        dict(BINDING, requested_permissions={"contents": "write"})]:
            result = self.run_probe(binding=binding, transport=lambda _: self.fail("unbound GET"))
            self.assertEqual(result["first_blocker"], "AUTHORITY_INSTALLATION_BINDING_NOT_VERIFIED")
        result = p.probe(TOKEN, "GITHUB_TOKEN", {}, binding=BINDING,
                         transport=lambda _: self.fail("Mirror credential GET"))
        self.assertEqual(result["first_blocker"], "AUTHORITY_INSTALLATION_BINDING_NOT_VERIFIED")

    def test_actual_app_installation_is_not_equated_with_connector_installation(self):
        env = {"QIKVRT_APP_TOKEN_ISSUANCE_OUTCOME": "success",
               "QIKVRT_AUTHORITY_APP_INSTALLATION_ID": "123456"}
        self.assertEqual(p.app_binding(env)["installation_id"], 123456)
        self.assertNotEqual(123456, p.CONNECTION_INSTALLATION_ID)
        for changed in [{}, dict(env, QIKVRT_APP_TOKEN_ISSUANCE_OUTCOME="failure"),
                        dict(env, QIKVRT_AUTHORITY_APP_INSTALLATION_ID=""),
                        dict(env, QIKVRT_AUTHORITY_APP_INSTALLATION_ID="1\n2")]:
            self.assertIsNone(p.app_binding(changed))

    def test_installation_token_is_scoped_to_exactly_the_fixed_repository(self):
        for value in [
            {"total_count": 2, "repositories": [REPOSITORY, REPOSITORY]},
            {"total_count": 1, "repositories": [dict(REPOSITORY, id=123)]},
            {"total_count": 1, "repositories": [dict(REPOSITORY, owner={"id": 123})]},
        ]:
            result = self.run_probe(transport=self.transport({
                "/installation/repositories?per_page=100": (200, value)}))
            self.assertEqual(result["first_blocker"], "AUTHORITY_INSTALLATION_TARGET_SCOPE_MISMATCH")
            self.assertEqual(len(self.paths), 1)

    def test_wrong_repository_identity_stops_before_ref_read(self):
        result = self.run_probe(transport=self.transport({
            f"/repositories/{p.AUTHORITY_ID}": (200, dict(REPOSITORY, id=123))}))
        self.assertEqual(result["first_blocker"], "AUTHORITY_IDENTITY_MISMATCH")
        self.assertFalse(any("/git/" in path for path in self.paths))

    def test_404_with_attested_credential_is_cause_undetermined_and_not_retried(self):
        result = self.run_probe(transport=self.transport({f"/repos/{p.AUTHORITY}": (404, {})}))
        self.assertEqual(result["first_blocker"], "AUTHORITY_READ_REJECTED_CAUSE_UNDETERMINED")
        self.assertEqual(self.paths.count(f"/repos/{p.AUTHORITY}"), 1)
        self.assertNotIn("suspended", json.dumps(result))
        self.assertNotIn("deleted", json.dumps(result))

    def test_wrong_ref_head_or_commit_tree_does_not_close_source(self):
        for path, value in [
            (f"/repos/{p.AUTHORITY}/git/ref/heads/main", dict(REF, ref="refs/heads/other")),
            (f"/repos/{p.AUTHORITY}/git/commits/{HEAD}",
             {"sha": "0" * 40, "tree": {"sha": TREE}, "parents": []}),
        ]:
            result = self.run_probe(transport=self.transport({path: (200, value)}))
            self.assertFalse(result["git_object_closure_verified"])
            self.assertEqual(result["state"], "BLOCK")

    def test_truncated_tree_mode_changes_and_missing_entries_fail_closed(self):
        changed_mode = copy.deepcopy(INVENTORY)
        changed_mode["tree"][1]["mode"] = "100644"
        missing = copy.deepcopy(INVENTORY)
        missing["tree"].pop()
        for inventory in [dict(INVENTORY, truncated=True), changed_mode, missing]:
            result = self.run_probe(transport=self.transport({
                f"/repos/{p.AUTHORITY}/git/trees/{TREE}?recursive=1": (200, inventory)}))
            self.assertEqual(result["first_blocker"], "AUTHORITY_TREE_CLOSURE_NOT_VERIFIED")

    def test_symlinks_and_gitlinks_require_their_separate_closure(self):
        for mode, kind in [("120000", "blob"), ("160000", "commit")]:
            inventory = copy.deepcopy(INVENTORY)
            inventory["tree"][1].update(mode=mode, type=kind)
            result = self.run_probe(transport=self.transport({
                f"/repos/{p.AUTHORITY}/git/trees/{TREE}?recursive=1": (200, inventory)}))
            self.assertEqual(result["first_blocker"], "AUTHORITY_TREE_CLOSURE_NOT_VERIFIED")

    def test_altered_or_invalid_binary_blob_is_rejected(self):
        for value in [
            dict(blob_response(BINARY), content=base64.b64encode(b"altered").decode()),
            dict(blob_response(BINARY), size=0),
            dict(blob_response(BINARY), content="!invalid!"),
        ]:
            result = self.run_probe(transport=self.transport({
                f"/repos/{p.AUTHORITY}/git/blobs/{BIN_BLOB}": (200, value)}))
            self.assertEqual(result["state"], "BLOCK")
            self.assertFalse(result["git_object_closure_verified"])

    def test_parent_commit_and_annotated_tag_objects_are_read(self):
        parent, tag = "e" * 40, "f" * 40
        tag_ref = {"ref": "refs/tags/v1", "object": {"type": "tag", "sha": tag}}
        result = self.run_probe(transport=self.transport({
            f"/repos/{p.AUTHORITY}/git/matching-refs/": (200, [REF, tag_ref]),
            f"/repos/{p.AUTHORITY}/git/commits/{HEAD}":
                (200, {"sha": HEAD, "tree": {"sha": TREE}, "parents": [{"sha": parent}]}),
            f"/repos/{p.AUTHORITY}/git/commits/{parent}":
                (200, {"sha": parent, "tree": {"sha": TREE}, "parents": []}),
            f"/repos/{p.AUTHORITY}/git/tags/{tag}":
                (200, {"sha": tag, "object": {"type": "commit", "sha": parent}}),
        }))
        self.assertTrue(result["git_object_closure_verified"])
        self.assertIn(f"/repos/{p.AUTHORITY}/git/tags/{tag}", self.paths)
        self.assertIn(f"/repos/{p.AUTHORITY}/git/commits/{parent}", self.paths)
        self.assertEqual(self.paths.count(f"/repos/{p.AUTHORITY}/git/blobs/{BIN_BLOB}"), 1)

    def test_object_read_budget_is_a_finite_fail_closed_boundary(self):
        result = self.run_probe(transport=self.transport(), object_budget=1)
        self.assertEqual(result["first_blocker"], "AUTHORITY_SOURCE_OBJECT_READ_BUDGET_REACHED")

    def test_partial_collection_is_not_a_complete_ref_inventory(self):
        read = self.transport()
        def paginated(path):
            status, headers, raw = read(path)
            if path.endswith("/git/matching-refs/"):
                headers = {"link": '<https://api.github.com/next>; rel="next"'}
            return status, headers, raw
        result = self.run_probe(transport=paginated)
        self.assertEqual(result["first_blocker"], "AUTHORITY_COLLECTION_PAGINATION_UNCLOSED")
        self.assertFalse(any("/git/blobs/" in v for v in self.paths))

    def test_LFS_pointer_is_not_treated_as_its_payload(self):
        pointer = b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"0" * 64 + b"\nsize 100\n"
        oid = blob(pointer)
        tree_raw = b"100644 AI\0" + bytes.fromhex(oid)
        tree = hashlib.sha1(f"tree {len(tree_raw)}\0".encode() + tree_raw).hexdigest()
        result = self.run_probe(transport=self.transport({
            f"/repos/{p.AUTHORITY}/git/commits/{HEAD}":
                (200, {"sha": HEAD, "tree": {"sha": tree}, "parents": []}),
            f"/repos/{p.AUTHORITY}/git/trees/{tree}?recursive=1":
                (200, {"sha": tree, "truncated": False, "tree": [
                    {"path": "AI", "mode": "100644", "type": "blob", "sha": oid}]}),
            f"/repos/{p.AUTHORITY}/git/blobs/{oid}": (200, blob_response(pointer)),
        }))
        self.assertEqual(result["first_blocker"], "AUTHORITY_LFS_PAYLOAD_CLOSURE_UNVERIFIED")
        self.assertFalse(result["git_object_closure_verified"])

    def test_main_movement_invalidates_source_closure(self):
        read = self.transport()
        calls = 0
        def moving(path):
            nonlocal calls
            result = read(path)
            if path.endswith("/git/ref/heads/main"):
                calls += 1
                if calls == 2:
                    value = copy.deepcopy(REF)
                    value["object"]["sha"] = "e" * 40
                    return 200, {}, json.dumps(value).encode()
            return result
        result = self.run_probe(transport=moving)
        self.assertEqual(result["first_blocker"], "AUTHORITY_REFS_CHANGED_DURING_PROBE")
        self.assertFalse(result["git_object_closure_verified"])

    def test_other_ref_movement_invalidates_source_closure(self):
        read = self.transport()
        calls = 0
        def moving(path):
            nonlocal calls
            result = read(path)
            if path.endswith("/git/matching-refs/"):
                calls += 1
                if calls == 2:
                    return 200, {}, json.dumps([REF, {
                        "ref": "refs/heads/new", "object": {"type": "commit", "sha": "e" * 40}
                    }]).encode()
            return result
        result = self.run_probe(transport=moving)
        self.assertEqual(result["first_blocker"], "AUTHORITY_REFS_CHANGED_DURING_PROBE")

    def test_public_404_does_not_erase_independent_git_source_verification(self):
        result = self.run_probe(transport=self.transport(), public_reader=lambda _: (404, b"Not Found"))
        self.assertTrue(result["git_object_closure_verified"])
        self.assertFalse(result["public_url_effect_verified"])
        self.assertEqual(result["public_url_first_blocker"], "PUBLIC_QR_URL_EFFECT_NOT_VERIFIED")

    def test_credential_material_is_never_persisted(self):
        with self.assertRaisesRegex(ValueError, "credential material"):
            self.run_probe(transport=self.transport({f"/repos/{p.AUTHORITY}":
                (200, dict(REPOSITORY, secret=TOKEN))}))

    def test_scope_escape_write_redirect_and_rate_limit_are_rejected_without_retry(self):
        for path in ["https://evil.example/", "/user", f"/repos/{p.MIRROR}",
                     f"/repos/{p.AUTHORITY}/git/commits/main",
                     "/installation/repositories?per_page=100&page=2"]:
            with self.assertRaises(ValueError):
                p.AuthorityURLAPI._validate_path(path)
        with self.assertRaises(SystemExit):
            p.AuthorityURLAPI(TOKEN).request("POST", f"/repos/{p.AUTHORITY}", payload={})
        for status in [301, 302, 403, 429]:
            with patch("time.sleep", side_effect=AssertionError("automatic retry")):
                result = self.run_probe(transport=self.transport({f"/repos/{p.AUTHORITY}": (status, {})}))
            self.assertEqual(result["state"], "BLOCK")
            self.assertEqual(self.paths.count(f"/repos/{p.AUTHORITY}"), 1)

    def test_response_byte_bound_covers_injected_transport(self):
        result = self.run_probe(transport=lambda _: (200, {}, b"x" * (p.MAX_RESPONSE + 1)))
        self.assertEqual(result["first_blocker"], "AUTHORITY_RESPONSE_BYTE_BOUND_EXCEEDED")

    def test_pure_tree_reader_imports_without_Unix_lock_and_mutation_fails_closed(self):
        code = """
import builtins, json, pathlib, sys, tempfile
original = builtins.__import__
def without_fcntl(name, *args, **kwargs):
    if name == "fcntl":
        raise ModuleNotFoundError("fixture: fcntl unavailable")
    return original(name, *args, **kwargs)
builtins.__import__ = without_fcntl
from tools import qikvrt_integrity as integrity
inventory = json.loads(sys.stdin.read())
assert integrity.fcntl is None
assert integrity.verify_recursive_git_tree(inventory, inventory["sha"])["complete_content_addressed_inventory"]
with tempfile.TemporaryDirectory() as directory:
    root = pathlib.Path(directory)
    try:
        with integrity._exclusive_integrity_lock(root):
            raise AssertionError("unlocked snapshot accepted")
    except RuntimeError as error:
        assert "lock is unavailable" in str(error)
    else:
        raise AssertionError("missing lock did not block snapshot mutation")
    assert not (root / integrity.LOCK_NAME).exists()
"""
        subprocess.run([sys.executable, "-B", "-c", code], cwd=p.ROOT,
                       input=json.dumps(INVENTORY), text=True, check=True,
                       capture_output=True, timeout=15)

    def test_resume_target_drift_is_rejected_without_consuming_credentials(self):
        value = json.loads((p.ROOT / p.RESUME_PATH).read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / p.RESUME_PATH
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(value))
            self.assertEqual(p.load_resume(root)["carrier_id"], p.CARRIER_ID)
            value["source_closure_resume"]["target"]["repository_id"] = 1
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                p.load_resume(root)

    def test_workflow_has_one_source_carrier_and_keeps_admission_separate(self):
        source = (p.ROOT / p.WORKFLOW).read_text()
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
        self.assertIn("steps.authority-app-token.outputs.installation-id", probe)
        self.assertIn("--preflight", probe)
        self.assertIn("python-version: '3.12.13'", probe)
        self.assertNotIn("pages-readback:", source)
        self.assertLess(probe.index("Verify probe boundaries"),
                        probe.index("QIKVRT_RULESET_ADMIN_TOKEN:"))
        consumer = probe.split("      - name: Resume fixed", 1)[1]
        self.assertNotIn("secrets.", consumer)
        self.assertNotIn("github.token", consumer)


if __name__ == "__main__":
    unittest.main()
