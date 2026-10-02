#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic global claim inventory, traceability and completion receipts."""
from __future__ import annotations

import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
FORM = ROOT / "formalization/QIKVRT_Formalization_v2.0"
GRAPH = FORM / "claims/CLAIM_GRAPH.json"
MATRIX = FORM / "claims/APPENDIX_MATRIX.json"
EFFECT = FORM / "effect_ack/DRAFT01_CLAIM_MATRIX.json"
PROOFS = FORM / "proofs/PROOF_OBJECT_MANIFEST.json"
FREADME = FORM / "README.md"
PLAN = FORM / "COMPLETION_PLAN.md"
FSTATUS = FORM / "GLOBAL_COMPLETION_STATUS.json"
README, STATUS, AI = ROOT / "README.md", ROOT / "STATUS.md", ROOT / "AI_PROGRESS.json"
BATCH_002_RECEIPT = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/terminal-disposition/CONTENT_DISPOSITION_BATCH_002_RECEIPT.json"
SCOPE = ROOT / "GLOBAL_COMPLETION_SCOPE.json"
INVENTORY = ROOT / "GLOBAL_CLAIM_INVENTORY.json"
TRACE = ROOT / "GLOBAL_SOURCE_CLAIM_DISPOSITION_TRACEABILITY.json"
KERNEL = ROOT / "GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json"
FINAL_INPUT = ROOT / "GLOBAL_COMPLETION_FINALIZATION_INPUT.json"
FINAL_RECEIPT = ROOT / "GLOBAL_COMPLETION_RECEIPT.json"
GLOBAL_RUN_EVIDENCE = ROOT / "evidence/receipts/global-completion-exact-head-runs-2026-07-29.json"

SCOPE_ID = "qikvrt-global-claim-scope-v1"
TAG = "v2026.07.28-authority-mirror-zenodo-equality-1.0.0"
AUTH_REPO, MIRROR_REPO = "Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt"
AUTH_TAG, MIRROR_TAG = "42389236ea638f5cd40c13a486b70b1e1bf03055", "5c710e98bea2a10035cf0ba2c8e30ffd5c98c279"
TAG_TREE = "cc3f0421c7eb9255ec35cdd5a7326d3a21dabb9e"
TAG_MANIFEST = "4c07246b9eb8a9947267d487f78b026b6078a2af7b0f0dbbe0542e01ac77a6c9"
TAG_CONTENT = "344d9fdb75575d2e7696425f686feeb6e2b6645d5d02b51a42bf251036d85c11"
ZENODO_PATH = "release/authority-mirror-equality-2026-07-27/zenodo-publication.json"
ZENODO_BLOB = "30b85229fba5b037046f94e6e127ae13f705e660"
ZENODO_SHA = "3b3f7773b080da41e94c04b03700660b05adf364c7c72576259855dc689dfd68"
DOI, CONCEPT_DOI = "10.5281/zenodo.21633411", "10.5281/zenodo.21633410"
ALLOWED = {"KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL", "EMPIRICAL_EVIDENCE_BOUND", "INTERPRETIVE", "NORMATIVE", "OPEN", "OUT_OF_SCOPE"}
EXPECTED = {"MANUSCRIPT": 43, "APPENDIX": 34, "EFFECT_ACK": 15, "TOTAL": 92, "KERNEL": 54}
LIC = {"classification":"machine_readable_global_completion_evidence","copyright":"Copyright 2026 Ingolf Lohmann","rights_holder":"Ingolf Lohmann","license":"CC-BY-NC-ND-4.0","license_text_ref":"LICENSES/CC-BY-NC-ND-4.0.txt"}


def rel(p: Path) -> str: return p.relative_to(ROOT).as_posix()
def load(p: Path) -> dict[str, Any]:
    v = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v, dict): raise ValueError(f"{rel(p)} is not an object")
    return v
def pretty(v: Any) -> str: return json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def blob(data: bytes) -> str: return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
def identity(p: Path) -> dict[str, Any]:
    b=p.read_bytes(); return {"path":rel(p),"bytes":len(b),"sha256":sha(b),"git_blob_sha1":blob(b)}
def ns(space: str, ident: str) -> str: return f"{space}::{ident}"
def source(p: Path, ident: str, span: Any=None) -> dict[str, Any]:
    x={**identity(p),"record_id":ident}
    if span is not None: x["source_span"]=span
    return x


def scope() -> dict[str, Any]:
    return {"_license":LIC,"schema":"qikvrt_global_completion_scope_v1","scope_id":SCOPE_ID,
      "semantics":{"global":"Every explicit ID in the three listed registries; not every prose sentence, external fact, future claim or possible proposition.",
        "completion":"Every included claim has exactly one terminal disposition. Every kernel-eligible primary claim requires an exact-tag Lean receipt.",
        "final_pass":"Scoped evidence completion; OPEN is retained as OPEN and empirical or interpretive content is not promoted to a theorem.",
        "effect_ack_done":"DONE for this bounded completion transaction only, not for every future repository effect."},
      "terminal_dispositions":sorted(ALLOWED),
      "included_registries":[
        {"namespace":"MANUSCRIPT","path":rel(GRAPH),"array":"nodes","expected":43},
        {"namespace":"APPENDIX","path":rel(MATRIX),"array":"rows","expected":34},
        {"namespace":"EFFECT_ACK","path":rel(EFFECT),"array":"claims","expected":15}],
      "excluded_classes":["unregistered prose assertions","third-party claims not adopted by a registry","historical payload and binary archive contents","future claims introduced after the candidate head","empirical reality beyond bound evidence","unregistered legal, medical, psychological, personal-event, religious, metaphysical or historical truth determinations"],
      "kernel_eligibility_rule":"Explicit Lean binding or EFFECT_ACK KERNEL_PROVED status only.",
      "exact_tag_binding":{"tag":TAG,"authority":{"repository":AUTH_REPO,"commit":AUTH_TAG},"mirror":{"repository":MIRROR_REPO,"commit":MIRROR_TAG},"shared_git_tree_sha1":TAG_TREE,"repository_manifest_sha256":TAG_MANIFEST,"repository_content_tree_sha256":TAG_CONTENT,"zenodo_doi":DOI,"zenodo_concept_doi":CONCEPT_DOI,"zenodo_evidence_path":ZENODO_PATH,"zenodo_evidence_git_blob_sha1":ZENODO_BLOB,"zenodo_evidence_sha256":ZENODO_SHA}}


def manuscript_disposition(n: dict[str, Any]) -> str:
    s,c=n.get("formalizationStatus"),n.get("epistemicCategory")
    if s=="KERNEL_CHECKED": return "KERNEL_PROVED"
    if s=="CONDITIONAL_CHECKED": return "KERNEL_PROVED_CONDITIONAL"
    if s=="PENDING": return "OPEN"
    if c=="EMPIRICAL": return "EMPIRICAL_EVIDENCE_BOUND"
    if c in {"INTERPRETIVE","BACKGROUND"}: return "INTERPRETIVE"
    if c=="NORMATIVE": return "NORMATIVE"
    return "OUT_OF_SCOPE"
def effect_disposition(c: dict[str, Any]) -> str:
    s=c.get("status")
    if s=="KERNEL_PROVED": return "KERNEL_PROVED"
    if s=="KERNEL_PROVED_CONDITIONAL": return "KERNEL_PROVED_CONDITIONAL"
    if s in {"OPEN","EMPIRICAL_OPEN"}: return "OPEN"
    k=c.get("classification")
    if k=="EMPIRICAL_PHYSICS": return "EMPIRICAL_EVIDENCE_BOUND"
    if k in {"INTERPRETIVE","BACKGROUND"}: return "INTERPRETIVE"
    if k=="NORMATIVE": return "NORMATIVE"
    return "OUT_OF_SCOPE"
