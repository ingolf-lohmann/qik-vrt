# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import unittest
import json
import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
from tools.qikvrt_devops_ring import plan, execute_roundtrip

HEAD = "a" * 40
class DevOpsRingTests(unittest.TestCase):
    def observation(self, runs=None, work=None):
        return {"repository": "ingolf-lohmann/qik-vrt", "head": HEAD,
                "runs": [] if runs is None else runs,
                "work": [] if work is None else work}

    def test_idle_is_not_effect(self):
        r = plan(self.observation())
        self.assertEqual(r["state"], "IDLE")
        self.assertFalse(r["effect_ack_done"])
        self.assertFalse(r["dispatch_executed"])

    def test_failure_does_not_hide_independent_work(self):
        r = plan(self.observation(
            [{"id": 5, "status": "completed", "conclusion": "failure"}],
            [{"id": 9, "state": "open"}]))
        self.assertEqual(len(r["tasks"]), 2)
        self.assertEqual({t["kind"] for t in r["tasks"]},
                         {"TEMDD_DIAGNOSE", "CONTINUATION_CANDIDATE"})

    def test_permutation_is_lossless(self):
        runs = [{"id": 2, "status": "completed", "conclusion": "success"},
                {"id": 1, "status": "in_progress", "conclusion": None}]
        a = plan(self.observation(runs))
        b = plan(self.observation(list(reversed(runs))))
        self.assertEqual(a["semantic_fingerprint"], b["semantic_fingerprint"])
        self.assertEqual(a["evidence_count"], 2)

    def test_duplicate_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_IDENTITY"):
            plan(self.observation([{"id": 1}, {"id": 1}]))

    def test_missing_inventory_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_INVENTORY"):
            plan({"repository": "ingolf-lohmann/qik-vrt", "head": HEAD, "runs": []})

    def test_replay_does_not_renew_progress(self):
        a = plan(self.observation([{"id": 1, "status": "completed", "conclusion": "success"}]))
        b = plan(self.observation([{"id": 1, "status": "completed", "conclusion": "success"}]), a)
        self.assertFalse(b["changed"])


class RoundtripTests(unittest.TestCase):
    def test_lossless_roundtrip_and_hash_chain(self):
        request = {"id": "r1", "payload": {"assignments": [
            {"id": "a", "feature": "f"}, {"id": "b", "feature": "f"}]}}
        catalog = [{"id": "f"}]
        observations = [{"assignment_id": "a", "status": "VERIFIED", "artifact": {"sha256": "abc"}},
                        {"assignment_id": "b", "status": "FAILED", "log": "causal error"}]
        result = execute_roundtrip(request, catalog, observations)
        self.assertEqual(result["response_status"], "HOLD")
        self.assertEqual(len(result["journal"]), 6)
        self.assertEqual(result["journal"][0]["kind"], "INTAKE")
        self.assertEqual(result["journal"][-1]["payload"]["unverified"], ["b"])
        self.assertEqual(result["artifacts"], [{"sha256": "abc"}])
        self.assertFalse(result["delegation_executed"])
        self.assertFalse(result["effect_ack_done"])
        self.assertEqual(result["journal_head"], execute_roundtrip(request, catalog, observations)["journal_head"])

    def test_missing_observation_never_passes(self):
        r = execute_roundtrip({"id": "r", "payload": {"assignments": [{"id": "a", "feature": "f"}]}},
                              [{"id": "f"}], [])
        self.assertEqual(r["response_status"], "HOLD")
        self.assertEqual(r["journal"][-1]["payload"]["unresolved"], ["a"])

    def test_unknown_feature_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_UNKNOWN_ASSIGNMENT"):
            execute_roundtrip({"id": "r", "payload": {"assignments": [{"id": "a", "feature": "missing"}]}},
                              [{"id": "f"}], [])

class IntegrityWorkflowExecutionTests(unittest.TestCase):
    def test_workflow_keeps_each_integrity_trigger_as_a_separate_path(self):
        source = (Path(__file__).resolve().parents[1] /
                  '.github/workflows/qikvrt_devops_ring_integrity_repair_candidate.yml').read_text()
        trigger = source.split('    paths:\n', 1)[1].split('  workflow_dispatch:', 1)[0]
        paths = [line.strip()[3:-1] for line in trigger.splitlines()
                 if line.strip().startswith("- '") and line.strip().endswith("'")]
        for required in ('docs/DEVOPS_RING_LOSSLESS_EKMP.md', 'REPOSITORY_FILE_MANIFEST.json',
                         'SHA256SUMS.txt', 'REPOSITORY_FILE_MANIFEST.json.sha256'):
            self.assertIn(required, paths)

    def test_same_branch_repair_checks_the_remote_lease_before_nonforced_push(self):
        source = (Path(__file__).resolve().parents[1] /
                  '.github/workflows/qikvrt_devops_ring_integrity_repair_candidate.yml').read_text()
        step = source.split('      - name: Commit verified integrity trio', 1)[1]
        block = step.split('        run: |\n', 1)[1].split('      - name:', 1)[0]
        shell = textwrap.dedent(block)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            shim = path / 'git'
            shim.write_text('''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ['FAKE_GIT_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
if args == ['rev-parse', 'HEAD']:
    print(os.environ['EXPECTED_HEAD'])
elif args == ['rev-parse', 'refs/remotes/origin/' + os.environ['PR_BRANCH']]:
    print(os.environ['FAKE_REMOTE_HEAD'])
elif args == ['diff', '--cached', '--quiet']:
    sys.exit(1)
elif args and args[0] in ('add', '-c', 'fetch', 'push'):
    pass
else:
    sys.exit(42)
''')
            shim.chmod(0o700)
            for remote, allowed in ((HEAD, True), ('b' * 40, False)):
                log = path / ('accepted.jsonl' if allowed else 'changed.jsonl')
                env = {**os.environ, 'PATH': directory + os.pathsep + os.environ['PATH'],
                       'EXPECTED_HEAD': HEAD, 'PR_BRANCH': 'docs/onboarding-test',
                       'FAKE_REMOTE_HEAD': remote, 'FAKE_GIT_LOG': str(log)}
                result = subprocess.run(['bash', '-euo', 'pipefail', '-c', shell],
                                        cwd=directory, env=env, capture_output=True, text=True, timeout=5)
                calls = [json.loads(line) for line in log.read_text().splitlines()]
                pushes = [call for call in calls if call and call[0] == 'push']
                self.assertEqual(result.returncode == 0, allowed, result.stderr)
                if allowed:
                    self.assertEqual(pushes, [['push', 'origin', 'HEAD:refs/heads/docs/onboarding-test']])
                    self.assertEqual(calls[-3:], [
                        ['fetch', '--no-tags', 'origin',
                         'refs/heads/docs/onboarding-test:refs/remotes/origin/docs/onboarding-test'],
                        ['rev-parse', 'refs/remotes/origin/docs/onboarding-test'], pushes[0]])
                else:
                    self.assertEqual(pushes, [])


if __name__ == "__main__":
    unittest.main()
