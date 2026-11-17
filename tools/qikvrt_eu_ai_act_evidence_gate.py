#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Conservative repository evidence gate for the QIK-VRT EU AI Act dossier.

This checks documentary status consistency only. It is not a legal classifier,
a conformity assessment, or evidence that deployed controls are effective.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=pathlib.Path, default=pathlib.Path("EU_AI_ACT_COMPLIANCE_STATUS.md"))
    parser.add_argument("--register", type=pathlib.Path, default=pathlib.Path("docs/regulatory/AI_ACT_REQUIREMENTS_CONTROL_EVIDENCE_REGISTER.md"))
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    result = audit_files(args.status, args.register)
    if args.json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    else:
        print(f"{result.result}: {result.scope}")
        for finding in result.findings:
            print(f"{finding.status} {finding.code}: {finding.detail}")
    return 0 if result.result == "DOCUMENTARY_GUARDS_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
