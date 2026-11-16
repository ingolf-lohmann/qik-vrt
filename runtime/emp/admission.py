"""EMP production admission gate.

Fail closed: a transition decision, GitHub commit, CI success or artifact upload
is not sufficient evidence for autonomous production operation.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AdmissionEvidence:
    exact_head_ci_passed: bool = False
    independent_review_approved: bool = False
    durable_shared_journal_verified: bool = False
    fenced_executor_verified: bool = False
    event_reentry_verified: bool = False
    independent_eap_readback_verified: bool = False
    governance_approved: bool = False
    original_host_verified: bool = False


def production_admission(evidence: AdmissionEvidence) -> tuple[bool, tuple[str, ...]]:
    missing = tuple(
        field for field in evidence.__dataclass_fields__
        if getattr(evidence, field) is not True
    )
    return not missing, missing
