#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools import qikvrt_workflow_executor as workflow_executor
from tools.qikvrt_seed_common import (
    FetchedJson,
    MAX_INPUT_BYTES,
    SeedError,
    canonical_json_bytes,
    load_nodes,
    parse_json_bytes,
    read_json,
    run_acceptance,
    run_audit_export,
    run_dashboard,
    run_maintenance,
    run_revalidation,
    validate_raw_request_url,
)


GUID = "a84f157a-cef2-4c47-bca9-8f407085bdbe"
SOURCE = "example/node"
SEED = "Goldkelch/qik-vrt"
REQUEST_URL = (
    "https://raw.githubusercontent.com/example/node/refs/tags/v1/"
    "qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json"
)
NOW = dt.datetime(2026, 7, 20, 12, 0, 0, tzinfo=dt.timezone.utc)


def continuity_declaration() -> dict[str, object]:
    return {
        "schema": "qikvrt_workflow_executor_mesh_continuity_declaration_v1",
        "receipt_path": "state/autonomy/WORKFLOW_EXECUTOR_MESH_NODE_RECEIPT_V1.json",
        "receipt_url": workflow_executor.expected_node_receipt_url(SOURCE, "main"),
        "acceptance_required": True,
    }


class FakeFetcher:
    def __init__(self, documents: dict[str, dict[str, object]]) -> None:
        self.documents = documents
        self.calls: list[str] = []

    def __call__(self, url: str) -> FetchedJson:
        self.calls.append(url)
        if url not in self.documents:
            raise SeedError(f"fixture has no response for {url}")
        raw = canonical_json_bytes(self.documents[url])
        return FetchedJson(self.documents[url], hashlib.sha256(raw).hexdigest())


def request_document() -> dict[str, object]:
    return {
        "version": "2.13.4",
        "event": "QIKVRT_NODE_ONBOARDING_REQUEST",
        "role": "node",
        "repository_guid": GUID,
        "source_repository": SOURCE,
        "seed_repository": SEED,
        "seed_url": f"https://github.com/{SEED}",
        "automatic_after_setup": True,
        "no_further_human_machine_interaction_after_setup": True,
        "authorized_manifest_graph_only": True,
        "no_global_scanning": True,
        "no_self_propagation": True,
        "no_remote_mutation_without_authorization": True,
        "workflow_executor_continuity": continuity_declaration(),
    }


def remote_documents() -> dict[str, dict[str, object]]:
    prefix = f"https://raw.githubusercontent.com/{SOURCE}/main/qikvrt/runtime/onboarding/"
    boundaries = {
        "no_global_scanning": True,
        "no_self_propagation": True,
        "no_remote_mutation_without_authorization": True,
    }
    return {
        REQUEST_URL: request_document(),
        prefix + "NODE_HEALTH.json": {
            "qikvrt_event": "NODE_HEALTH_HEARTBEAT",
            "guid": GUID,
            "repository": SOURCE,
            "seed_repository": SEED,
            "node_branch": "main",
            "status": "ACTIVE",
            "heartbeat_utc": "2026-07-20T11:50:00Z",
            "expires_utc": "2026-07-21T12:00:00Z",
            "boundaries": boundaries,
        },
        prefix + "SEED_ACCEPTANCE_STATUS.json": {
            "qikvrt_event": "NODE_ACK_OF_SEED_ACCEPTANCE",
            "guid": GUID,
            "repository": SOURCE,
            "seed_repository": SEED,
            "status": "ACCEPTED_BY_SEED",
        },
        prefix + "NODE_REGISTRATION_RENEWAL.json": {
            "qikvrt_event": "NODE_REGISTRATION_RENEWAL",
            "guid": GUID,
            "repository": SOURCE,
            "seed_repository": SEED,
        },
        workflow_executor.expected_node_receipt_url(SOURCE, "main"): workflow_executor.build_node_receipt(
            SOURCE,
            "main",
        ),
    }


class SeedWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "registry/node_request_queue").mkdir(parents=True)
        (self.root / "registry/KNOWN_NODE_REQUESTS.tsv").write_text(
            "# guid\tsource_repo\tseed_repo\trequest_url\tnode_branch\theartbeat_ttl_minutes\tlifecycle_policy\n"
            f"{GUID}\t{SOURCE}\t{SEED}\t{REQUEST_URL}\tmain\t1500\tACTIVE\n",
            encoding="utf-8",
        )
        (self.root / "registry/NODE_POLICY.tsv").write_text(
            f"# guid\tpolicy_status\treason\n{GUID}\tACTIVE\ttest authorization\n",
            encoding="utf-8",
        )
        (self.root / "registry/node_request_queue/OPEN_NODE_REQUESTS.tsv").write_text(
            "# empty queue\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def accept(self) -> None:
        result = run_acceptance(
            self.root,
            "accept-1",
            FakeFetcher(remote_documents()),
            now=NOW,
        )
        self.assertEqual("PASS", result["status"])

    def move_node_to_future_queue(self) -> None:
        known = self.root / "registry/KNOWN_NODE_REQUESTS.tsv"
        queue = self.root / "registry/node_request_queue/OPEN_NODE_REQUESTS.tsv"
        row = next(line for line in known.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#"))
        known.write_text("# guid\tsource_repo\tseed_repo\trequest_url\tnode_branch\theartbeat_ttl_minutes\tlifecycle_policy\n", encoding="utf-8")
        queue.write_text(
            "# guid\tsource_repo\tseed_repo\trequest_url\tnode_branch\theartbeat_ttl_minutes\tlifecycle_policy\n"
            + row
            + "\n",
            encoding="utf-8",
        )

    def test_duplicate_json_keys_and_non_object_documents_are_rejected(self) -> None:
        with self.assertRaises(SeedError):
            parse_json_bytes(b'{"a":1,"a":2}', "duplicate")
        with self.assertRaises(SeedError):
            parse_json_bytes(b"[]", "array")

    def test_local_registry_symlink_is_rejected(self) -> None:
        policy = self.root / "registry/NODE_POLICY.tsv"
        external = self.root / "external-policy.tsv"
        external.write_text(policy.read_text(encoding="utf-8"), encoding="utf-8")
        policy.unlink()
        try:
            os.symlink(external, policy)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are unavailable")
        with self.assertRaisesRegex(SeedError, "symlink"):
            load_nodes(self.root, SEED)

    def test_tsv_requires_exact_columns_explicit_policy_and_unique_guid(self) -> None:
        queue = self.root / "registry/node_request_queue/OPEN_NODE_REQUESTS.tsv"
        queue.write_text(
            f"{GUID}\t{SOURCE}\t{SEED}\t{REQUEST_URL}\tmain\t1500\tACTIVE\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(SeedError, "duplicate node GUID"):
            load_nodes(self.root, SEED)

        queue.write_text("not\tenough\tfields\n", encoding="utf-8")
        with self.assertRaisesRegex(SeedError, "expected exactly 7"):
            load_nodes(self.root, SEED)

    def test_request_url_is_bound_to_declared_repository(self) -> None:
        with self.assertRaises(SeedError):
            validate_raw_request_url(
                "https://raw.githubusercontent.com/attacker/repo/main/qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json",
                SOURCE,
            )
        with self.assertRaises(SeedError):
            validate_raw_request_url(REQUEST_URL + "?download=1", SOURCE)
        with self.assertRaises(SeedError):
            validate_raw_request_url(
                "https://raw.githubusercontent.com:not-a-port/example/node/main/qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json",
                SOURCE,
            )

    def test_acceptance_is_transactional_and_counts_validation_failure(self) -> None:
        documents = remote_documents()
        documents[REQUEST_URL] = {**request_document(), "no_global_scanning": "true"}
        result = run_acceptance(
            self.root,
            "blocked-1",
            FakeFetcher(documents),
            now=NOW,
        )
        self.assertEqual("BLOCK", result["status"])
        self.assertEqual(1, result["fail_count"])
        self.assertFalse((self.root / f"registry/nodes/{GUID}.json").exists())
        evidence = read_json(self.root / "evidence/seed_acceptance/runs/blocked-1.json")
        self.assertEqual("BLOCK", evidence["status"])

    def test_acceptance_writes_valid_bound_evidence_and_ledger(self) -> None:
        self.accept()
        entry = read_json(self.root / f"registry/nodes/{GUID}.json")
        self.assertEqual("qikvrt_seed_registry_entry_v2", entry["schema"])
        self.assertEqual(1500, entry["heartbeat_ttl_minutes"])
        self.assertRegex(entry["node_request_sha256"], r"^[0-9a-f]{64}$")
        lines = (self.root / "ledger/NODE_REGISTRATION_LEDGER.jsonl").read_bytes().splitlines()
        self.assertEqual(1, len(lines))
        self.assertEqual(GUID, parse_json_bytes(lines[0], "ledger")["guid"])

    def test_future_queue_node_requires_exact_workflow_executor_continuity_receipt(self) -> None:
        self.move_node_to_future_queue()
        result = run_acceptance(
            self.root,
            "continuity-1",
            FakeFetcher(remote_documents()),
            now=NOW,
        )
        self.assertEqual("PASS", result["status"])
        entry = read_json(self.root / f"registry/nodes/{GUID}.json")
        continuity = entry["workflow_executor_continuity"]
        self.assertEqual(
            continuity["receipt_url"],
            workflow_executor.expected_node_receipt_url(SOURCE, "main"),
        )
        self.assertRegex(continuity["receipt_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(continuity["validation"], "STRUCTURAL_ACCEPTANCE_ONLY")

    def test_future_queue_node_without_continuity_declaration_is_blocked(self) -> None:
        self.move_node_to_future_queue()
        documents = remote_documents()
        request = dict(documents[REQUEST_URL])
        del request["workflow_executor_continuity"]
        documents[REQUEST_URL] = request
        result = run_acceptance(self.root, "continuity-blocked", FakeFetcher(documents), now=NOW)
        self.assertEqual("BLOCK", result["status"])
        self.assertEqual(result["fail_count"], 1)
        self.assertIn("workflow executor continuity", result["errors"][0]["error"])

    def test_corrupt_ledger_blocks_before_registry_mutation(self) -> None:
        ledger = self.root / "ledger/NODE_REGISTRATION_LEDGER.jsonl"
        ledger.parent.mkdir(parents=True)
        ledger.write_text("not-json\n", encoding="utf-8")
        with self.assertRaises(SeedError):
            run_acceptance(
                self.root,
                "corrupt-ledger",
                FakeFetcher(remote_documents()),
                now=NOW,
            )
        self.assertFalse((self.root / f"registry/nodes/{GUID}.json").exists())

        ledger.write_bytes(b"x" * (16 * MAX_INPUT_BYTES + 1))
        with self.assertRaisesRegex(SeedError, "exceeds"):
            run_acceptance(
                self.root,
                "oversized-ledger",
                FakeFetcher(remote_documents()),
                now=NOW,
            )
        self.assertFalse((self.root / f"registry/nodes/{GUID}.json").exists())

    def test_maintenance_uses_ttl_and_revalidates_remote_identity(self) -> None:
        self.accept()
        result = run_maintenance(
            self.root,
            "maint-1",
            FakeFetcher(remote_documents()),
            now=NOW,
        )
        self.assertEqual("PASS", result["status"])
        self.assertEqual(1, result["active_count"])
        node = result["nodes"][0]
        self.assertEqual("FRESH", node["heartbeat_status"])
        # Claimed expiry is capped by the allowlisted 1500-minute TTL.
        self.assertEqual("2026-07-21T12:00:00Z", node["effective_expires_utc"])
        run_revalidation(self.root, "revalidate-1", now=NOW)
        revalidation = read_json(self.root / "registry/NODEMESH_REVALIDATION.json")
        self.assertEqual("PASS", revalidation["status"])

    def test_missing_ack_is_visible_and_never_reported_as_pass(self) -> None:
        self.accept()
        documents = remote_documents()
        ack_url = next(url for url in documents if url.endswith("SEED_ACCEPTANCE_STATUS.json"))
        del documents[ack_url]
        result = run_maintenance(
            self.root,
            "maint-blocked",
            FakeFetcher(documents),
            now=NOW,
        )
        self.assertEqual("CONTINUE", result["status"])
        self.assertEqual(0, result["active_count"])
        self.assertEqual(1, result["error_count"])
        revalidation = run_revalidation(self.root, "revalidate-blocked", now=NOW)
        self.assertEqual("CONTINUE", revalidation["status"])

    def test_revalidation_detects_counter_tampering(self) -> None:
        self.accept()
        run_maintenance(self.root, "maint-2", FakeFetcher(remote_documents()), now=NOW)
        status_path = self.root / "registry/NODEMESH_STATUS.json"
        status = read_json(status_path)
        status["active_count"] = 999
        status_path.write_bytes(canonical_json_bytes(status))
        with self.assertRaisesRegex(SeedError, "active_count"):
            run_revalidation(self.root, "revalidate-tampered", now=NOW)

    def test_dashboard_and_audit_require_current_pass_revalidation(self) -> None:
        self.accept()
        run_maintenance(self.root, "maint-3", FakeFetcher(remote_documents()), now=NOW)
        run_revalidation(self.root, "revalidate-3", now=NOW)
        dashboard = run_dashboard(self.root, "dashboard-3", now=NOW)
        audit = run_audit_export(self.root, "audit-3", now=NOW)
        self.assertEqual("PASS", dashboard["status"])
        self.assertEqual("PASS", audit["status"])
        self.assertIn("source_status_run_id", (self.root / "docs/QIKVRT_MESH_DASHBOARD.md").read_text())
        self.assertEqual(
            "qikvrt_seed_mesh_audit_export_v2",
            read_json(self.root / "audit/QIKVRT_MESH_AUDIT_SUMMARY.json")["schema"],
        )

    def test_dashboard_build_binds_every_main_push_to_exact_head_artifact(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        workflow = (
            repository / ".github/workflows/qikvrt_seed_dashboard_publish.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("push:\n    branches: [main]", workflow)
        self.assertIn("ref: ${{ github.sha }}", workflow)
        self.assertIn('actual_head="$(git rev-parse --verify HEAD^{commit})"', workflow)
        self.assertIn('test "$actual_head" = "$EXPECTED_HEAD"', workflow)
        self.assertIn('actual_tree="$(git show -s --format=%T HEAD)"', workflow)
        self.assertIn("dashboard-exact-head-binding.json", workflow)
        self.assertIn('"source_head": os.environ["EXPECTED_HEAD"]', workflow)
        self.assertIn('"source_tree": os.environ["ACTUAL_TREE"]', workflow)
        self.assertIn("qikvrt_seed_dashboard_exact_head_binding_v1", workflow)

    def test_seed_workflows_are_pinned_read_only_and_do_not_push(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        for workflow in sorted((repository / ".github/workflows").glob("qikvrt_seed_*.yml")):
            text = workflow.read_text(encoding="utf-8")
            self.assertIn("contents: read", text, workflow.name)
            self.assertNotIn("contents: write", text, workflow.name)
            self.assertIn("persist-credentials: false", text, workflow.name)
            self.assertNotRegex(text, r"actions/(?:checkout|upload-artifact)@v\d")
            self.assertNotRegex(text, r"\bgit (?:push|pull|commit)\b")


class MirrorLifecycleGovernanceTests(unittest.TestCase):
    """Execute the actual persistence shell against local Git and a bounded API fixture."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.container = Path(self.temporary.name)
        self.root = self.container / "node"
        self.root.mkdir()
        self.repository = Path(__file__).resolve().parents[1]
        self.remote = self.container / "remote.git"
        self.receipts = self.container / "receipts"
        self.bin = self.container / "bin"
        self.bin.mkdir()
        for path in (
            "tools/qikvrt_autonomous_self_heal.py",
            "tools/qikvrt_required_review_gate.py",
        ):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.repository / path, target)
        # The existing watchdog deliberately has a sparse checkout. Use a
        # declared fixture configuration, without requiring productive node state.
        config = self.root / "qikvrt/runtime/onboarding/NODE_HANDSHAKE_CONFIG.tsv"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            f"{GUID}\t{SOURCE}\t{SEED}\t{REQUEST_URL}\tfixture\tmain\t1500\n",
            encoding="utf-8",
        )
        # Only transport is simulated here; these fixture projections are not
        # evidence that the complete repository integrity generator executed.
        (self.root / "tools/qikvrt_integrity.py").write_text(
            "import pathlib,sys\n"
            "if sys.argv[1] == 'generate':\n"
            " for p in ('REPOSITORY_FILE_MANIFEST.json','REPOSITORY_FILE_MANIFEST.json.sha256','SHA256SUMS.txt'):\n"
            "  pathlib.Path(p).write_text('fixture successor\\n')\n",
            encoding="utf-8",
        )
        (self.root / "tools/qikvrt_mirror_node_lifecycle.py").write_text(
            "import os,subprocess,json\n"
            "head=os.environ['CANDIDATE_HEAD']; branch=os.environ['CANDIDATE_BRANCH']\n"
            "payload=json.dumps({'ref':'refs/heads/'+branch,'sha':head})\n"
            "subprocess.run(['gh','api','--method','POST','repos/'+os.environ['GITHUB_REPOSITORY']+'/git/refs','--input','-'],input=payload,text=True,check=True,capture_output=True)\n"
            "print(head)\n", encoding="utf-8")
        self.env = {
            **os.environ,
            "REAL_GIT": shutil.which("git") or "git",
            "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            "GH_TOKEN": "fixture-token",
            "GITHUB_REPOSITORY": "ingolf-lohmann/qik-vrt",
            "QIKVRT_RUN_ID": "governance-case-1",
            "LIFECYCLE_RECEIPT_DIR": str(self.receipts),
            "MOCK_ORIGIN": str(self.remote),
            "MOCK_LOG": str(self.container / "api-calls.jsonl"),
            "PUSH_LOG": str(self.container / "git-push-calls.jsonl"),
            "MOCK_MODE": "success",
        }
        self.git("init", "-b", "main")
        self.git("config", "user.name", "fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.materialize("initial-1")
        for path in ("REPOSITORY_FILE_MANIFEST.json", "REPOSITORY_FILE_MANIFEST.json.sha256", "SHA256SUMS.txt"):
            (self.root / path).write_text("fixture base\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "fixture base")
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "origin", "refs/heads/main:refs/heads/main")
        self.base = self.git("rev-parse", "HEAD")
        self.materialize(self.env["QIKVRT_RUN_ID"])
        (self.remote / 'objects/info/alternates').write_text(str(self.root / '.git/objects') + '\n')
        mock = self.bin / "gh"
        mock.write_text(textwrap.dedent('''\
            #!/usr/bin/env python3
            import json,os,pathlib,subprocess,sys
            args=sys.argv[1:]
            mode=os.environ['MOCK_MODE']
            log=pathlib.Path(os.environ['MOCK_LOG'])
            with log.open('a') as f: f.write(json.dumps(args)+'\\n')
            path=next(a for a in args if a.startswith('repos/'))
            def rev(ref):
                return subprocess.check_output(['git','--git-dir',os.environ['MOCK_ORIGIN'],'rev-parse',ref],text=True).strip()
            if path.endswith('/rules/branches/main'):
                out=[] if mode=='native_missing' else [{'type':'pull_request','parameters':{
                    'required_approving_review_count':1,'require_code_owner_review':True,
                    'dismiss_stale_reviews_on_push':True,'require_last_push_approval':True}}]
            elif '/git/ref/heads/' in path:
                ref=path.split('/git/ref/heads/',1)[1]
                out=rev('refs/heads/'+ref)
                calls=[json.loads(s) for s in log.read_text().splitlines()]
                count=sum(path in c for c in calls)
                if (mode=='base_drift' and ref=='main' and count==2) or (mode=='branch_drift' and ref!='main'): out='a'*40
            elif path.endswith('/git/refs'):
                payload=json.load(sys.stdin)
                if mode=='branch_denied': sys.exit(1)
                subprocess.run(['git','--git-dir',os.environ['MOCK_ORIGIN'],'update-ref',payload['ref'],payload['sha']],check=True)
                out={'object':{'sha':payload['sha']}}
            elif '/git/commits/' in path:
                out=rev(path.rsplit('/',1)[1]+'^{tree}')
            elif '/pulls?' in path:
                existing=pathlib.Path(os.environ['LIFECYCLE_RECEIPT_DIR'],'fixture-pr.json')
                out=[json.loads(existing.read_text())] if existing.exists() else []
            elif path.endswith('/pulls'):
                if mode=='pr_denied':
                    print('GitHub Actions is not permitted to create pull requests',file=sys.stderr)
                    sys.exit(1)
                payload=json.loads(pathlib.Path(args[args.index('--input')+1]).read_text())
                pr={'number':7,'state':'open','draft':payload['draft'],
                    'base':{'ref':payload['base'],'sha':rev('refs/heads/main')},
                    'head':{'ref':payload['head'],'sha':rev('refs/heads/'+payload['head']),
                            'repo':{'full_name':os.environ['GITHUB_REPOSITORY']}}}
                pathlib.Path(os.environ['LIFECYCLE_RECEIPT_DIR'],'fixture-pr.json').write_text(json.dumps(pr))
                if mode=='ambiguous': sys.exit(1)
                out={'number':7}
            elif path.endswith('/pulls/7'):
                out=json.loads(pathlib.Path(os.environ['LIFECYCLE_RECEIPT_DIR'],'fixture-pr.json').read_text())
                if mode=='pr_drift': out['head']['sha']='b'*40
            else:
                raise SystemExit('unsupported fixture API: '+path)
            print(out if isinstance(out,str) else json.dumps(out))
            '''), encoding="utf-8")
        mock.chmod(0o755)
        # Observe actual Git transport arguments after fixture initialization.
        # Reject implicit destinations, Main and force options before delegating
        # the single allowed review-branch push to the real local Git transport.
        git_spy = self.bin / "git"
        git_spy.write_text(textwrap.dedent('''\
            #!/usr/bin/env python3
            import json,os,pathlib,re,sys
            args=sys.argv[1:]
            if 'push' in args:
                with pathlib.Path(os.environ['PUSH_LOG']).open('a') as f:
                    f.write(json.dumps(args)+'\\n')
                if not (len(args)==3 and args[:2]==['push','origin'] and
                        re.fullmatch(r'HEAD:refs/heads/automation/mirror-lifecycle-[0-9a-f]{24}',args[2])):
                    raise SystemExit('BLOCK: lifecycle push outside the review branch')
            os.execv(os.environ['REAL_GIT'],['git',*args])
            '''), encoding="utf-8")
        git_spy.chmod(0o755)

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=self.root, env=self.env, text=True, stderr=subprocess.DEVNULL).strip()

    def materialize(self, run_id: str) -> None:
        subprocess.run(
            ["sh", str(self.repository / "tools/qikvrt_mirror_node_lifecycle.sh")],
            cwd=self.root, env={**self.env, "QIKVRT_RUN_ID": run_id}, check=True, capture_output=True,
        )

    def execute(self, mode: str = "success") -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        workflow = (self.repository / ".github/workflows/qikvrt_mirror_node_lifecycle.yml").read_text()
        section = workflow.split("      - name: Propose lifecycle successor through existing expected-head governance\n", 1)[1]
        script = textwrap.dedent(section.split("        run: |\n", 1)[1].split("      - name:", 1)[0])
        result = subprocess.run(["bash", "-c", script], cwd=self.root, env={**self.env, "MOCK_MODE": mode}, text=True, capture_output=True, timeout=30)
        receipt = json.loads((self.receipts / "PERSISTENCE.json").read_text())
        remote_main = subprocess.check_output(["git", "--git-dir", str(self.remote), "rev-parse", "refs/heads/main"], text=True).strip()
        self.assertEqual(self.base, remote_main, result.stdout + result.stderr)
        self.assertFalse(receipt["main_persisted"])
        self.assertFalse(receipt["effect_ack_done"])
        pushes = self.container / "git-push-calls.jsonl"
        self.pushes = [json.loads(line) for line in pushes.read_text().splitlines()] if pushes.exists() else []
        for push in self.pushes:
            self.assertEqual(["push", "origin", "HEAD:refs/heads/" + str(receipt["candidate_branch"])], push)
        return result, receipt

    def api_calls(self) -> list[list[str]]:
        path = self.container / "api-calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_no_pr_write(self) -> None:
        self.assertFalse(any("POST" in c and c[-1:] != ["-"] and any(a.endswith("/pulls") for a in c) for c in self.api_calls()))

    def test_success_is_a_readback_bound_draft_and_never_main_persistence(self) -> None:
        result, receipt = self.execute()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("PR_PENDING_EXPECTED_HEAD_GOVERNANCE", receipt["state"])
        self.assertIsNone(receipt["first_blocker"])
        self.assertEqual(self.base, receipt["base_head"])
        self.assertEqual(self.git("rev-parse", "HEAD^{tree}"), receipt["candidate_tree"])
        self.assertEqual(self.git("rev-parse", "HEAD"), receipt["candidate_head"])
        request = json.loads((self.receipts / "pr-request.json").read_text())
        self.assertTrue(request["draft"])
        self.assertIn("qikvrt-expected-head-promotion:enabled external_effect=NONE", request["body"])
        self.assertEqual(1, sum("POST" in c and any(a.endswith("/pulls") for a in c) for c in self.api_calls()))
        self.assertEqual(0, len(self.pushes))
        remote_refs = subprocess.check_output(
            ["git", "--git-dir", str(self.remote), "for-each-ref", "--format=%(refname)"], text=True,
        ).splitlines()
        self.assertEqual(sorted(["refs/heads/main", "refs/heads/" + str(receipt["candidate_branch"])]), remote_refs)

    def test_missing_native_governance_blocks_before_any_branch_or_pr(self) -> None:
        result, receipt = self.execute("native_missing")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("CODE_OWNER_RULE_NOT_ENFORCED", receipt["first_blocker"])
        self.assertEqual("", receipt["candidate_head"])
        self.assert_no_pr_write()
        self.assertEqual([], self.pushes)

    def test_base_drift_blocks_before_branch_write(self) -> None:
        result, receipt = self.execute("base_drift")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("LIFECYCLE_BASE_DRIFT", receipt["first_blocker"])
        self.assert_no_pr_write()
        self.assertEqual([], self.pushes)
        remote_refs = subprocess.check_output(["git", "--git-dir", str(self.remote), "for-each-ref", "--format=%(refname)"], text=True).splitlines()
        self.assertEqual(["refs/heads/main"], remote_refs)

    def test_wrong_branch_readback_blocks_before_pr(self) -> None:
        result, receipt = self.execute("branch_drift")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("LIFECYCLE_BRANCH_READBACK_MISMATCH", receipt["first_blocker"])
        self.assert_no_pr_write()

    def test_workflow_token_pr_denial_preserves_branch_and_capability_receipt(self) -> None:
        result, receipt = self.execute("pr_denied")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("LIFECYCLE_WORKFLOW_TOKEN_PR_CREATE_UNAVAILABLE_OR_AMBIGUOUS", receipt["first_blocker"])
        self.assertEqual(1, sum("POST" in c and any(a.endswith("/pulls") for a in c) for c in self.api_calls()))
        self.assertEqual(receipt["candidate_head"], subprocess.check_output(["git", "--git-dir", str(self.remote), "rev-parse", "refs/heads/" + str(receipt["candidate_branch"])], text=True).strip())

    def test_ambiguous_pr_response_is_not_retried(self) -> None:
        result, receipt = self.execute("ambiguous")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("LIFECYCLE_WORKFLOW_TOKEN_PR_CREATE_UNAVAILABLE_OR_AMBIGUOUS", receipt["first_blocker"])
        self.assertEqual(1, sum("POST" in c and any(a.endswith("/pulls") for a in c) for c in self.api_calls()))

    def test_pr_subject_drift_is_not_accepted(self) -> None:
        result, receipt = self.execute("pr_drift")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("LIFECYCLE_PR_SUBJECT_READBACK_MISMATCH", receipt["first_blocker"])

    def test_non_allowlisted_staged_path_blocks_before_branch_write(self) -> None:
        (self.root / "unexpected.py").write_text("forbidden fixture delta\n")
        self.git("add", "unexpected.py")
        result, receipt = self.execute()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("LIFECYCLE_NON_ALLOWLISTED_DELTA", receipt["first_blocker"])
        self.assert_no_pr_write()
        self.assertEqual([], self.pushes)

    def test_missing_token_blocks_without_an_api_effect(self) -> None:
        self.env["GH_TOKEN"] = ""
        result, receipt = self.execute()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("LIFECYCLE_TOKEN_UNAVAILABLE", receipt["first_blocker"])
        self.assertEqual([], self.api_calls())
        self.assertEqual([], self.pushes)

    def test_active_lifecycle_callers_use_only_the_review_workflow(self) -> None:
        # Active workflow/tool sources are the scope; immutable incoming
        # packages and historical Git objects are deliberately not rewritten.
        sources = [
            path for directory in (".github/workflows", ".github/actions", "tools")
            for path in (self.repository / directory).rglob("*")
            if path.is_file() and path.suffix in {".yml", ".yaml", ".sh", ".py", ".ps1"}
        ]
        references = sorted(
            path.relative_to(self.repository).as_posix() for path in sources
            if "qikvrt_mirror_node_lifecycle.sh" in path.read_text(encoding="utf-8")
        )
        self.assertEqual([
            ".github/workflows/qikvrt_mirror_node_lifecycle.yml",
            ".github/workflows/qikvrt_requested_review_contract.yml",
            "tools/qikvrt_mirror_node_lifecycle.py",
        ], references)
        callers = sorted(
            path.relative_to(self.repository).as_posix() for path in sources
            if re.search(r"^\s*(?:sh|bash)\s+tools/qikvrt_mirror_node_lifecycle\.sh\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)
        )
        self.assertEqual([".github/workflows/qikvrt_mirror_node_lifecycle.yml"], callers)
        workflow = (self.repository / callers[0]).read_text(encoding="utf-8")
        pushes = [line.strip() for line in workflow.splitlines() if "git push" in line]
        self.assertEqual([], pushes)
        self.assertIn('tools.qikvrt_mirror_node_lifecycle candidate', workflow)
        self.assertIn("print(f'automation/mirror-lifecycle-{identity[:24]}')", workflow)
        self.assertNotIn("Persist lifecycle successor on mirror main", workflow)
        self.assertIn("'base': 'main'", workflow)
        self.assertIn("'draft': True", workflow)

    def test_scheduler_concurrency_ttl_and_renewal_semantics_are_preserved(self) -> None:
        workflow = (self.repository / ".github/workflows/qikvrt_mirror_node_lifecycle.yml").read_text()
        self.assertEqual(1, workflow.count("cron:"))
        self.assertIn('cron: "17 */6 * * *"', workflow)
        self.assertIn("group: qikvrt-mirror-node-lifecycle", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertNotRegex(workflow, r"\bgit\s+push[^\n]*(?:HEAD:|refs/heads/)main\b")
        self.assertNotIn("--force", workflow)
        self.assertNotIn("/merge", workflow)
        health = json.loads((self.root / "qikvrt/runtime/onboarding/NODE_HEALTH.json").read_text())
        renewal = json.loads((self.root / "qikvrt/runtime/onboarding/NODE_REGISTRATION_RENEWAL.json").read_text())
        timestamp = lambda value: dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        # The preserved materializer uses separate wall-clock reads.
        self.assertAlmostEqual(60 * health["heartbeat_ttl_minutes"], (timestamp(health["expires_utc"]) - timestamp(health["heartbeat_utc"])).total_seconds(), delta=2)
        self.assertAlmostEqual(24 * 3600, (timestamp(renewal["next_renewal_due_utc"]) - timestamp(renewal["renewed_utc"])).total_seconds(), delta=2)
        for directory in ("node_health", "node_registration_renewal"):
            self.assertEqual((self.root / f"evidence/{directory}/LATEST.json").read_bytes(), (self.root / f"evidence/{directory}/{self.env['QIKVRT_RUN_ID']}.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
