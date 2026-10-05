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
import sys
import tempfile
import time
import unittest
from unittest import mock
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("selfhost", ROOT / "tools/qikvrt_self_host.py")
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


class WorkflowRuntimeTests(unittest.TestCase):
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


class StandaloneTests(unittest.TestCase):
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


if __name__ == '__main__': unittest.main()
