# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Real native CI supervisor; a local fixture, never own-host acceptance.

Explicitly selected by the existing terminal workflow on its disposable Linux
runner. No mock systemd, skip, production unit or provider credentials.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
import uuid

from tests import test_self_host as standalone
from tests import test_self_host_temdd as native

host = standalone.host


class SystemdRecoveryTests(unittest.TestCase):
    setUpClass = classmethod(standalone.StandaloneTests.setUpClass.__func__)
    tearDownClass = classmethod(standalone.StandaloneTests.tearDownClass.__func__)
    save_config = standalone.StandaloneTests.save_config
    stop = standalone.StandaloneTests.stop
    get = standalone.StandaloneTests.get
    seed_acknowledged_event = standalone.StandaloneTests.seed_acknowledged_event
    cli = native.NativeStandaloneTests.cli
    sql = native.NativeStandaloneTests.sql
    commit_input = native.NativeStandaloneTests.commit_input

    def ctl(self, *args, check=True):
        result = subprocess.run(['sudo', '-n', 'systemctl', *args], capture_output=True,
                                text=True, timeout=30)
        if check: self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def status(self):
        result = self.ctl('show', self.unit, '--property=MainPID,InvocationID,NRestarts,ExecMainStatus,ActiveState,UnitFileState')
        return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)

    def ready(self, previous=None):
        edge = time.monotonic() + 35
        while time.monotonic() < edge:
            status = self.status()
            if int(status.get('MainPID', 0)) and status.get('InvocationID') != previous:
                try:
                    code, value = self.get('/api/terminal')
                    if code == 200 and value.get('state') == 'NATIVE_TEMDD_READY': return status
                except (OSError, ValueError): pass
            time.sleep(0.1)
        self.ctl('status', self.unit, check=False)
        self.fail('native systemd recovery/readiness deadline exceeded: ' + json.dumps(status))

    def setUp(self):
        self.assertEqual(Path('/proc/1/comm').read_text().strip(), 'systemd', 'native systemd PID1 required; no skip')
        standalone.StandaloneTests.setUp(self)
        self.config.update(terminal_profile='temdd', source_repository='ingolf-lohmann/qik-vrt', subject_pr=457)
        self.save_config()
        self.unit = 'qikvrt-ci-fixture-' + uuid.uuid4().hex + '.service'
        self.path_unit = self.unit[:-8] + '.path'
        self.admission_path = self.work / 'admission.json'
        declaration = {'schema':'qikvrt-own-host-admission/v1','source_head':self.head,'source_tree':self.tree,
            'manifest_sha256':self.pin,'config_sha256':host.digest(self.config_path.read_bytes()),
            'node_id':self.config['node_id'], **host.own_host_observation(self.volume),
            'public_origin':'https://ci-fixture-only.example.org', 'execution_operation':'CI fixture only; no public effect',
            'supervisor_id':'systemd:' + self.unit, 'authorization_evidence_sha256':'b'*64,
            'persistence_evidence_sha256':'c'*64,'https_routing_evidence_sha256':'d'*64}
        self.admission_bytes = host.raw_json(declaration)
        self.admission_path.write_bytes(self.admission_bytes); self.admission_path.chmod(0o600)
        plan = host.supervisor_plan(self.export,self.pin,self.config_path,self.admission_path,
            host.digest(self.admission_bytes),host.digest(Path(host.__file__).read_bytes()))
        output = self.work / 'systemd'
        self.plan = host.materialize_supervisor(plan,output)
        units = [str(output / name) for name in (self.unit,self.path_unit)]
        result = subprocess.run(['systemd-analyze','verify',*units],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertNotIn('Unknown',result.stderr)
        self.addCleanup(self.cleanup_units)
        self.expected_journal = self.seed_acknowledged_event()
        self.ctl('enable','--now',*units)

    def cleanup_units(self):
        self.ctl('stop',self.path_unit,self.unit,check=False)
        self.ctl('disable',self.path_unit,self.unit,check=False)
        self.ctl('daemon-reload',check=False)

    def test_actual_mainpid_crash_and_exact_admission_restoration_recover_durable_native_state(self):
        first = self.ready()
        self.assertEqual(first['UnitFileState'],'enabled')
        prepared,event = self.commit_input()
        journal_before = self.get('/api/events?after=0')[1]
        self.assertEqual(journal_before['events'],self.expected_journal)
        rows = self.sql('SELECT binding,source,native_id,native_digest,body,body_digest FROM events')
        binding = (self.volume/'binding.json').read_bytes()
        epoch = self.get('/api/terminal')[1]['ledger_id']
        parent = int(first['MainPID'])
        children = [int(p) for p in Path('/proc/'+str(parent)+'/task/'+str(parent)+'/children').read_text().split()]
        self.assertTrue(children,'real original monitor child must exist')
        identities = {p:Path('/proc/'+str(p)+'/stat').read_text().split()[21] for p in children}
        self.ctl('kill','--kill-who=main','--signal=SIGKILL',self.unit)
        second = self.ready(first['InvocationID'])
        self.assertGreater(int(second['NRestarts']),int(first['NRestarts']))
        for p,start in identities.items():
            stat = Path('/proc/'+str(p)+'/stat')
            if stat.exists(): self.assertNotEqual(stat.read_text().split()[21],start,'old cgroup child survived')
        self.assertEqual(self.sql('SELECT binding,source,native_id,native_digest,body,body_digest FROM events'),rows)
        self.assertEqual(self.get('/api/events?after=0')[1],journal_before)
        self.assertEqual(self.get('/api/terminal')[1]['ledger_id'],epoch)
        self.assertEqual((self.volume/'binding.json').read_bytes(),binding)
        code,fresh = self.cli('durable-readback',prepared)
        self.assertEqual(code,0,fresh); self.assertEqual(fresh['durable_readback'],event)
        # Drift is a terminal HOLD, not a restart storm or a new admission pin.
        self.admission_path.write_bytes(self.admission_bytes+b'\n')
        self.ctl('kill','--kill-who=main','--signal=SIGKILL',self.unit)
        edge=time.monotonic()+30
        while time.monotonic()<edge:
            held=self.status()
            if held.get('ExecMainStatus')=='78' and held.get('MainPID')=='0': break
            time.sleep(0.1)
        self.assertEqual(held.get('ExecMainStatus'),'78',held)
        count=held['NRestarts']; time.sleep(4)
        self.assertEqual(self.status()['NRestarts'],count,'HOLD retried without a restoration event')
        self.assertEqual((self.volume/'binding.json').read_bytes(),binding)
        self.admission_path.write_bytes(self.admission_bytes)
        third=self.ready(second['InvocationID'])
        self.assertEqual(self.sql('SELECT binding,source,native_id,native_digest,body,body_digest FROM events'),rows)
        self.assertEqual(self.get('/api/events?after=0')[1],journal_before)
        result=subprocess.run(self.plan['readback_argv'][:4]+[self.url]+self.plan['readback_argv'][5:],
            capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(json.loads(result.stdout)['effect_ack_done'])
        evidence={'schema':'qikvrt-systemd-recovery-test/v1','scope':'NATIVE_CI_LOCAL_FIXTURE_ONLY',
            'source_head':host.git(standalone.ROOT,'rev-parse','HEAD').decode(),
            'source_tree':host.git(standalone.ROOT,'rev-parse','HEAD^{tree}').decode(),
            'fixture_head':self.head,'fixture_tree':self.tree,'manifest_sha256':self.pin,
            'unit_sha256':self.plan['unit_sha256'],'path_unit_sha256':self.plan['path_unit_sha256'],
            'invocations':[first['InvocationID'],second['InvocationID'],third['InvocationID']],
            'mainpid_only_sigkill_cgroup_cleanup':True,'hold_exit_status':78,
            'exact_admission_restoration_automatically_restarted':True,'native_sqlite_original_bytes_preserved':True,
            'journal_readback_preserved':True,'public_readback_verified':False,'deployed_restart_verified':False,
            'host_admission_verified':False,'review_governance_satisfied':False,'effect_ack_done':False}
        output=Path(os.environ['QIKVRT_SYSTEMD_TEST_EVIDENCE'])
        output.mkdir(mode=0o700,parents=True,exist_ok=True)
        (output/'RECOVERY.json').write_bytes(host.raw_json(evidence))
        (output/'SYSTEMD_VERSION.txt').write_bytes(subprocess.check_output(['systemctl','--version']))
        print(json.dumps(evidence,sort_keys=True))


if __name__ == '__main__': unittest.main()
