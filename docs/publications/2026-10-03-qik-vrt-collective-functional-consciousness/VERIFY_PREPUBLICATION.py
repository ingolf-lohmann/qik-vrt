#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only validation of the explicitly migrated, unauthorized v3 candidate."""
from pathlib import Path
import copy
import hashlib
import json
import os
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools import qikvrt_zenodo_machine_proof as proof
from tools import qikvrt_zenodo_publish as publisher

HERE = Path(__file__).resolve().parent
REL = HERE.relative_to(ROOT).as_posix() + "/"
BUNDLE = HERE / "MACHINE_PROOF_BUNDLE.json"
EXPECTED_BLOCK = "NO_REVIEWED_V3_ACTIVATION_NO_V3_PRODUCTION_MUTATION: detached activation missing"


def inspect_invalid(value):
    scratch = ROOT / ".qikvrt" / "evidence"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", dir=scratch, encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False)
        stream.flush()
        try:
            proof.validate_publication_bundle_v3(ROOT, Path(stream.name))
        except proof.ProofGateError as exc:
            return str(exc)
    raise AssertionError("Invalid v3 proof passed the technical gate")


def verify():
    bundle = json.loads(BUNDLE.read_text())
    assert bundle["schema"] == proof.PROPOSED_BUNDLE_SCHEMA
    assert bundle["completion_claims"] == {"machine_proof_complete": True}
    planned = json.loads((HERE/"ZENODO_FILESET.json").read_text())["paths"]
    receipt = proof.validate_publication_bundle_v3(ROOT, BUNDLE, upload_paths=planned)
    assert receipt["review_state"] == "REVIEW_REQUIRED"
    assert not receipt["zenodo_upload_authorized"]
    assert not receipt["production_mutation_authorized"]
    matrix = json.loads((HERE/"CLAIM_MATRIX.json").read_text())
    assert len(matrix["claims"]) == matrix["claim_count"] == len(bundle["claims"]) == 18
    assert not any(c["classification"] == "FORMAL_PROVED" for c in bundle["claims"])
    assert len(planned) == len(set(planned))
    assert len({Path(p).name for p in planned}) == len(planned)
    metadata = json.loads((HERE/"ZENODO_METADATA.json").read_text())
    assert publisher._validate_metadata(metadata) == metadata
    metadata_sha = hashlib.sha256(publisher.zenodo._json_bytes(metadata)).hexdigest()
    pdf = ROOT/bundle["candidate"]["primary_document_path"]
    assert proof.identity(pdf)["sha256"] in (HERE/"ARTICLE.md").read_text()
    assert pdf.read_bytes().startswith(b"%PDF-")
    for name in ("OWNER_ZENODO_AUTHORIZATION.json", "V3_CONTRACT_ACTIVATION.json", "publish-request.json"):
        assert not (HERE/name).exists()
    cases = []
    for name, mutate, expected in [
        ("PDF_HASH_TAMPER", lambda b: b["candidate"]["files"][0].update(sha256="0"*64), "SHA-256 mismatch"),
        ("CLAIM_OMISSION", lambda b: b["claims"].pop(), "bidirectionally"),
        ("SOURCE_HASH_TAMPER", lambda b: b["artifacts"][0].update(sha256="0"*64), "SHA-256 mismatch"),
        ("OPEN_CLAIM_PROMOTION", lambda b: next(c for c in b["claims"] if c["classification"]=="OPEN").update(publication_wording="ESTABLISHED_WITHIN_SCOPE"), "disposition inconsistent"),
        ("EMBEDDED_UPLOAD_FALSE", lambda b: b["completion_claims"].update(zenodo_upload_authorized=False), "unknown=zenodo_upload_authorized"),
        ("EMBEDDED_UPLOAD_TRUE", lambda b: b["completion_claims"].update(zenodo_upload_authorized=True), "unknown=zenodo_upload_authorized"),
    ]:
        changed = copy.deepcopy(bundle)
        mutate(changed)
        error = inspect_invalid(changed)
        assert expected in error, (name, error)
        cases.append({"test_id":name, "result":"REJECTED_AS_EXPECTED", "observed_error":error})
    for name, upload_set in [
        ("OMITTED_PROOF_UPLOAD", [p for p in planned if p != REL+"MACHINE_PROOF_BUNDLE.json"]),
        ("EXTRA_UPLOAD", planned+[REL+"ZENODO_FILESET.json"]),
        ("DUPLICATE_UPLOAD", planned+[planned[0]]),
    ]:
        try:
            proof.validate_publication_bundle_v3(ROOT, BUNDLE, upload_paths=upload_set)
        except proof.ProofGateError as exc:
            cases.append({"test_id":name, "result":"REJECTED_AS_EXPECTED", "observed_error":str(exc)})
        else:
            raise AssertionError(name)
    frozen = BUNDLE.read_bytes()
    files = [{"path":p, "name":Path(p).name,
              "git_blob_sha":proof.identity(ROOT/p)["git_blob_sha1"]} for p in planned]
    source_head = json.loads((HERE/"PREPUBLICATION_STATUS.json").read_text())["migration_input_head"]
    value = {"schema":publisher.SCHEMA_V3, "state":"publish",
             "confirm":"PUBLISH_TO_PRODUCTION_ZENODO", "repository":publisher.PRODUCTION_REPOSITORY,
             "source_head":source_head, "metadata":metadata, "files":files,
             "machine_proof":{"path":REL+"MACHINE_PROOF_BUNDLE.json", "git_blob_sha":receipt["git_blob_sha1"],
                              "policy_id":proof.PROPOSED_POLICY_ID},
             "contract_activation":None, "owner_authorization":None,
             "evidence_path":REL+"zenodo-publication.json"}
    scratch = ROOT/".qikvrt"/"evidence"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", dir=scratch, encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False)
        stream.flush()
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY":publisher.PRODUCTION_REPOSITORY}), \
                mock.patch.object(publisher, "_github_api_request") as github, \
                mock.patch.object(publisher.zenodo, "ZenodoClient") as client:
            try:
                publisher.publish(Path(stream.name), ROOT)
            except publisher.zenodo.ZenodoError as exc:
                assert str(exc) == EXPECTED_BLOCK, str(exc)
            else:
                raise AssertionError("Missing detached activation did not block production")
            github.assert_not_called()
            client.assert_not_called()
    materialized = [publisher._materialize_file(item, ROOT, "candidate files") for item in files]
    normalized = publisher._validate_machine_proof(value["machine_proof"], ROOT, materialized, v3=True)
    try:
        publisher._validate_owner_authorization(None, ROOT, publisher.PRODUCTION_REPOSITORY,
            metadata, materialized, normalized, HERE/"zenodo-publication.json", source_head)
    except publisher.zenodo.ZenodoError as exc:
        owner_error = str(exc)
    else:
        raise AssertionError("Missing detached Owner decision did not block")
    assert BUNDLE.read_bytes() == frozen
    return {"schema":"qikvrt_prepublication_verification_result_v2",
            "publication_id":bundle["publication_id"], "proof_schema_version":3,
            "candidate_byte_bindings":"PASS", "claim_matrix_bidirectional_projection":"PASS",
            "source_references":"PASS", "changed_content_return_chain":"PASS",
            "fileset_closure":"PASS", "unique_upload_filenames":"PASS",
            "canonical_metadata_sha256":metadata_sha, "negative_controls":cases,
            "technical_v3_proof_contract":"PASS",
            "return_receipt_v2_semantic_contract":"PASS via repository-native validator",
            "production_gate":"HOLD", "production_error":EXPECTED_BLOCK,
            "owner_decision_error":owner_error, "upload_authorized":False,
            "contract_activation_present":False, "external_publication_effect":"NONE",
            "hash_stability":{"proof_unchanged_by_readiness_and_denied_effect_probes":True,
                "embedded_authorization_field":"FORBIDDEN",
                "detached_decision_hash_stability_regressions":"tests/test_zenodo_machine_proof_policy.py",
                "actual_owner_decision_created":False, "authorization_consumed":False},
            "subject_binding":"Current candidate bytes; execution HEAD/TREE are external to this hash-bound report and must be validated afresh. Predecessor executions do not transfer.",
            "verification_scope":"Repository-native exact policy/schema, claim, source, return and upload-closure validation. No general JSON Schema engine invoked. Missing activation and Owner decision block before any transport; no synthetic activation or upload decision is persisted in this candidate."}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2, sort_keys=True))
