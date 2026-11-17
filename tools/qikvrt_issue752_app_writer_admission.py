# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Issue #752: fail-closed admission for a downstream-CI-capable App writer.

Pure validation only. This module never mints tokens, writes refs, or dispatches CI.
The existing fenced writer must call this gate before an effecting operation.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

_SHA = re.compile(r"^[0-9a-f]{40}$")
_AUTHORITY = "ingolf-lohmann/qik-vrt"


@dataclass(frozen=True)
class AppWriterAdmission:
    repository: str
    expected_head: str
    observed_head: str
    installation_id: int | None
    token_expires_after_seconds: int | None
    permissions: frozenset[str]
    active_writer_lease: bool
    fence_matches: bool
    app_identity_verified: bool
    downstream_ci_required: bool = True


class AdmissionBlocked(ValueError):
    """No effecting write is authorized; preserve blocker and receipt."""


def admit_app_writer(a: AppWriterAdmission) -> None:
    """Reject incomplete evidence; success is permission to attempt, not EAP."""
    if a.repository != _AUTHORITY:
        raise AdmissionBlocked("WRONG_AUTHORITY_REPOSITORY")
    if not _SHA.fullmatch(a.expected_head) or a.expected_head != a.observed_head:
        raise AdmissionBlocked("EXACT_HEAD_DRIFT_OR_INVALID")
    if not a.active_writer_lease or not a.fence_matches:
        raise AdmissionBlocked("WRITER_LEASE_OR_FENCE_UNVERIFIED")
    if not a.app_identity_verified or not a.installation_id or a.installation_id <= 0:
        raise AdmissionBlocked("APP_IDENTITY_UNVERIFIED")
    if a.token_expires_after_seconds is None or a.token_expires_after_seconds <= 0:
        raise AdmissionBlocked("APP_TOKEN_MISSING_OR_EXPIRED")
    required = {"contents:write", "pull_requests:write"}
    if a.downstream_ci_required:
        required.add("actions:read")
    if not required.issubset(a.permissions):
        raise AdmissionBlocked("APP_TOKEN_PERMISSIONS_INSUFFICIENT")


if __name__ == "__main__":
    import unittest
    from dataclasses import replace

    class AdmissionTests(unittest.TestCase):
        def setUp(self):
            self.ok = AppWriterAdmission(
                _AUTHORITY, "a" * 40, "a" * 40, 147838968, 300,
                frozenset({"contents:write", "pull_requests:write", "actions:read"}),
                True, True, True,
            )

        def test_positive(self):
            admit_app_writer(self.ok)

        def test_fail_closed(self):
            for change in (
                {"repository": "other/repo"},
                {"observed_head": "b" * 40},
                {"expected_head": "bad"},
                {"installation_id": None},
                {"token_expires_after_seconds": 0},
                {"permissions": frozenset({"contents:write"})},
                {"active_writer_lease": False},
                {"fence_matches": False},
                {"app_identity_verified": False},
            ):
                with self.subTest(change=change), self.assertRaises(AdmissionBlocked):
                    admit_app_writer(replace(self.ok, **change))

    unittest.main()
