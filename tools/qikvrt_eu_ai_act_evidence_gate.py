#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Conservative repository evidence gate for the QIK-VRT EU AI Act dossier.

This checks documentary status consistency only. It is not a legal classifier,
a conformity assessment, or evidence that deployed controls are effective.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import pathlib
import re
import stat
import sys
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Finding:
    code: str
    status: str
    detail: str


@dataclass(frozen=True)
class AuditResult:
    schema: str
    result: str
    scope: str
    findings: tuple[Finding, ...]

    def as_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["findings"] = [asdict(item) for item in self.findings]
        return value


REQUIRED_STATUS_MARKERS = {
    "classification": re.compile(r"MORE_FACTS_REQUIRED"),
    "compliance_not_established": re.compile(r"COMPLIANCE NOT ESTABLISHED"),
    "requirement_register_link": re.compile(r"AI_ACT_REQUIREMENTS_CONTROL_EVIDENCE_REGISTER\.md"),
}
REQUIRED_REGISTER_MARKERS = {
    "classification": re.compile(r"MORE_FACTS_REQUIRED"),
    "open_applicability_gates": re.compile(r"\bOPEN\b"),
    "missing_evidence_disposition": re.compile(r"NOT_EVIDENCED"),
    "no_shortcut_to_not_applicable": re.compile(r"N/A.*reasoned, signed applicability decision", re.I | re.S),
}
UNSUPPORTED_GREEN_CLAIMS = (
    re.compile(r"\b(?:fully|overall) compliant with (?:the )?(?:EU AI Act|Regulation \(EU\) 2024/1689)", re.I),
    re.compile(r"\bAI Act compliance (?:is )?(?:established|confirmed|proven)\b", re.I),
    re.compile(r"\bclassification (?:is )?(?:final|conclusive)\b", re.I),
    # Conservative warning terms from the architecture review: quoted or
    # negated occurrences also require review; this is not semantic NLP.
    re.compile(r"\bEU AI Act[ -]compliant\b", re.I),
    re.compile(r"\bfully compliant\b", re.I),
    re.compile(r"\baudit passed\b", re.I),
    re.compile(r"\bconformity established\b", re.I),
    re.compile(r"\bregulatory approval achieved\b", re.I),
)


def audit_text(status_text: str, register_text: str) -> AuditResult:
    findings: list[Finding] = []
    for code, pattern in REQUIRED_STATUS_MARKERS.items():
        present = bool(pattern.search(status_text))
        findings.append(Finding(
            code=f"STATUS_{code.upper()}",
            status="PASS" if present else "BLOCK",
            detail="Required conservative status marker present." if present
            else f"Required marker missing from status document: {code}.",
        ))
    for code, pattern in REQUIRED_REGISTER_MARKERS.items():
        present = bool(pattern.search(register_text))
        findings.append(Finding(
            code=f"REGISTER_{code.upper()}",
            status="PASS" if present else "BLOCK",
            detail="Required evidence-control marker present." if present
            else f"Required marker missing from requirement register: {code}.",
        ))
    combined = status_text + "\n" + register_text
    for index, pattern in enumerate(UNSUPPORTED_GREEN_CLAIMS, start=1):
        if pattern.search(combined):
            findings.append(Finding(
                code=f"UNSUPPORTED_GREEN_CLAIM_{index}",
                status="BLOCK",
                detail="Potential unsupported affirmative conformity/classification claim detected; human review required.",
            ))
    blocked = any(item.status == "BLOCK" for item in findings)
    return AuditResult(
        schema="qikvrt_eu_ai_act_evidence_gate_v1",
        result="BLOCKED" if blocked else "DOCUMENTARY_GUARDS_PASS",
        scope="repository-document consistency only; no legal or operational conformity conclusion",
        findings=tuple(findings),
    )


def audit_files(status_path: pathlib.Path, register_path: pathlib.Path) -> AuditResult:
    try:
        status_text = status_path.read_text(encoding="utf-8")
        register_text = register_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return AuditResult(
            schema="qikvrt_eu_ai_act_evidence_gate_v1",
            result="BLOCKED",
            scope="repository-document consistency only; no legal or operational conformity conclusion",
            findings=(Finding("INPUT_READ_FAILURE", "BLOCK", str(exc)),),
        )
    return audit_text(status_text, register_text)


SUBJECT_FIELDS = (
    "system_id", "source_commit", "source_tree", "purpose_sha256",
    "model_configuration", "data_configuration", "deployment_configuration", "law_version",
)
ARTICLE_IDS = frozenset(f"ART_{n}" for n in (9, 10, 11, 12, 13, 14, 15, 17, 19, 43, 50))


