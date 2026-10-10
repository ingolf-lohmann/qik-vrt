# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Real exported-process tests; local filesystem/HTTP evidence, not deployment."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import socket
import subprocess
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest import mock
import urllib.error
import urllib.request
import hmac
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("selfhost", ROOT / "tools/qikvrt_self_host.py")
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


class WorkflowRuntimeTests(unittest.TestCase):
    def test_terminal_lane_requires_real_supervisor_recovery_without_host_acceptance_inference(self):
        workflow=(ROOT/'.github/workflows/qikvrt_effect_ack_http_terminal.yml').read_text()
        start=workflow.index('- name: Verify existing native systemd crash and admission restoration recovery')
        end=workflow.index('- name: Preserve native systemd recovery readback')
        gate=workflow[start:end]
        self.assertIn('python3 -B -m unittest -v tests.test_self_host_systemd',gate)
        self.assertIn('--profile self-host-systemd --adapter none',gate)
        for weakening in ('continue-on-error','|| true','if:'): self.assertNotIn(weakening,gate)
        fixture=(ROOT/'tests/test_self_host_systemd.py').read_text()
        self.assertIn("'public_readback_verified':False",fixture)
        self.assertIn("'deployed_restart_verified':False",fixture)
        self.assertIn("'effect_ack_done':False",fixture)

    def test_batch003_requires_s1_runtime_and_tests_before_persistence(self):
        workflow = (ROOT / ".github/workflows/qikvrt_batch003_remaining_disposition.yml").read_text()
        gates = workflow.index("- name: Run complete repository gates")
        prefix = workflow[:gates]
        self.assertIn("ref: ${{ github.event.pull_request.head.sha || github.sha }}", prefix)
        self.assertIn("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", prefix)
        self.assertIn("python-version: '3.12'", prefix)
        self.assertIn("actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020", prefix)
        self.assertIn("node-version: '24'", prefix)
        preflight = prefix.index("- name: Verify standalone runtime for complete repository gates")
        self.assertLess(prefix.index("node-version: '24'"), preflight)
        self.assertIn("sh tools/bootstrap-runtime.sh --check-only --profile self-host --adapter none", prefix[preflight:])
        self.assertIn('sys.platform == "linux" and sys.version_info[:2] == (3, 12)', prefix[preflight:])
        complete = workflow[gates:workflow.index("- name: Persist exact evidence head")]
        self.assertIn("make test repository-monitor-test self-host-test", complete)
        self.assertNotIn("continue-on-error", complete)
        self.assertNotIn("|| true", complete)


