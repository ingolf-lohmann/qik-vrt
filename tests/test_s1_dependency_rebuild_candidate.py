# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Check the historic carrier never becomes a silent candidate substitution."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "runtime/self-host/Dockerfile"
WORKFLOW = ROOT / ".github/workflows/qikvrt_s1_dependency_rebuild_candidate.yml"
ORIGINAL = ROOT / "runtime/self-host/CONTAINER_CARRIER.json"


class S1DependencyCandidateTests(unittest.TestCase):
    def test_original_contract_remains_byte_bound(self):
        original = json.loads(ORIGINAL.read_bytes())
        self.assertEqual(original["schema"], "qikvrt-s1-frozen-container-carrier/v1")
        self.assertEqual(original["artifact_id"], 11521962723)
        self.assertEqual(original["archive_bytes"], 382994793)
        self.assertEqual(original["archive_sha256"],
                         "5a912ccde96253bdba5f5e82cd0a36a4ff89de58dabbe57977bc1acf298d9695")

    def test_successor_is_not_the_original_frozen_image(self):
        source = DOCKERFILE.read_text(encoding="utf-8")
        self.assertEqual(source.count("FROM runtime AS s1-dependency-carrier-candidate"), 1)
        self.assertIn('de.qikvrt.carrier-scope="NEW_DEPENDENCY_CANDIDATE_NOT_PR494"', source)
        self.assertIn('USER 10001:10001\n\nFROM ${QIKVRT_DEPENDENCY_IMAGE} AS delivery-runtime', source)
        self.assertTrue(source.rstrip().endswith('LABEL de.qikvrt.terminal-profile="firefox"'))

    def test_exact_source_two_builds_and_native_oci_verification(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for required in (
                "permissions:\n  contents: read",
                "docker buildx build --no-cache --pull",
                "--target s1-dependency-carrier-candidate",
                "for n in 1 2; do",
                "--expected-head \"$head\" --expected-tree \"$tree\"",
                "--second-oci-archive",
                "receipt[\"independent_rebuild_digest_equal\"] is True",
                "replaces_frozen_pr494\":False",
                "effect_ack_done\":False",
                "if: success()",
                "docker/setup-buildx-action@f87e5991a6d7451dcb8d9637bfbc97413f497069",
        ):
            with self.subTest(value=required):
                self.assertIn(required, source)

    def test_action_is_pinned_to_repository_verified_upload_ref(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(source.count("actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"), 2)
        self.assertNotIn("043fb46d1a93c77aae656e75b540449e92b4886f43607fa02", source)

    def test_data_only_layer_difference_and_no_false_promotion(self):
        import io
        import tarfile
        from tools.qikvrt_s1_dependency_layer_diff import layer_records
        # A tiny synthetic OCI outer tar with one gzip layer. Input is never extracted.
        def example(data):
            packed = io.BytesIO()
            with tarfile.open(fileobj=packed, mode="w:gz") as layer:
                member = tarfile.TarInfo("etc/test.conf")
                member.size = len(data)
                member.mtime = 0
                layer.addfile(member, io.BytesIO(data))
            payload = packed.getvalue()
            import hashlib
            digest = hashlib.sha256(payload).hexdigest()
            with tempfile.TemporaryDirectory() as directory:
                outer = Path(directory) / "oci.tar"
                with tarfile.open(outer, mode="w") as archive:
                    item = tarfile.TarInfo("blobs/sha256/" + digest)
                    item.size = len(payload)
                    archive.addfile(item, io.BytesIO(payload))
                return layer_records(outer, "sha256:" + digest)
        import tempfile
        first = example(b"a")
        second = example(b"b")
        self.assertEqual(len(first), 1)
        self.assertNotEqual(first["etc/test.conf"]["sha256"], second["etc/test.conf"]["sha256"])
        self.assertEqual(first["etc/test.conf"]["bytes"], second["etc/test.conf"]["bytes"])

    def test_layer_diff_preserved_when_oci_digest_is_not_equal(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("tools/qikvrt_s1_dependency_layer_diff.py", workflow)
        self.assertIn("LAYER_DIFF.json", workflow)
        self.assertIn('exit "$check_status"', workflow)

    def test_no_production_route_or_automatic_substitute(self):
        src = WORKFLOW.read_text(encoding="utf-8")
        forbidden = (
            "container-deploy", "git push", "gh release create", "docker login",
            "GITHUB_TOKEN:", "contents: write", "pull_request_target:", "docker/build-push-action",
        )
        for value in forbidden:
            with self.subTest(forbidden=value):
                self.assertNotIn(value, src)


if __name__ == "__main__":
    unittest.main()
