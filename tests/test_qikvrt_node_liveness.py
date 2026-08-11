#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import datetime as dt
import io
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_node_liveness",
    ROOT / "tools/qikvrt_node_liveness.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

NOW = dt.datetime(2026, 8, 11, 0, 0, tzinfo=dt.timezone.utc)
GUID = "a84f157a-cef2-4c47-bca9-8f407085bdbe"
SOURCE = MODULE.RepositorySnapshot(
    MODULE.MIRROR_REPOSITORY,
    "a" * 40,
    "b" * 40,
)
AUTHORITY = MODULE.RepositorySnapshot(
    MODULE.AUTHORITY_REPOSITORY,
    "c" * 40,
    "d" * 40,
)


def boundaries() -> dict[str, bool]:
    return {
        "node_writes_only_to_node_repository": True,
        "no_global_scanning": True,
        "no_self_propagation": True,
        "no_remote_mutation_without_authorization": True,
    }


def documents(
    *,
    due: str = "2026-08-10T20:59:14Z",
    expires: str = "2026-08-10T21:59:14Z",
    renewed: str = "2026-08-09T20:59:14Z",
    heartbeat: str = "2026-08-09T20:59:14Z",
    acknowledgement_status: str = "ACCEPTED_BY_SEED",
) -> dict[pathlib.PurePosixPath, dict[str, object]]:
    return {
        MODULE.ACK_PATH: {
            "qikvrt_event": "NODE_ACK_OF_SEED_ACCEPTANCE",
            "guid": GUID,
            "repository": MODULE.MIRROR_REPOSITORY,
            "seed_repository": MODULE.AUTHORITY_REPOSITORY,
            "status": acknowledgement_status,
            "checked_utc": "2026-08-08T19:11:03Z",
            "observed_authority_commit": "0" * 40,
            "boundaries": boundaries(),
        },
        MODULE.RENEWAL_PATH: {
            "qikvrt_event": "NODE_REGISTRATION_RENEWAL",
            "guid": GUID,
            "repository": MODULE.MIRROR_REPOSITORY,
            "seed_repository": MODULE.AUTHORITY_REPOSITORY,
            "node_branch": "main",
            "status": "RENEWED",
            "renewed_utc": renewed,
            "next_renewal_due_utc": due,
            "run_id": "old-run",
            "boundaries": boundaries(),
        },
        MODULE.HEALTH_PATH: {
            "qikvrt_event": "NODE_HEALTH_HEARTBEAT",
            "guid": GUID,
            "repository": MODULE.MIRROR_REPOSITORY,
            "seed_repository": MODULE.AUTHORITY_REPOSITORY,
            "node_branch": "main",
            "status": "ACTIVE",
            "heartbeat_utc": heartbeat,
            "expires_utc": expires,
            "heartbeat_ttl_minutes": 1500,
            "run_id": "old-run",
            "boundaries": boundaries(),
        },
    }


def write_documents(
    root: pathlib.Path,
    values: dict[pathlib.PurePosixPath, dict[str, object]],
) -> None:
    for relative, value in values.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(MODULE.canonical_json_bytes(value))


def fresh_documents() -> dict[pathlib.PurePosixPath, dict[str, object]]:
    return documents(
        due="2026-08-12T00:00:00Z",
        expires="2026-08-12T01:00:00Z",
        renewed="2026-08-11T00:00:00Z",
        heartbeat="2026-08-11T00:00:00Z",
    )