class MeshContractTests(unittest.TestCase):
    """Source admission controls; no simulated receipt becomes live failover evidence."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qikvrt-mesh-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.definition = json.loads((ROOT / host.DEFINITION).read_bytes())
        self.activation = json.loads((ROOT / host.MESH_CONTRACT).read_bytes())
        required = {host.DEFINITION, host.MESH_CONTRACT, "tools/qikvrt_self_host.py",
                    "docs/monitor/self-host.mjs", "runtime/self-host/MESH_FILE.md", *host.MESH_PORTABLE_FILES}
        required.update(path for paths in host.MESH_COMPONENT_FILES.values() for path in paths)
        required.update(host.MESH_CACHE_SOURCE_FILES)
        for name in required:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, dest)

    def save(self):
        (self.root / host.DEFINITION).write_bytes(host.raw_json(self.definition))
        (self.root / host.MESH_CONTRACT).write_bytes(host.raw_json(self.activation))

    def refuse(self, reason):
        self.save()
        with self.assertRaisesRegex(ValueError, reason):
            host.mesh_contract(self.root)

    def test_each_role_requires_both_components_without_runtime_success_inference(self):
        result = host.mesh_contract(self.root)
        self.assertEqual(result["state"], "SOURCE_OBLIGATIONS_BOUND")
        self.assertEqual(result["contract_sha256"], host.digest((self.root / host.MESH_CONTRACT).read_bytes()))
        self.assertEqual(set(result["required_fault_cases"]), set(host.MESH_FAULT_CASES))
        for field in ("native_runtime_executed", "all_node_runtime_verified", "write_failover_verified",
                      "application_transparency_verified", "effect_ack_done"):
            self.assertIs(result[field], False)

    def test_missing_node_runtime_contract_refused(self):
        del self.activation["required_node_runtime"]
        self.refuse("EVERY_NODE_TRANSPUTER_AND_TERMINAL_CONTRACT_REQUIRED")

    def test_missing_local_cache_or_weakened_idle_contract_refuses_package_admission(self):
        original = json.loads(host.raw_json(self.activation))
        del self.activation["required_node_runtime"]["local_repository_cache"]
        self.refuse("MESH_LOCAL_CACHE_AND_IDLE_TRANSFER_CONTRACT_REQUIRED")
        for key in host.MESH_CACHE_INVARIANTS:
            self.activation = json.loads(host.raw_json(original))
            self.activation["required_node_runtime"]["local_repository_cache"][key] = False
            self.refuse("MESH_LOCAL_CACHE_AND_IDLE_TRANSFER_CONTRACT_REQUIRED")

    def test_native_effect_replication_cannot_be_delayed_or_received_proposals_auto_executed(self):
        original = json.loads(host.raw_json(self.activation))
        for key in ("native_effect_replication_deferred", "received_proposals_auto_execute"):
            self.activation = json.loads(host.raw_json(original))
            self.activation["required_node_runtime"]["local_repository_cache"][key] = True
            self.refuse("MESH_LOCAL_CACHE_AND_IDLE_TRANSFER_CONTRACT_REQUIRED")
    def test_node_client_deployment_cannot_exempt_a_role_or_launch_an_active_terminal(self):
        deployment = self.activation['deployment_contract']
        for field, value in (('role_scope', ['REPOSITORY_NODE']), ('role_exemptions', ['REPOSITORY_CLIENT']),
                             ('same_store_format_and_starter', False), ('terminal', 'AUTOMATIC_ACTIVE_CONTROLLER'),
                             ('runtime_adapter_required', False), ('live_acceptance_required', False),
                             ('app_store_required', True), ('git_required_at_runtime', True)):
            with self.subTest(field=field):
                old = deployment[field]
                deployment[field] = value
                self.refuse('NODE_CLIENT_MONOLITHIC_PASSIVE_DEPLOYMENT_CONTRACT_REQUIRED')
                deployment[field] = old

    def test_portable_file_obligations_cannot_be_removed_or_replaced_by_git_at_runtime(self):
        portable = self.activation["portable_repository"]
        for field in ("single_persistent_file", "react_html_client", "git_and_github_optional_at_runtime",
                      "mobile_file_chooser_fallback_required", "consistency_and_io_metrics_required"):
            with self.subTest(field=field):
                portable[field] = False
                self.refuse("PORTABLE_MONOLITHIC_REPOSITORY_CONTRACT_REQUIRED")
                portable[field] = True

    def test_second_canonical_format_or_transport_writer_or_predecessor_evidence_is_refused(self):
        storage = self.activation['storage_contract']
        for field,bad in [('canonical_format','QIKMESH1'),('identical_bytes_across_roles',False),
                          ('transport_role','NATIVE_PRODUCT_STORE'),('transport_mutations_allowed',True),
                          ('qikmesh_canonical_promotion_allowed',True),('predecessor_evidence_transfer',True)]:
            old = storage[field]
            with self.subTest(field=field):
                storage[field] = bad
                self.refuse('ONE_CANONICAL_SQLITE_STORAGE_CONTRACT_REQUIRED')
                storage[field] = old

    def test_wrong_json_shapes_refuse_through_the_structured_cli(self):
        for activation in ([], {"required_node_runtime": []}):
            with self.subTest(activation=activation):
                (self.root / host.MESH_CONTRACT).write_bytes(host.raw_json(activation))
                run = subprocess.run([sys.executable, "-B", str(ROOT / "tools/qikvrt_self_host.py"),
                                      "mesh-contract", "--root", str(self.root)], capture_output=True, text=True)
                self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
                result = json.loads(run.stdout)
                self.assertEqual(result["state"], "HOLD")
                self.assertIs(result["effect_ack_done"], False)

    def test_declared_live_success_is_not_trusted_as_a_runtime_receipt(self):
        contract = self.activation["required_node_runtime"]
        for key in ("all_node_runtime_verified", "write_failover_verified",
                    "application_transparency_verified", "effect_ack_done"):
            contract[key] = True
        self.save()
        result = host.mesh_contract(self.root)
        for key in ("all_node_runtime_verified", "write_failover_verified",
                    "application_transparency_verified", "effect_ack_done"):
            self.assertIs(result[key], False)

    def test_role_exemption_refused_for_authority_and_mirror(self):
        for role in ("Authority", "Mirror"):
            with self.subTest(role=role):
                self.activation["required_node_runtime"]["role_exemptions"] = [role]
                self.refuse("EVERY_NODE_TRANSPUTER_AND_TERMINAL_CONTRACT_REQUIRED")

    def test_current_nodes_only_scope_refused(self):
        self.activation["required_node_runtime"]["scope"] = "CURRENT_NODES_ONLY"
        self.refuse("EVERY_NODE_TRANSPUTER_AND_TERMINAL_CONTRACT_REQUIRED")

    def test_source_presence_cannot_replace_live_acceptance(self):
        self.activation["required_node_runtime"]["live_acceptance_required"] = False
        self.refuse("EVERY_NODE_TRANSPUTER_AND_TERMINAL_CONTRACT_REQUIRED")

    def test_removed_terminal_or_transputer_carrier_refused(self):
        for name in ("src/qikvrt_temdd_event_ledger.py", "src/qikvrt_effect_ack_http_terminal.py",
                     "docs/terminal/temdd/index.html", "docs/monitor/client-replica.js"):
            with self.subTest(name=name):
                original = list(self.definition["files"])
                self.definition["files"].remove(name)
                self.refuse("MESH_NATIVE_COMPONENT_PACKAGE_REQUIRED")
                self.definition["files"] = original

    def test_reference_only_package_refused(self):
        self.definition["native_terminal_daemon_included"] = False
        self.refuse("MESH_NATIVE_COMPONENT_PACKAGE_REQUIRED")

    def test_duplicate_package_carrier_refused(self):
        self.definition["files"].append(self.definition["files"][0])
        self.refuse("MESH_NATIVE_COMPONENT_PACKAGE_REQUIRED")

    def test_every_effect_continuity_invariant_is_required(self):
        invariants = self.activation["required_node_runtime"]["invariants"]
        for field in host.MESH_INVARIANTS:
            with self.subTest(field=field):
                invariants[field] = False
                self.refuse("MESH_CONTINUITY_INVARIANTS_REQUIRED")
                invariants[field] = True

    def test_every_fault_case_is_required_including_provider_loss_and_rejoin(self):
        for case in host.MESH_FAULT_CASES:
            with self.subTest(case=case):
                cases = list(host.MESH_FAULT_CASES)
                cases.remove(case)
                self.activation["required_node_runtime"]["required_fault_cases"] = cases
                self.refuse("MESH_FAULT_MODEL_REQUIRED")

    def test_duplicate_fault_case_cannot_supply_missing_coverage(self):
        cases = self.activation["required_node_runtime"]["required_fault_cases"]
        cases.append(cases[0])
        self.refuse("MESH_FAULT_MODEL_REQUIRED")

    def test_effect_loss_duplication_and_parallel_writers_refused(self):
        limits = self.activation["required_node_runtime"]["acceptance_limits"]
        for field, bad in (("acknowledged_effect_loss", 1), ("duplicate_irreversible_effects", 1),
                           ("concurrent_writers_per_effect", 2), ("acknowledged_effect_loss", False)):
            with self.subTest(field=field, bad=bad):
                original = limits[field]
                limits[field] = bad
                self.refuse("MESH_EFFECT_SAFETY_LIMITS_REQUIRED")
                limits[field] = original

    def test_available_partition_cannot_allow_unsafe_writes(self):
        self.activation["required_node_runtime"]["acceptance_limits"]["quorum_loss_behavior"] = "WRITE_ANYWHERE"
        self.refuse("MESH_SAFE_PARTITION_BEHAVIOR_REQUIRED")

    def test_missing_or_invalid_workload_limits_refused(self):
        limits = self.activation["required_node_runtime"]["acceptance_limits"]
        del limits["rto_ms"]
        self.refuse("MESH_WORKLOAD_BOUND_AVAILABILITY_LIMIT_REQUIRED")
        for bad in (-1, True, "unlimited"):
            with self.subTest(bad=bad):
                limits["rto_ms"] = bad
                self.refuse("MESH_WORKLOAD_BOUND_AVAILABILITY_LIMIT_REQUIRED")

    def test_unknown_slo_preserved_and_never_promoted_to_transparent_recovery(self):
        result = host.mesh_contract(self.root)
        self.assertIsNone(self.activation["required_node_runtime"]["acceptance_limits"]["rto_ms"])
        self.assertIs(result["application_transparency_verified"], False)

    def test_missing_source_refused_without_replacing_node_with_central_link(self):
        (self.root / "docs/monitor/client-replica.js").unlink()
        with self.assertRaisesRegex(ValueError, "MESH_REGULAR_SOURCE_COMPONENT_REQUIRED"):
            host.mesh_contract(self.root)

    def test_symlinked_carrier_refused(self):
        path = self.root / "src/qikvrt_effect_ack_http_terminal.py"
        path.unlink()
        path.symlink_to(ROOT / "src/qikvrt_effect_ack_http_terminal.py")
        with self.assertRaisesRegex(ValueError, "MESH_REGULAR_SOURCE_COMPONENT_REQUIRED"):
            host.mesh_contract(self.root)

    def test_cli_is_read_only_and_does_not_infer_effect_ack(self):
        self.save()
        before = {p.relative_to(self.root).as_posix(): host.digest(p.read_bytes())
                  for p in self.root.rglob("*") if p.is_file()}
        run = subprocess.run([sys.executable, "-B", str(ROOT / "tools/qikvrt_self_host.py"),
                              "mesh-contract", "--root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIs(json.loads(run.stdout)["effect_ack_done"], False)
        after = {p.relative_to(self.root).as_posix(): host.digest(p.read_bytes())
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


class StandaloneTests(unittest.TestCase):
    def test_portable_export_contains_one_canonical_sqlite_full_tree_and_derived_transport(self):
        output = self.work / "portable"
        receipt = host.portable(self.source, output, self.head, self.tree)
        self.assertEqual(receipt["state"], "PORTABLE_CANONICAL_SQLITE_EXPORTED")
        self.assertEqual({p.name for p in output.iterdir()}, {"repository.sqlite3", "repository.qmesh", "universal-terminal.html"})
        html = (output / "universal-terminal.html").read_text()
        self.assertIn('data-qikvrt-offline="true"', html)
        self.assertIn('MIT License', html)
        self.assertNotIn('<script defer src=', html)
        self.assertNotIn('Neues Repository', html)
        store = output / "repository.sqlite3"
        with sqlite3.connect(store) as db:
            files = list(db.execute('SELECT path,mode,git_blob_sha1,body FROM repository_files ORDER BY path'))
            self.assertEqual(dict((r[0],r[3]) for r in files)['AI'], subprocess.check_output(['git','-C',str(self.source),'cat-file','blob',self.head+':AI']))
            for path, mode, sha, raw in files:
                self.assertEqual(host.git_blob_digest(raw), sha, path)
                self.assertEqual(raw, subprocess.check_output(['git','-C',str(self.source),'cat-file','blob',sha]))
            self.assertEqual(host.source_tree_digest([(p,m,h) for p,m,h,_ in files]), self.tree)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone(), (0,))
        restored = self.work / 'restored.sqlite3'
        imported = host.transport_import(output/'repository.qmesh', receipt['manifest_sha256'],
                                         receipt['canonical_sha256'], receipt['transport_sha256'], restored)
        self.assertEqual(restored.read_bytes(), store.read_bytes())
        self.assertTrue(imported['full_tree_present'])
        self.assertEqual(receipt['source_files'], len(files))
        self.assertFalse(imported['effect_ack_done'])
        with self.assertRaises(ValueError): host.portable(self.source, output, self.head, self.tree)

    def test_optional_mesh_file_is_authenticated_read_only_derived_sqlite_transport(self):
        output = self.work / 'portable'
        exported = host.portable(self.source, output, self.head, self.tree)
        path = self.volume / 'repository.qmesh'
        path.write_bytes((output/'repository.qmesh').read_bytes()); path.chmod(0o600)
        self.config['mesh_file'] = 'repository.qmesh'
        self.save_config(); self.start()
        self.assertEqual(self.get('/api/mesh-file/status')[0], 401)
        code, state = self.get('/api/mesh-file/status', headers={'Authorization':'Bearer '+self.token_file.read_text()})
        self.assertEqual(code, 200)
        self.assertEqual(state['state'], 'VERIFIED')
        self.assertEqual(state['canonical_format'], 'SQLITE3_WITH_CARRIER_META_AND_EVENTS')
        self.assertEqual(state['transport_role'], 'DERIVED_BYTE_EXACT_SQLITE_EXPORT_ONLY')
        self.assertFalse(state['orchestration']['accept_writes'])
        self.assertFalse(state['effect_ack_done'])
        self.assertNotIn('genesis', state)
        request = urllib.request.Request(self.url+'/api/mesh-file/append', data=b'forbidden', method='POST',
            headers={'Authorization':'Bearer '+self.token_file.read_text(),'Content-Type':'application/octet-stream'})
        with self.assertRaises(urllib.error.HTTPError) as error: urllib.request.urlopen(request)
        self.assertEqual(error.exception.code, 405)
        self.assertEqual(path.read_bytes(), (output/'repository.qmesh').read_bytes())
        self.assertEqual(self.get('/api/runtime')[0], 200)

    def test_full_tree_preserves_original_eol_unicode_modes_and_symlink_bytes_and_rejects_changes(self):
        source = self.work/'source-with-virtual-keys'
        subprocess.run(['git','clone','-q',str(self.source),str(source)],check=True)
        (source/'.gitattributes').write_bytes(b'*.cmd text eol=crlf\n')
        (source/'example.cmd').write_bytes(b'@echo off\r\necho original\r\n')
        (source/'CON:Grüße.txt').write_bytes(b'\0original binary\xff')
        executable = source/'local.sh'; executable.write_bytes(b'#!/bin/sh\nexit 0\n'); executable.chmod(0o755)
        (source/'virtual-link').symlink_to('CON:Grüße.txt')
        subprocess.run(['git','-C',str(source),'add','.'],check=True)
        subprocess.run(['git','-C',str(source),'-c','user.name=QIKVRT fixture','-c',
                        'user.email=fixture@example.invalid','commit','-qm','Original tree-byte fixture'],check=True)
        head = host.git(source,'rev-parse','HEAD').decode(); tree = host.git(source,'rev-parse','HEAD^{tree}').decode()
        output = self.work/'full-tree'; receipt = host.portable(source,output,head,tree)
        store = output/'repository.sqlite3'
        with sqlite3.connect(store) as db:
            values = {p:(m,h,b) for p,m,h,b in db.execute('SELECT * FROM repository_files')}
        committed = subprocess.check_output(['git','-C',str(source),'cat-file','blob',head+':example.cmd'])
        self.assertEqual(values['example.cmd'][2], committed)
        self.assertNotEqual(committed, (source/'example.cmd').read_bytes())
        self.assertEqual(values['CON:Grüße.txt'][2], b'\0original binary\xff')
        self.assertEqual(values['local.sh'][0], '100755')
        self.assertEqual(values['virtual-link'][0], '120000')
        self.assertEqual(values['virtual-link'][2], 'CON:Grüße.txt'.encode())
        for label,sql in [('mode',"UPDATE repository_files SET mode='100644' WHERE path='local.sh'"),
                          ('case',"UPDATE repository_files SET path='Example.cmd' WHERE path='example.cmd'"),
                          ('missing',"DELETE FROM repository_files WHERE path='example.cmd'"),
                          ('bytes',"UPDATE repository_files SET body=x'0001' WHERE path='example.cmd'")]:
            changed = self.work/(label+'.sqlite3'); changed.write_bytes(store.read_bytes()); changed.chmod(0o600)
            with sqlite3.connect(changed) as db: db.execute(sql)
            with self.subTest(label=label), self.assertRaisesRegex(ValueError,'SOURCE_'):
                host.inspect_stable_monolith(changed,receipt['manifest_sha256'])

    def test_frozen_manifest_binds_mesh_contract_and_rejects_digest_substitution(self):
        self.assertEqual(self.manifest["mesh_node_contract_sha256"],
                         host.digest((self.export / host.MESH_CONTRACT).read_bytes()))
        original = (self.export / "MANIFEST.json").read_bytes()
        for bad in (None, "0" * 64):
            with self.subTest(bad=bad):
                manifest = json.loads(original)
                if bad is None:
                    del manifest["mesh_node_contract_sha256"]
                else:
                    manifest["mesh_node_contract_sha256"] = bad
                raw = host.raw_json(manifest)
                (self.export / "MANIFEST.json").write_bytes(raw)
                try:
                    with self.assertRaisesRegex(ValueError, "MESH_NODE_CONTRACT_BINDING_MISMATCH"):
                        host.verify(self.export, host.digest(raw))
                finally:
                    (self.export / "MANIFEST.json").write_bytes(original)

    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="qikvrt-node-test-")
        cls.base = Path(cls.scratch.name)
        cls.source = cls.base / "source"
        cls.source.mkdir()
        definition = json.loads((ROOT / host.DEFINITION).read_bytes())
        for name in definition["files"]:
            dest = cls.source / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, dest)
        for args in (("init", "-q"), ("add", "."), ("-c", "user.name=QIKVRT fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Exact local package fixture")):
            subprocess.run(["git", "-C", str(cls.source), *args], check=True, capture_output=True)
        cls.head = host.git(cls.source, "rev-parse", "HEAD").decode()
        cls.tree = host.git(cls.source, "rev-parse", "HEAD^{tree}").decode()
        cls.export = cls.base / "export"
        cls.receipt = host.freeze(cls.source, cls.export, cls.head, cls.tree)
        cls.pin = cls.receipt["manifest_sha256"]
        cls.manifest = json.loads((cls.export / "MANIFEST.json").read_bytes())

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qikvrt-node-instance-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.volume = self.work / "volume"
        self.volume.mkdir(mode=0o700)
        self.token_file = self.work / "terminal.token"
        self.token_file.write_text("test-only-32-byte-local-token-no-real-credential")
        self.token_file.chmod(0o600)
        def port():
            with socket.socket() as s:
                s.bind(("127.0.0.1",0)); return s.getsockname()[1]
        self.config = {"schema":"qikvrt-self-host-config/v1","node_id":"fixture:standalone",
            "source_head":self.head,"source_tree":self.tree,"adapter":"none","state_dir":str(self.volume),
            "host":"127.0.0.1","port":port(),"terminal_port":port(),"terminal_token_file":str(self.token_file)}
        self.config_path = self.work / "config.json"
        self.save_config()
        self.url = "http://127.0.0.1:"+str(self.config["port"])
        self.process = None
        self.addCleanup(self.stop)

    def save_config(self):
        self.config_path.write_bytes(host.raw_json(self.config)); self.config_path.chmod(0o600)

    def command(self, package=None, pin=None):
        return [sys.executable,"-B",str(self.export/"tools/qikvrt_self_host.py"),"run",
                "--root",str(package or self.export),"--manifest-sha256",pin or self.pin,"--config",str(self.config_path)]

    def start(self, path=None):
        # Both legacy providers are unavailable in this environment; the child
        # receives no provider credentials, proxy routes or mutable Node options.
        env = dict(os.environ, HTTPS_PROXY="http://127.0.0.1:1", HTTP_PROXY="http://127.0.0.1:1",
                   RAILWAY_GIT_COMMIT_SHA="f"*40, RAILWAY_API_TOKEN="synthetic-unusable-not-a-real-secret",
                   NODE_OPTIONS="--this-inherited-option-must-not-be-used")
        if path is not None: env['PATH'] = str(path)
        self.process = subprocess.Popen(self.command(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,start_new_session=True)
        until = time.monotonic()+getattr(self, 'START_TIMEOUT', 10)
        while time.monotonic() < until:
            if self.process.poll() is not None:
                out,err = self.process.communicate(); self.fail("No ready runtime: "+out+err)
            try:
                status,value = self.get("/api/runtime")
                if status == 200: return value
            except (OSError, urllib.error.URLError): pass
            time.sleep(0.025)
        self.fail("bounded runtime start timeout")

    def stop(self, abrupt=False):
        if self.process is None: return
        if abrupt:
            try: os.killpg(self.process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
        elif self.process.poll() is None: self.process.terminate()
        try: self.process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid,signal.SIGKILL); self.process.communicate(timeout=2)
        self.process = None

    def get(self,path,method="GET",headers=None,url=None):
        request=urllib.request.Request((url or self.url)+path,method=method,headers=headers or {})
        try: response=urllib.request.urlopen(request,timeout=4)
        except urllib.error.HTTPError as error: response=error
        raw=response.read()
        try: value=json.loads(raw)
        except (ValueError,UnicodeError): value=raw.decode()
        return response.status,value

    def denied(self,package=None,pin=None):
        p=subprocess.run(self.command(package,pin),capture_output=True,text=True,timeout=8)
        self.assertEqual(p.returncode,2,p.stdout+p.stderr)
        value=json.loads(p.stdout)
        self.assertFalse(value["effect_ack_done"])
        return value["cause"]

    def seed_acknowledged_event(self):
        (self.volume/"monitor").mkdir(mode=0o700)
        script="""
