"""TEMDD: control-ref fencing, atomic acquisition, stale-writer and restart."""
import datetime as dt
import hashlib
import json
import os
import unittest
from unittest.mock import patch

from tools import qikvrt_writer_fence as fence

MAIN = "a" * 40
SOURCE = "b" * 40
CANDIDATE = "c" * 40
TREE = "d" * 40


class FakeAPI:
    repository = "ingolf-lohmann/qik-vrt"

    def __init__(self):
        self.refs = {"refs/heads/main": MAIN, "refs/heads/repair": SOURCE}
        self.commits = {i: {"tree": {"sha": TREE}, "message": "", "parents": []}
                        for i in (MAIN, SOURCE, CANDIDATE)}
        self.atomic_calls = []
        self.fail_atomic = False

    def ref(self, name):
        oid = self.refs.get(name)
        return {"ref": name, "object": {"sha": oid}} if oid else None

    def call(self, method, path, payload=None):
        if method == "GET" and path.startswith("git/commits/"):
            return self.commits[path.removeprefix("git/commits/")]
        if method == "POST" and path == "git/commits":
            parent = payload["parents"][0]
            assert parent in self.commits
            data = json.dumps(payload, sort_keys=True)
            oid = hashlib.sha1(data.encode()).hexdigest()
            self.commits[oid] = {
                "tree": {"sha": payload["tree"]},
                "message": payload["message"],
                "parents": [{"sha": parent}],
            }
            return {"sha": oid}
        raise AssertionError((method, path))

    def atomic_refs(self, changes, *, operation_id):
        self.atomic_calls.append((changes, operation_id))
        if self.fail_atomic:
            raise fence.FenceBlocked("GRAPHQL_REJECTED")
        if any(self.refs.get(c["name"], fence.ZERO) != c["beforeOid"] for c in changes):
            raise fence.FenceBlocked("CAS_CONFLICT")
        for c in changes:
            self.refs[c["name"]] = c["afterOid"]


class FenceTEMDD(unittest.TestCase):
    def setUp(self):
        self.api = FakeAPI()
        self.plan = {
            "base_sha": MAIN, "turn_number": 500,
            "selected": {"head_ref": "repair", "head_sha": SOURCE, "pull_request": 756},
        }
        self.env = patch.dict(os.environ, {
            "GITHUB_REPOSITORY": self.api.repository,
            "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_ACTOR": "github-actions[bot]",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def claim(self):
        return fence.acquire(self.api, self.plan, 123)

    def test_atomic_claim_and_publish_control_and_target(self):
        c = self.claim()
        self.assertEqual(c["fencing_epoch"], 1)
        self.assertEqual(len(self.api.atomic_calls), 1)
        self.assertEqual(len(self.api.atomic_calls[0][0]), 6)
        plan = dict(self.plan, **c)
        effect = "refs/qikvrt/pr-continuation/effects/756/" + SOURCE + "-" + MAIN + "/successor"
        res = fence.publish(self.api, plan, CANDIDATE, effect_ref=effect)
        self.assertEqual(res["state"], "FENCED_BRANCH_PUBLISHED")
        self.assertEqual(self.api.refs["refs/heads/repair"], CANDIDATE)
        self.assertEqual(self.api.refs[effect], CANDIDATE)
        self.assertFalse(res["effect_ack_done"])
        self.assertEqual(len(self.api.atomic_calls[1][0]), 4)

    def test_atomic_claim_failure_no_partial_ref(self):
        self.api.fail_atomic = True
        with self.assertRaises(fence.FenceBlocked): self.claim()
        self.assertEqual(self.api.refs, {"refs/heads/main": MAIN, "refs/heads/repair": SOURCE})

    def test_no_parallel_claim_even_while_main_unchanged(self):
        self.claim()
        with self.assertRaisesRegex(fence.FenceBlocked, "ACTIVE_EXCLUSIVE"):
            self.claim()

    def test_control_cas_rejects_renewed_writer(self):
        c = self.claim()
        plan = dict(self.plan, **c)
        self.api.refs[fence.CONTROL_REF] = "f" * 40
        self.api.commits["f" * 40] = self.api.commits[c["control_sha"]]
        with self.assertRaises(fence.FenceBlocked):
            fence.publish(self.api, plan, CANDIDATE, effect_ref="refs/qikvrt/pr-continuation/effects/x")
        self.assertEqual(self.api.refs["refs/heads/repair"], SOURCE)

    def test_recovery_monotonic_epoch_after_expiry(self):
        old = self.claim()
        # The immutable original receipt remains unchanged; advance the clock.
        with patch.object(fence, "_now", return_value=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)):
            new = dict(self.plan, turn_number=501)
            with patch.dict(os.environ, {"GITHUB_RUN_ID": "124"}):
                res = fence.acquire(self.api, new, 124)
        self.assertEqual(res["fencing_epoch"], 2)

    def test_publication_atomic_conflict_no_partial_effect(self):
        claim = self.claim()
        plan = dict(self.plan, **claim)
        self.api.fail_atomic = True
        with self.assertRaises(fence.FenceBlocked):
            fence.publish(self.api, plan, CANDIDATE, effect_ref="refs/qikvrt/pr-continuation/effects/x")
        self.assertEqual(self.api.refs["refs/heads/repair"], SOURCE)

    def test_head_drift_claim_refused(self):
        self.api.refs["refs/heads/main"] = "e" * 40
        with self.assertRaisesRegex(fence.FenceBlocked, "EXACT_HEAD_DRIFT"):
            self.claim()

    def test_mismatched_run_identity_refused(self):
        with patch.dict(os.environ, {"GITHUB_RUN_ID": "999"}):
            with self.assertRaisesRegex(fence.FenceBlocked, "WRITER_IDENTITY_REQUIRED"):
                self.claim()


if __name__ == "__main__":
    unittest.main()
