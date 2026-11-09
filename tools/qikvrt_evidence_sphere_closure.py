#!/usr/bin/env python3
"""Fail-closed, offline, deterministic evidence-sphere closure verifier.

No network, publishing, production effect, or approval is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def verify(sphere):
    failures = []
    if sphere.get("schema") != "qikvrt_mesh_evidence_sphere_links_v1":
        failures.append("SCHEMA_MISMATCH")
    rules = sphere.get("rules", {})
    for key in ("existing_nodes_must_not_be_deleted", "existing_edges_must_not_be_deleted",
                "corrections_are_appended_as_supersedes_or_refines_edges"):
        if rules.get(key) is not True:
            failures.append("MONOTONIC_RULE_MISSING:" + key)
    if rules.get("predecessor_evidence_transfer") is not False:
        failures.append("PREDECESSOR_TRANSFER_NOT_DENIED")
    core = sphere.get("zenodo_core", {})
    concepts = core.get("concepts", [])
    records = core.get("records", [])
    if len(concepts) != core.get("concept_line_count"):
        failures.append("CONCEPT_COUNT_MISMATCH")
    if len(records) != core.get("record_count"):
        failures.append("RECORD_COUNT_MISMATCH")
    ids = [n.get("id") for n in concepts + records + sphere.get("external_reference_nodes", [])
           + sphere.get("internal_reference_nodes", [])]
    if len(ids) != len(set(ids)):
        failures.append("DUPLICATE_NODE_ID")
    concept_dois = {c.get("doi") for c in concepts}
    record_ids = {r.get("record_id") for r in records}
    if len(record_ids) != len(records):
        failures.append("DUPLICATE_RECORD")
    for r in records:
        if r.get("concept_doi") not in concept_dois:
            failures.append("UNBOUND_RECORD:" + str(r.get("record_id")))
    for c in concepts:
        for rid in c.get("records", []):
            if rid not in record_ids:
                failures.append("UNBOUND_CONCEPT_RECORD:" + str(rid))
    edges = sphere.get("edges", [])
    keys = [(e.get("from"), e.get("to"), e.get("relation")) for e in edges]
    if len(keys) != len(set(keys)):
        failures.append("DUPLICATE_EDGE")
    for e in edges:
        if e.get("evidence_semantics") == "REFERENCE_ONLY_NO_EVIDENCE_TRANSFER":
            continue
        # Unknown evidence semantics cannot silently become an attestation.
        if e.get("evidence_semantics") not in ("REFERENCE_ONLY_NO_EVIDENCE_TRANSFER", "CANONICAL_INTERNAL_MONOTONICITY_RULE"):
            failures.append("UNADMITTED_EDGE_SEMANTICS:" + str(e.get("relation")))
    # Monotone fixed point: propagate ONLY explicitly admitted logical edges.
    # Reference-only edges must never be promoted into proof dependencies.
    closure = set(ids)
    rounds = 0
    while True:
        successor = set(closure)
        for e in edges:
            if e.get("evidence_semantics") == "ADMITTED_LOGICAL_DERIVATION" and e.get("from") in closure:
                successor.add(e.get("to"))
        if successor == closure:
            break
        closure = successor
        rounds += 1
        if rounds > len(ids) + len(edges):
            failures.append("FIXPOINT_DID_NOT_CONVERGE")
            break
    return {"schema": "qikvrt_evidence_sphere_closure_v1",
            "status": "PASS_OFFLINE_STRUCTURE_ONLY" if not failures else "FAIL_CLOSED",
            "source_sha256": hashlib.sha256(canonical(sphere)).hexdigest(),
            "node_count": len(ids), "edge_count": len(edges),
            "closure_node_count": len(closure), "closure_rounds": rounds,
            "external_proof_admitted": False, "production_effect_ack_done": False,
            "failures": sorted(set(failures))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("sphere", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = verify(json.loads(args.sphere.read_text(encoding="utf-8")))
    payload = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    raise SystemExit(0 if not result["failures"] else 1)


if __name__ == "__main__":
    main()
