# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import hashlib
import tempfile
import unittest
from unittest.mock import patch
from tools import qikvrt_live_authority_mirror_ab as bench
from tools.qikvrt_authority_credentials import credential, CREDENTIALS


class CredentialBoundaryTests(unittest.TestCase):
    def test_existing_priority_and_app_fallback(self):
        env={name: 'sentinel-'+str(i) for i,name in enumerate(CREDENTIALS)}
        for name in CREDENTIALS:
            token,source,present=credential(env)
            self.assertEqual((token,source),(env[name],name))
            self.assertTrue(present[name])
            del env[name]

    def test_missing_authority_and_mirror_only_fail_before_network(self):
        with patch.dict(os.environ,{'GITHUB_TOKEN':'mirror-sentinel'},clear=True), \
             patch.object(bench,'head') as network, \
             patch.object(bench,'run',return_value=subprocess.CompletedProcess([],0,b'a'*40+b'\n',b'')):
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(bench.main(),0)
            result=json.loads(output.getvalue())
            self.assertEqual(result['status'],'HOLD_AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED')
            self.assertFalse(result['speedup_claim'])
            self.assertNotIn('wall_speedup_x',result)
            self.assertEqual(result['schema'],'qikvrt_live_authority_mirror_ab_v2')
            self.assertFalse(result['end_to_end']['complete_cycle_observed'])
            self.assertFalse(result['distributed_cycle']['complete_cycle_observed'])
            self.assertNotIn('medians_s',result['local_comparison'])
            self.assertNotIn('mirror-sentinel',output.getvalue())
            network.assert_not_called()

    def test_token_scope_environment_only_and_no_redirect(self):
        with patch.dict(os.environ,{'GIT_TRACE':'1','GIT_CONFIG_COUNT':'9','QIKVRT_MESH_TOKEN':'sentinel'},clear=True):
            authority=bench.network_environment(bench.AUTHORITY_URL,'sentinel')
            mirror=bench.network_environment(bench.MIRROR_URL,'sentinel')
        self.assertNotIn('GIT_TRACE',authority)
        self.assertNotIn('QIKVRT_MESH_TOKEN',authority)
        self.assertEqual(authority['GIT_CONFIG_KEY_2'],'http.'+bench.AUTHORITY_URL+'.extraheader')
        self.assertEqual(authority['GIT_CONFIG_VALUE_1'],'false')
        self.assertEqual(mirror['GIT_CONFIG_COUNT'],'2')
        self.assertFalse(any('AUTHORIZATION' in value for value in mirror.values()))
        with self.assertRaises(ValueError):
            bench.network_environment('https://example.com/repo','sentinel')

    def test_git_failure_cannot_expose_diagnostics(self):
        failure=subprocess.CompletedProcess([],1,b'',b'sentinel-secret')
        with patch.object(bench.subprocess,'run',return_value=failure):
            with self.assertRaisesRegex(RuntimeError,'^GIT_OPERATION_FAILED$'):
                bench.run('git','fetch')
            self.assertEqual(bench.head(bench.AUTHORITY_URL,'sentinel'),(None,'MAIN_READ_FAILED'))

    def test_git_receives_auth_only_through_environment(self):
        success=subprocess.CompletedProcess([],0,b'a'*40+b'\trefs/heads/main\n',b'')
        with patch.object(bench.subprocess,'run',return_value=success) as call:
            self.assertEqual(bench.head(bench.AUTHORITY_URL,'sentinel'),('a'*40,None))
            args,kwargs=call.call_args
            self.assertNotIn('sentinel',repr(args))
            self.assertIn('extraheader',kwargs['env']['GIT_CONFIG_KEY_2'])
            self.assertFalse(kwargs['text'])

    def test_workflow_preserves_fixed_scope(self):
        workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/qikvrt_live_authority_mirror_ab.yml').read_text()
        for text in ('owner: Goldkelch','repositories: qik-vrt','permission-contents: read','persist-credentials: false'):
            self.assertIn(text,workflow)
        self.assertNotIn('contents: write',workflow)
        self.assertNotIn('pull_request_target:',workflow)




def git(repo, *args, data=None):
    result = subprocess.run(["git", "-C", str(repo), *args], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=bench.local_environment(), timeout=30, check=True)
    return result.stdout