def git(root: pathlib.Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def initialize_git(root: pathlib.Path) -> None:
    git(root, "init", "-q")
    # Git may detach automatic object maintenance after a commit.  These
    # repositories are intentionally tiny and ephemeral, so disable it
    # before the fixture can race TemporaryDirectory cleanup.
    git(root, "config", "maintenance.auto", "false")
    git(root, "config", "gc.auto", "0")
    git(root, "config", "user.name", "test")
    git(root, "config", "user.email", "test@example.invalid")


def snapshot(root: pathlib.Path) -> MODULE.RepositorySnapshot:
    return MODULE.RepositorySnapshot(
        MODULE.MIRROR_REPOSITORY,
        git(root, "rev-parse", "HEAD"),
        git(root, "show", "-s", "--format=%T", "HEAD"),
    )


class NodeLivenessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_all_absent_active_mirror_records_fail_closed(self) -> None:
        with self.assertRaisesRegex(MODULE.NodeLivenessBlock, "all required"):
            MODULE.evaluate_liveness(self.root, now=NOW)

    def test_partial_records_fail_closed(self) -> None:
        write_documents(self.root, {MODULE.ACK_PATH: documents()[MODULE.ACK_PATH]})
        with self.assertRaisesRegex(MODULE.NodeLivenessBlock, "partial"):
            MODULE.evaluate_liveness(self.root, now=NOW)

    def test_overdue_renewal_and_expired_health_require_refresh(self) -> None:
        write_documents(self.root, documents())
        result = MODULE.evaluate_liveness(self.root, now=NOW)
        self.assertEqual("MIRROR_NODE_LIVENESS_REFRESH_REQUIRED", result["state"])
        self.assertEqual(
            {
                "RENEWAL_DUE_OR_WITHIN_LEAD",
                "HEALTH_EXPIRED_OR_WITHIN_LEAD",
            },
            set(result["reasons"]),
        )

    def test_authority_ttl_mismatch_fails_closed(self) -> None:
        write_documents(self.root, fresh_documents())
        with self.assertRaisesRegex(MODULE.NodeLivenessBlock, "disagrees"):
            MODULE.evaluate_liveness(
                self.root,
                now=NOW,
                authority_ttl_minutes=1499,
                authority_node_branch="main",
            )

    def test_nonaccepted_ack_status_fails_closed(self) -> None:
        write_documents(self.root, documents(acknowledgement_status="REJECTED"))
        with self.assertRaisesRegex(MODULE.NodeLivenessBlock, "status"):
            MODULE.evaluate_liveness(self.root, now=NOW)

    def test_materialization_refreshes_only_local_liveness_before_ack_phase(self) -> None:
        values = documents()
        write_documents(self.root, values)
        ack_before = (self.root / MODULE.ACK_PATH).read_bytes()
        result = MODULE.materialize_liveness(
            self.root,
            now=NOW,
            source=SOURCE,
            authority=AUTHORITY,
        )
        self.assertEqual("REPAIRED", result["state"])
        self.assertEqual(ack_before, (self.root / MODULE.ACK_PATH).read_bytes())
        renewal = json.loads((self.root / MODULE.RENEWAL_PATH).read_text())
        health = json.loads((self.root / MODULE.HEALTH_PATH).read_text())
        self.assertEqual("2026-08-11T00:00:00Z", renewal["renewed_utc"])
        self.assertEqual("2026-08-12T00:00:00Z", renewal["next_renewal_due_utc"])
        self.assertEqual("2026-08-12T01:00:00Z", health["expires_utc"])
        work_unit = json.loads((self.root / MODULE.LIVENESS_WORK_UNIT).read_text())
        self.assertEqual(SOURCE.commit, work_unit["inputs"]["mirror_main"])
        self.assertEqual(AUTHORITY.tree, work_unit["inputs"]["authority_tree"])
        self.assertIn(
            "PRESERVE_UNCHANGED_UNTIL_POST_PROMOTION_AUTHORITY_REOBSERVATION",
            work_unit["inputs"]["seed_acceptance_status_policy"],
        )

    def test_check_acceptance_cli_serializes_bound_snapshots(self) -> None:
        assessment = {
            "state": "MIRROR_SEED_ACCEPTANCE_REFRESH_REQUIRED",
            "refresh_required": True,
            "guid": GUID,
            "source": SOURCE,
            "authority": AUTHORITY,
        }
        with (
            mock.patch.object(
                MODULE,
                "acceptance_assessment",
                return_value=assessment,
            ),
            mock.patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            returncode = MODULE.main(["check-acceptance"])
        self.assertEqual(1, returncode)
        rendered = output.getvalue()
        self.assertIn("MIRROR_SEED_ACCEPTANCE_REFRESH_REQUIRED", rendered)
        value = json.loads(rendered)
        self.assertEqual(SOURCE.commit, value["source"]["commit"])
        self.assertEqual(SOURCE.tree, value["source"]["tree"])
        self.assertEqual(AUTHORITY.commit, value["authority"]["commit"])
        self.assertEqual(AUTHORITY.tree, value["authority"]["tree"])

    def test_acceptance_refresh_is_separate_and_exact_pair_bound(self) -> None:
        write_documents(self.root, fresh_documents())
        with (
            mock.patch.object(MODULE, "_liveness_paths_modified", return_value=False),
            mock.patch.object(MODULE, "_ack_covers_current_mirror", return_value=False),
        ):
            initial = MODULE.acceptance_assessment(
                self.root,
                now=NOW,
                source=SOURCE,
                authority=AUTHORITY,
            )
            self.assertTrue(initial["refresh_required"])
            result = MODULE.materialize_acceptance(
                self.root,
                now=NOW,
                source=SOURCE,
                authority=AUTHORITY,
            )
        self.assertEqual("REPAIRED", result["state"])
        acknowledgement = json.loads((self.root / MODULE.ACK_PATH).read_text())
        self.assertEqual(AUTHORITY.commit, acknowledgement["observed_authority_commit"])
        self.assertEqual(AUTHORITY.tree, acknowledgement["observed_authority_tree"])
        self.assertEqual(SOURCE.commit, acknowledgement["observed_mirror_commit"])
        work_unit = json.loads((self.root / MODULE.ACK_WORK_UNIT).read_text())
        self.assertEqual(AUTHORITY.commit, work_unit["inputs"]["authority_main"])

    def test_acceptance_is_deferred_while_liveness_candidate_is_unpromoted(self) -> None:
        write_documents(self.root, fresh_documents())
        with mock.patch.object(MODULE, "_liveness_paths_modified", return_value=True):
            result = MODULE.acceptance_assessment(
                self.root,
                now=NOW,
                source=SOURCE,
                authority=AUTHORITY,
            )
        self.assertEqual("DEFERRED_UNTIL_LIVENESS_PROMOTION", result["state"])
        self.assertFalse(result["refresh_required"])

    def test_staged_liveness_change_defers_acceptance(self) -> None:
        write_documents(self.root, fresh_documents())
        initialize_git(self.root)
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "initial liveness")
        health = json.loads((self.root / MODULE.HEALTH_PATH).read_text())
        health["run_id"] = "staged-new-liveness"
        (self.root / MODULE.HEALTH_PATH).write_bytes(
            MODULE.canonical_json_bytes(health)
        )
        git(self.root, "add", str(MODULE.HEALTH_PATH))
        self.assertTrue(MODULE._liveness_paths_modified(self.root))
        with mock.patch.object(MODULE, "_ack_covers_current_mirror", return_value=False):
            result = MODULE.acceptance_assessment(
                self.root,
                now=NOW,
                source=snapshot(self.root),
                authority=AUTHORITY,
            )
        self.assertEqual("DEFERRED_UNTIL_LIVENESS_PROMOTION", result["state"])

    def test_ack_coverage_accepts_ack_only_descendant_without_liveness_loop(self) -> None:
        write_documents(self.root, fresh_documents())
        initialize_git(self.root)
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "liveness snapshot")
        liveness_snapshot = snapshot(self.root)
        acknowledgement = json.loads((self.root / MODULE.ACK_PATH).read_text())
        acknowledgement.update(
            {
                "observed_authority_commit": AUTHORITY.commit,
                "observed_authority_tree": AUTHORITY.tree,
                "observed_mirror_commit": liveness_snapshot.commit,
                "observed_mirror_tree": liveness_snapshot.tree,
            }
        )
        (self.root / MODULE.ACK_PATH).write_bytes(
            MODULE.canonical_json_bytes(acknowledgement)
        )
        git(self.root, "add", str(MODULE.ACK_PATH))
        git(self.root, "commit", "-qm", "ack only")
        result = MODULE.acceptance_assessment(
            self.root,
            now=NOW,
            source=snapshot(self.root),
            authority=AUTHORITY,
        )
        self.assertEqual("FRESH", result["state"])
        self.assertFalse(result["refresh_required"])

    def test_ack_coverage_requires_refresh_after_liveness_bytes_change(self) -> None:
        write_documents(self.root, fresh_documents())
        initialize_git(self.root)
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "liveness snapshot")
        liveness_snapshot = snapshot(self.root)
        acknowledgement = json.loads((self.root / MODULE.ACK_PATH).read_text())
        acknowledgement.update(
            {
                "observed_authority_commit": AUTHORITY.commit,
                "observed_authority_tree": AUTHORITY.tree,
                "observed_mirror_commit": liveness_snapshot.commit,
                "observed_mirror_tree": liveness_snapshot.tree,
            }
        )
        (self.root / MODULE.ACK_PATH).write_bytes(
            MODULE.canonical_json_bytes(acknowledgement)
        )
        git(self.root, "add", str(MODULE.ACK_PATH))
        git(self.root, "commit", "-qm", "ack only")
        health = json.loads((self.root / MODULE.HEALTH_PATH).read_text())
        health["run_id"] = "changed-after-ack"
        (self.root / MODULE.HEALTH_PATH).write_bytes(
            MODULE.canonical_json_bytes(health)
        )
        git(self.root, "add", str(MODULE.HEALTH_PATH))
        git(self.root, "commit", "-qm", "change health")
        result = MODULE.acceptance_assessment(
            self.root,
            now=NOW,
            source=snapshot(self.root),
            authority=AUTHORITY,
        )
        self.assertEqual("MIRROR_SEED_ACCEPTANCE_REFRESH_REQUIRED", result["state"])
        self.assertTrue(result["refresh_required"])

    def test_ack_nonancestor_or_unresolvable_history_fails_closed(self) -> None:
        write_documents(self.root, fresh_documents())
        initialize_git(self.root)
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "liveness snapshot")
        observed = snapshot(self.root)
        acknowledgement = json.loads((self.root / MODULE.ACK_PATH).read_text())
        acknowledgement.update(
            {
                "observed_mirror_commit": observed.commit,
                "observed_mirror_tree": observed.tree,
            }
        )
        orphan = git(
            self.root,
            "commit-tree",
            observed.tree,
            "-m",
            "unrelated snapshot",
        )
        with self.assertRaisesRegex(MODULE.NodeLivenessBlock, "not an ancestor"):
            MODULE._ack_covers_current_mirror(
                self.root,
                acknowledgement,
                MODULE.RepositorySnapshot(
                    MODULE.MIRROR_REPOSITORY,
                    orphan,
                    observed.tree,
                ),
            )
        acknowledgement["observed_mirror_commit"] = "f" * 40
        with self.assertRaisesRegex(MODULE.NodeLivenessBlock, "cannot be resolved"):
            MODULE._ack_covers_current_mirror(self.root, acknowledgement, observed)


if __name__ == "__main__":
    unittest.main()