def strict_json(text: str) -> object:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_number(value):
        raise ValueError(f"Non-finite JSON number: {value}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_number)


def audit_bundle(bundle: object, root: pathlib.Path, expected_subject: object,
                 *, now: datetime | None = None) -> dict[str, object]:
    """Check evidence bindings, never infer truth, legal approval or deployment.

    The caller supplies the independently observed assessment context. Hashes
    authenticate byte identity only, not authorship or the truth of a receipt.
    Unknown facts and unbound original artifacts remain explicit OPEN items.
    """
    findings: list[dict[str, str]] = []

    def add(code, status, detail):
        findings.append({"code": code, "status": status, "detail": detail})

    def nonempty(value):
        return isinstance(value, str) and bool(value.strip())

    def reference(ref, label):
        if not isinstance(ref, dict) or ref.get("state") not in ("BOUND", "UNRESOLVED"):
            add(label, "BLOCK", "Typed artifact reference required.")
            return
        if ref["state"] == "UNRESOLVED":
            if not nonempty(ref.get("reason")):
                add(label, "BLOCK", "Unresolved source requires its reason.")
            else:
                add(label, "OPEN", ref["reason"])
            return
        path, expected = ref.get("path"), ref.get("sha256")
        if (not nonempty(path) or "\\" in path or
                any(part in ("", ".", "..") for part in path.split("/")) or
                pathlib.PurePosixPath(path).is_absolute() or
                not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected)):
            add(label, "BLOCK", "Safe relative path and SHA-256 required.")
            return
        try:
            current = root.resolve()
            for part in pathlib.PurePosixPath(path).parts:
                current = current / part
                if current.is_symlink():
                    raise ValueError("Symlink evidence is not accepted.")
            metadata = current.stat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("Regular evidence file required.")
            if metadata.st_size > 32 * 1024 * 1024:
                raise ValueError("Evidence file exceeds the 32 MiB inspection limit.")
            with current.open("rb") as stream:
                data = stream.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024:
                raise ValueError("Evidence file grew beyond the inspection limit.")
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("Evidence bytes changed: dependent assessment invalidated.")
        except (OSError, ValueError) as exc:
            add(label, "BLOCK", str(exc))
            return
        add(label, "BOUND", "Exact local bytes match; no truth or authenticity conclusion.")

    if not isinstance(bundle, dict) or bundle.get("schema") != "qikvrt_ai_act_evidence_bundle_v1":
        add("BUNDLE_SCHEMA", "BLOCK", "Unsupported or missing evidence schema.")
        bundle = {}
    subject = bundle.get("subject")
    if not isinstance(subject, dict) or not isinstance(expected_subject, dict):
        add("ASSESSMENT_CONTEXT", "BLOCK", "Declared and independently supplied subjects required.")
        subject, expected_subject = {}, {}
    for field in SUBJECT_FIELDS:
        value = subject.get(field)
        if field not in subject or field not in expected_subject:
            add(f"SUBJECT_{field}", "BLOCK", "Assessment context field missing.")
        elif value != expected_subject[field]:
            add(f"SUBJECT_{field}", "BLOCK", "Changed context invalidates predecessor evidence.")
        elif value is None:
            add(f"SUBJECT_{field}", "OPEN", "Context value not established.")
        elif not nonempty(value):
            add(f"SUBJECT_{field}", "BLOCK", "Context value must be a nonempty string or null.")
        elif field in ("source_commit", "source_tree", "purpose_sha256"):
            size = 64 if field == "purpose_sha256" else 40
            if not re.fullmatch(f"[0-9a-f]{{{size}}}", value):
                add(f"SUBJECT_{field}", "BLOCK", "Invalid subject digest.")
    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        add("ARTIFACT_INVENTORY", "BLOCK", "Nonempty artifact inventory required.")
    else:
        names = set()
        for index, ref in enumerate(artifacts):
            name = ref.get("id") if isinstance(ref, dict) else None
            if not nonempty(name) or name in names:
                add("ARTIFACT_ID", "BLOCK", "Artifact IDs must be nonempty and unique.")
            names.add(name if isinstance(name, str) else index)
            reference(ref, f"ARTIFACT_{index}")
    controls = bundle.get("controls")
    seen = set()
    if not isinstance(controls, list):
        controls = []
        add("CONTROL_REGISTER", "BLOCK", "Control register must be a list.")
    for control in controls:
        if not isinstance(control, dict):
            add("CONTROL_RECORD", "BLOCK", "Control object required.")
            continue
        key = control.get("requirement_id")
        if not isinstance(key, str) or key in seen:
            add("CONTROL_ID", "BLOCK", "Unique string requirement ID required.")
            continue
        seen.add(key)
        applicability = control.get("applicability")
        if applicability == "OPEN":
            add(key, "OPEN", "Legal applicability remains open.")
        elif applicability not in ("APPLIES", "NOT_APPLICABLE"):
            add(key, "BLOCK", "Invalid applicability disposition.")
        else:
            decision = control.get("applicability_decision")
            if (not isinstance(decision, dict) or
                    not all(nonempty(decision.get(k)) for k in ("reviewer", "rationale"))):
                add(key, "BLOCK", "Accountable, reasoned applicability decision required.")
            else:
                reference(decision.get("record"), key + "_DECISION")
        disposition = control.get("evidence_status")
        if disposition not in ("NOT_EVIDENCED", "PARTIAL", "EVIDENCED"):
            add(key, "BLOCK", "Evidence disposition must not assert a conformity PASS.")
        elif disposition != "EVIDENCED":
            add(key, "OPEN", "Control effectiveness remains unestablished.")
        refs = control.get("evidence", [])
        if not isinstance(refs, list) or (disposition == "EVIDENCED" and not refs):
            add(key, "BLOCK", "Evidence list required; EVIDENCED requires references.")
            continue
        for index, evidence in enumerate(refs):
            if not isinstance(evidence, dict) or evidence.get("kind") not in (
                    "ARCHITECTURE", "SOURCE", "TEST", "OPERATION", "REVIEW"):
                add(key, "BLOCK", "Typed evidence class required.")
                continue
            if evidence.get("subject") != subject:
                add(key, "BLOCK", "Evidence belongs to another assessment context.")
            if evidence.get("kind") in ("TEST", "OPERATION", "REVIEW"):
                clock = now or datetime.now(timezone.utc)
                try:
                    recorded = datetime.fromisoformat(evidence["observed_at"].replace("Z", "+00:00"))
                    expires = datetime.fromisoformat(evidence["valid_until"].replace("Z", "+00:00"))
                    if recorded.utcoffset() is None or expires.utcoffset() is None:
                        raise ValueError("Timezone required.")
                    if recorded > clock or expires <= clock or expires <= recorded:
                        raise ValueError("Future or expired evidence.")
                except (KeyError, TypeError, AttributeError, ValueError) as exc:
                    add(key, "BLOCK", "Dated evidence invalid: " + str(exc))
            if evidence.get("kind") == "TEST" and (
                    type(evidence.get("exit_code")) is not int or evidence["exit_code"] != 0 or
                    not all(nonempty(evidence.get(k)) for k in ("command", "environment"))):
                add(key, "BLOCK", "Successful, environment-bound test receipt required.")
            reference(evidence.get("artifact"), f"{key}_EVIDENCE_{index}")
    for missing in sorted(ARTICLE_IDS - seen):
        add(missing, "OPEN", "Requirement missing from this selected-article register.")
    blocked = any(f["status"] == "BLOCK" for f in findings)
    opened = any(f["status"] == "OPEN" for f in findings)
    return {
        "schema": "qikvrt_ai_act_binding_audit_v1",
        "result": "BINDINGS_INVALID" if blocked else "BINDINGS_INCOMPLETE" if opened else "BINDINGS_VALID",
        "compliance_status": "COMPLIANCE_NOT_ESTABLISHED",
        "scope": "Byte and context bindings only; no legal decision, receipt authentication or operational acceptance.",
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=pathlib.Path, default=pathlib.Path("EU_AI_ACT_COMPLIANCE_STATUS.md"))
    parser.add_argument("--register", type=pathlib.Path, default=pathlib.Path("docs/regulatory/AI_ACT_REQUIREMENTS_CONTROL_EVIDENCE_REGISTER.md"))
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--bundle", type=pathlib.Path, help="optional typed evidence bundle")
    parser.add_argument("--subject", type=pathlib.Path, help="independently observed assessment context")
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."))
    args = parser.parse_args(argv)
    result = audit_files(args.status, args.register)
    output = result.as_dict()
    binding_result = None
    if args.bundle or args.subject:
        if not (args.bundle and args.subject):
            parser.error("--bundle and --subject must be supplied together")
        try:
            binding_result = audit_bundle(strict_json(args.bundle.read_text(encoding="utf-8")),
                                          args.root, strict_json(args.subject.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError) as exc:
            binding_result = {"result": "BINDINGS_INVALID", "error": str(exc),
                              "compliance_status": "COMPLIANCE_NOT_ESTABLISHED"}
        output["evidence_bindings"] = binding_result
    if args.json:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print(f"{result.result}: {result.scope}")
        for finding in result.findings:
            print(f"{finding.status} {finding.code}: {finding.detail}")
        if binding_result:
            print(binding_result["result"] + ": COMPLIANCE_NOT_ESTABLISHED")
    return 0 if (result.result == "DOCUMENTARY_GUARDS_PASS" and
                 (binding_result is None or binding_result["result"] != "BINDINGS_INVALID")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
