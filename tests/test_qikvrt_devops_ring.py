# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import unittest
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime, timezone
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

    def test_unexecuted_admission_never_becomes_an_idle_queue(self):
        for conclusion in ('action_required', 'startup_failure'):
            result = plan(self.observation([{'id': 8, 'status': 'completed',
                                            'conclusion': conclusion}]))
            self.assertEqual(result['state'], 'WORK_PENDING')
            self.assertEqual(result['tasks'][0]['kind'], 'WORKFLOW_ADMISSION_REPAIR')
            self.assertFalse(result['dispatch_executed'])


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



class WatchdogWakeupTests(unittest.TestCase):
    def wakeup(self, runs):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / '.github/workflows/qikvrt_watchdog_periodic_wakeup.yml').read_text()
        body = textwrap.dedent(workflow.split('        run: |\n', 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'runs.json').write_text(json.dumps(runs))
            gh = folder / 'gh'
            gh.write_text(f'''#!{sys.executable}
import json, os, pathlib, sys
p=pathlib.Path(os.environ['FIXTURE_ROOT'])
endpoint=sys.argv[2]
with (p/'calls.jsonl').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
if '--method' in sys.argv:
 print('DISPATCH_ACCEPTED')
elif '/git/ref/' in endpoint:
 print('a'*40)
elif '/runs?' in endpoint:
 runs=json.loads((p/'runs.json').read_text())
 state=endpoint.split('status=')[1].split('&')[0]
 selected=[r for r in runs if r['status']==state]
 value={{'total_count':len(selected),'workflow_runs':selected[:1]}}
 print(value['total_count'] if '--jq' in sys.argv else json.dumps(value))
else: print('main')
''')
            gh.chmod(0o700)
            env = {**os.environ, 'PATH':str(folder)+os.pathsep+os.environ['PATH'],
                   'FIXTURE_ROOT':str(folder),'REPOSITORY':'example/qik-vrt',
                   'WATCHDOG':'qikvrt_reflexive_repository_watchdog.yml',
                   'QUEUE_LEASE_SECONDS':'600','PROGRESS_LEASE_SECONDS':'900',
                   'GITHUB_STEP_SUMMARY':str(folder/'summary')}
            result=subprocess.run(['bash','-c',body],env=env,capture_output=True,text=True,timeout=10)
            calls=[json.loads(s) for s in (folder/'calls.jsonl').read_text().splitlines()]
            return result,calls

    def test_old_queued_run_cannot_report_success_or_trigger_another_run(self):
        result,calls=self.wakeup([{'id':7,'status':'queued','head_sha':'a'*40,
                                  'created_at':'2026-09-13T09:27:13Z'}])
        self.assertEqual(result.returncode,2,result.stderr)
        self.assertIn('STALE_WATCHDOG_ACTIVITY',result.stderr)
        self.assertTrue(all('--method' not in c for c in calls))

    def test_foreign_head_and_invalid_creation_remain_unknown(self):
        for head,created in [('b'*40,'2026-09-13T09:27:13Z'),('a'*40,'invalid')]:
            result,calls=self.wakeup([{'id':7,'status':'queued','head_sha':head,'created_at':created}])
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertTrue(all('--method' not in c for c in calls))

    def test_fresh_queued_run_is_observed_without_duplicate_dispatch(self):
        result,calls=self.wakeup([{'id':7,'status':'queued','head_sha':'a'*40,
                                  'created_at':datetime.now(timezone.utc).isoformat()}])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(all('--method' not in c for c in calls))

    def test_empty_activity_preserves_one_existing_observer_dispatch(self):
        result,calls=self.wakeup([])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(sum('--method' in c for c in calls),1)

    def test_wakeup_leases_match_existing_watchdog_contract(self):
        root=Path(__file__).resolve().parents[1]
        contract=json.loads((root/'state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json').read_text())
        guard=contract['reflexive_deadlock_prevention']
        self.assertEqual(guard['queue_lease_seconds'],600)
        self.assertEqual(guard['progress_lease_seconds'],900)


class RoundtripTests(unittest.TestCase):
    def test_integrity_candidate_preserves_ci_writer_head_in_real_git_fixture(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / '.github/workflows/qikvrt_devops_ring_integrity_repair_candidate.yml').read_text()
        marker = '      - name: Commit verified integrity trio to the same PR branch with exact-head lease\n'
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            remote, writer = folder / 'remote.git', folder / 'writer'
            def git(*args, cwd=folder):
                return subprocess.check_output(['git', *args], cwd=cwd, stderr=subprocess.DEVNULL, text=True).strip()
            git('init', '--bare', str(remote))
            git('init', str(writer))
            git('config', 'user.name', 'fixture', cwd=writer)
            git('config', 'user.email', 'fixture@example.invalid', cwd=writer)
            for path in ('REPOSITORY_FILE_MANIFEST.json', 'SHA256SUMS.txt', 'REPOSITORY_FILE_MANIFEST.json.sha256'):
                (writer / path).write_text('original\n')
            git('add', '.', cwd=writer)
            git('commit', '-m', 'original fixture', cwd=writer)
            git('branch', '-M', 'repair-fixture', cwd=writer)
            git('remote', 'add', 'origin', str(remote), cwd=writer)
            git('push', 'origin', 'HEAD', cwd=writer)
            expected = git('rev-parse', 'HEAD', cwd=writer)
            (writer / 'REPOSITORY_FILE_MANIFEST.json').write_text('generated candidate\n')
            if marker in source:
                step = source.split(marker, 1)[1].split('      - name:', 1)[0]
                body = textwrap.dedent(step.split('        run: |\n', 1)[1])
                result = subprocess.run(['bash', '-c', body], cwd=writer,
                    env={**os.environ, 'EXPECTED_HEAD': expected, 'PR_BRANCH': 'repair-fixture'},
                    capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
            observed = git('ls-remote', '--heads', 'origin', 'refs/heads/repair-fixture', cwd=writer).split()[0]
            self.assertEqual(observed, expected, 'Candidate writer invalidates existing CI same-writer fence')

    def test_integrity_candidate_keeps_validation_without_branch_write_authority(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / '.github/workflows/qikvrt_devops_ring_integrity_repair_candidate.yml').read_text()
        self.assertIn('contents: read', source)
        self.assertIn('persist-credentials: false', source)
        self.assertIn('python3 -B tools/qikvrt_integrity.py generate', source)
        self.assertIn('python3 -B tools/qikvrt_integrity.py verify', source)
        self.assertIn('tests.test_qikvrt_devops_ring', source)
        self.assertIn('actions/upload-artifact@', source)
        self.assertNotIn('git push', source)
        ci = (root / '.github/workflows/qikvrt_ci.yml').read_text()
        self.assertIn('Same-writer successor re-entry to tested fixpoint', ci)
        self.assertIn('test "$remote" = "$subject"', ci)

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

if __name__ == "__main__":
    unittest.main()