import {createMonitor,VERSION} from './docs/monitor/server.mjs';
import {createHmac} from 'node:crypto';
const m=createMonitor({statePath:process.argv[1],env:{QIKVRT_MONITOR_NODE_ID:'fixture:standalone',QIKVRT_GITHUB_WEBHOOK_SECRET:'fixture-only'},observe:async()=>({schema:'qikvrt-public-activity/v1',version:VERSION,generated_at:new Date().toISOString(),repositories:[],delivery:{}})});
await new Promise(r=>m.server.listen(0,'127.0.0.1',r));
const raw=JSON.stringify({repository:{full_name:'ingolf-lohmann/qik-vrt',private:false},message:'original confirmed bytes: Grüße'});
const reply=await fetch('http://127.0.0.1:'+m.server.address().port+'/api/webhooks/github',{method:'POST',headers:{'content-type':'application/json','x-github-delivery':'fixture-accepted-0001','x-github-event':'push','x-hub-signature-256':'sha256='+createHmac('sha256','fixture-only').update(raw).digest('hex')},body:raw});
console.log(JSON.stringify({status:reply.status,receipt:await reply.json()}));
m.server.closeAllConnections();await new Promise(r=>m.server.close(r));
"""
        p=subprocess.run(["node","--input-type=module","-e",script,str(self.volume/"monitor/node.json")],cwd=self.export,capture_output=True,text=True,timeout=8,check=True)
        ack=json.loads(p.stdout)
        self.assertEqual(ack["status"],200)
        self.assertTrue(ack["receipt"]["durable"])
        self.assertFalse(ack["receipt"]["effect_ack_done"])
        return json.loads((self.volume/"monitor/node.json").read_bytes())["deliveries"]

    def test_export_is_deterministic_and_contains_only_committed_public_bytes(self):
        second=self.work/"second"
        previous_umask = os.umask(0o077)
        try: receipt=host.freeze(self.source,second,self.head,self.tree)
        finally: os.umask(previous_umask)
        self.assertEqual(self.receipt["archive_sha256"],receipt["archive_sha256"])
        self.assertEqual(self.pin,receipt["manifest_sha256"])
        self.assertFalse((second/".git").exists())
        host.verify(second,self.pin)

    def test_static_react_export_serves_each_scope_and_preserves_original_bytes(self):
        self.start()
        for route in ("/mesh", "/node?repository=ingolf-lohmann%2Fqik-vrt", "/client"):
            code, page = self.get(route)
            self.assertEqual(code, 200)
            self.assertIn('data-qikvrt-monitor-version="2026-10-04.9"', page)
            self.assertIn('/assets/js/qikvrt-react-runtime.js', page)
            self.assertNotIn('MONITOR_VERSION', page)
        for route, name in (("/assets/js/qikvrt-react-runtime.js", "react-runtime.js"),
                            ("/assets/js/qikvrt-mesh-react.js", "mesh-react.js"),
                            ("/assets/css/qikvrt-mesh-react.css", "mesh-react.css"),
                            ("/scheibenhard-original.html", "scheibenhard-original.html")):
            code, body = self.get(route)
            self.assertEqual(code, 200)
            self.assertEqual(body, (self.export / "docs/monitor" / name).read_text())
            self.assertEqual(self.get(route, method="POST")[0], 405)
        original = (self.export / "docs/monitor/scheibenhard-original.html").read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         "141035ce256549227e3a427fe0db5558a7356c530ec4d7662abddad4a0b80de6")
        code, runtime = self.get("/api/runtime")
        self.assertEqual(code, 200)
        self.assertFalse(runtime["public_routing_verified"])
        self.assertFalse(runtime["effect_ack_done"])
        script = """
