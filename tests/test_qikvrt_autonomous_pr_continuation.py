# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import copy
import concurrent.futures
import base64
import datetime
import io
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
import textwrap
import threading
import unittest
from unittest import mock

from tools import qikvrt_autonomous_self_heal as controller

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
CONTINUATION = ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml"
VERIFIER = ROOT / ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"


class AutonomousPRContinuationTests(unittest.TestCase):
    def test_contract_is_opt_in_same_repo_draft_and_one_at_a_time(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        value = contract["pull_request_continuation"]
        self.assertEqual(
            value["opt_in_marker"],
            "<!-- qikvrt-autonomous-self-heal:enabled -->",
        )
        self.assertTrue(value["same_repository_only"])
        self.assertTrue(value["draft_only"])
        self.assertEqual(value["maximum_pull_requests_per_run"], 1)
        self.assertEqual(value["history_rewrite"], "FORBIDDEN")
        self.assertEqual(
            value["automatic_promotion"],
            "TWO_PHASE_EXPECTED_HEAD_BOUND_ONLY",
        )

    def test_continuation_preserves_history_and_never_merges_or_force_pushes(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        self.assertIn("git merge-tree --write-tree", source)
        self.assertIn('-p "$EXPECTED_HEAD" -p "$live_main"', source)
        self.assertIn("live_head_before_push", source)
        self.assertIn("pr-publish", source)
        self.assertNotIn("git fetch", source)
        self.assertNotIn("git push", source)
        self.assertNotIn("actions/checkout", source)
        self.assertNotIn("git push --force", source)
        self.assertNotIn("git push -f", source)
        self.assertNotIn("gh pr merge", source)
        self.assertNotIn("refs/heads/main\"", source)
        self.assertIn("make test", source)
        self.assertIn("qikvrt_autonomous_exact_head_verify", source)

    def test_only_handler_owned_generated_conflicts_are_auto_resolved(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        self.assertIn("/tmp/qikvrt-merge-conflicts.txt", source)
        self.assertIn(".allowlisted_handlers[].mutable_paths[]", source)
        self.assertIn("BLOCK: non-allowlisted merge conflicts", source)
        self.assertIn('git checkout "$EXPECTED_HEAD"', source)
        self.assertIn("generated-output reset", source)
        self.assertNotIn("git checkout --theirs", source)
        self.assertNotIn("git merge --abort || true", source)

    def test_continuation_shell_block_is_syntax_valid(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        blocks = source.split("        run: |\n")[1:]
        for block in blocks:
            script = textwrap.dedent(block.split("\n      - name:", 1)[0])
            completed = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_single_native_lane_and_new_regressions_are_mandatory(self) -> None:
        source = CONTINUATION.read_text()
        self.assertIn("group: qikvrt-autonomous-pr-continuation-${{ github.repository }}", source)
        self.assertIn("cancel-in-progress: false", source)
        self.assertIn("timeout-minutes: 60", source)
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("test: autonomous-pr-continuation-test", makefile)
        self.assertIn("tests.test_qikvrt_autonomous_pr_continuation", makefile)

    def test_dispatch_verifier_binds_exact_head_and_posts_a_distinct_status(self) -> None:
        source = VERIFIER.read_text(encoding="utf-8")
        self.assertIn("repository_dispatch", source)
        self.assertIn("qikvrt_autonomous_exact_head_verify", source)
        self.assertIn("test \"$(git rev-parse --verify HEAD^{commit})\" = \"$TARGET_SHA\"", source)
        self.assertIn("make test", source)
        self.assertIn("verify_qce_package.py", source)
        self.assertIn("QIKVRT autonomous exact-head verification", source)
        self.assertNotIn("gh pr merge", source)
        self.assertNotIn("zenodo", source.casefold())
        self.assertNotIn("ietf", source.casefold())

    def test_external_review_and_publication_gates_remain_distinct(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        gates = contract["pull_request_continuation"]["external_gates"]
        self.assertEqual(
            gates,
            [
                "IDENTIFIED_HUMAN_PHYSICS_REVIEW_WHEN_REQUIRED",
                "SEPARATE_EXPLICIT_ZENODO_AUTHORIZATION",
            ],
        )


REPOSITORY = "ingolf-lohmann/qik-vrt"
MAIN = "a" * 40


def pr(number: int, head: str | None = None) -> dict:
    return {"number": number, "state": "open", "draft": True,
            "body": controller.PR_MARKER,
            "head": {"repo": {"full_name": REPOSITORY}, "ref": f"work/pr-{number}",
                     "sha": head or f"{number:040x}"},
            "base": {"repo": {"full_name": REPOSITORY}, "ref": "main", "sha": MAIN}}


class MemoryREST(controller.GitHubREST):
    """An independent in-memory REST server with atomic create-only refs."""
    def __init__(self, prs=None):
        super().__init__(REPOSITORY)
        self.prs = copy.deepcopy(prs or [pr(437), pr(459)])
        self.refs = {"refs/heads/main": {"ref": "refs/heads/main", "object": {"sha": MAIN}}}
        self.comments = {}
        self.statuses = {}
        self.posts = []
        self.failures = {}
        self.rejections = {}
        self.lock = threading.RLock()
        self.barrier = None
        self._reads = 0

    def ref(self, ref):
        with self.lock:
            value = copy.deepcopy(self.refs.get(ref))
        if self.barrier and "/turns/" in ref and value is None:
            self.barrier.wait(timeout=10)
        return value

    def pages(self, path):
        with self.lock:
            if path.startswith("pulls?"): return copy.deepcopy(self.prs)
            if path.startswith("git/matching-refs/"):
                prefix = "refs/" + path.removeprefix("git/matching-refs/")
                return copy.deepcopy([v for key, v in self.refs.items() if key.startswith(prefix)])
            if path.startswith("commits/"): return copy.deepcopy(self.statuses.get(path.split('/')[1], []))
            if path.startswith("issues/"): return copy.deepcopy(self.comments.get(int(path.split('/')[1]), []))
        raise AssertionError(path)

    def call(self, method, path, payload=None):
        with self.lock:
            if (method, path) in self.rejections:
                raise controller.SelfHealBlock('REST ' + method + ' ' + path + ': 403; no automatic retry')
            if method == "GET" and path.startswith("pulls/"):
                return copy.deepcopy(next(p for p in self.prs if p['number'] == int(path.split('/')[1])))
            if method == "GET" and path.startswith("issues/comments/"):
                return copy.deepcopy(next(c for cs in self.comments.values() for c in cs if c['id'] == int(path.split('/')[-1])))
            if method == "POST" and path == "git/refs":
                if payload['ref'] in self.refs:
                    raise controller.SelfHealBlock("REST POST git/refs: 422; no automatic retry")
                self.refs[payload['ref']] = {"ref": payload['ref'], "object": {"sha": payload['sha']}}
                result = copy.deepcopy(self.refs[payload['ref']])
            elif method == "POST" and path.startswith("statuses/"):
                result = dict(payload, id=len(self.posts) + 1)
                self.statuses.setdefault(path.split('/')[1], []).append(result)
            elif method == "POST" and path == "dispatches":
                result = None
            elif method == "POST" and path.startswith("issues/"):
                result = dict(payload, id=len(self.posts) + 1, user={"login": "github-actions[bot]"})
                self.comments.setdefault(int(path.split('/')[1]), []).append(result)
            else:
                raise AssertionError((method, path, payload))
            self.posts.append((method, path, copy.deepcopy(payload)))
            if path in self.failures:
                self.failures.pop(path)
                raise controller.SelfHealBlock("ambiguous transport after accepted " + path)
            return result


class FairContinuationRegressionTests(unittest.TestCase):
    def test_initial_selection_uses_legacy_service_without_touching_459(self):
        api = MemoryREST()
        api.comments[437] = [{"user": {"login": "github-actions[bot]"},
                              "body": controller.CONTINUATION_MARKER + "\nold receipt",
                              "created_at": "2026-10-08T09:26:01Z"}]
        original = copy.deepcopy(api.prs[1])
        plan = controller.observe_pr_plan(api)
        self.assertEqual(plan['selected']['pull_request'], 459)
        self.assertEqual(api.prs[1], original)
        self.assertEqual(api.posts, [])

    def test_many_noops_rotate_all_prs_without_commits_or_handoffs(self):
        api = MemoryREST([pr(500), pr(459), pr(437)])
        selected = []
        for run_id in range(1, 13):
            result = controller.claim_pr_plan(api, controller.observe_pr_plan(api), run_id)
            selected.append(result['selected']['pull_request'])
        self.assertEqual(selected, [437, 459, 500] * 4)
        self.assertTrue(all(path == 'git/refs' for _, path, _ in api.posts))
        self.assertTrue(all(value['ref'].startswith(controller.CONTINUATION_REFS) for _, _, value in api.posts))

    def test_noop_cannot_publish_a_successor(self):
        api = MemoryREST()
        plan = controller.observe_pr_plan(api)
        with self.assertRaisesRegex(controller.SelfHealBlock, 'NOOP'):
            controller.export_rest_successor(api, ROOT, plan, plan['selected']['head_sha'])
        self.assertEqual(api.posts, [])

    def test_new_heads_and_updated_at_do_not_reset_fairness(self):
        api = MemoryREST()
        controller.claim_pr_plan(api, controller.observe_pr_plan(api), 100)
        api.prs[0]['head']['sha'] = 'f' * 40
        api.prs[0]['updated_at'] = '2099-01-01T00:00:00Z'
        plan = controller.observe_pr_plan(api)
        self.assertEqual(plan['selected']['pull_request'], 459)
        controller.claim_pr_plan(api, plan, 101)
        self.assertEqual(controller.observe_pr_plan(api)['selected']['pull_request'], 437)

    def test_out_of_order_native_run_ids_still_rotate_by_actual_claim_order(self):
        api = MemoryREST([pr(437), pr(459), pr(500)])
        result = []
        for run_id in [100, 5, 999, 1, 888, 7]:
            plan = controller.claim_pr_plan(api, controller.observe_pr_plan(api), run_id)
            result.append(plan['selected']['pull_request'])
        self.assertEqual(result, [437, 459, 500] * 2)

    def test_changed_head_after_observation_fails_before_any_claim(self):
        api = MemoryREST()
        plan = controller.observe_pr_plan(api)
        api.prs[0]['head']['sha'] = 'e' * 40
        with self.assertRaisesRegex(controller.SelfHealBlock, 'exact head'):
            controller.claim_pr_plan(api, plan, 1)
        self.assertEqual(api.posts, [])

    def test_opt_out_after_observation_fails_before_any_claim(self):
        api = MemoryREST()
        plan = controller.observe_pr_plan(api)
        api.prs[0]['body'] = ''
        with self.assertRaises(controller.SelfHealBlock): controller.claim_pr_plan(api, plan, 1)
        self.assertEqual(api.posts, [])

    def test_ineligible_prs_cannot_enter_the_queue(self):
        for mutation in ('closed', 'ready', 'fork', 'base', 'main_head', 'marker'):
            value = pr(437)
            if mutation == 'closed': value['state'] = 'closed'
            elif mutation == 'ready': value['draft'] = False
            elif mutation == 'fork': value['head']['repo']['full_name'] = 'someone/qik-vrt'
            elif mutation == 'base': value['base']['ref'] = 'develop'
            elif mutation == 'main_head': value['head']['ref'] = 'main'
            else: value['body'] = ''
            self.assertEqual(controller.rank_prs([value], REPOSITORY, [], {}), [])

    def test_legacy_user_text_cannot_forge_native_service_age(self):
        comments = {437: [{'user': {'login': 'someone'}, 'body': controller.CONTINUATION_MARKER + '\n', 'created_at': '2099'}]}
        ranked = controller.rank_prs([pr(459), pr(437)], REPOSITORY, [], comments)
        self.assertEqual([p['pull_request'] for p in ranked], [437, 459])

    def test_malformed_attempt_inventory_fails_closed(self):
        with self.assertRaises(controller.SelfHealBlock):
            controller.rank_prs([pr(437)], REPOSITORY, [{'ref': 'refs/other', 'object': {'sha': MAIN}}], {})

    def test_native_run_rerun_is_noop_even_when_queue_would_rotate(self):
        api = MemoryREST()
        controller.claim_pr_plan(api, controller.observe_pr_plan(api), 1)
        count = len(api.posts)
        result = controller.claim_pr_plan(api, controller.observe_pr_plan(api), 1)
        self.assertEqual(result['state'], 'DUPLICATE_RUN_NOOP')
        self.assertIsNone(result['selected'])
        self.assertEqual(len(api.posts), count)

    def test_parallel_stale_plans_have_one_atomic_turn_winner(self):
        api = MemoryREST()
        plan = controller.observe_pr_plan(api)
        api.barrier = threading.Barrier(2)
        def claim(run_id):
            try: return controller.claim_pr_plan(api, copy.deepcopy(plan), run_id)['state']
            except controller.SelfHealBlock: return 'BLOCK'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, [1, 2]))
        self.assertEqual(results.count('SELECTION_CLAIMED'), 1)
        self.assertEqual(len(api.pages('git/matching-refs/qikvrt/pr-continuation/attempts/')), 1)
        api.barrier = None
        self.assertEqual(controller.observe_pr_plan(api)['selected']['pull_request'], 459)

    def prepare_handoff(self):
        api = MemoryREST()
        plan = controller.claim_pr_plan(api, controller.observe_pr_plan(api), 1)
        candidate = 'c' * 40
        api.prs[0]['head']['sha'] = candidate
        return api, plan, candidate

    def test_handoff_has_one_status_dispatch_and_comment_on_repeat(self):
        api, plan, candidate = self.prepare_handoff()
        first = controller.handoff_pr(api, plan, candidate)
        count = len(api.posts)
        second = controller.handoff_pr(api, plan, candidate)
        self.assertEqual(first, second)
        self.assertEqual(len(api.posts), count)
        self.assertEqual(first['workflow_admission'], 'UNESTABLISHED')
        self.assertFalse(first['main_activation'])

    def test_ambiguous_dispatch_is_never_replayed_and_does_not_starve_other_pr(self):
        api, plan, candidate = self.prepare_handoff()
        api.failures['dispatches'] = True
        with self.assertRaises(controller.SelfHealBlock): controller.handoff_pr(api, plan, candidate)
        with self.assertRaisesRegex(controller.SelfHealBlock, 'DISPATCH_OUTCOME_UNESTABLISHED'):
            controller.handoff_pr(api, plan, candidate)
        self.assertEqual(sum(path == 'dispatches' for _, path, _ in api.posts), 1)
        self.assertEqual(controller.observe_pr_plan(api)['selected']['pull_request'], 459)

    def test_ambiguous_delivered_comment_is_recovered_by_get_without_duplicate(self):
        api, plan, candidate = self.prepare_handoff()
        api.failures['issues/437/comments'] = True
        with self.assertRaises(controller.SelfHealBlock): controller.handoff_pr(api, plan, candidate)
        self.assertEqual(controller.handoff_pr(api, plan, candidate)['state'], 'HANDOFF_SUBMITTED')
        self.assertEqual(sum(path == 'issues/437/comments' for _, path, _ in api.posts), 1)

    def test_status_outcome_can_be_reobserved_without_duplicate_status(self):
        api, plan, candidate = self.prepare_handoff()
        api.failures['statuses/' + candidate] = True
        with self.assertRaises(controller.SelfHealBlock): controller.handoff_pr(api, plan, candidate)
        controller.handoff_pr(api, plan, candidate)
        self.assertEqual(sum(path.startswith('statuses/') for _, path, _ in api.posts), 1)

    def test_rejected_handoff_cannot_starve_the_next_pr_or_claim_admission(self):
        api, plan, candidate = self.prepare_handoff()
        api.rejections[('POST', 'dispatches')] = True
        with self.assertRaisesRegex(controller.SelfHealBlock, '403'):
            controller.handoff_pr(api, plan, candidate)
        next_plan = controller.claim_pr_plan(api, controller.observe_pr_plan(api), 2)
        self.assertEqual(next_plan['selected']['pull_request'], 459)
        self.assertFalse(any(path == 'dispatches' for _, path, _ in api.posts))

    def test_existing_successor_resumes_handoff_without_another_commit(self):
        api, plan, candidate = self.prepare_handoff()
        selected = plan['selected']
        ref = controller.CONTINUATION_REFS + f"effects/437/{selected['head_sha']}-{MAIN}/successor"
        api.create_once(ref, candidate)
        controller.claim_pr_plan(api, controller.observe_pr_plan(api), 2)  # 459
        resumed = controller.claim_pr_plan(api, controller.observe_pr_plan(api), 3)
        self.assertTrue(resumed['selected']['resume_handoff'])
        self.assertEqual(resumed['selected']['source_head_sha'], selected['head_sha'])
        self.assertEqual(resumed['selected']['head_sha'], candidate)
        self.assertTrue(all(path == 'git/refs' for _, path, _ in api.posts))

    def test_changed_head_before_handoff_has_no_external_effect(self):
        api, plan, candidate = self.prepare_handoff()
        api.prs[0]['head']['sha'] = 'd' * 40
        count = len(api.posts)
        with self.assertRaises(controller.SelfHealBlock): controller.handoff_pr(api, plan, candidate)
        self.assertEqual(len(api.posts), count)

    def test_action_required_is_neither_selected_as_success_nor_approved(self):
        api = MemoryREST()
        api.prs[0]['workflow_conclusion'] = 'action_required'
        plan = controller.observe_pr_plan(api)
        self.assertEqual(plan['selected']['pull_request'], 437)
        controller.claim_pr_plan(api, plan, 1)
        self.assertFalse(any('approve' in path or 'rerun' in path for _, path, _ in api.posts))

    def test_complete_shell_noop_preserves_git_head_and_has_only_rest_gets(self):
        source = CONTINUATION.read_text()
        marker = '      - name: Continue exact draft head through deterministic repairs\n'
        block = source[source.index(marker):].split('        run: |\n', 1)[1].split('\n      - name:', 1)[0]
        script = textwrap.dedent(block)
        with tempfile.TemporaryDirectory() as directory:
            parent = pathlib.Path(directory); root = parent / 'repo'; root.mkdir()
            (root / 'tools').mkdir()
            (root / 'tools/qikvrt_autonomous_self_heal.py').write_text("print('{\"state\":\"NOOP\",\"changed_paths\":[]}')\n")
            def git(*args): return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
            git('init', '-b', 'main'); git('config', 'user.name', 'test'); git('config', 'user.email', 'test@example.invalid')
            git('add', '.'); git('commit', '-m', 'initial'); head = git('rev-parse', 'HEAD')
            runtime = parent / 'runtime'; runtime.mkdir()
            (runtime / 'qikvrt-pr-controller.py').write_text("import sys\nassert sys.argv[1]=='pr-import'\n")
            bindir = parent / 'bin'; bindir.mkdir()
            gh = bindir / 'gh'
            gh.write_text("#!/usr/bin/env python3\nimport os,sys,json\n"
                          "with open(os.environ['REST_CALL_LOG'],'a') as f:f.write(' '.join(sys.argv[1:])+'\\n')\n"
                          "head=os.environ['EXPECTED_HEAD']\n"
                          "print(json.dumps({'merge_base_commit':{'sha':head}}) if any('/compare/' in a for a in sys.argv) else head)\n")
            gh.chmod(0o755)
            env = dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ['PATH'], RUNNER_TEMP=str(runtime),
                       EXPECTED_HEAD=head, PR_NUMBER='437', BASE_REF='main', HEAD_REF='work/pr-437',
                       GITHUB_REPOSITORY=REPOSITORY, REST_CALL_LOG=str(parent / 'rest.log'))
            script = script.replace('/tmp/qikvrt-', str(runtime / 'qikvrt-'))
            completed = subprocess.run(['bash', '-e'], input=script, cwd=root, env=env,
                                       text=True, capture_output=True, timeout=30)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(git('rev-parse', 'HEAD'), head)
            self.assertEqual(git('rev-list', '--count', 'HEAD'), '1')
            self.assertEqual(git('status', '--porcelain'), '')
            calls = (parent / 'rest.log').read_text()
            self.assertNotIn('POST', calls); self.assertNotIn('PATCH', calls)


def git_bytes(root, *args, data=None, env=None):
    return subprocess.check_output(['git', *args], cwd=root, input=data,
                                   env=env, stderr=subprocess.DEVNULL)


def commit_metadata(root, sha):
    raw = git_bytes(root, 'cat-file', 'commit', sha).decode()
    headers, message = raw.split('\n\n', 1)
    result = {'sha': sha, 'parents': [], 'message': message.removesuffix('\n'), 'verification': {}}
    for line in headers.splitlines():
        if line.startswith('tree '): result['tree'] = {'sha': line.split()[1]}
        elif line.startswith('parent '): result['parents'].append({'sha': line.split()[1]})
        elif line.startswith(('author ', 'committer ')):
            role, identity = line.split(' ', 1)
            name, remainder = identity.rsplit(' <', 1)
            email, stamp, zone = remainder.replace('>', '').split()
            result[role] = {'name': name, 'email': email,
                            'date': datetime.datetime.fromtimestamp(int(stamp), datetime.timezone.utc).isoformat()}
    return result


class GitDataREST(MemoryREST):
    """Compute Git-data responses from independent real Git object/index logic."""
    def __init__(self, root, main, source):
        super().__init__([pr(437, source)])
        self.root = root
        self.refs['refs/heads/main']['object']['sha'] = main
        self.prs[0]['base']['sha'] = main

    def call(self, method, path, payload=None):
        if method == 'GET' and path.startswith('git/commits/'):
            return commit_metadata(self.root, path.split('/')[-1])
        if method == 'GET' and path.startswith('git/trees/'):
            sha = path.split('/')[-1].split('?')[0]
            records = git_bytes(self.root, 'ls-tree', '-r', '-t', '-z', sha).split(b'\0')
            entries = []
            for record in records:
                if not record: continue
                info, name = record.split(b'\t', 1); mode, kind, identity = info.decode().split()
                entries.append({'path': name.decode(), 'mode': mode, 'type': kind, 'sha': identity})
            return {'tree': entries, 'truncated': False}
        if method == 'GET' and path.startswith('git/blobs/'):
            raw = git_bytes(self.root, 'cat-file', 'blob', path.split('/')[-1])
            return {'content': base64.b64encode(raw).decode(), 'encoding': 'base64'}
        if method == 'POST' and path == 'git/blobs':
            sha = git_bytes(self.root, 'hash-object', '-w', '--stdin', data=base64.b64decode(payload['content'])).decode().strip()
            result = {'sha': sha}
        elif method == 'POST' and path == 'git/trees':
            with tempfile.TemporaryDirectory() as directory:
                env = dict(os.environ, GIT_INDEX_FILE=str(pathlib.Path(directory) / 'index'))
                git_bytes(self.root, 'read-tree', payload['base_tree'], env=env)
                entries = []
                for item in payload['tree']:
                    mode, sha = (item['mode'], item['sha']) if item['sha'] else ('0', '0' * 40)
                    entries.append(f"{mode} {sha}\t{item['path']}".encode() + b'\0')
                git_bytes(self.root, 'update-index', '-z', '--index-info', env=env, data=b''.join(entries))
                result = {'sha': git_bytes(self.root, 'write-tree', env=env).decode().strip()}
        elif method == 'POST' and path == 'git/commits':
            headers = ['tree ' + payload['tree'], *['parent ' + p for p in payload['parents']]]
            for role in ('author', 'committer'):
                identity = payload[role]; date = datetime.datetime.fromisoformat(identity['date'])
                zone = date.strftime('%z')
                headers.append(f"{role} {identity['name']} <{identity['email']}> {int(date.timestamp())} {zone}")
            raw = ('\n'.join(headers) + '\n\n' + payload['message'] + '\n').encode()
            result = {'sha': git_bytes(self.root, 'hash-object', '-w', '-t', 'commit', '--stdin', data=raw).decode().strip()}
        elif method == 'PATCH' and path.startswith('git/refs/heads/'):
            assert payload['force'] is False
            self.prs[0]['head']['sha'] = payload['sha']
            result = {'object': {'sha': payload['sha']}}
        else:
            return super().call(method, path, payload)
        self.posts.append((method, path, copy.deepcopy(payload)))
        return result


class RESTTransportRegressionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.directory.name) / 'source'; self.root.mkdir()
        git_bytes(self.root, 'init', '-b', 'main')
        git_bytes(self.root, 'config', 'user.name', 'test'); git_bytes(self.root, 'config', 'user.email', 'test@example.invalid')
        (self.root / 'file.cmd').write_bytes(b'first\nsecond\n')
        (self.root / 'nested').mkdir(); (self.root / 'nested/run.sh').write_text('#!/bin/sh\nexit 0\n')
        (self.root / 'nested/run.sh').chmod(0o755)
        self.env = dict(os.environ, GIT_AUTHOR_DATE='2026-10-08T12:00:00+0000', GIT_COMMITTER_DATE='2026-10-08T12:00:00+0000')
        self.commit('initial')
        self.initial = git_bytes(self.root, 'rev-parse', 'HEAD').decode().strip()

    def tearDown(self): self.directory.cleanup()

    def commit(self, message):
        git_bytes(self.root, 'add', '.')
        git_bytes(self.root, 'commit', '-m', message, env=self.env)
        return git_bytes(self.root, 'rev-parse', 'HEAD').decode().strip()

    def plan(self, api):
        return controller.claim_pr_plan(api, controller.observe_pr_plan(api), 1)

    def test_rest_snapshot_recovers_raw_archive_bytes_and_executable_modes(self):
        api = GitDataREST(self.root, self.initial, self.initial)
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode='w:gz') as bundle:
            for relative in ('file.cmd', 'nested/run.sh'):
                raw = (self.root / relative).read_bytes()
                if relative == 'file.cmd': raw = raw.replace(b'\n', b'\r\n')
                info = tarfile.TarInfo('archive-root/' + relative); info.size = len(raw); info.mode = 0o644
                bundle.addfile(info, io.BytesIO(raw))
        real_run = subprocess.run
        def archive_run(command, **kwargs):
            if command[0] == 'gh':
                self.assertEqual(command[1:4], ['api', '--method', 'GET'])
                kwargs['stdout'].write(archive.getvalue())
                return subprocess.CompletedProcess(command, 0, stderr=b'')
            return real_run(command, **kwargs)
        target = pathlib.Path(self.directory.name) / 'target'
        with mock.patch.object(controller.subprocess, 'run', side_effect=archive_run):
            controller.import_rest_snapshot(api, target, self.initial, checkout=True)
        self.assertEqual(git_bytes(target, 'rev-parse', 'HEAD').decode().strip(), self.initial)
        self.assertEqual(git_bytes(target, 'rev-parse', 'HEAD^{tree}'), git_bytes(self.root, 'rev-parse', 'HEAD^{tree}'))
        self.assertEqual((target / 'file.cmd').read_bytes(), (self.root / 'file.cmd').read_bytes())
        self.assertTrue((target / 'nested/run.sh').stat().st_mode & 0o111)
        self.assertEqual(git_bytes(target, 'status', '--porcelain'), b'')
        self.assertEqual(api.posts, [])

    def test_non_utc_original_commit_is_recovered_without_rewriting_it(self):
        self.env.update(GIT_AUTHOR_DATE='2026-10-08T15:00:00+0300', GIT_COMMITTER_DATE='2026-10-08T15:00:00+0300')
        (self.root / 'file.cmd').write_text('changed\n'); sha = self.commit('time zone')
        api = GitDataREST(self.root, sha, sha)
        target = pathlib.Path(self.directory.name) / 'other'; target.mkdir(); git_bytes(target, 'init')
        controller.import_rest_commit(api, target, sha)
        self.assertEqual(git_bytes(target, 'cat-file', 'commit', sha), git_bytes(self.root, 'cat-file', 'commit', sha))

    def test_signed_raw_commit_import_preserves_signature_without_claiming_validity(self):
        metadata = commit_metadata(self.root, self.initial)
        unsigned = git_bytes(self.root, 'cat-file', 'commit', self.initial).decode()
        headers, message = unsigned.split('\n\n', 1)
        signature = '-----BEGIN PGP SIGNATURE-----\nfixture bytes\n-----END PGP SIGNATURE-----\n'
        raw = (headers + '\ngpgsig ' + '\n '.join(signature.rstrip('\n').split('\n')) + '\n\n' + message).encode()
        sha = git_bytes(self.root, 'hash-object', '-w', '-t', 'commit', '--stdin', data=raw).decode().strip()
        metadata.update(sha=sha, verification={'payload': unsigned, 'signature': signature, 'verified': False})
        api = GitDataREST(self.root, self.initial, self.initial)
        original_call = api.call
        api.call = lambda method, path, payload=None: metadata if path == 'git/commits/' + sha else original_call(method, path, payload)
        target = pathlib.Path(self.directory.name) / 'signed'; target.mkdir(); git_bytes(target, 'init')
        controller.import_rest_commit(api, target, sha)
        self.assertEqual(git_bytes(target, 'cat-file', 'commit', sha), raw)

    def test_shallow_rest_merge_uses_explicit_common_ancestor_and_two_parents(self):
        (self.root / 'main.txt').write_text('main addition\n'); main = self.commit('main change')
        git_bytes(self.root, 'checkout', '-b', 'work', self.initial)
        (self.root / 'draft.txt').write_text('draft addition\n'); source = self.commit('draft change')
        # Test the actual primitive used by the workflow, even when both source
        # commits are shallow and local ancestry walking cannot supply a base.
        (self.root / '.git/shallow').write_text(main + '\n' + source + '\n' + self.initial + '\n')
        result = git_bytes(self.root, 'merge-tree', '--write-tree', '--name-only', '-z',
                           '--merge-base=' + self.initial, source, main)
        tree = result.split(b'\0', 1)[0].decode()
        successor = git_bytes(self.root, 'commit-tree', tree, '-p', source, '-p', main,
                              '-m', 'merge', env=self.env).decode().strip()
        metadata = commit_metadata(self.root, successor)
        self.assertEqual([p['sha'] for p in metadata['parents']], [source, main])
        self.assertEqual(git_bytes(self.root, 'show', successor + ':main.txt'), b'main addition\n')
        self.assertEqual(git_bytes(self.root, 'show', successor + ':draft.txt'), b'draft addition\n')

    def test_rest_successor_exports_exact_tree_commit_and_nonforce_ref(self):
        (self.root / 'file.cmd').write_text('main\n'); main = self.commit('main change')
        git_bytes(self.root, 'checkout', '-b', 'work', self.initial)
        (self.root / 'new.txt').write_text('draft\n'); source = self.commit('draft change')
        (self.root / 'file.cmd').write_text('main\n'); (self.root / 'nested/run.sh').unlink()
        git_bytes(self.root, 'add', '.')
        tree = git_bytes(self.root, 'write-tree').decode().strip()
        candidate = git_bytes(self.root, 'commit-tree', tree, '-p', source, '-p', main,
                              '-m', 'legitimate successor', env=self.env).decode().strip()
        api = GitDataREST(self.root, main, source); plan = self.plan(api)
        controller.export_rest_successor(api, self.root, plan, candidate)
        self.assertEqual(api.prs[0]['head']['sha'], candidate)
        patches = [payload for method, _, payload in api.posts if method == 'PATCH']
        self.assertEqual(patches, [{'sha': candidate, 'force': False}])
        commits = [payload for _, path, payload in api.posts if path == 'git/commits']
        self.assertEqual(commits[0]['parents'], [source, main])
        trees = [payload for _, path, payload in api.posts if path == 'git/trees']
        self.assertTrue(any(item['sha'] is None and item['path'] == 'nested/run.sh' for item in trees[0]['tree']))
        self.assertEqual(git_bytes(self.root, 'rev-parse', candidate + '^{tree}').decode().strip(), tree)

    def test_bad_remote_tree_never_advances_the_branch(self):
        (self.root / 'file.cmd').write_text('candidate\n'); candidate = self.commit('candidate')
        api = GitDataREST(self.root, self.initial, self.initial); plan = self.plan(api)
        real_call = api.call
        def bad_tree(method, path, payload=None):
            if method == 'POST' and path == 'git/trees': return {'sha': 'f' * 40}
            return real_call(method, path, payload)
        api.call = bad_tree
        with self.assertRaisesRegex(controller.SelfHealBlock, 'tree mismatch'):
            controller.export_rest_successor(api, self.root, plan, candidate)
        self.assertEqual(api.prs[0]['head']['sha'], self.initial)
        self.assertFalse(any(method == 'PATCH' for method, _, _ in api.posts))


if __name__ == "__main__":
    unittest.main()