def appendix_disposition(r: dict[str, Any], primary: dict[str, dict[str, Any]]) -> tuple[str,str]:
    c,t=r.get("epistemicCategory"),str(r.get("truthDisposition",""))
    if c=="EMPIRICAL": return "EMPIRICAL_EVIDENCE_BOUND","Source-bound empirical classification; no theorem promotion."
    if c in {"INTERPRETIVE","BACKGROUND"}: return "INTERPRETIVE","Source-bound interpretive/background classification."
    if c=="NORMATIVE": return "NORMATIVE","Source-bound normative classification."
    if t in {"OPEN","UNRESOLVED","HYPOTHESIS"}: return "OPEN","The source marks the assertion unresolved."
    ids=r.get("relatedClaimIds",[]); related=[primary[x] for x in ids if x in primary]
    if ids and len(related)==len(ids):
        ds={x["terminal_disposition"] for x in related}
        if ds <= {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"}:
            if c=="CONDITIONAL" or "KERNEL_PROVED_CONDITIONAL" in ds: return "KERNEL_PROVED_CONDITIONAL","Inherited from explicit related conditional Lean claims."
            return "KERNEL_PROVED","Inherited from explicit related Lean claims."
    return "OUT_OF_SCOPE","Classified appendix assertion without a direct primary kernel binding; retained without proof inflation."


def build_inventory() -> tuple[dict[str, Any],dict[str,dict[str,Any]]]:
    g,m,e=load(GRAPH),load(MATRIX),load(EFFECT)
    nodes,rows,eclaims=g.get("nodes"),m.get("rows"),e.get("claims")
    if not all(isinstance(x,list) for x in (nodes,rows,eclaims)): raise ValueError("malformed registry array")
    for name,arr in (("MANUSCRIPT",nodes),("APPENDIX",rows),("EFFECT_ACK",eclaims)):
        if len(arr)!=EXPECTED[name]: raise ValueError(f"{name}: expected {EXPECTED[name]}, got {len(arr)}")
    claims=[]; primary={}
    for n in nodes:
        ident=n["id"]; d=manuscript_disposition(n); b=n.get("formalBinding")
        proofs=[] if not isinstance(b,dict) else [{"proof_system":b.get("proofSystem"),"statement_constant":b.get("statementConstant"),"proof_constant":b.get("proofConstant"),"registry_constant":b.get("registryConstant"),"source_path":b.get("sourcePath"),"source_sha256":b.get("leanSourceSha256"),"registry_source_path":b.get("registrySourcePath"),"registry_source_sha256":b.get("registrySourceSha256"),"claim_scope":b.get("claimScope"),"assumption_policy":b.get("assumptionPolicy")}]
        item={"inventory_id":ns("MANUSCRIPT",ident),"namespace":"MANUSCRIPT","claim_id":ident,"statement":n.get("statement"),"epistemic_category":n.get("epistemicCategory"),"source_status":n.get("formalizationStatus"),"terminal_disposition":d,"dependencies":[ns("MANUSCRIPT",x) for x in n.get("dependencies",[])],"source_refs":[source(GRAPH,ident,{"source_span_ids":n.get("sourceSpanIds",[])})],"proof_refs":proofs,"environment_ids":n.get("environmentIds",[]),"proof_block_ids":n.get("proofBlockIds",[])}
        claims.append(item); primary[ident]=item
    for r in rows:
        ident=r["id"]; d,why=appendix_disposition(r,primary); related=[ns("MANUSCRIPT",x) for x in r.get("relatedClaimIds",[])]
        aliases=[{"kind":"PRIMARY_CLAIM_ALIAS","inventory_id":x} for x in related if primary.get(x.split("::",1)[1],{}).get("terminal_disposition") in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"}]
        claims.append({"inventory_id":ns("APPENDIX",ident),"namespace":"APPENDIX","claim_id":ident,"statement":r.get("statementTex"),"epistemic_category":r.get("epistemicCategory"),"source_status":r.get("truthDisposition"),"terminal_disposition":d,"disposition_rationale":why,"dependencies":related,"source_refs":[source(MATRIX,ident,r.get("sourceSpan"))],"proof_refs":aliases,"machine_proof_binding_allowed":r.get("machineProofBindingAllowed"),"manuscript_status":r.get("manuscriptStatusTex"),"rationale":r.get("rationaleTex")})
    for c in eclaims:
        ident=c["id"]; d=effect_disposition(c)
        proofs=[] if d not in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"} else [{"proof_system":"Lean4","proof_constants":c.get("proof_constants",[]),"registry_constant":c.get("registry_constant"),"source_path":c.get("source_path")}]
        claims.append({"inventory_id":ns("EFFECT_ACK",ident),"namespace":"EFFECT_ACK","claim_id":ident,"statement":c.get("statement"),"epistemic_category":c.get("classification"),"source_status":c.get("status"),"terminal_disposition":d,"dependencies":[],"source_refs":[source(EFFECT,ident,{"source_sections":c.get("source_sections",[]),"related_sections":c.get("related_sections",[]),"source_provenance":e.get("source_provenance")})],"proof_refs":proofs,"draft_relationship":c.get("draft_relationship")})
    claims.sort(key=lambda x:x["inventory_id"]); ids=[x["inventory_id"] for x in claims]
    dup=[x for x,n in Counter(ids).items() if n>1]
    if dup or len(claims)!=92 or any(x["terminal_disposition"] not in ALLOWED for x in claims): raise ValueError("inventory uniqueness/count/disposition invariant failed")
    inv={"_license":LIC,"schema":"qikvrt_global_claim_inventory_v1","scope_id":SCOPE_ID,"source_tag":TAG,
      "counts":{"total":len(claims),"by_namespace":dict(sorted(Counter(x["namespace"] for x in claims).items())),"by_terminal_disposition":dict(sorted(Counter(x["terminal_disposition"] for x in claims).items())),"kernel_eligible_primary_claims":sum(x["namespace"] in {"MANUSCRIPT","EFFECT_ACK"} and x["terminal_disposition"] in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"} for x in claims),"open_claims":sum(x["terminal_disposition"]=="OPEN" for x in claims)},
      "completion_invariants":{"all_included_registry_records_present":True,"all_inventory_ids_unique":True,"all_claims_terminally_classified":True,"open_is_terminal_not_proved":True,"out_of_scope_is_explicit":True},"claims":claims}
    return inv,{x["inventory_id"]:x for x in claims}


def build_kernel(inv: dict[str,Any],byid: dict[str,dict[str,Any]]) -> dict[str,Any]:
    g,e,p=load(GRAPH),load(EFFECT),load(PROOFS); effect_root=p.get("effectAck",{}); effect_map={x.get("claimId"):x for x in effect_root.get("claims",[]) if isinstance(x,dict)}
    primary=[]; protected={rel(GRAPH),rel(MATRIX),rel(EFFECT),rel(PROOFS),ZENODO_PATH}
    for n in g["nodes"]:
        b=n.get("formalBinding")
        if not isinstance(b,dict): continue
        ident=ns("MANUSCRIPT",n["id"]); sp=FORM/b["sourcePath"]; rp=FORM/b["registrySourcePath"]; protected|={rel(sp),rel(rp)}
        obj=next((x.get("compiledObject") for x in p.get("objects",[]) if isinstance(x,dict) and x.get("claimId")==n["id"]),None)
        primary.append({"receipt_id":f"kernel::{ident}","inventory_id":ident,"terminal_disposition":byid[ident]["terminal_disposition"],"proof_system":"Lean4","statement_constant":b["statementConstant"],"proof_constants":[b["proofConstant"]],"registry_constant":b["registryConstant"],"claim_scope":b["claimScope"],"assumption_policy":b["assumptionPolicy"],"source":identity(sp),"registry_source":identity(rp),"compiled_object":obj,"exact_tag_required":True})
    effect_registry=effect_root.get("registrySourcePath")
    for c in e["claims"]:
        ident=ns("EFFECT_ACK",c["id"]); d=byid[ident]["terminal_disposition"]
        if d not in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"}: continue
        me=effect_map.get(c["id"])
        if not isinstance(me,dict): raise ValueError(f"missing proof manifest entry {c['id']}")
        sp=FORM/c["source_path"]; protected.add(rel(sp)); rp=FORM/effect_registry if effect_registry else None
        if rp: protected.add(rel(rp))
        primary.append({"receipt_id":f"kernel::{ident}","inventory_id":ident,"terminal_disposition":d,"proof_system":"Lean4","statement_constant":None,"proof_constants":c.get("proof_constants",[]),"registry_constant":c.get("registry_constant"),"claim_scope":c.get("draft_relationship"),"assumption_policy":"EXPLICIT_IN_LEAN_TYPE" if d=="KERNEL_PROVED_CONDITIONAL" else "NO_HIDDEN_ASSUMPTIONS","source":identity(sp),"registry_source":identity(rp) if rp else None,"compiled_objects":me.get("compiledObjects",[]),"exact_tag_required":True})
    primary.sort(key=lambda x:x["inventory_id"])
    expected={x["inventory_id"] for x in inv["claims"] if x["namespace"] in {"MANUSCRIPT","EFFECT_ACK"} and x["terminal_disposition"] in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"}}
    if len(primary)!=54 or {x["inventory_id"] for x in primary}!=expected: raise ValueError("primary kernel receipt coverage mismatch")
    aliases=[]
    for x in inv["claims"]:
        if x["namespace"]=="APPENDIX" and x["terminal_disposition"] in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"}:
            targets=[r["inventory_id"] for r in x["proof_refs"] if r.get("kind")=="PRIMARY_CLAIM_ALIAS"]
            if not targets or any(t not in expected for t in targets): raise ValueError(f"incomplete alias {x['inventory_id']}")
            aliases.append({"inventory_id":x["inventory_id"],"terminal_disposition":x["terminal_disposition"],"primary_kernel_inventory_ids":targets})
    return {"_license":LIC,"schema":"qikvrt_global_exact_tag_kernel_receipts_v1","scope_id":SCOPE_ID,"tag_binding":scope()["exact_tag_binding"],"proof_object_manifest":identity(PROOFS),"counts":{"primary_receipts":len(primary),"appendix_alias_receipts":len(aliases),"conditional_primary_receipts":sum(x["terminal_disposition"]=="KERNEL_PROVED_CONDITIONAL" for x in primary)},"verification_policy":{"fresh_lake_build_required_on_exact_candidate_head":True,"proof_object_runtime_evidence_required":True,"tagged_source_blob_equality_required":True,"cache_may_replace_kernel_verification":False,"foundational_axiom_allowlist":["Classical.choice","Quot.sound","propext"]},"tag_protected_paths":sorted(protected),"primary_receipts":primary,"appendix_alias_receipts":aliases}


def build_trace(inv: dict[str,Any],kernel: dict[str,Any]) -> dict[str,Any]:
    receipts={x["inventory_id"]:x["receipt_id"] for x in kernel["primary_receipts"]}; aliases={x["inventory_id"]:x["primary_kernel_inventory_ids"] for x in kernel["appendix_alias_receipts"]}; records=[]
    for c in inv["claims"]:
        ident,d=c["inventory_id"],c["terminal_disposition"]
        if ident in receipts: proof={"requirement":"NATIVE_LEAN_KERNEL_RECEIPT","receipt_ids":[receipts[ident]]}
        elif ident in aliases: proof={"requirement":"PRIMARY_KERNEL_CLAIM_ALIAS","primary_inventory_ids":aliases[ident]}
        elif d=="OPEN": proof={"requirement":"OPEN_BOUNDARY_RETAINED","receipt_ids":[]}
        else: proof={"requirement":"NON_KERNEL_TERMINAL_DISPOSITION","receipt_ids":[]}
        records.append({"inventory_id":ident,"source_refs":c["source_refs"],"claim":{"statement":c.get("statement"),"epistemic_category":c.get("epistemic_category"),"source_status":c.get("source_status")},"terminal_disposition":d,"proof_or_disposition":proof})
    return {"_license":LIC,"schema":"qikvrt_global_source_claim_disposition_traceability_v1","scope_id":SCOPE_ID,"counts":{"records":len(records),"source_bound":sum(bool(x["source_refs"]) for x in records),"native_kernel_receipts":len(receipts),"kernel_aliases":len(aliases),"non_kernel_terminal_records":sum(x["proof_or_disposition"]["requirement"] in {"NON_KERNEL_TERMINAL_DISPOSITION","OPEN_BOUNDARY_RETAINED"} for x in records)},"completeness":{"every_inventory_claim_has_source":all(x["source_refs"] for x in records),"every_inventory_claim_has_terminal_disposition":all(x["terminal_disposition"] in ALLOWED for x in records),"every_primary_kernel_claim_has_native_receipt":all(x["proof_or_disposition"]["requirement"]!="NATIVE_LEAN_KERNEL_RECEIPT" or x["proof_or_disposition"]["receipt_ids"] for x in records),"non_kernel_claims_are_not_misrepresented_as_lean_theorems":True},"records":records}


def validate_final(v: dict[str,Any]) -> dict[str,Any]:
    required={"schema","scope_id","state","candidate_pair","exact_head_gates","authority_mirror_equality_receipt_sha256"}
    if set(v)!=required or v["schema"]!="qikvrt_global_completion_finalization_input_v1" or v["scope_id"]!=SCOPE_ID or v["state"]!="AUTHORIZE_FINALIZATION": raise ValueError("finalization input contract mismatch")
    pair=v["candidate_pair"]; pkeys={"authority_exact_head","authority_main","mirror_exact_head","mirror_main","shared_git_tree_sha1","repository_manifest_sha256","repository_content_tree_sha256"}
    if not isinstance(pair,dict) or set(pair)!=pkeys: raise ValueError("candidate_pair contract mismatch")
    for k,n in (("authority_exact_head",40),("authority_main",40),("mirror_exact_head",40),("mirror_main",40),("shared_git_tree_sha1",40),("repository_manifest_sha256",64),("repository_content_tree_sha256",64)):
        if not isinstance(pair[k],str) or not re.fullmatch(rf"[0-9a-f]{{{n}}}",pair[k]): raise ValueError(f"invalid candidate_pair.{k}")
    gates=v["exact_head_gates"]
    if not isinstance(gates,dict) or set(gates)!={"authority","mirror"}: raise ValueError("gate evidence contract mismatch")
    for side in ("authority","mirror"):
        x=gates[side]
        if not isinstance(x,dict) or any(x.get(k)!="success" for k in ("global_completion","manuscript_proof","mandatory_repository_gates")): raise ValueError(f"{side} exact-head gates incomplete")
    if not re.fullmatch(r"[0-9a-f]{64}",v["authority_mirror_equality_receipt_sha256"]): raise ValueError("invalid equality receipt hash")
    return v


def completion_receipt(fin: dict[str,Any],inv: dict[str,Any],trace: dict[str,Any],kernel: dict[str,Any]) -> dict[str,Any]:
    opens=[x["inventory_id"] for x in inv["claims"] if x["terminal_disposition"]=="OPEN"]
    return {"_license":LIC,"schema":"qikvrt_global_completion_receipt_v1","scope_id":SCOPE_ID,"state":"FINAL_PASS","claims":{"PASS":True,"FINAL_PASS":True,"EFFECT_ACK_DONE":True,"fully_kernel_verified_overall_completion":True,"complete_claim_inventory":True,"complete_lean_kernel_coverage":True,"complete_source_claim_proof_traceability":True},"claim_semantics":{"scope_qualified":True,"effect_ack_done_transaction":"qikvrt-global-claim-completion-v1","fully_kernel_verified_overall_completion":"Every kernel-eligible primary claim in the exact scope has a native Lean receipt and fresh exact-head kernel gate.","complete_source_claim_proof_traceability":"Every included claim is source-bound; every kernel-eligible claim reaches a native proof receipt; every non-kernel claim reaches an explicit terminal disposition.","open_claims_remain_open":opens,"open_claims_are_not_claimed_proved":True},"scope":{"file":identity(SCOPE),"inventory":identity(INVENTORY),"traceability":identity(TRACE),"kernel_receipts":identity(KERNEL)},"counts":{"claims":inv["counts"]["total"],"primary_kernel_receipts":kernel["counts"]["primary_receipts"],"open_claims":len(opens)},"candidate_pair":fin["candidate_pair"],"exact_head_gates":fin["exact_head_gates"],"authority_mirror_equality_receipt_sha256":fin["authority_mirror_equality_receipt_sha256"],"exact_tag_kernel_source":scope()["exact_tag_binding"],"zenodo_evidence":{"doi":DOI,"concept_doi":CONCEPT_DOI,"path":ZENODO_PATH,"git_blob_sha1":ZENODO_BLOB,"sha256":ZENODO_SHA},"post_receipt_requirement":"Promote this byte-identical receipt and generated projections to Authority and Mirror; a reciprocal PR receipt binds the final main refs without changing this content-addressed evaluation."}


def block(name: str,body: str)->str: return f"<!-- qikvrt-{name}:start -->\n{body.rstrip()}\n<!-- qikvrt-{name}:end -->"
def marked(text: str,name: str,body: str,anchor: str)->str:
    b=block(name,body); pat=re.compile(rf"<!-- qikvrt-{re.escape(name)}:start -->.*?<!-- qikvrt-{re.escape(name)}:end -->",re.S)
    if pat.search(text): return pat.sub(b,text,count=1)
    i=text.find(anchor)
    if i<0: raise ValueError(f"missing marker anchor {name}")
    j=i+len(anchor); return text[:j].rstrip()+"\n\n"+b+"\n\n"+text[j:].lstrip()
def root_block(final: bool,inv: dict[str,Any])->str:
    state="FINAL_PASS" if final else "CANDIDATE_MATERIALIZED"; claim="`PASS`, `FINAL_PASS` and transaction-scoped `EFFECT_ACK_DONE` are granted by `GLOBAL_COMPLETION_RECEIPT.json`." if final else "No global `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE` is claimed before exact-head gates and Authority/Mirror equality."
    files="- `GLOBAL_COMPLETION_SCOPE.json`\n- `GLOBAL_CLAIM_INVENTORY.json`\n- `GLOBAL_SOURCE_CLAIM_DISPOSITION_TRACEABILITY.json`\n- `GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json`"+("\n- `GLOBAL_COMPLETION_RECEIPT.json`" if final else "")
    c=inv["counts"]["by_namespace"]
    return f"## Global claim-completion contract\n\nState: **`{state}`** for **`{SCOPE_ID}`**. The finite scope contains {inv['counts']['total']} explicit registry claims: {c['MANUSCRIPT']} manuscript graph nodes, {c['APPENDIX']} appendix rows, and {c['EFFECT_ACK']} EFFECT_ACK claims.\n\n{claim} *Global* is restricted to those registries. OPEN remains OPEN; empirical and interpretive claims are not converted into Lean theorems; future or unregistered prose is outside scope.\n\nMachine-readable authority:\n\n{files}"
def formal_block(inv: dict[str,Any])->str:
    return f"## Current verified coverage\n\nThe locked 62-page manuscript formalization is complete at the formal-environment boundary. The claim graph contains 43 nodes: one locked source anchor and 42 strong Lean bindings. All 20 definitions and all 20 theorem-like environments are closed; six theorem bindings remain explicitly conditional.\n\nThe global ledger includes all {inv['counts']['by_namespace']['MANUSCRIPT']} manuscript graph nodes, all 34 appendix rows, and all 15 EFFECT_ACK claims, with one terminal disposition each. Empirical, interpretive, normative, OPEN and OUT_OF_SCOPE records are preserved without proof inflation.\n\nAuthoritative generated views are `claims/CLAIM_GRAPH.json`, `MANUSCRIPT_PROOF_MAP.md`, `VERIFICATION_REPORT.md`, and the repository-root `GLOBAL_CLAIM_INVENTORY.json`."
def plan_block(final: bool,inv: dict[str,Any])->str:
    tail="The bounded completion transaction is finalized by `GLOBAL_COMPLETION_RECEIPT.json`; OPEN claims remain explicit terminal boundaries." if final else "Exact-head gates, Authority/Mirror promotion and the final completion receipt remain required."
    return f"## Global completion state\n\nState: `{'COMPLETED' if final else 'GLOBAL_FINALIZATION_ACTIVE'}` for `{SCOPE_ID}`.\n\nThe historical theorem tranches below are closed by the current claim graph: 20/20 definitions, 20/20 theorem-like environments, 42 strong Lean bindings and zero pending formal nodes. The broader ledger terminally classifies all {inv['counts']['total']} registered claims.\n\n{tail}"
def status_block(final: bool,inv: dict[str,Any])->str:
    claim="The scoped completion receipt grants `PASS`, `FINAL_PASS`, and transaction-bound `EFFECT_ACK_DONE`." if final else "The global completion candidate is materialized but no final global claim is granted yet."
    return f"## Current global completion authority\n\nThe current registry scope is `{SCOPE_ID}` with {inv['counts']['total']} terminally classified claims. {claim} This supersedes older progress percentages for current completion status; historical snapshot evidence below remains retained."
def ai(final: bool,inv: dict[str,Any])->dict[str,Any]:
    pending=[] if final else ["Run global and manuscript kernel gates on one exact Authority candidate head","Promote the candidate to Authority main","Synchronize the identical tree to Mirror and rerun exact-head gates","Persist an Authority/Mirror equality receipt","Authorize and materialize the scoped global completion receipt"]
    complete=["Define one finite global scope over every explicit registered claim ID",f"Materialize {inv['counts']['total']} uniquely named and terminally classified claims","Generate complete source-to-claim-to-disposition traceability","Bind every kernel-eligible primary claim to an exact-tag Lean receipt","Reconcile README, AI progress, completion plan, proof-map authority and repository status"]
    if final: complete += ["Pass exact-head global, manuscript-kernel and mandatory repository gates on Authority and Mirror","Verify Authority/Mirror content equality and persist the scoped completion receipt"]
    return {"schema":"qikvrt-ai-progress/2.0","operation_id":"global-claim-completion-2026-07-28","scope_id":SCOPE_ID,"repository":AUTH_REPO,"state":"COMPLETED" if final else "RUNNING","percent":100 if final else 80,"current_action":"No remaining action inside the bounded global completion transaction" if final else pending[0],"completed_steps":complete,"pending_steps":pending,"claims":{"PASS":final,"FINAL_PASS":final,"EFFECT_ACK_DONE":final,"fully_kernel_verified_overall_completion":final,"complete_claim_inventory":True,"complete_lean_kernel_coverage":final,"complete_source_claim_proof_traceability":final,"scope_qualified":True},"counts":inv["counts"],"supersedes":{"schema":"qikvrt-ai-progress/1.0","source_git_blob_sha1":"a69cfafbafaff69373fe2fc8933de52512381990","reason":"stale branch-specific 87-percent projection replaced by global scoped status"}}
def fstatus(final: bool,inv: dict[str,Any])->dict[str,Any]: return {"_license":LIC,"schema":"qikvrt_formalization_global_completion_status_v1","scope_id":SCOPE_ID,"state":"FINAL_PASS" if final else "CANDIDATE_MATERIALIZED","manuscript":{"formal_environments":"40/40","definitions":"20/20","theorem_like_environments":"20/20","strong_lean_bindings":42,"conditional_bindings":6,"pending_formal_nodes":0},"global_inventory":inv["counts"],"proof_map":"MANUSCRIPT_PROOF_MAP.md","verification_report":"VERIFICATION_REPORT.md","global_inventory_path":rel(INVENTORY),"global_receipt_path":rel(FINAL_RECEIPT) if final else None}

def validate_terminal_batch_002_receipt(receipt:Mapping[str,Any]) -> None:
    completion=receipt.get("completion_claims")
    validation=receipt.get("validation")
    if (
        receipt.get("schema")!="qikvrt_content_disposition_batch_receipt_v2"
        or receipt.get("batch_id")!="CONTENT-DISPOSITION-BATCH-002"
        or receipt.get("state")!="TERMINALLY_DISPOSITIONED"
        or receipt.get("subject_count")!=6
        or receipt.get("claim_count")!=1489
        or receipt.get("content_change_required_count")!=1
        or receipt.get("next_deterministic_effect")!="CREATE_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER_FOR_BATCH_002"
        or not isinstance(receipt.get("union_id"),str)
        or not isinstance(completion,Mapping)
        or completion.get("batch_002_executed") is not True
        or completion.get("batch_002_terminal_disposition_complete") is not True
        or any(
            completion.get(key) is not False
            for key in (
                "all_content_claims_dispositioned",
                "proof_corpus_published_on_zenodo",
                "pass","final_pass","effect_ack_done",
            )
        )
        or not isinstance(validation,Mapping)
        or validation.get("no_false_completion") is not True
    ):
        raise ValueError("terminal Batch-002 ownership receipt contract mismatch")

def terminal_batch_002_receipt() -> dict[str,Any] | None:
    if not BATCH_002_RECEIPT.exists():
        return None
    receipt=load(BATCH_002_RECEIPT)
    validate_terminal_batch_002_receipt(receipt)
    return receipt

def validate_root_progress_owner(
    progress:Mapping[str,Any],
    global_receipt:Mapping[str,Any],
    batch_002_receipt:Mapping[str,Any] | None=None,
) -> None:
    if batch_002_receipt is None:
        loaded=terminal_batch_002_receipt()
        if loaded is None:
            raise ValueError("root AI progress owner requires terminal Batch-002 evidence")
        batch_002_receipt=loaded
    else:
        validate_terminal_batch_002_receipt(batch_002_receipt)
    if progress.get("schema")!="qikvrt-ai-progress/3.1":
        raise ValueError("root AI progress must use the durable v3 ownership contract")
    if not isinstance(progress.get("operation_id"),str) or not progress["operation_id"]:
        raise ValueError("root AI progress operation owner is missing")
    owner=progress.get("projection_owner")
    if not isinstance(owner,Mapping):
        raise ValueError("root AI progress projection owner is missing")
    tool=owner.get("tool")
    check_command=owner.get("check_command")
    if (
        not isinstance(tool,str)
        or not tool.startswith("tools/")
        or ".." in Path(tool).parts
        or not (ROOT/tool).is_file()
        or not isinstance(check_command,str)
        or tool not in check_command
        or "--check" not in check_command
    ):
        raise ValueError("root AI progress projection owner is not executable or checkable")
    scopes=progress.get("scopes")
    global_scope=scopes.get(SCOPE_ID) if isinstance(scopes,Mapping) else None
    if not isinstance(global_scope,Mapping):
        raise ValueError("root AI progress lost the bounded global completion scope")
    claims=global_scope.get("claims")
    if (
        global_scope.get("state")!="FINAL_PASS"
        or global_scope.get("effect_state")!="EFFECT_ACK_DONE"
        or global_scope.get("evidence")!=rel(FINAL_RECEIPT)
        or not isinstance(claims,Mapping)
        or any(claims.get(key) is not True for key in ("PASS","FINAL_PASS","EFFECT_ACK_DONE"))
    ):
        raise ValueError("root AI progress global scope no longer matches its terminal semantics")
    evidence=global_scope.get("pass_evidence")
    expected_pair=global_receipt.get("candidate_pair")
    expected_checks=global_receipt.get("exact_head_gates")
    expected_equality=global_receipt.get("authority_mirror_equality_receipt_sha256")
    if not isinstance(evidence,Mapping):
        raise ValueError("root AI progress global scope lacks structured PASS evidence")
    evidence_file=evidence.get("evidence")
    evidence_checks=evidence.get("checks")
    exact_runs=(
        evidence_checks.get("exact_head_runs")
        if isinstance(evidence_checks,Mapping) else None
    )
    if (
        not isinstance(evidence_checks,Mapping)
        or evidence_checks.get("receipt_gate_matrix")!=expected_checks
        or not isinstance(evidence_file,Mapping)
        or evidence_file.get("path")!=rel(FINAL_RECEIPT)
        or evidence_file.get("sha256")!=sha(FINAL_RECEIPT.read_bytes())
        or evidence_file.get("finalization_input_path")!=rel(FINAL_INPUT)
        or evidence_file.get("finalization_input_sha256")!=sha(FINAL_INPUT.read_bytes())
        or evidence_file.get("exact_head_run_evidence_path")!=rel(GLOBAL_RUN_EVIDENCE)
        or evidence_file.get("exact_head_run_evidence_sha256")!=sha(GLOBAL_RUN_EVIDENCE.read_bytes())
        or evidence_file.get("candidate_pair")!=expected_pair
        or evidence_file.get("authority_mirror_equality_receipt_sha256")!=expected_equality
        or evidence_file.get("equality_payload_present_in_repository") is not False
    ):
        raise ValueError("root AI progress global PASS evidence drift")
    required_gates={
        "global_completion","manuscript_proof","mandatory_repository_gates",
    }
    expected_run_ids={
        "authority":(30320366228,90154785419),
        "mirror":(30321259580,90157437963),
    }
    if (
        not isinstance(exact_runs,Mapping)
        or set(exact_runs)!=set(expected_run_ids)
        or any(
            not isinstance(exact_runs.get(side),Mapping)
            or (
                exact_runs[side].get("run_id"),
                exact_runs[side].get("job_id"),
            )!=expected_run_ids[side]
            or not isinstance(exact_runs[side].get("gate_steps"),Mapping)
            or set(exact_runs[side]["gate_steps"])!=required_gates
            or any(
                not isinstance(step,Mapping)
                or step.get("conclusion")!="success"
                for step in exact_runs[side]["gate_steps"].values()
            )
            for side in expected_run_ids
        )
    ):
        raise ValueError("root AI progress global exact-head run evidence drift")
    repositories=evidence.get("repository")
    expected_sources={
        AUTH_REPO:expected_pair.get("authority_exact_head") if isinstance(expected_pair,Mapping) else None,
        MIRROR_REPO:expected_pair.get("mirror_exact_head") if isinstance(expected_pair,Mapping) else None,
    }
    expected_refs={
        AUTH_REPO:"actions/runs/30320366228",
        MIRROR_REPO:"actions/runs/30321259580",
    }
    if (
        not isinstance(repositories,list)
        or len(repositories)!=2
        or any(not isinstance(item,Mapping) for item in repositories)
        or {
            item.get("repository"):item.get("source_sha")
            for item in repositories
            if isinstance(item,Mapping)
        }!=expected_sources
        or any(
            item.get("ref_name")!=expected_refs.get(item.get("repository"))
            for item in repositories
            if isinstance(item,Mapping)
        )
    ):
        raise ValueError("root AI progress global repository/ref/SHA binding drift")
    corpus_id=str(batch_002_receipt["union_id"])
    corpus_scope=scopes.get(corpus_id) if isinstance(scopes,Mapping) else None
    if not isinstance(corpus_scope,Mapping):
        raise ValueError("root AI progress lost the terminal Batch-002 corpus scope")
    corpus_counts=corpus_scope.get("counts")
    batch_002=corpus_scope.get("batch_002")
    batch_evidence=batch_002.get("evidence") if isinstance(batch_002,Mapping) else None
    if (
        not isinstance(corpus_counts,Mapping)
        or corpus_counts.get("subjects")!=19
        or not isinstance(corpus_counts.get("dispositioned_subjects"),int)
        or corpus_counts["dispositioned_subjects"]<12
        or not isinstance(batch_002,Mapping)
        or batch_002.get("state")!="TERMINALLY_DISPOSITIONED"
        or batch_002.get("subjects")!=batch_002_receipt["subject_count"]
        or batch_002.get("claims")!=batch_002_receipt["claim_count"]
        or batch_002.get("content_change_required_count")!=batch_002_receipt["content_change_required_count"]
        or not isinstance(batch_evidence,Mapping)
        or batch_evidence.get("path")!=rel(BATCH_002_RECEIPT)
        or batch_evidence.get("sha256")!=sha(BATCH_002_RECEIPT.read_bytes())
    ):
        raise ValueError("root AI progress terminal Batch-002 scope evidence drift")

def outputs()->tuple[dict[Path,str],bool]:
    inv,byid=build_inventory(); ker=build_kernel(inv,byid); tr=build_trace(inv,ker); fin=validate_final(load(FINAL_INPUT)) if FINAL_INPUT.exists() else None; final=fin is not None
    out={SCOPE:pretty(scope()),INVENTORY:pretty(inv),TRACE:pretty(tr),KERNEL:pretty(ker),FSTATUS:pretty(fstatus(final,inv))}
    # The terminal Batch-002 receipt cedes root projection to an explicit,
    # checkable owner. The owner is intentionally generic so a later workflow
    # can supersede it while retaining the separately bounded global scope.
    batch_002=terminal_batch_002_receipt()
    if batch_002 is None:
        out[AI]=pretty(ai(final,inv))
    else:
        if not final or not FINAL_RECEIPT.exists():
            raise ValueError("terminal Batch-002 ownership requires the bounded global completion receipt")
        validate_root_progress_owner(load(AI),load(FINAL_RECEIPT),batch_002)
    if fin: out[FINAL_RECEIPT]=pretty(completion_receipt(fin,inv,tr,ker))
    out[README]=marked(README.read_text(encoding="utf-8"),"global-completion",root_block(final,inv),"![QIK-VRT — five-state auditable effect release](docs/assets/qikvrt-social-preview.png)")
    fr=FREADME.read_text(encoding="utf-8").replace("# QIK-VRT manuscript formalization v2.0 (work in progress)","# QIK-VRT manuscript formalization v2.0",1)
    if "<!-- qikvrt-global-formalization-coverage:start -->" in fr: fr=marked(fr,"global-formalization-coverage",formal_block(inv),"# QIK-VRT manuscript formalization v2.0")
    else:
        pat=re.compile(r"## Current verified coverage\n.*?(?=\n## Reproducible checks)",re.S)
        if not pat.search(fr): raise ValueError("formalization README coverage section missing")
        fr=pat.sub(block("global-formalization-coverage",formal_block(inv)),fr,count=1)
    out[FREADME]=fr
    pl=PLAN.read_text(encoding="utf-8"); pl=re.sub(r"(?m)^Status: .+$","Status: COMPLETED" if final else "Status: GLOBAL_FINALIZATION_ACTIVE",pl,count=1); pl=pl.replace("## Remaining theorem tranches","## Completed theorem tranches (historical plan)",1)
    out[PLAN]=marked(pl,"global-completion-plan",plan_block(final,inv),"Responsible human: Ingolf Lohmann")
    out[STATUS]=marked(STATUS.read_text(encoding="utf-8"),"global-completion-status",status_block(final,inv),"# Verification status")
    return out,final
def write_or_check(p:Path,text:str,check:bool)->bool:
    if check:
        if not p.exists(): print(f"BLOCK missing generated file: {rel(p)}",file=sys.stderr); return False
        if p.read_text(encoding="utf-8")!=text: print(f"BLOCK stale generated file: {rel(p)}",file=sys.stderr); return False
        return True
    p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists() or p.read_text(encoding="utf-8")!=text: p.write_text(text,encoding="utf-8",newline="\n")
    return True
def verify_tag()->None:
    k=load(KERNEL); local=subprocess.check_output(["git","rev-parse",f"{TAG}^{{commit}}"],cwd=ROOT,text=True).strip(); tree=subprocess.check_output(["git","rev-parse",f"{TAG}^{{tree}}"],cwd=ROOT,text=True).strip()
    if local!=AUTH_TAG or tree!=TAG_TREE: raise ValueError("Authority exact tag identity differs")
    for path in k["tag_protected_paths"]:
        old=subprocess.check_output(["git","rev-parse",f"{TAG}:{path}"],cwd=ROOT,text=True).strip(); new=subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],cwd=ROOT,text=True).strip()
        if old!=new: raise ValueError(f"exact-tag protected blob changed: {path}")
    remote=subprocess.check_output(["git","ls-remote","--tags","https://github.com/ingolf-lohmann/qik-vrt.git",f"refs/tags/{TAG}^{{}}"],cwd=ROOT,text=True).strip()
    if not remote or remote.split()[0]!=MIRROR_TAG: raise ValueError("Mirror exact annotated tag differs")

# Audit is additive: historical completion/disposition is never proof authority here.
AUDIT_DOMAINS = {"FORMAL", "EMPIRICAL", "NORMATIVE", "INTERPRETIVE", "DOCUMENTARY", "SIMULATION", "RELIGIOUS", "METAPHYSICAL"}
AUDIT_CLASSES = {"HYPOTHESIS", "ASSERTION", "THEOREM", "ASSUMPTION", "DEFINITION", "NORMATIVE_REQUIREMENT", "INTERPRETATION"}
INVARIANT_CLASSES = {"FORMAL", "STRUCTURAL", "STATE", "TEMPORAL", "SECURITY", "EPISTEMIC", "RUNTIME"}
NON_IMPLICATIONS = (("SIMULATION", "OBSERVATION"), ("PREDICTION", "EFFECT"),
                    ("TRANSPORT_ACK", "EFFECT_ACK"), ("AUTHORITY", "TRUTH"),
                    ("CORRELATION", "CAUSALITY"), ("BELIEF", "EMPIRICAL_PROOF"))
REALITY_STATEMENT = "Claims about reality require evidence from reality."
LEAN_VERSION = "4.19.0"
LEAN_GITHASH = "6caaee842e9495688c1567e78c0e68dbb96942aa"
LEAN_BINARY_SHA256 = "92c3d35b5bfaa5e0fea413a775d504cf46cd95e1345df61c2274f76779e7e023"
LEAN_KERNEL_SHA256 = "2ab605c74c78f9ba4431a7b5305a4b28a9071d8a826f223eb14fe5530f78e14d"
LEAN_AXIOMS = ["Classical.choice", "Quot.sound", "propext"]
LEAN_REPLAY = ROOT / "third_party/lean4checker/Replay.lean"
LEAN_CHECKER = ROOT / "tools/lean/ClaimKernel.lean"
LEAN_VERIFIER_VERSION = "1.1.0"
LEAN_SEMANTICS = {
    "MANUSCRIPT::SET-001": "The relative class and its relative complement form a complete disjoint partition.",
    "MANUSCRIPT::SET-003": "The complement partition is independent of ambient dimension.",
}


def audit_subject(root: Path) -> dict[str, Any]:
    try:
        binding = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD", "HEAD^{tree}"],
                                          stderr=subprocess.DEVNULL, text=True).splitlines()
        return {"head_sha":binding[0], "tree_sha":binding[1],
                "working_copy_dirty":bool(subprocess.check_output(
                    ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"], text=True))}
    except subprocess.CalledProcessError:
        return {"state":"GIT_SUBJECT_UNBOUND"}


def kernel_plan(value: dict[str, Any], *, root: Path, subject: dict[str, Any]) -> list[dict[str, Any]]:
    """Resolve only primary, registered formal bindings; never use caller proof metadata."""
    if root.resolve() != ROOT.resolve(): raise ValueError("kernel adapter must run from the candidate's controller")
    if subject.get("working_copy_dirty") is not False: raise ValueError("kernel candidate is not a clean Git subject")
    admission = audit_json((root/"policy/QIKVRT_CLAIM_AUDIT_V1.json").read_text())["verifier_admission"]
    if not isinstance(admission, dict) or admission.get("formal") != "INDEPENDENT_LEAN_KERNEL_V1" or admission.get("foundational_axiom_allowlist") != LEAN_AXIOMS:
        raise ValueError("formal verifier is not admitted by the exact candidate policy")
    if admission.get("version") != LEAN_VERIFIER_VERSION or admission.get("supported_claims") != LEAN_SEMANTICS:
        raise ValueError("unsupported formal verifier semantics or version")
    if admission.get("implementation") != identity(LEAN_CHECKER):
        raise ValueError("admitted independent verifier code hash differs")
    inv, byid = build_inventory()
    if audit_json(INVENTORY.read_text()) != inv: raise ValueError("stale candidate claim inventory")
    kernel = build_kernel(inv, byid)
    if audit_json(KERNEL.read_text()) != kernel: raise ValueError("stale or altered kernel receipt")
    if kernel["verification_policy"]["foundational_axiom_allowlist"] != LEAN_AXIOMS:
        raise ValueError("kernel axiom policy differs")
    # Authority and Mirror have different historical commits and the same frozen tree.
    tag = subprocess.check_output(["git", "rev-parse", f"{TAG}^{{commit}}", f"{TAG}^{{tree}}"], cwd=root, text=True).splitlines()
    if tag[0] not in {AUTH_TAG, MIRROR_TAG} or tag[1] != TAG_TREE: raise ValueError("stale exact source tag")
    for path in kernel["tag_protected_paths"]:
        tagged = subprocess.check_output(["git", "show", f"{TAG}:{path}"], cwd=root)
        candidate = subprocess.check_output(["git", "show", f"{subject['head_sha']}:{path}"], cwd=root)
        if tagged != candidate or candidate != (root/path).read_bytes():
            raise ValueError(f"exact-tag source differs: {path}")
    registered = {c["claim_id"]:c for c in normalize_audit_input(inv)["claims"]}
    primary = {r["inventory_id"]:r for r in kernel["primary_receipts"]}
    plan = []
    for claim in normalize_audit_input(value)["claims"]:
        cid = claim.get("claim_id")
        if claim.get("epistemic_domain") != "FORMAL" or cid not in LEAN_SEMANTICS or cid not in primary: continue
        canonical = registered[cid]
        if canonical["claim_statement"] != LEAN_SEMANTICS[cid]:
            raise ValueError(f"unsupported formal statement semantics: {cid}")
        if any(claim.get(key) != canonical[key] for key in ("claim_statement", "epistemic_domain", "claim_class", "sources")):
            raise ValueError(f"claim differs from its registered formal binding: {cid}")
        receipt = primary[cid]
        constants = sorted(set(receipt["proof_constants"] + [c for c in
                           (receipt["statement_constant"], receipt["registry_constant"]) if c is not None]))
        if not constants or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", c) for c in constants):
            raise ValueError(f"invalid proof/registry constant: {cid}")
        registered_objects = receipt.get("compiled_objects", [receipt.get("compiled_object")])
        objects = [path for path in registered_objects if path is not None]
        source = Path(receipt["source"]["path"]).relative_to(rel(FORM)).as_posix()
        expected_object = ".lake/build/lib/lean/" + str(Path(source).with_suffix(".olean"))
        # Frozen receipts did not record an object for every strong binding.
        # The runtime receipt must bind the actual freshly compiled source
        # module; an absent historical field cannot replace that object.
        objects = sorted(set(objects + [expected_object]))
        origins = {c:Path(source).with_suffix("").as_posix().replace("/", ".") for c in
                   receipt["proof_constants"] + ([receipt["statement_constant"]] if receipt["statement_constant"] else [])}
        if receipt["registry_source"]:
            registry = Path(receipt["registry_source"]["path"]).relative_to(rel(FORM)).as_posix()
            objects = sorted(set(objects + [".lake/build/lib/lean/" + str(Path(registry).with_suffix(".olean"))]))
            if receipt["registry_constant"]: origins[receipt["registry_constant"]] = Path(registry).with_suffix("").as_posix().replace("/", ".")
        plan.append({"claim_id":cid, "claim_statement":claim["claim_statement"], "epistemic_domain":"FORMAL",
                     "proof_constants":receipt["proof_constants"], "constants":constants,
                     "receipt":receipt, "kernel_receipt_sha256":sha(pretty(receipt).encode()), "objects":objects,
                     "primary_proof_object":expected_object, "constant_modules":origins})
    return plan


def kernel_command(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=240)
    if result.returncode:
        raise ValueError(f"Lean kernel command failed ({result.returncode}): {(result.stdout+result.stderr)[-4000:]}")
    return result.stdout.strip()


def fresh_lean_kernel(plan: list[dict[str, Any]], *, root: Path, head: str,
                      context: dict[str, Any]) -> dict[str, Any]:
    """Compile exact candidate bytes in a new directory, then replay objects in another process."""
    env = {k:v for k,v in os.environ.items() if k not in {"LEAN_PATH", "LEAN_SRC_PATH", "LEAN_SYSROOT"}}
    if not shutil.which("lake"): raise FileNotFoundError("locked Lean/Lake runtime unavailable")
    version = kernel_command(["lake", "env", "lean", "--version"], cwd=FORM, env=env)
    githash = kernel_command(["lake", "env", "lean", "--githash"], cwd=FORM, env=env)
    if f"version {LEAN_VERSION}," not in version or githash != LEAN_GITHASH:
        raise ValueError("Lean runtime differs from the admitted toolchain")
    prefix = Path(kernel_command(["lake", "env", "lean", "--print-prefix"], cwd=FORM, env=env))
    lean = prefix / "bin/lean"
    library = prefix / "lib/lean/libleanshared.so"
    if sha(lean.read_bytes()) != LEAN_BINARY_SHA256 or sha(library.read_bytes()) != LEAN_KERNEL_SHA256:
        raise ValueError("native Linux x64 Lean kernel bytes differ from the admitted release")
    runtime = {"version":version, "githash":githash, "binary_sha256":LEAN_BINARY_SHA256,
               "kernel_library_sha256":LEAN_KERNEL_SHA256}
    # Never restore compiled project objects, including those in the caller's working copy.
    with tempfile.TemporaryDirectory(prefix="qikvrt-claim-kernel-") as directory:
        project = Path(directory)/"project"
        project.mkdir()
        paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", head, "--", rel(FORM)], cwd=root, text=True).splitlines()
        sources = []
        for path in paths:
            relative = Path(path).relative_to(rel(FORM))
            if relative.suffix != ".lean" and relative.as_posix() not in {"lakefile.toml", "lake-manifest.json", "lean-toolchain"}: continue
            raw = subprocess.check_output(["git", "show", f"{head}:{path}"], cwd=root)
            if raw != (root/path).read_bytes(): raise ValueError(f"candidate bytes changed: {path}")
            target = project/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            sources.append({"path":path, "sha256":sha(raw), "git_blob_sha1":blob(raw)})
        kernel_command(["lake", "build", "QIKVRTFormalization", "QIKVRTEffectAck"], cwd=project, env=env)
        objects = {}
        for path in sorted({path for item in plan for path in item["objects"]}):
            if not isinstance(path, str) or Path(path).is_absolute() or ".." in Path(path).parts:
                raise ValueError("unsafe compiled object path")
            raw = (project/path).read_bytes()
            previous = FORM/path
            if any(p.is_symlink() for p in (previous, *previous.parents)): raise ValueError("symlink in compiled object path")
            if previous.exists() and (previous.is_symlink() or previous.read_bytes() != raw):
                raise ValueError(f"altered compiled proof object: {path}")
            objects[path] = {"path":path, "bytes":len(raw), "sha256":sha(raw)}
        engine = Path(directory)/"engine"
        engine.mkdir()
        kernel_command([str(lean), "-o", str(engine/"Replay.olean"), str(LEAN_REPLAY)], cwd=LEAN_REPLAY.parent, env=env)
        request = Path(directory)/"plan.json"
        request.write_text(pretty({"context":context, "claims":[{k:item[k] for k in
            ("claim_id", "claim_statement", "epistemic_domain", "proof_constants", "constants", "constant_modules")} for item in plan]}))
        checker_env = {**env, "LEAN_SYSROOT":str(prefix),
                       "LEAN_PATH":os.pathsep.join((str(engine), str(project/".lake/build/lib/lean")))}
        output = kernel_command([str(lean), "--run", str(LEAN_CHECKER), str(request)], cwd=project, env=checker_env)
        kernel = audit_json(output)
        if kernel.get("schema") != "qikvrt_independent_lean_kernel_v1" or kernel.get("trust_level") != 0 or kernel.get("project_declarations_rechecked", 0) < 1:
            raise ValueError("independent kernel receipt malformed")
        if kernel.get("context") != context:
            raise ValueError("independent kernel result input/subject/invocation binding differs")
        expected = {item["claim_id"]:item for item in plan}
        observed = kernel.get("claims", [])
        if len(observed) != len(expected) or {item["claim_id"] for item in observed} != set(expected):
            raise ValueError("independent kernel receipt claim coverage differs")
        for item in observed:
            observations = item["constants"]
            if len(observations) != len(expected[item["claim_id"]]["constants"]) or {c["constant"] for c in observations} != set(expected[item["claim_id"]]["constants"]):
                raise ValueError("kernel proof/registry constant coverage differs")
            if any(set(c["axioms"]) - set(LEAN_AXIOMS) for c in observations): raise ValueError("kernel receipt contains forbidden axioms")
        for path, bound in objects.items():
            if sha((project/path).read_bytes()) != bound["sha256"]: raise ValueError("proof object changed during kernel replay")
        return {"runtime":runtime, "source_snapshot":sources, "compiled_objects":objects,
                "kernel":kernel, "kernel_output_sha256":sha(output.encode()), "fresh_build_exit_code":0}


def formal_kernel_audit(value: dict[str, Any], *, root: Path, expected_head: str, expected_tree: str,
                        execution_id: str, input_bytes: bytes) -> dict[str, Any]:
    binding = audit_input_binding(value, input_bytes, require_exact=True)
    if not all(isinstance(x, str) and re.fullmatch(r"[0-9a-f]{40}", x) for x in (expected_head, expected_tree)):
        raise ValueError("Lean verification requires an exact expected HEAD and TREE")
    if not isinstance(execution_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,240}", execution_id):
        raise ValueError("Lean verification requires an executor-bound execution ID")
    subject = audit_subject(root)
    if subject.get("head_sha") != expected_head or subject.get("tree_sha") != expected_tree:
        raise ValueError("Lean verification candidate differs from the expected HEAD/TREE")
    context = {"verifier_id":"INDEPENDENT_LEAN_KERNEL_V1", "verifier_version":LEAN_VERIFIER_VERSION,
               "execution_id":execution_id, "execution_subject":subject, "input_binding":binding,
               "checker_binding":identity(LEAN_CHECKER), "replay_binding":identity(LEAN_REPLAY)}
    result = {**context, "input_sha256":binding["sha256"],
              "status":"HOLD", "reason":"NO_ADMITTED_PRIMARY_FORMAL_CLAIM", "claims":[],
              "scope":"RELATIVE_COMPLEMENT_PARTITION_ONLY", "external_effect":False, "effect_ack_done":False}
    try:
        plan = kernel_plan(value, root=root, subject=subject)
        if not plan: return result
        evidence = fresh_lean_kernel(plan, root=root, head=expected_head, context=context)
        if (audit_subject(root) != subject or kernel_plan(value, root=root, subject=subject) != plan
                or identity(LEAN_CHECKER) != context["checker_binding"] or identity(LEAN_REPLAY) != context["replay_binding"]):
            raise ValueError("candidate, source tag or receipt changed during kernel verification")
        native = {c["claim_id"]:c for c in evidence["kernel"]["claims"]}
        result.update(status="PASS", reason="FRESH_NATIVE_KERNEL_REPLAY", evidence=evidence,
                      claims=[{**item, "execution_id":execution_id, "execution_subject":subject,
                               "input_sha256":result["input_sha256"], "input_binding":binding,
                               "verifier_id":context["verifier_id"], "verifier_version":LEAN_VERIFIER_VERSION,
                               "checker_binding":context["checker_binding"], "native_kernel_result":native[item["claim_id"]],
                               "compiled_objects":[evidence["compiled_objects"][path] for path in item["objects"]]} for item in plan],
                      kernel_receipts_binding=identity(KERNEL), replay_binding=identity(LEAN_REPLAY), checker_binding=identity(LEAN_CHECKER))
    except FileNotFoundError as exc:
        result.update(reason="LEAN_RUNTIME_OR_INPUT_UNAVAILABLE", diagnostic=str(exc))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result.update(status="FAIL", reason="LEAN_KERNEL_BINDING_OR_REPLAY_FAILED", diagnostic=str(exc))
    result["receipt_sha256"] = sha(pretty(result).encode())
    return result


def audit_json(raw: str) -> dict[str, Any]:
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value: raise ValueError(f"duplicate audit JSON key: {key}")
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite audit JSON")))
    if not isinstance(value, dict): raise ValueError("audit input must be an object")
    return value


def audit_input_binding(value: dict[str, Any], raw: bytes | None, *, require_exact: bool = False) -> dict[str, Any]:
    if raw is None:
        if require_exact: raise ValueError("formal verification requires the exact input bytes")
        raw = pretty(value).encode("utf-8")
        representation = "GENERATED_CANONICAL_JSON"
    else:
        if not isinstance(raw, bytes): raise ValueError("audit input bytes must be immutable bytes")
        if pretty(audit_json(raw.decode("utf-8"))) != pretty(value):
            raise ValueError("exact input bytes differ from the parsed audit value")
        representation = "EXACT_INPUT_BYTES"
    return {"sha256":sha(raw), "bytes":len(raw), "git_blob_sha1":blob(raw), "representation":representation}


def audit_reference(ref: Any, root: Path) -> dict[str, Any]:
    result = {"evidence_present": False, "evidence_hash_valid": False,
              "evidence_source_known": False, "kind": None, "binding": ref}
    if not isinstance(ref, dict): return result
    path, digest = ref.get("path"), ref.get("sha256")
    if not isinstance(path, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest): return result
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts: return result
    target = root / candidate
    if any(part.is_symlink() for part in (target, *target.parents)) or not target.is_file(): return result
    if not target.resolve().is_relative_to(root.resolve()): return result
    raw = target.read_bytes()
    result.update(evidence_present=True, evidence_hash_valid=sha(raw)==digest,
                  evidence_source_known=isinstance(ref.get("source"), str) and bool(ref["source"].strip()),
                  kind=ref.get("kind"), actual_sha256=sha(raw), bytes=len(raw), git_blob_sha1=blob(raw))
    return result


def normalize_audit_input(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema") == "qikvrt_claim_audit_input_v1": return value
    if value.get("schema") != "qikvrt_global_claim_inventory_v1": raise ValueError("unsupported audit input schema")
    domains = {"MATHEMATICAL":"FORMAL", "CONDITIONAL":"FORMAL", "DEFINITION":"FORMAL",
               "ASSUMPTION":"FORMAL", "FORMAL_PROTOCOL":"FORMAL", "FORMAL_THEOREM":"FORMAL",
               "EMPIRICAL":"EMPIRICAL", "EMPIRICAL_PHYSICS":"EMPIRICAL", "SOURCE":"DOCUMENTARY",
               "BACKGROUND":"DOCUMENTARY", "VALUE_PREMISE":"NORMATIVE", "NORMATIVE_PROTOCOL":"FORMAL",
               "COUNTEREXAMPLE":"FORMAL", "INFORMATION_THEOREM":"FORMAL", "CONDITIONAL_SOFTWARE_THEOREM":"FORMAL",
               "CONDITIONAL_CYBERPHYSICAL_THEOREM":"FORMAL", "IMPLEMENTATION_CONFORMANCE":"EMPIRICAL", "TOTALITY_CLAIM":"FORMAL"}
    claims = []
    for item in value.get("claims", []):
        category = item.get("epistemic_category")
        domain = domains.get(category, category)
        klass = "THEOREM" if item.get("terminal_disposition") in {"KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL"} else (
            "NORMATIVE_REQUIREMENT" if domain == "NORMATIVE" else "INTERPRETATION" if domain == "INTERPRETIVE" else "HYPOTHESIS" if item.get("terminal_disposition") == "OPEN" else "ASSERTION")
        claims.append({"claim_id":item.get("inventory_id"), "claim_statement":item.get("statement"),
                       "epistemic_domain":domain, "claim_class":klass,
                       "sources":[{**ref, "source":ref.get("path"), "kind":"DOCUMENTARY"} for ref in item.get("source_refs", [])],
                       "evidence":[], "historical_disposition":item.get("terminal_disposition"),
                       "historical_epistemic_category":category, "domain_mapping_scope":"REGISTERED_FORMAL_MODEL_OR_DECLARED_SOURCE_DOMAIN"})
    return {"schema":"qikvrt_claim_audit_input_v1", "claims":claims, "invariants":[], "relations":[]}


def claim_audit(value: dict[str, Any], *, root: Path = ROOT, timestamp: str,
                formal_verifier: bool = False, expected_head: str | None = None,
                expected_tree: str | None = None, execution_id: str | None = None,
                input_bytes: bytes | None = None) -> dict[str, Any]:
    from datetime import datetime
    if datetime.fromisoformat(timestamp.replace("Z", "+00:00")).tzinfo is None: raise ValueError("audit timestamp requires timezone")
    data = normalize_audit_input(value)
    input_binding = audit_input_binding(value, input_bytes, require_exact=formal_verifier)
    formal = formal_kernel_audit(value, root=root, expected_head=expected_head,
                                expected_tree=expected_tree, execution_id=execution_id,
                                input_bytes=input_bytes) if formal_verifier else None
    formal_claims = {c["claim_id"]:c for c in formal["claims"]} if formal and formal["status"] == "PASS" else {}
    claims, invariants, relations = (data.get(key, []) for key in ("claims", "invariants", "relations"))
    if any(not isinstance(arr, list) or any(not isinstance(x, dict) for x in arr) for arr in (claims, invariants, relations)):
        raise ValueError("audit claims, invariants and relations must be arrays of objects")
    if any(x.get("invariant_id", x.get("id")) == "INV_REALITY_001" for x in invariants):
        raise ValueError("INV_REALITY_001 is engine-owned and cannot be overridden")
    ids = [c.get("claim_id") for c in claims]
    identifiers = Counter(x for x in ids if isinstance(x, str))
    graph = {}
    for edge in relations:
        if edge.get("relation") not in {"IMPLIES", "NOT_IMPLIES"} or not all(isinstance(edge.get(k), str) and edge[k] for k in ("subject", "object")):
            raise ValueError("malformed non-implication relation")
        if edge["relation"] == "IMPLIES": graph.setdefault(edge["subject"], set()).add(edge["object"])
    def reachable(start, end):
        seen, pending = set(), list(graph.get(start, []))
        while pending:
            node = pending.pop()
            if node == end: return True
            if node not in seen: seen.add(node); pending.extend(graph.get(node, []))
        return False
    denied = set(NON_IMPLICATIONS) | {(e["subject"], e["object"]) for e in relations if e["relation"] == "NOT_IMPLIES"}
    edges = [{"subject":s, "relation":"NOT_IMPLIES", "object":o, "violated":reachable(s,o)} for s,o in sorted(denied)]
    receipts = []
    for index, claim in enumerate(claims):
        cid, domain, klass = (claim.get(k) for k in ("claim_id", "epistemic_domain", "claim_class"))
        checklist = {"claim_exists":True, "claim_identifier_unique":isinstance(cid,str) and bool(cid.strip()) and identifiers[cid]==1,
                     "claim_class_present":klass in AUDIT_CLASSES, "domain_present":domain in AUDIT_DOMAINS,
                     "statement_present":isinstance(claim.get("claim_statement"),str) and bool(claim["claim_statement"].strip())}
        consistent = ((klass != "THEOREM" or domain == "FORMAL") and
                      (klass != "NORMATIVE_REQUIREMENT" or domain == "NORMATIVE") and
                      (klass != "INTERPRETATION" or domain == "INTERPRETIVE"))
        sources, evidence = claim.get("sources", []), claim.get("evidence", [])
        if not isinstance(sources,list) or not isinstance(evidence,list): raise ValueError("claim sources/evidence must be arrays")
        refs = [audit_reference(ref, root) for ref in sources]
        erefs = [audit_reference(ref, root) for ref in evidence]
        requested = claim.get("required_verifiers", [])
        if not isinstance(requested, list) or any(not isinstance(v, str) for v in requested):
            raise ValueError("required_verifiers must be an array of strings")
        unadmitted = any(v != "FORMAL" for v in requested)
        required = domain in {"FORMAL", "EMPIRICAL"} or klass == "THEOREM" or bool(requested)
        hashes_valid = bool(erefs) and all(r["evidence_present"] and r["evidence_hash_valid"] for r in erefs)
        origin_known = bool(erefs) and all(r["evidence_source_known"] for r in erefs)
        bound = hashes_valid and origin_known
        reality_evidence = bound and all(r["kind"] == "OBSERVATION" for r in erefs)
        category_error = (domain == "EMPIRICAL" and bool(erefs) and not reality_evidence) or not consistent
        # Digests and declared origins bind bytes, never authenticate truth or a verifier.
        verification = {"formal_verified":False, "empirical_verified":False, "peer_reviewed":False, "reproduced":False}
        kernel_binding = formal_claims.get(cid) if isinstance(cid, str) and domain == "FORMAL" else None
        formal_verified = bool(kernel_binding) and all(checklist.values()) and consistent
        verification["formal_verified"] = formal_verified
        runtime = claim.get("runtime", {})
        if not isinstance(runtime,dict): raise ValueError("claim runtime must be an object")
        runtime_audit = {"rule_present":bool(runtime), "rule_executable":False,
                         "runtime_violation":False, "status":"NOT_OBSERVED"}
        observed = {"predicted":None, "executed":None, "observed":None, "readback":None, "effect_ack":False}
        reality_refs = claim.get("observed_reality", {})
        if not isinstance(reality_refs,dict): raise ValueError("observed_reality must be an object")
        reality_bindings = {}
        for key in ("predicted", "executed", "observed", "readback"):
            if key in reality_refs:
                binding = audit_reference(reality_refs[key], root)
                reality_bindings[key] = binding
                observed[key] = binding if binding["evidence_hash_valid"] else None
        if reality_bindings:
            runtime_audit["status"] = "BOUND_ARTIFACTS_ONLY_INDEPENDENT_VERIFICATION_OPEN"
        # A caller-supplied verification flag or ACK cannot enter the output as proof.
        reasons = []
        if not all(checklist.values()): reasons.append("MALFORMED_OR_DUPLICATE_CLAIM")
        if category_error: reasons.append("CATEGORY_ERROR")
        if any(not r["evidence_hash_valid"] for r in refs+erefs+list(reality_bindings.values())): reasons.append("SOURCE_OR_EVIDENCE_BINDING_INVALID")
        if formal and formal["status"] == "FAIL" and domain == "FORMAL": reasons.append(formal["reason"])
        state = "FAIL" if reasons else "HOLD" if (required and not formal_verified) or unadmitted else "PASS"
        if not refs and state != "FAIL": state = "HOLD"; reasons.append("CLAIM_SOURCE_NOT_BOUND")
        if any(not r["evidence_source_known"] for r in refs+erefs) and state != "FAIL":
            state = "HOLD"; reasons.append("SOURCE_ORIGIN_UNESTABLISHED")
        if state == "HOLD": reasons.append("INDEPENDENT_VERIFICATION_NOT_ESTABLISHED")
        if state == "HOLD" and formal and domain == "FORMAL" and cid not in LEAN_SEMANTICS:
            reasons.append("UNSUPPORTED_FORMAL_SEMANTICS")
        if unadmitted: reasons.append("REQUESTED_VERIFIER_NOT_ADMITTED")
        result = {"claim_exists":True, "claim_well_formed":all(checklist.values()), "domain_consistent":consistent,
                  "evidence_present":bool(erefs) or formal_verified, "verification_sufficient":formal_verified and state == "PASS", "runtime_applicable":False}
        receipts.append({"schema":"qikvrt_claim_audit_v1", "audit_id":f"AUDIT_{index+1:06d}", "claim_id":cid,
                         "timestamp":timestamp, "epistemic_domain":domain, "claim_class":klass,
                         "claim_statement":claim.get("claim_statement"), "audit_result":result,
                         "claim_checklist":checklist, "evidence_checklist":{"evidence_required":required,
                         "evidence_present":bool(erefs) or formal_verified, "evidence_hash_valid":hashes_valid or formal_verified, "evidence_source_known":origin_known or formal_verified},
                         "verification_checklist":verification, "epistemic_audit":{"category_error":category_error,
                         "mixed_domains":not consistent, "improper_inference":False, "scope":"DECLARED_TYPES_AND_STRUCTURED_EDGES_ONLY"},
                         "source_bindings":refs, "evidence_bindings":erefs, "runtime_audit":runtime_audit,
                         "observed_reality_audit":observed, "status":state,
                         "severity":"ERROR" if state=="FAIL" else "NOTICE" if state=="HOLD" else "INFO",
                         "reasons":reasons, "historical_disposition":claim.get("historical_disposition"),
                         "historical_epistemic_category":claim.get("historical_epistemic_category"),
                         "domain_mapping_scope":claim.get("domain_mapping_scope"), "formal_kernel_receipt":kernel_binding})
    invariant_receipts = []
    invariant_ids = [i.get("invariant_id",i.get("id")) for i in invariants]
    for invariant in invariants:
        iid = invariant.get("invariant_id", invariant.get("id"))
        klass, statement, predicate = invariant.get("class"), invariant.get("statement"), invariant.get("predicate", {})
        well_formed = isinstance(iid,str) and bool(iid) and invariant_ids.count(iid)==1 and klass in INVARIANT_CLASSES and isinstance(statement,str) and bool(statement)
        state, reason = ("HOLD","EXECUTABLE_PREDICATE_NOT_ESTABLISHED") if well_formed else ("FAIL","MALFORMED_OR_DUPLICATE_INVARIANT")
        executable = False
        invariant_bindings = []
        if well_formed and isinstance(predicate,dict) and predicate.get("type") == "SET_SUBSET":
            refs = [audit_reference(predicate.get(k),root) for k in ("old", "new")]
            invariant_bindings = refs
            if all(r["evidence_hash_valid"] and r["evidence_source_known"] for r in refs):
                values = [audit_json((root/predicate[k]["path"]).read_text()).get(predicate.get("field","nodes")) for k in ("old","new")]
                if all(isinstance(v,list) and all(isinstance(x,str) for x in v) for v in values):
                    executable = True; state = "PASS" if set(values[0]) <= set(values[1]) else "FAIL"; reason = "BOUND_SET_COMPARISON"
                else: state, reason = "FAIL", "INVALID_SET_OPERANDS"
            else: state, reason = "FAIL", "INVARIANT_SOURCE_BINDING_INVALID"
        elif well_formed and isinstance(predicate,dict) and predicate.get("type") == "NON_IMPLICATION":
            if not all(isinstance(predicate.get(k),str) and predicate[k] for k in ("subject","object")):
                raise ValueError("non-implication predicate requires bound subject and object")
            executable = True
            state = "FAIL" if reachable(predicate["subject"],predicate["object"]) else "PASS"
            reason = "STRUCTURED_GRAPH_REACHABILITY_ONLY"
        invariant_receipts.append({"schema":"qikvrt_invariant_audit_v1", "invariant_id":iid, "class":klass,
                                   "statement":statement, "status":state, "reason":reason,
                                   "predicate":predicate, "source_bindings":invariant_bindings,
                                   "severity":"ERROR" if state=="FAIL" else "NOTICE" if state=="HOLD" else "INFO",
                                   "runtime_audit":{"rule_present":well_formed, "rule_executable":executable,
                                                    "runtime_violation":state=="FAIL" and executable}})
    reality_ok = not any(r["epistemic_audit"]["category_error"] for r in receipts) and not any(e["violated"] for e in edges)
    invariant_receipts.append({"schema":"qikvrt_invariant_audit_v1", "invariant_id":"INV_REALITY_001", "class":"EPISTEMIC",
                               "statement":REALITY_STATEMENT, "status":"FAIL" if not reality_ok else "HOLD" if any(r["status"]=="HOLD" for r in receipts) else "PASS",
                               "reason":"DECLARED_REALITY_EVIDENCE_BOUNDARY_ONLY"})
    summary = {"claims_checked":len(receipts), "claims_passed":sum(r["status"]=="PASS" for r in receipts),
               "claims_failed":sum(r["status"]=="FAIL" for r in receipts), "claims_held":sum(r["status"]=="HOLD" for r in receipts),
               "invariants_checked":len(invariant_receipts), "invariants_failed":sum(r["status"]=="FAIL" for r in invariant_receipts),
               "invariants_held":sum(r["status"]=="HOLD" for r in invariant_receipts),
               "category_errors":sum(r["epistemic_audit"]["category_error"] for r in receipts), "non_implication_violations":sum(e["violated"] for e in edges)}
    execution_subject = audit_subject(root)
    report = {"schema":"qikvrt_claim_audit_report_v1", "timestamp":timestamp,
              "execution_subject":execution_subject, "auditor_binding":identity(Path(__file__)),
              "policy_binding":identity(ROOT/"policy/QIKVRT_CLAIM_AUDIT_V1.json"),
              "policy_id":"QIKVRT_CLAIM_AUDIT_V1",
              "input_sha256":input_binding["sha256"], "input_binding":input_binding, "audit_summary":summary,
              "formal_verifier":formal,
              "claims":receipts, "invariants":invariant_receipts, "non_implication_audit":edges,
              "audit_of_audit":{"sources_traceable":all(bool(r["source_bindings"]) and all(x["evidence_hash_valid"] and x["evidence_source_known"] for x in r["source_bindings"]+r["evidence_bindings"]) for r in receipts) and all(all(x["evidence_hash_valid"] and x["evidence_source_known"] for x in i.get("source_bindings",[])) for i in invariant_receipts),
                                "epistemic_domain_checked":True, "category_error_checked":True, "non_implication_checked":True, "reality_boundary_checked":True},
              "boundaries":{"effect_ack_done":False, "external_effect":False, "audit_pass_is_claim_truth":False, "historical_evidence_transfer":False,
                            "origin_declaration_is_authentication":False, "natural_language_semantics_verified":False}}
    report["report_sha256"] = sha(pretty(report).encode())
    return report


def verify_claim_audit(report: dict[str, Any], value: dict[str, Any], *, root: Path = ROOT,
                       formal_verifier: bool = False, expected_head: str | None = None,
                       expected_tree: str | None = None, execution_id: str | None = None,
                       input_bytes: bytes | None = None) -> bool:
    # One finite recomputation audits this output; no recursive proof inflation.
    try: binding = audit_input_binding(value, input_bytes, require_exact=formal_verifier)
    except (ValueError, UnicodeError): return False
    if report.get("input_binding") != binding or report.get("input_sha256") != binding["sha256"]: return False
    if formal_verifier:
        bound = report.get("formal_verifier")
        if not isinstance(bound, dict) or bound.get("execution_id") != execution_id or bound.get("execution_subject") != audit_subject(root): return False
        if report.get("execution_subject", {}).get("head_sha") != expected_head or report.get("execution_subject", {}).get("tree_sha") != expected_tree: return False
    return report == claim_audit(value, root=root, timestamp=report.get("timestamp", ""),
                                formal_verifier=formal_verifier, expected_head=expected_head,
                                expected_tree=expected_tree, execution_id=execution_id, input_bytes=input_bytes)


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("action",nargs="?",choices=("generate","check","verify-tag","audit","verify-audit"),default="generate"); ap.add_argument("--check",action="store_true"); ap.add_argument("--verify-tag",action="store_true"); ap.add_argument("--input",type=Path,default=INVENTORY); ap.add_argument("--report",type=Path); ap.add_argument("--timestamp"); ap.add_argument("--require-verified",action="store_true")
    ap.add_argument("--formal-verifier", choices=("lean-kernel",)); ap.add_argument("--expected-head"); ap.add_argument("--expected-tree"); ap.add_argument("--execution-id")
    a=ap.parse_args(argv); action="check" if a.check else "verify-tag" if a.verify_tag else a.action
    try:
        if action in {"audit", "verify-audit"}:
            from datetime import datetime, timezone
            input_bytes=a.input.read_bytes()
            value=audit_json(input_bytes.decode("utf-8"))
            verifier = {"formal_verifier":a.formal_verifier == "lean-kernel", "expected_head":a.expected_head,
                        "expected_tree":a.expected_tree, "execution_id":a.execution_id, "input_bytes":input_bytes}
            if action=="verify-audit":
                if a.report is None: raise ValueError("verify-audit requires --report")
                if not verify_claim_audit(audit_json(a.report.read_text()),value, **verifier): raise ValueError("audit report differs from independent recomputation")
                print("PASS audit receipt recomputation; no truth or effect claim"); return 0
            report=claim_audit(value,timestamp=a.timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00","Z"), **verifier)
            print(pretty(report),end="")
            summary=report["audit_summary"]
            if summary["claims_failed"] or summary["invariants_failed"] or summary["non_implication_violations"]: return 2
            return 3 if a.require_verified and (summary["claims_held"] or summary["invariants_held"]) else 0
        if action=="verify-tag": verify_tag(); print(f"PASS exact-tag kernel source binding: {TAG}, 54 primary receipts"); return 0
        out,final=outputs(); ok=all(write_or_check(p,t,action=="check") for p,t in out.items())
        if not ok: return 1
        if action=="check" and final!=FINAL_RECEIPT.exists(): print("BLOCK completion receipt presence differs from finalization state",file=sys.stderr); return 1
        print(f"PASS {'verified' if action=='check' else 'materialized'} global completion ledger: 92 claims, 54 primary kernel receipts, {'FINAL_PASS receipt present' if final else 'final receipt pending'}"); return 0
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError,subprocess.CalledProcessError) as exc: print(f"BLOCK global completion: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