import vm from 'node:vm'; import {readFileSync} from 'node:fs';
const context=vm.createContext({setTimeout,clearTimeout,performance});
vm.runInContext(readFileSync('docs/monitor/react-runtime.js','utf8'),context);
console.log(JSON.stringify({version:context.QikvrtReact.React.version,createRoot:typeof context.QikvrtReact.ReactDOM.createRoot}));
"""
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.export,
                                capture_output=True, text=True, timeout=8, check=True)
        self.assertEqual(json.loads(result.stdout), {"version":"19.2.6", "createRoot":"function"})

    def test_static_react_source_and_license_drift_refuse_before_export(self):
        copy = self.work / "react-drift"
        shutil.copytree(self.export, copy)
        self.assertEqual(host.verify_react_assets(copy)["state"], "STATIC_REACT_BYTES_VERIFIED")
        license_path = copy / "docs/monitor/REACT_LICENSE.txt"
        original_license = license_path.read_bytes()
        license_path.write_bytes(original_license + b"changed")
        with self.assertRaisesRegex(ValueError, "STATIC_REACT_BYTES_OR_LICENSE_DRIFT"):
            host.verify_react_assets(copy)
        license_path.write_bytes(original_license)
        bundle_path = copy / "docs/monitor/react-runtime.js"
        raw = bundle_path.read_bytes().replace(b'exports.version = "19.2.6"', b'exports.version = "19.2.5"')
        if raw == bundle_path.read_bytes(): raw += b'changed'
        bundle_path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "STATIC_REACT_BYTES_OR_LICENSE_DRIFT"):
            host.verify_react_assets(copy)

    def test_wrong_source_and_unreviewed_worktree_fail_export(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_BINDING"):
            host.freeze(self.source,self.work/"bad","0"*40,self.tree)
        path=self.source/"STATUS.md"; original=path.read_bytes()
        try:
            path.write_bytes(original+b"\nchanged\n")
            with self.assertRaises(subprocess.CalledProcessError): host.freeze(self.source,self.work/"bad",self.head,self.tree)
        finally: path.write_bytes(original)

    def test_wrong_node_versions_fail_preflight_and_export_without_artifacts(self):
        binpath = self.work / "wrong-node"
        binpath.mkdir()
        node = binpath / "node"
        env = dict(os.environ, PATH=str(binpath) + os.pathsep + os.environ["PATH"])
        for version in ("v20.19.0", "v22.19.0", "v25.0.0", "v240.0.0"):
            with self.subTest(version=version):
                # A deterministic executable version fixture, not an installed
                # alternate runtime. The real pack CLI must reject it.
                node.write_text("#!/bin/sh\nprintf '%s\\n' '" + version + "'\n")
                node.chmod(0o755)
                preflight = subprocess.run(
                    ["sh", str(ROOT / "tools/bootstrap-runtime.sh"), "--check-only",
                     "--profile", "self-host", "--adapter", "none"],
                    env=env, capture_output=True, text=True, timeout=8)
                self.assertEqual(preflight.returncode, 20, preflight.stdout + preflight.stderr)
                self.assertIn("Node 24.x is absent", preflight.stderr)
                output = self.work / ("rejected-" + version)
                packed = subprocess.run(
                    [sys.executable, "-B", str(ROOT / "tools/qikvrt_self_host.py"), "pack",
                     "--root", str(self.source), "--expected-head", self.head,
                     "--expected-tree", self.tree, "--output", str(output)],
                    env=env, capture_output=True, text=True, timeout=8)
                self.assertEqual(packed.returncode, 2, packed.stdout + packed.stderr)
                receipt = json.loads(packed.stdout)
                self.assertEqual(receipt["cause"], "LINUX_NODE24_PYTHON312_REQUIRED")
                self.assertFalse(receipt["effect_ack_done"])
                self.assertFalse(output.exists())
                self.assertFalse(Path(str(output) + ".tar").exists())

    def test_missing_gh_is_optional_only_for_the_standalone_none_adapter(self):
        binpath=self.work/"bin"; binpath.mkdir()
        for command in ("sh","dirname","uname","awk","sed","tr","cut","cat","sha256sum","node","python3","python3.12"):
            found=shutil.which(command)
            if found: (binpath/command).symlink_to(found)
        env=dict(os.environ,PATH=str(binpath),QIKVRT_TOOLCHAIN_CACHE=str(self.work/"empty-cache"))
        self.assertIsNone(shutil.which("gh",path=str(binpath)))
        script=str(ROOT/"tools/bootstrap-runtime.sh")
        standalone=subprocess.run([str(binpath/"sh"),script,"--check-only","--profile","self-host"],env=env,capture_output=True,text=True,timeout=8)
        self.assertEqual(standalone.returncode,0,standalone.stdout+standalone.stderr)
        github=subprocess.run([str(binpath/"sh"),script,"--check-only","--profile","self-host","--adapter","github"],env=env,capture_output=True,text=True,timeout=8)
        self.assertEqual(github.returncode,20,github.stdout+github.stderr)
        for profile in ("core","ietf","formal","audio","publication","all"):
            with self.subTest(profile=profile):
                p=subprocess.run([str(binpath/"sh"),script,"--profile",profile,"--adapter","none"],env=env,capture_output=True,text=True,timeout=8)
                self.assertEqual(p.returncode,1)
                self.assertIn("require the GitHub adapter",p.stderr)
        self.assertEqual(self.start(path=binpath)['adapter'],'none')
        self.stop()
        self.config['adapter']='github';self.save_config()
        p=subprocess.run(self.command(),env=env,capture_output=True,text=True,timeout=8)
        self.assertEqual(p.returncode,2,p.stdout+p.stderr)
        self.assertIn('GITHUB_ADAPTER_REQUIRES_LOCKED_GH',p.stdout)

    def test_railway_denial_happens_before_transport_with_or_without_github(self):
        script="""