def make_repo(path, entries, message="fixture"):
    """Real Git objects, including modes and byte paths; no worktree filters."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)],
                   env=bench.local_environment(), check=True, timeout=30,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    git(path, "config", "user.name", "Benchmark fixture")
    git(path, "config", "user.email", "benchmark@example.invalid")
    records = []
    for name, mode, payload in entries:
        kind = "commit" if mode == "160000" else "blob"
        oid = (payload if kind == "commit"
               else git(path, "hash-object", "-w", "--stdin", data=payload).strip())
        records.append(mode.encode() + b" " + kind.encode() + b" " + oid
                       + b"\t" + name + b"\0")
    tree = git(path, "mktree", "--missing", "-z", data=b"".join(records)).strip()
    commit = git(path, "commit-tree", tree.decode(), "-m", message).strip().decode()
    git(path, "update-ref", "refs/heads/main", commit)
    return commit


class GitObjectComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a, self.b = self.root / "a", self.root / "b"

    def compare(self, left, right, expected):
        ah = make_repo(self.a, left, "authority")
        bh = make_repo(self.b, right, "mirror")
        bench.import_subject(self.a, self.b, bh)
        self.assertEqual(bench.full_compare(self.a, self.b), expected)
        self.assertEqual(bench.delta_compare(self.a, self.b), expected)
        return ah, bh

    def test_binary_payload_is_exact_not_decoded_or_newline_normalized(self):
        left = b"\xff\xfe\0\r\n" + bytes(range(256))
        right = b"\xff\xfe\0\n" + bytes(range(256))
        self.compare([(b"binary.dat", "100644", left)],
                     [(b"binary.dat", "100644", right)], [b"binary.dat"])
        self.assertEqual(bench.hash_path(self.a, b"binary.dat"),
                         hashlib.sha256(left).digest())
        self.assertEqual(bench.hash_path(self.b, b"binary.dat"),
                         hashlib.sha256(right).digest())

    def test_identical_binary_bytes_are_equal(self):
        data = bytes(range(256)) + b"\r\n\0"
        self.compare([(b"blob", "100644", data)],
                     [(b"blob", "100644", data)], [])

    def test_mode_only_change_keeps_blob_id_but_changes_both_comparisons(self):
        self.compare([(b"script", "100644", b"same\n")],
                     [(b"script", "100755", b"same\n")], [b"script"])
        a = bench.tree_entries(self.a)[b"script"]
        b = bench.tree_entries(self.b)[b"script"]
        self.assertEqual(a.oid, b.oid)
        self.assertNotEqual(bench.signature(self.a, a), bench.signature(self.b, b))

    def test_same_blob_as_regular_file_and_symlink_is_unequal(self):
        self.compare([(b"link", "100644", b"target")],
                     [(b"link", "120000", b"target")], [b"link"])

    def test_missing_empty_and_deleted_files_do_not_collapse(self):
        self.compare([(b"deleted", "100644", b""), (b"stable", "100644", b"x")],
                     [(b"added", "100644", b""), (b"stable", "100644", b"x")],
                     [b"added", b"deleted"])
        self.assertIsNone(bench.hash_path(self.a, b"added"))
        self.assertEqual(bench.hash_path(self.b, b"added"), hashlib.sha256(b"").digest())

    def test_commit_metadata_changes_are_distinct_subjects_with_equal_trees(self):
        ah, bh = self.compare([(b"file", "100644", b"identical")],
                              [(b"file", "100644", b"identical")], [])
        self.assertNotEqual(ah, bh)
        self.assertEqual(bench.git_value(self.a, "HEAD^{tree}"),
                         bench.git_value(self.b, "HEAD^{tree}"))

    def test_nul_delimited_byte_paths_preserve_newline_tab_and_non_utf8(self):
        name = b"odd\nname\t\xff"
        self.compare([(name, "100644", b"a")], [(name, "100644", b"b")], [name])
        self.assertEqual(bench.files(self.a), [name])

    def test_gitlinks_bind_commit_identity_without_local_submodule_objects(self):
        self.compare([(b"module", "160000", b"1" * 40)],
                     [(b"module", "160000", b"2" * 40)], [b"module"])

    def test_corrupt_or_missing_blob_is_failure_not_missing_path(self):
        self.compare([(b"file", "100644", b"data")],
                     [(b"file", "100644", b"data")], [])
        entry = bench.tree_entries(self.a)[b"file"]
        (self.a / ".git/objects" / entry.oid[:2] / entry.oid[2:]).unlink()
        with self.assertRaisesRegex(RuntimeError, "^GIT_OPERATION_FAILED$"):
            bench.full_compare(self.a, self.b)

    def test_returned_bytes_must_match_bound_object_id(self):
        entry = bench.Entry("100644", "blob", "a" * 40)
        returned = subprocess.CompletedProcess([], 0, b"tampered", b"")
        with patch.object(bench, "run", return_value=returned):
            with self.assertRaisesRegex(RuntimeError, "^BLOB_OBJECT_ID_MISMATCH$"):
                bench.blob_digest(self.a, entry)

    def test_partial_universe_cannot_hide_a_missing_file(self):
        self.compare([(b"file", "100644", b"data")], [], [b"file"])
        with self.assertRaisesRegex(RuntimeError, "^INCOMPLETE_COMPARISON_UNIVERSE$"):
            bench.full_compare(self.a, self.b, [])

    def test_local_samples_are_scoped_and_methods_must_agree(self):
        self.compare([(b"file", "100644", b"data")],
                     [(b"file", "100755", b"data")], [b"file"])
        result = bench.measure_local(self.a, self.b, repeats=2)
        self.assertEqual(result["scope"], bench.LOCAL_SCOPE)
        self.assertEqual(len(result["samples_s"]["full"]), 2)
        self.assertFalse(result["distributed_speedup_claim"])
        self.assertIn("remote_fetch", result["excluded_phases"])
        with patch.dict(bench.COMPARISONS, {"delta": lambda *args: []}):
            with self.assertRaisesRegex(RuntimeError, "^COMPARISON_RESULT_MISMATCH$"):
                bench.measure_local(self.a, self.b, repeats=1)


class LocalGitTransport:
    """Exercise the production carrier with two real local Git remotes."""
    def __init__(self, authority, mirror, clock=None):
        self.remotes = {"authority": authority, "mirror": mirror}
        self.events = []
        self.clock = clock
        self.drift_on_readback = False
        self.head_reads = 0

    def heads(self):
        self.events.append("heads")
        self.head_reads += 1
        if self.clock:
            self.clock.advance(3)
        values = tuple(bench.git_value(self.remotes[role], "HEAD^{commit}")
                       for role in ("authority", "mirror"))
        if self.drift_on_readback and self.head_reads > 1:
            return "f" * 40, values[1]
        return values

    def fetch(self, role, sha, dest):
        self.events.append("fetch-" + role)
        if self.clock:
            self.clock.advance(2)
        # Test-only local transport; production fixed-URL policy is unchanged.
        with patch.object(bench, "network_environment", return_value=bench.local_environment()):
            bench.fetch_repo(str(self.remotes[role]), sha, dest)


class EventClock:
    def __init__(self):
        self.value = 0.0
        self.calls = []

    def advance(self, seconds):
        self.value += seconds

    def __call__(self):
        self.calls.append(self.value)
        return self.value


class EndToEndBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a, self.b = self.root / "remote-a", self.root / "remote-b"
        self.ah = make_repo(self.a, [(b"binary", "100755", b"\xff\r\n\0"),
                                    (b"new", "100644", b"")], "new subject")
        self.mh = make_repo(self.b, [(b"binary", "100644", b"\xff\r\n\0"),
                                    (b"old", "100644", b"x")], "replica base")
        self.subjects = self.ah, self.mh
        self.transport = LocalGitTransport(self.a, self.b)

    def test_real_fetch_reconcile_and_independent_readback_for_both_methods(self):
        result = bench.measure_end_to_end(self.transport, self.root / "cycles",
                                         self.subjects, repeats=2)
        self.assertTrue(result["complete_cycle_observed"])
        self.assertEqual(len(result["cycles"]), 4)
        for cycle in result["cycles"]:
            self.assertEqual(cycle["completed_phases"], list(bench.PHASES))
            self.assertEqual(cycle["changed_file_count"], 3)
            self.assertEqual(cycle["readback"]["head"], self.ah)
            self.assertEqual(cycle["readback"]["tree"],
                             bench.git_value(self.a, "HEAD^{tree}"))
            self.assertTrue(cycle["readback"]["independent_remote_refetch"])
            self.assertFalse(cycle["remote_mirror_mutated"])
            self.assertFalse(cycle["distributed_speedup_claim"])
        self.assertEqual(self.transport.events.count("fetch-authority"), 8)
        self.assertEqual(bench.git_value(self.b, "HEAD^{commit}"), self.mh)
        self.assertFalse(result["distributed_speedup_claim"])
        self.assertNotIn("wall_speedup_x", result)

    def test_clock_includes_binding_fetch_reconciliation_and_last_readback(self):
        clock = EventClock()
        transport = LocalGitTransport(self.a, self.b, clock)
        original_compare = bench.full_compare
        original_reconcile = bench.reconcile
        original_readback = bench.fresh_readback

        def compare(*args):
            clock.advance(5)
            return original_compare(*args)

        def reconcile(*args):
            clock.advance(7)
            return original_reconcile(*args)

        def readback(*args):
            clock.advance(11)
            return original_readback(*args)

        with patch.dict(bench.COMPARISONS, {"full": compare}), \
             patch.object(bench, "reconcile", side_effect=reconcile), \
             patch.object(bench, "fresh_readback", side_effect=readback):
            cycle = bench.end_to_end_cycle(transport, self.root / "timed",
                                          self.subjects, "full", clock=clock)
        self.assertTrue(cycle["complete_cycle_observed"])
        self.assertEqual(cycle["elapsed_s"], 35)
        self.assertEqual(clock.calls[0], 0)
        self.assertEqual(clock.calls[-1], 35)
        self.assertEqual(transport.events, ["heads", "fetch-authority", "fetch-mirror",
                                           "fetch-authority", "heads"])
        for phase in cycle["phases"].values():
            self.assertGreater(phase["duration_s"], 0)
            self.assertGreaterEqual(phase["start_offset_s"], 0)
            self.assertLessEqual(phase["end_offset_s"], cycle["elapsed_s"])

    def test_drift_before_fetch_prevents_measurement_and_ratio(self):
        result = bench.measure_end_to_end(self.transport, self.root / "drift",
                                         ("0" * 40, self.mh), repeats=1)
        self.assertEqual(result["status"], "HOLD_REMOTE_SUBJECT_MOVED")
        self.assertFalse(result["complete_cycle_observed"])
        self.assertEqual(self.transport.events, ["heads"])
        self.assertNotIn("sandbox_median_ratio_full_over_delta", result)

    def test_drift_at_final_fresh_readback_never_becomes_a_complete_cycle(self):
        self.transport.drift_on_readback = True
        result = bench.measure_end_to_end(self.transport, self.root / "late-drift",
                                         self.subjects, repeats=1)
        self.assertEqual(result["status"], "HOLD_REMOTE_SUBJECT_MOVED")
        self.assertFalse(result["complete_cycle_observed"])
        self.assertNotIn("fresh_readback", result["cycles"][0]["completed_phases"])
        self.assertNotIn("medians_s", result)

    def test_skipped_reconciliation_is_rejected_by_actual_readback(self):
        with patch.object(bench, "reconcile", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "^RECONCILIATION_READBACK_MISMATCH$"):
                bench.end_to_end_cycle(self.transport, self.root / "skipped",
                                       self.subjects, "delta")

    def test_same_head_is_not_a_new_subject_cycle(self):
        transport = LocalGitTransport(self.a, self.a)
        cycle = bench.end_to_end_cycle(transport, self.root / "same",
                                      (self.ah, self.ah), "full")
        self.assertEqual(cycle["status"], "HOLD_NEW_SUBJECT_NOT_ESTABLISHED")
        self.assertFalse(cycle["complete_cycle_observed"])
        self.assertEqual(transport.events, ["heads"])

    def test_new_commit_with_equal_tree_is_reconciled_and_read_back_by_head(self):
        make_repo(self.b, [(b"binary", "100755", b"\xff\r\n\0"),
                          (b"new", "100644", b"")], "different metadata")
        subjects = self.ah, bench.git_value(self.b, "HEAD^{commit}")
        cycle = bench.end_to_end_cycle(self.transport, self.root / "metadata",
                                      subjects, "delta")
        self.assertTrue(cycle["complete_cycle_observed"])
        self.assertEqual(cycle["changed_file_count"], 0)
        self.assertEqual(cycle["readback"]["head"], self.ah)

    def test_failed_remote_fetch_never_produces_a_measurement(self):
        with patch.object(self.transport, "fetch",
                          side_effect=RuntimeError("GIT_OPERATION_FAILED")):
            with self.assertRaisesRegex(RuntimeError, "^GIT_OPERATION_FAILED$"):
                bench.measure_end_to_end(self.transport, self.root / "failed",
                                         self.subjects, repeats=1)

if __name__=='__main__':
    unittest.main()
