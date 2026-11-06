# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import unittest
from tools.qikvrt_public_artifact import NOTICE, evaluate, validate_catalog

RECORD = {
    "id": "qikvrt-test-artifact",
    "source_commit": "a" * 40,
    "artifact_sha256": "b" * 64,
    "license": "PolyForm-Noncommercial-1.0.0",
    "rights_review": "PASS",
    "third_party_review": "PASS",
    "security_review": "PASS",
    "build_review": "PASS",
    "publication_approval": "PASS",
    "distribution_url": "https://example.org/artifact.tar.gz",
    "required_notice": NOTICE,
    "runtime_effect_status": "UNVERIFIED"
}
class TestPublicArtifact(unittest.TestCase):
    def test_valid_metadata_only(self):
        self.assertEqual(evaluate(RECORD)["status"], "METADATA_ELIGIBLE")
    def test_missing_rights(self):
        self.assertEqual(evaluate(dict(RECORD, rights_review="UNVERIFIED"))["status"], "BLOCKED")
    def test_missing_approval(self):
        self.assertEqual(evaluate(dict(RECORD, publication_approval="UNVERIFIED"))["status"], "BLOCKED")
    def test_insecure_url(self):
        self.assertEqual(evaluate(dict(RECORD, distribution_url="http://example.org/a"))["status"], "BLOCKED")
    def test_notice(self):
        self.assertEqual(evaluate(dict(RECORD, required_notice="Changed"))["status"], "BLOCKED")
    def test_wrong_digest(self):
        self.assertEqual(evaluate(dict(RECORD, artifact_sha256="invalid"))["status"], "BLOCKED")
    def test_license_unknown(self):
        self.assertEqual(evaluate(dict(RECORD, license="UNKNOWN"))["status"], "BLOCKED")
    def test_eap_not_implied(self):
        self.assertEqual(evaluate(dict(RECORD, runtime_effect_status="EFFECT_ACK_DONE"))["status"], "BLOCKED")
    def test_duplicate(self):
        self.assertEqual(validate_catalog({"schema": "qikvrt.public-artifacts-index.v1", "artifacts": [RECORD, RECORD]})["status"], "BLOCKED")
    def test_missing(self):
        self.assertEqual(evaluate({"id": "x"})["status"], "BLOCKED")
    def test_sha256_git_object_id(self):
        self.assertEqual(evaluate(dict(RECORD, source_commit="a" * 64))["status"], "METADATA_ELIGIBLE")
    def test_invalid_git_object_id(self):
        self.assertEqual(evaluate(dict(RECORD, source_commit="a" * 39))["status"], "BLOCKED")
    def test_https_without_host(self):
        self.assertEqual(evaluate(dict(RECORD, distribution_url="https:///artifact.zip"))["status"], "BLOCKED")
    def test_url_credentials(self):
        self.assertEqual(evaluate(dict(RECORD, distribution_url="https://user:pass@example.org/artifact.zip"))["status"], "BLOCKED")
    def test_url_fragment(self):
        self.assertEqual(evaluate(dict(RECORD, distribution_url="https://example.org/artifact.zip#fragment"))["status"], "BLOCKED")
    def test_url_nonstandard_port(self):
        self.assertEqual(evaluate(dict(RECORD, distribution_url="https://example.org:8443/artifact.zip"))["status"], "BLOCKED")
    def test_non_string_license(self):
        self.assertEqual(evaluate(dict(RECORD, license=["MIT"]))["status"], "BLOCKED")
    def test_invalid_id_is_not_hashable(self):
        broken = dict(RECORD, id=["not-a-string"])
        outcome = validate_catalog({"schema": "qikvrt.public-artifacts-index.v1", "artifacts": [broken]})
        self.assertEqual(outcome["status"], "BLOCKED")
    def test_empty_candidate(self):
        self.assertEqual(validate_catalog({"schema": "qikvrt.public-artifacts-index.v1", "artifacts": []})["status"], "CANDIDATE_EMPTY")
if __name__ == "__main__":
    unittest.main()