import assert from 'node:assert/strict';import {providerFetch} from './docs/monitor/server.mjs';
let transports=0;for(const adapter of ['none','github']){const request=providerFetch(adapter,()=>{transports++;});
for(const url of ['https://backboard.railway.app/graphql/v2','https://api.railway.app/','https://github.com/'])assert.throws(()=>request(url),/PROVIDER_NETWORK_DENIED/);
if(adapter==='none')assert.throws(()=>request('https://api.github.com/repos/ingolf-lohmann/qik-vrt'),/PROVIDER_NETWORK_DENIED/);}
assert.equal(transports,0);console.log('PROVIDER_NEGATIVE_CONTROL_TRANSPORT_COUNT=0');
"""
        p=subprocess.run(["node","--input-type=module","-e",script],cwd=self.export,capture_output=True,text=True,timeout=5,check=True)
        self.assertIn("COUNT=0",p.stdout)
        observed=self.start()
        self.assertEqual(observed["adapter"],"none")
        self.assertEqual(observed["source_head"],self.head)
        self.assertFalse(observed["effect_ack_done"])
        self.assertEqual(self.get('/api/webhooks/github',method='POST')[0],409)
        self.assertEqual(self.get('/api/run?repo=x&id=1')[0],503)

    def test_authenticated_reference_terminal_and_public_read_only_boundary(self):
        self.start()
        local="http://127.0.0.1:"+str(self.config["terminal_port"])
        self.assertEqual(self.get('/terminal/state',url=local)[0],401)
        token=self.token_file.read_text().strip()
        status,value=self.get('/terminal/state',url=local,headers={'Authorization':'Bearer '+token})
        self.assertEqual(status,200)
        self.assertEqual(value['runtime_binding']['manifest_sha256'],self.pin)
        status,public=self.get('/api/terminal')
        self.assertEqual(status,200)
        self.assertNotIn(token,json.dumps(public))
        self.assertNotIn('last_event',public)
        self.assertEqual(self.get('/api/terminal',method='POST')[0],405)
        page=self.get('/AI/')[1]
        self.assertIn('data-qikvrt-source="node"',page)
        self.assertEqual(self.get('/assets/js/qikvrt-local-engine.js')[0],200)
        self.assertEqual(self.get('/api/repository?repository=other/x&path=')[0],409)
        self.assertEqual(self.get('/api/repository?repository=ingolf-lohmann/qik-vrt&path=%2Fcontents%2F..%2Fterminal.token%3Fref%3Dmain')[0],404)

    def test_sigkill_restart_preserves_acknowledged_original_bytes_and_independent_readback(self):
        expected=self.seed_acknowledged_event()
        self.start()
        before=self.get('/api/events?after=0')[1]
        self.assertEqual(before['events'],expected)
        self.stop(abrupt=True)
        self.start()
        after=self.get('/api/events?after=0')[1]
        self.assertEqual(after,before)
        cfg=host.digest(self.config_path.read_bytes())
        args=["node",str(self.export/'tools/qikvrt_mesh_monitor_readback.mjs'),"--self-host",str(self.export),self.url,self.pin,cfg,self.config['node_id'],'none']
        p=subprocess.run(args,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        receipt=json.loads(p.stdout)
        self.assertEqual(receipt['event_sequence'],len(expected))
        self.assertFalse(receipt['effect_ack_done'])
        p=subprocess.run([*args[:6],'0'*64,*args[7:]],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)

    def test_wrong_manifest_pin_and_runtime_executable_binding_fail_closed(self):
        self.assertIn('MANIFEST_PIN',self.denied(pin='0'*64))
        package=self.work/'altered';shutil.copytree(self.export,package)
        m=json.loads((package/'MANIFEST.json').read_bytes());m['runtime']['python']['version']='Python 3.12.0'
        (package/'MANIFEST.json').write_bytes(host.raw_json(m))
        self.assertIn('RUNTIME_EXECUTABLE',self.denied(package,host.digest((package/'MANIFEST.json').read_bytes())))

    def test_tampered_artifact_and_extra_file_are_not_admitted(self):
        package=self.work/'altered';shutil.copytree(self.export,package)
        (package/'docs/monitor/server.mjs').write_text('tampered')
        self.assertIn('ARTIFACT_MISMATCH',self.denied(package))
        shutil.copy2(self.export/'docs/monitor/server.mjs',package/'docs/monitor/server.mjs')
        (package/'unreviewed.js').write_text('extra')
        self.assertIn('INVENTORY_MISMATCH',self.denied(package))

    def test_wrong_source_binding_does_not_start(self):
        self.config['source_tree']='0'*40;self.save_config()
        self.assertIn('CONFIGURATION_BINDING',self.denied())

    def test_wrong_volume_identity_preserves_confirmed_data(self):
        expected=self.seed_acknowledged_event()
        self.start()
        bound=self.volume/'binding.json';original=bound.read_bytes()
        wrong=json.loads(original);wrong['node_id']='wrong:live-volume'
        bound.write_bytes(host.raw_json(wrong))
        args=['node',str(self.export/'tools/qikvrt_mesh_monitor_readback.mjs'),'--self-host',str(self.export),self.url,self.pin,
              host.digest(self.config_path.read_bytes()),self.config['node_id'],'none']
        try:
            p=subprocess.run(args,capture_output=True,text=True,timeout=10)
            self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
        finally: bound.write_bytes(original)
        self.stop()
        before=(self.volume/'monitor/node.json').read_bytes()
        self.config['node_id']='wrong:node';self.save_config()
        self.assertIn('VOLUME_BINDING',self.denied())
        self.assertEqual((self.volume/'monitor/node.json').read_bytes(),before)
        self.assertEqual(json.loads(before)['deliveries'],expected)

    def test_second_writer_is_rejected_by_kernel_lock(self):
        self.start()
        self.assertIn('unavailable',self.denied())
        self.assertEqual(self.get('/api/runtime')[0],200)

    def test_surviving_monitor_retains_lock_after_launcher_only_sigkill(self):
        expected=self.seed_acknowledged_event()
        self.start()
        before=self.get('/api/events?after=0')[1]
        os.kill(self.process.pid,signal.SIGKILL)
        self.process.wait(timeout=3)
        try:
            self.assertEqual(self.get('/api/runtime')[0],200)
            self.assertIn('unavailable',self.denied())
            self.assertEqual(self.get('/api/events?after=0')[1],before)
        finally: self.stop(abrupt=True)
        self.start()
        after=self.get('/api/events?after=0')[1]
        self.assertEqual(after,before)
        self.assertEqual(after['events'],expected)

    def test_private_config_and_secret_symlink_fail_before_listener(self):
        self.config_path.chmod(0o644)
        self.assertIn('OWNER_ONLY',self.denied())
        self.config_path.chmod(0o700)
        self.assertIn('OWNER_ONLY',self.denied())
        self.config_path.chmod(0o600)
        alias=self.work/'token-alias';alias.symlink_to(self.token_file)
        self.config['terminal_token_file']=str(alias);self.save_config()
        self.assertIn('NOT_SYMLINKED',self.denied())

    def host_declaration(self):
        self.config.update(terminal_profile='temdd', source_repository=self.manifest['source_repository'], subject_pr=457)
        self.save_config()
        observed={'machine_id_sha256':'a'*64,'mount':{'mount_point':str(self.volume),'mount_root':'/',
            'device_major_minor':'8:1','filesystem':'ext4','mount_source':'/dev/fixture-only'}}
        declaration={'schema':'qikvrt-own-host-admission/v1','source_head':self.head,'source_tree':self.tree,
            'manifest_sha256':self.pin,'config_sha256':host.digest(self.config_path.read_bytes()),
            'node_id':self.config['node_id'],**observed,'public_origin':'https://operator-host.example.org',
            'execution_operation':'fixture-only: no external operation','supervisor_id':'fixture:existing-supervisor',
            'authorization_evidence_sha256':'b'*64,'persistence_evidence_sha256':'c'*64,
            'https_routing_evidence_sha256':'d'*64}
        path=self.work/'admission.json'
        def save():
            raw=host.raw_json(declaration);path.write_bytes(raw);path.chmod(0o600);return host.digest(raw)
        return declaration,observed,path,save

    def test_admission_missing_does_not_start_or_claim_completion(self):
        command=[sys.executable,'-B',str(self.export/'tools/qikvrt_self_host.py'),'admit',
            '--root',str(self.export),'--manifest-sha256',self.pin]
        result=subprocess.run(command,capture_output=True,text=True,timeout=8)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        value=json.loads(result.stdout)
        self.assertEqual(value['cause'],'HOLD_OWN_HOST_IDENTITY_STORAGE_ROUTING_UNAVAILABLE')
        self.assertFalse(value['effect_ack_done'])
        self.assertFalse((self.volume/'binding.json').exists())

    def test_admission_binds_original_launcher_without_any_external_effect(self):
        declaration,observed,path,save=self.host_declaration()
        host.verify(self.export,self.pin)
        with mock.patch.object(host,'own_host_observation',return_value=observed), \
                mock.patch.object(host,'runtime',side_effect=lambda command:self.manifest['runtime']['node' if command=='node' else 'python']), \
                mock.patch.object(host.subprocess,'Popen',side_effect=AssertionError('must not execute')):
            result=host.admission_plan(self.export,self.pin,self.config_path,path,save())
        self.assertEqual(result['state'],'HOST_LAUNCHER_BOUND_PENDING_EXTERNAL_ACCEPTANCE')
        expected=self.command();expected[0]=str(Path(sys.executable).resolve())
        self.assertEqual(result['run_argv'],expected)
        self.assertEqual(result['readback_argv'][2:],['--self-host',str(self.export),declaration['public_origin'],
            self.pin,host.digest(self.config_path.read_bytes()),self.config['node_id'],'none'])
        for key in ('execution_performed','host_admission_verified','public_readback_verified',
                    'restart_verified','review_governance_satisfied','effect_ack_done'):
            self.assertIs(result[key],False)
        self.assertFalse((self.volume/'binding.json').exists())

    def test_admission_rejects_pin_subject_route_identity_and_mount_drift(self):
        declaration,observed,path,save=self.host_declaration()
        pin=save()
        with self.assertRaisesRegex(ValueError,'PIN_MISMATCH'):
            host.admission_plan(self.export,self.pin,self.config_path,path,'0'*64)
        controls=[('source_tree','0'*40,'SUBJECT_MISMATCH'),('public_origin','http://127.0.0.1','PUBLIC_HTTPS'),
            ('public_origin','https://127.0.0.1','PUBLIC_HTTPS'),('public_origin','https://mesh.up.railway.app','PUBLIC_HTTPS'),
            ('machine_id_sha256','e'*64,'IDENTITY_OR_MOUNT'),('mount',{**observed['mount'],'mount_source':'/dev/wrong'},'IDENTITY_OR_MOUNT'),
            ('persistence_evidence_sha256',None,'EVIDENCE_BINDINGS')]
        for key,value,cause in controls:
            before=declaration[key];declaration[key]=value
            with self.subTest(key=key,value=value), mock.patch.object(host,'own_host_observation',return_value=observed):
                with self.assertRaisesRegex(ValueError,cause):
                    host.admission_plan(self.export,self.pin,self.config_path,path,save())
            declaration[key]=before
        self.assertFalse((self.volume/'binding.json').exists())

    def test_ephemeral_mount_cannot_be_host_persistence_evidence(self):
        with mock.patch.object(Path,'read_bytes',return_value=b'a'*32+b'\n'), \
                mock.patch.object(Path,'read_text',return_value='17 1 0:4 / / rw - overlay overlay rw\n'):
            with self.assertRaisesRegex(ValueError,'PERSISTENT_HOST_MOUNT_REQUIRED'):
                host.own_host_observation(self.volume)

    def test_supervisor_is_create_only_and_preserves_admission_on_every_start(self):
        declaration,observed,path,save=self.host_declaration()
        declaration['supervisor_id']='systemd:qikvrt-fixture-only.service'
        tool_pin=host.digest(Path(host.__file__).read_bytes())
        with mock.patch.object(host,'own_host_observation',return_value=observed):
            plan=host.supervisor_plan(self.export,self.pin,self.config_path,path,save(),tool_pin)
        output=self.work/'supervisor'
        receipt=host.materialize_supervisor(plan,output)
        unit=(output/plan['unit_name']).read_bytes()
        self.assertEqual(host.digest(unit),receipt['unit_sha256'])
        self.assertIn(b'run-admitted',unit)
        self.assertIn(path.as_posix().encode(),unit)
        for directive in (b'Restart=always',b'RestartPreventExitStatus=78',b'KillMode=control-group',
                b'StartLimitBurst=5',b'RequiresMountsFor=',b'BindsTo=',b'WantedBy=multi-user.target'):
            self.assertIn(directive,unit)
        self.assertNotIn(self.token_file.read_bytes(),unit)
        path_unit=(output/plan['path_unit_name']).read_bytes()
        self.assertEqual(host.digest(path_unit),receipt['path_unit_sha256'])
        self.assertIn(b'PathChanged=',path_unit)
        self.assertNotIn(b'PathExists=',path_unit)
        for line in path_unit.decode().splitlines():
            if line.startswith('PathChanged='):
                self.assertTrue(line.split('=',1)[1].startswith('/'),'systemd path parser requires raw absolute path')
        for k in ('supervisor_installed','live_recovery_verified','public_readback_verified','effect_ack_done'):
            self.assertIs(receipt[k],False)
        with self.assertRaises(FileExistsError): host.materialize_supervisor(plan,output)
        self.assertFalse((self.volume/'binding.json').exists())

    def test_guard_independently_verifies_then_execs_original_export(self):
        declaration,observed,path,save=self.host_declaration()
        declaration['supervisor_id']='systemd:qikvrt-fixture-only.service'
        tool_pin=host.digest(Path(host.__file__).read_bytes())
        with mock.patch.object(host,'own_host_observation',return_value=observed), \
                mock.patch.object(host,'systemd_invocation',return_value='a'*32), \
                mock.patch.object(host.os,'execv',side_effect=RuntimeError('exec observed')) as execute:
            with self.assertRaisesRegex(RuntimeError,'exec observed'):
                host.run_admitted(self.export,self.pin,self.config_path,path,save(),tool_pin)
        args=execute.call_args.args[1]
        self.assertEqual(args[1:],self.command()[1:])
        self.assertFalse((self.volume/'binding.json').exists())

    def test_guard_pin_drift_and_wrong_persisted_identity_cannot_execute(self):
        declaration,observed,path,save=self.host_declaration()
        declaration['supervisor_id']='systemd:qikvrt-fixture-only.service'
        tool_pin=host.digest(Path(host.__file__).read_bytes())
        with mock.patch.object(host,'own_host_observation',return_value=observed), \
                mock.patch.object(host.os,'execv',side_effect=AssertionError('must not execute')):
            with self.assertRaisesRegex(ValueError,'TOOL_PIN_MISMATCH'):
                host.run_admitted(self.export,self.pin,self.config_path,path,save(),'0'*64)
            binding=self.volume/'binding.json'
            binding.write_bytes(b'{"node_id":"wrong-node"}\n');binding.chmod(0o600)
            before=binding.read_bytes()
            with self.assertRaisesRegex(ValueError,'VOLUME_BINDING_MISMATCH'):
                host.run_admitted(self.export,self.pin,self.config_path,path,save(),tool_pin)
            self.assertEqual(binding.read_bytes(),before)
        result=subprocess.run([sys.executable,'-B',str(ROOT/'tools/qikvrt_self_host.py'),'run-admitted',
            '--root',str(self.export),'--manifest-sha256',self.pin,'--admission-tool-sha256','0'*64],
            capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,78,result.stdout+result.stderr)
        self.assertFalse(json.loads(result.stdout)['effect_ack_done'])

    def test_supervisor_invocation_requires_actual_manager_mainpid_and_id(self):
        with mock.patch.object(Path,'read_text',return_value='python\n'):
            with self.assertRaisesRegex(ValueError,'ACTIVE_HOST_SYSTEMD'):
                host.systemd_invocation('qikvrt-fixture-only.service')
        with mock.patch.object(Path,'read_text',return_value='systemd\n'), \
                mock.patch.dict(os.environ,{'INVOCATION_ID':'a'*32}), \
                mock.patch.object(host.subprocess,'check_output',side_effect=[b'systemd 255\n',b'MainPID=0\nInvocationID='+b'a'*32+b'\n']):
            with self.assertRaisesRegex(ValueError,'INVOCATION_BINDING_MISMATCH'):
                host.systemd_invocation('qikvrt-fixture-only.service')


class MeshWorkCacheTests(unittest.TestCase):
    """Actual local Git, Python cache, Node receiver and authenticated HTTP.

    Fixtures establish bounded proposal delivery; not productive Mesh/idle or
    optimal scheduling acceptance. Received instruction bytes are never run.
    """
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qikvrt-mesh-work-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.repo = self.directory / "repo"; self.repo.mkdir(mode=0o700)
        self.git("init", "-q")
        self.git("config", "user.name", "Mesh test fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.file = self.repo / "work.txt"; self.file.write_bytes(b"Original exportable bytes: Gr\xc3\xbc\xc3\x9fe \xce\xa9\n")
        self.git("add", "."); self.git("commit", "-qm", "Fixture")
        self.cache = host.MeshWorkCache(self.directory / "cache", "ingolf-lohmann/qik-vrt", "local:fixture")
        self.key = self.directory / "peer.key"; self.key.write_bytes(b"fixture-only-mesh-peer-key-32-bytes-exact"); self.key.chmod(0o600)
        self.peer = {"node_id": "cloud:fixture", "source_head": "a" * 40, "source_tree": "b" * 40, "secret_file": str(self.key)}
        self.calls = []

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.DEVNULL).strip()

    def stage(self, identifier="unit:one", instructions=b"Owner-approved exportable proposal; do not execute automatically."):
        return self.cache.stage(self.repo, ["work.txt"], identifier, instructions)

    def freeze(self):
        return self.cache.idle([sys.executable, "-B", "-c", "from pathlib import Path; assert Path('work.txt').is_file()"])

    def state(self):
        return json.loads(self.cache.path.read_bytes())["state"]

    def pending(self):
        with self.cache.locked(): return self.cache.pending()

    def transport(self, url, method, raw, headers):
        self.calls.append((method, url, len(raw)))
        return host.mesh_work_transport(url, method, raw, headers)

    def cloud(self, occupied=False, label="cloud"):
        import select
        state = self.directory / (label + ".json")
        config = self.directory / (label + "-config.json")
        config.write_bytes(host.raw_json({"statePath": str(state), "env": {
            "QIKVRT_MONITOR_NODE_ID": self.peer["node_id"], "QIKVRT_MONITOR_SOURCE_HEAD": self.peer["source_head"],
            "QIKVRT_MONITOR_SOURCE_TREE": self.peer["source_tree"],
            "QIKVRT_MESH_WORK_PEERS": json.dumps([{"node_id": "local:fixture", "repository": "ingolf-lohmann/qik-vrt", "secret_file": str(self.key)}])}}))
        code = "import {readFileSync} from 'node:fs';import {createMonitor} from './docs/monitor/server.mjs';const m=createMonitor(JSON.parse(readFileSync(process.argv[1])));m.server.listen(0,'127.0.0.1',()=>console.log(JSON.stringify({port:m.server.address().port})));"
        process = subprocess.Popen(["node", "--input-type=module", "-e", code, str(config)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        def stop():
            if process.poll() is None: process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
            process.stdout.close()
        self.addCleanup(stop)
        self.assertTrue(select.select([process.stdout], [], [], 5)[0], "Cloud fixture did not become ready")
        ready = process.stdout.readline()
        self.assertTrue(ready, "Cloud fixture exited before readiness")
        self.peer["url"] = "http://127.0.0.1:" + str(json.loads(ready)["port"])
        if occupied: state.mkdir(mode=0o700)
        return state, stop

    def test_32_local_changes_use_one_payload_after_real_validation_and_less_measured_traffic(self):
        self.cloud(label="baseline-cloud")
        baseline_peer = dict(self.peer)
        baseline = host.MeshWorkCache(self.directory / "baseline-cache", **self.cache.binding)
        self.cloud()
        original = b"a" * (64 * 1024)
        full_bytes = 0; baseline_posts = []
        for n in range(32):
            self.file.write_bytes(original + str(n).encode())
            self.git("add", "."); self.git("commit", "-qm", f"Local work {n}")
            self.stage(f"work:{n}", f"Keep proposal {n} with its original provenance".encode())
            full_bytes += len(self.file.read_bytes())
            baseline.stage(self.repo, ["work.txt"], f"work:{n}", f"Keep proposal {n} with its original provenance".encode())
            baseline.idle([sys.executable, "-B", "-c", "from pathlib import Path; assert Path('work.txt').is_file()"])
            def baseline_transport(url, method, raw, headers):
                if method == "POST": baseline_posts.append(len(raw))
                return host.mesh_work_transport(url, method, raw, headers)
            baseline.send(baseline_peer, baseline_transport)
        self.assertFalse(self.calls)
        receipt = self.freeze()
        self.assertEqual(receipt["work_units"], 32)
        raw, packet = self.pending()
        self.assertLess(len(raw), full_bytes)
        self.assertEqual(len(baseline_posts), 32)
        self.assertLess(len(raw), sum(baseline_posts))
        self.assertEqual(packet["idle"]["state"], "IDLE_STABLE_VALIDATED")
        self.assertIs(receipt["whole_node_idle_verified"], False)
        result = self.cache.send(self.peer, self.transport)
        self.assertEqual(result["state"], "MESH_WORK_BATCH_READBACK_CONFIRMED")
        self.assertEqual([method for method, _, _ in self.calls], ["POST", "GET"])
        self.assertIsNone(self.state()["pending"])
        self.assertIs(result["effect_ack_done"], False)
        state = json.loads((self.directory / "cloud.json").read_bytes())["mesh_work"]
        self.assertEqual(len(state["nodes"]["local:fixture"]["units"]), 32)
        key = packet["entries"]["work.txt"]["sha256"]
        self.assertEqual(base64.b64decode(state["objects"][key]), self.file.read_bytes())
        self.assertFalse((self.directory / "executed-instruction").exists())
        # Scope-bound comparable payload counts, not an invented speedup/SLO.
        evidence = {"schema": "qikvrt-local-mesh-work-measurement/v1", "work_units": 32,
            "per_update_source_bytes": full_bytes, "baseline_payload_posts": len(baseline_posts),
            "baseline_payload_wire_bytes": sum(baseline_posts), "single_batch_wire_bytes": len(raw), "payload_posts": 1,
            "metadata_readbacks": 1, "network_scope": "LOOPBACK_PYTHON_TO_NODE",
            "fixture_head": self.git("rev-parse", "HEAD").decode(), "fixture_tree": self.git("rev-parse", "HEAD^{tree}").decode(),
            "runtime_component_sha256": {name: host.digest((ROOT / name).read_bytes()) for name in host.MESH_CACHE_SOURCE_FILES},
            "whole_mesh_performance_verified": False,
            "effect_ack_done": False}
        if os.environ.get("QIKVRT_MESH_WORK_TEST_EVIDENCE"):
            try:
                source_head = host.git(ROOT, "rev-parse", "HEAD^{commit}").decode()
                source_tree = host.git(ROOT, "rev-parse", source_head + "^{tree}").decode()
            except subprocess.SubprocessError: source_head = source_tree = None
            evidence.update(source_head=source_head, source_tree=source_tree,
                run_id=os.environ.get("GITHUB_RUN_ID"), source_binding_scope="EXACT_CHECKOUT" if source_head else "SELECTED_API_FILES_ONLY")
            path = Path(os.environ["QIKVRT_MESH_WORK_TEST_EVIDENCE"]); path.mkdir(parents=True, exist_ok=True)
            (path / "LOCAL_WORK_BATCH.json").write_bytes(host.raw_json(evidence))

    def test_warm_objects_and_original_instruction_bytes_survive_restart(self):
        first = self.stage()
        self.assertEqual(first["cache_hits"], 0)
        new = host.MeshWorkCache(self.cache.directory, **self.cache.binding)
        self.assertEqual(new.stage(self.repo, ["work.txt"], "unit:two", b"Owner-approved exportable proposal; do not execute automatically.")["cache_hits"], 2)
        new.idle([sys.executable, "-c", "pass"])
        self.assertEqual(len(self.pending()[1]["objects"]), 2)
        self.assertEqual(len(self.pending()[1]["work_units"]), 2)

    def test_reserved_object_names_cannot_drop_a_work_unit_in_the_node_receiver(self):
        for name in ("__proto__", "constructor", "prototype"):
            with self.assertRaisesRegex(ValueError, "MESH_WORK_UNIT_REQUIRED"): self.stage(name)
        self.assertFalse(self.cache.path.exists())

    def test_no_transfer_before_validated_idle_and_no_request_from_failed_gate(self):
        self.stage()
        with self.assertRaisesRegex(ValueError, "VALIDATED_IDLE_BATCH_REQUIRED"): self.cache.send({}, self.transport)
        with self.assertRaisesRegex(ValueError, "VALIDATION_FAILED"): self.cache.idle([sys.executable, "-c", "raise SystemExit(7)"])
        self.assertEqual(self.state()["mode"], "HOLD")
        self.assertFalse(self.calls)
        self.assertIsNone(self.state()["pending"])

    def test_gate_that_changes_exact_bytes_cannot_produce_idle(self):
        self.stage()
        with self.assertRaisesRegex(ValueError, "CLEAN_LOCAL_COMMIT_REQUIRED"):
            self.cache.idle([sys.executable, "-c", "from pathlib import Path; Path('work.txt').write_text('changed')"])
        self.assertIsNone(self.state()["pending"])

    def test_new_commit_invalidates_idle_before_any_transport(self):
        self.stage(); self.freeze()
        self.file.write_bytes(b"new local state")
        self.git("add", "."); self.git("commit", "-qm", "Changed while idle")
        with self.assertRaisesRegex(ValueError, "IDLE_INVALIDATED"): self.cache.send({}, self.transport)
        self.assertFalse(self.calls)
        self.assertIsNotNone(self.state()["pending"])

    def test_pending_batch_blocks_new_work_without_dropping_original(self):
        self.stage(); receipt = self.freeze()
        with self.assertRaisesRegex(ValueError, "PENDING_BATCH_BACKPRESSURE"): self.stage("unit:two")
        self.assertEqual(self.state()["pending"]["batch_id"], receipt["batch_id"])

    def test_same_unit_retry_is_noop_and_changed_content_conflicts(self):
        self.stage()
        self.assertEqual(self.stage()["state"], "MESH_WORK_DUPLICATE_NOOP")
        with self.assertRaisesRegex(ValueError, "UNIT_CONFLICT"): self.stage(instructions=b"different bytes")
        self.assertEqual(self.state()["revision"], 1)

    def test_lost_response_is_resolved_by_readback_after_both_process_restarts_without_repost(self):
        state, stop = self.cloud()
        self.stage(instructions=b"touch /this-command-is-not-executed")
        self.freeze()
        def lost(url, method, raw, headers):
            result = self.transport(url, method, raw, headers)
            if method == "POST": raise ConnectionError("Response lost after actual durable receiver commit")
            return result
        with self.assertRaises(ConnectionError): self.cache.send(self.peer, lost)
        before = state.read_bytes(); stop()
        self.cloud()
        self.cache = host.MeshWorkCache(self.cache.directory, **self.cache.binding)
        result = self.cache.send(self.peer, self.transport)
        self.assertEqual(result["state"], "MESH_WORK_BATCH_READBACK_CONFIRMED")
        self.assertEqual([method for method, _, _ in self.calls], ["POST", "GET"])
        self.assertEqual(state.read_bytes(), before)

    def test_already_delivered_batch_can_be_read_back_after_local_work_advances(self):
        self.cloud(); self.stage(); self.freeze()
        def lost(url, method, raw, headers):
            result = self.transport(url, method, raw, headers)
            if method == "POST": raise ConnectionError("Durable delivery response lost")
            return result
        with self.assertRaises(ConnectionError): self.cache.send(self.peer, lost)
        self.file.write_bytes(b"Local successor bytes")
        self.git("add", "."); self.git("commit", "-qm", "Local successor")
        result = self.cache.send(self.peer, self.transport)
        self.assertEqual(result["local_idle_state"], "DIRTY")
        self.assertEqual([method for method, _, _ in self.calls], ["POST", "GET"])
        self.assertIsNone(self.state()["pending"])
        self.stage("successor:unit")

    def test_bad_authenticated_response_keeps_outbox_then_reads_real_receipt(self):
        self.cloud(); self.stage(); self.freeze()
        def bad(url, method, raw, headers):
            status, body, _ = self.transport(url, method, raw, headers)
            return status, body, "sha256=" + "0" * 64
        with self.assertRaisesRegex(ValueError, "AUTHENTICATED_READBACK_REQUIRED"): self.cache.send(self.peer, bad)
        self.assertIsNotNone(self.state()["pending"])
        self.cache.send(self.peer, self.transport)
        self.assertEqual(sum(method == "POST" for method, _, _ in self.calls), 1)

    def test_receiver_storage_failure_holds_original_batch_until_recovery(self):
        state, stop = self.cloud(occupied=True)
        self.stage(); self.freeze()
        raw, packet = self.pending()
        with self.assertRaisesRegex(ValueError, "TRANSFER_REFUSED"): self.cache.send(self.peer, self.transport)
        self.assertEqual(self.pending()[0], raw)
        stop(); state.rmdir(); self.cloud()
        self.assertEqual(self.cache.send(self.peer, self.transport)["batch_id"], packet["batch_id"])
        self.assertEqual([method for method, _, _ in self.calls], ["POST", "GET", "POST", "GET"])

    def test_network_outage_keeps_pending_then_reads_before_retrying_same_bytes(self):
        self.cloud(); self.stage(); self.freeze()
        raw, _ = self.pending()
        def outage(*args): raise ConnectionError("Actual send route unavailable before transport")
        with self.assertRaises(ConnectionError): self.cache.send(self.peer, outage)
        self.assertEqual(self.pending()[0], raw)
        self.cache.send(self.peer, self.transport)
        self.assertEqual([method for method, _, _ in self.calls], ["GET", "POST", "GET"])

    def packet_request(self, packet, node_id="local:fixture", secret=None):
        raw = host.mesh_wire(packet)
        key = secret if secret is not None else self.key.read_bytes()
        signature = "sha256=" + hmac.new(key, b"POST\n/api/mesh-work/batch\n" + raw, hashlib.sha256).hexdigest()
        return host.mesh_work_transport(self.peer["url"] + "/api/mesh-work/batch", "POST", raw,
            {"content-type": "application/json", "x-qikvrt-mesh-node": node_id, "x-qikvrt-replication-signature": signature})

    def test_bad_peer_digest_idle_or_object_cannot_mutate_the_cloud(self):
        state, _ = self.cloud(); self.stage(); self.freeze()
        _, packet = self.pending()
        self.assertEqual(self.packet_request(packet, secret=b"wrong-key")[0], 401)
        self.assertEqual(self.packet_request(packet, node_id="unadmitted:node")[0], 403)
        for change in ("idle", "object", "repository", "entries", "unit-identity", "unused-object"):
            candidate = json.loads(host.mesh_wire(packet))
            if change == "idle": candidate["idle"]["validation"]["exit_code"] = 1
            elif change == "object": candidate["objects"][next(iter(candidate["objects"]))] = base64.b64encode(b"corrupt bytes").decode()
            elif change == "repository": candidate["repository"] = "unknown/repository"
            elif change == "entries": candidate["entries"]["work.txt"]["bytes"] += 1
            elif change == "unit-identity": candidate["work_units"][0]["id"] = "__proto__"
            else: candidate["objects"][host.digest(b"unreferenced")] = base64.b64encode(b"unreferenced").decode()
            del candidate["batch_id"]; candidate["batch_id"] = host.digest(host.mesh_wire(candidate))
            self.assertEqual(self.packet_request(candidate)[0], 409, change)
            self.assertFalse(state.exists(), change)

    def test_stale_concurrent_local_copy_cannot_overwrite_the_confirmed_cloud_prefix(self):
        state, _ = self.cloud(); self.stage(); self.freeze(); self.cache.send(self.peer, self.transport)
        before = state.read_bytes()
        stale = host.MeshWorkCache(self.directory / "stale-cache", **self.cache.binding)
        stale.stage(self.repo, ["work.txt"], "stale:unit", b"Proposal from a separate unacknowledged copy")
        stale.idle([sys.executable, "-c", "pass"])
        with self.assertRaisesRegex(ValueError, "TRANSFER_REFUSED"): stale.send(self.peer, self.transport)
        self.assertEqual(state.read_bytes(), before)
        with stale.locked(): self.assertIsNotNone(stale.state["pending"])

    def test_numeric_file_names_preserve_cross_language_canonical_digests(self):
        self.cloud()
        for name in ("2", "10"): (self.repo / name).write_bytes(b"original " + name.encode())
        self.git("add", "."); self.git("commit", "-qm", "Numeric file names")
        self.cache.stage(self.repo, ["2", "10"], "numeric:unit", b"Preserve lexical canonical ordering")
        self.freeze()
        self.assertEqual(self.cache.send(self.peer, self.transport)["state"], "MESH_WORK_BATCH_READBACK_CONFIRMED")

    def test_cloud_restart_rejects_corrupted_original_object_or_receipt(self):
        state, stop = self.cloud(); self.stage(); self.freeze(); self.cache.send(self.peer, self.transport); stop()
        original = state.read_bytes()
        for target in ("object", "receipt"):
            prior = json.loads(original)
            if target == "object": prior["mesh_work"]["objects"][next(iter(prior["mesh_work"]["objects"]))] = base64.b64encode(b"wrong").decode()
            else:
                receipt = next(iter(prior["mesh_work"]["nodes"]["local:fixture"]["receipts"].values()))
                receipt["source_tree"] = "c" * 40
            state.write_bytes(host.raw_json(prior))
            code = "import {MonitorStore} from './docs/monitor/server.mjs';new MonitorStore(process.argv[1],'cloud:fixture');"
            run = subprocess.run(["node", "--input-type=module", "-e", code, str(state)], cwd=ROOT, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(run.returncode, 0, target)
            self.assertIn("MESH_WORK_", run.stderr)

    def test_acknowledged_content_is_not_retransmitted_in_successor_batch(self):
        self.cloud(); self.stage(); first = self.freeze(); self.cache.send(self.peer, self.transport)
        self.stage("unit:two", b"A new proposal reuses the same local source bytes")
        self.freeze(); _, packet = self.pending()
        self.assertEqual(packet["base_digest"], first["batch_id"])
        self.assertNotIn(host.digest(self.file.read_bytes()), packet["objects"])
        self.assertEqual(len(packet["objects"]), 1)
        self.cache.send(self.peer, self.transport)

    def test_wrong_server_source_pins_cannot_confirm_the_local_batch(self):
        self.cloud(); self.stage(); self.freeze()
        self.peer["source_tree"] = "c" * 40
        with self.assertRaisesRegex(ValueError, "RECEIPT_BINDING_MISMATCH"): self.cache.send(self.peer, self.transport)
        self.assertIsNotNone(self.state()["pending"])

    def test_corrupt_cached_original_bytes_are_not_trusted_on_a_warm_path(self):
        self.stage()
        path = self.cache.directory / "objects" / host.digest(self.file.read_bytes())
        path.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "OBJECT_READBACK_MISMATCH"): self.freeze()
        self.assertIsNone(self.state()["pending"])

    def test_corrupt_outbox_and_state_refuse_before_transport(self):
        self.stage(); self.freeze()
        raw, packet = self.pending()
        (self.cache.directory / "outbox" / packet["batch_id"]).write_bytes(raw + b" ")
        with self.assertRaisesRegex(ValueError, "OUTBOX_READBACK_MISMATCH"): self.cache.send({}, self.transport)
        envelope = json.loads(self.cache.path.read_bytes()); envelope["state"]["revision"] += 1
        self.cache.path.write_bytes(host.raw_json(envelope))
        with self.assertRaisesRegex(ValueError, "CACHE_READBACK_MISMATCH"): self.freeze()
        self.assertFalse(self.calls)

    def test_symlinks_dirty_worktree_and_untracked_files_do_not_enter_the_cache(self):
        self.file.unlink(); self.file.symlink_to(self.key)
        with self.assertRaisesRegex(ValueError, "CLEAN_LOCAL_COMMIT_REQUIRED"): self.stage()
        self.file.unlink(); self.git("checkout", "--", "work.txt")
        (self.repo / "unknown.txt").write_text("untracked")
        with self.assertRaisesRegex(ValueError, "CLEAN_LOCAL_COMMIT_REQUIRED"): self.stage()
        self.assertFalse(self.cache.path.exists())

    def test_second_cache_writer_cannot_stage_or_validate_under_existing_os_lock(self):
        with self.cache.locked():
            with self.assertRaises(BlockingIOError): self.stage()
        self.assertFalse(self.cache.path.exists())

    def test_cli_uses_private_explicit_request_and_has_no_implicit_cloud_transfer(self):
        instructions = self.directory / "instructions.txt"; instructions.write_bytes(b"Original approved proposal"); instructions.chmod(0o600)
        request = self.directory / "request.json"
        request.write_bytes(host.raw_json({"schema": "qikvrt-repository-work-request/v1", "scope": host.MESH_WORK_SCOPE,
            **self.cache.binding, "paths": ["work.txt"], "work_unit_id": "cli:work", "instructions_file": str(instructions)})); request.chmod(0o600)
        args = [sys.executable, "-B", str(ROOT / "tools/qikvrt_self_host.py"), "mesh-cache-stage", "--root", str(self.repo),
                "--mesh-cache", str(self.cache.directory), "--work-request", str(request)]
        run = subprocess.run(args, capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["cloud_requests"], 0)
        args[3] = "mesh-cache-idle"
        run = subprocess.run(args + ["--validation-command", sys.executable, "-c", "pass"], capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["state"], "MESH_WORK_IDLE_BATCH_FROZEN")


if __name__ == '__main__': unittest.main()
