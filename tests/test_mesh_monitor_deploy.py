# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import qikvrt_mesh_monitor_deploy as deploy


def observation(pending=True, exact=False, status="SUCCESS"):
    service = {}
    for path, value in deploy.EXPECTED_SETTINGS.items():
        target = service
        parts = path.split('.')
        for part in parts[:-1]: target = target.setdefault(part, {})
        target[parts[-1]] = copy.deepcopy(value)
    service['variables'] = {k:{'value':v} for k,v in deploy.EXPECTED_VARIABLES.items()}
    service['variables']['QIKVRT_GITHUB_WEBHOOK_SECRET'] = {'value':'fixture-only-webhook-secret'}
    staged = {
        'id':deploy.PATCH, 'status':'STAGED', 'patch':{
            'services':{deploy.SERVICE:{
                'source':{k:v for k,v in service['source'].items() if k!='rootDirectory'},
                'build':{k:service['build'][k] for k in ('buildCommand','watchPatterns')},
                'deploy':{k:service['deploy'][k] for k in ('startCommand','healthcheckPath','healthcheckTimeout','restartPolicyType','sleepApplication')},
                'volumeMounts':service['volumeMounts'], 'variables':service['variables']}},
            'volumes':{deploy.VOLUME:{'region':'iad','sizeMB':500,'isCreated':'CREATED'}}}}
    live = copy.deepcopy(service)
    if pending:
        live['source']['repo']='Goldkelch/qik-vrt'
        live['source'].pop('commitSha');live['source'].pop('branch');live.pop('variables');live.pop('volumeMounts')
    return {'environment':{
        'id':deploy.ENVIRONMENT,'projectId':deploy.PROJECT,'name':'production','isEphemeral':False,
        'config':{'services':{deploy.SERVICE:live}},
        'volumeInstances':{'edges':[] if pending else [{'node':{'volumeId':deploy.VOLUME,'serviceId':deploy.SERVICE,'mountPath':'/var/lib/qikvrt/monitor','state':'READY'}}]}},
        'serviceInstance':{'serviceName':'mesh-monitor','latestDeployment':{'id':'fixture-deployment','status':status,'meta':{'commitHash':deploy.SOURCE_HEAD if exact else '0'*40}}},
        'environmentStagedChanges':staged if pending else {'id':deploy.PATCH,'status':'COMMITTED','patch':{}}}


class FakeApi:
    def __init__(self, data=None):
        self.data = data or observation(); self.lock=None; self.mutations=[]; self.reads=0; self.change=None; self.lost_response=False
    def observe(self):
        self.reads+=1
        value=copy.deepcopy(self.data)
        if self.reads>1 and self.change:self.change(value)
        return value
    def github(self, method, path, body=None, **_):
        if path.startswith('ref/heads/'):return {'object':{'sha':deploy.SOURCE_HEAD}}
        if method=='GET':return self.lock
        self.lock={'object':{'sha':body['sha']},'ref':body['ref']};return self.lock
    def gql(self, query, variables):
        self.mutations.append((query,variables))
        if self.lost_response:raise deploy.Hold('HOLD_API_TRANSPORT_UNVERIFIED')
        return {'environmentPatchCommitStaged':'fixture-patch','serviceInstanceDeployV2':'fixture-deployment'}


def run(api, **kwargs):
    return deploy.execute(api, {}, apply=True, executor_head=deploy.SOURCE_HEAD,
        ref=deploy.EXPECTED_SETTINGS['source.branch'],readback=lambda _:{'verified':True},**kwargs)


class FakeClock:
    def __init__(self, api, states=()):self.now=0;self.api=api;self.states=iter(states);self.sleeps=[]
    def __call__(self):return self.now
    def sleep(self, seconds):
        self.sleeps.append(seconds);self.now+=seconds
        self.api.data=next(self.states,self.api.data)


def wait(api, dispatch, timer, readback=lambda _:{'verified':True}):
    return deploy.observe_after_dispatch(api,{},dispatch,executor_head=deploy.SOURCE_HEAD,
        ref='main',readback=readback,clock=timer,sleep=timer.sleep)


class DeploymentTests(unittest.TestCase):
    def test_missing_credential_fails_before_network(self):
        with patch('urllib.request.build_opener') as opener:
            with self.assertRaisesRegex(deploy.Hold,'CREDENTIAL_UNAVAILABLE'):deploy.Api({})
            opener.assert_not_called()

    def test_project_and_account_tokens_use_correct_distinct_headers(self):
        self.assertEqual(deploy.Api({'RAILWAY_TOKEN':'fixture-project-token'}).railway_header,{'Project-Access-Token':'fixture-project-token'})
        self.assertEqual(deploy.Api({'RAILWAY_API_TOKEN':'fixture-account-token'}).railway_header,{'Authorization':'Bearer fixture-account-token'})
        with self.assertRaises(deploy.Hold):deploy.Api({'RAILWAY_TOKEN':'a','RAILWAY_API_TOKEN':'b'})

    def test_exact_patch_once_and_second_runner_cannot_dispatch(self):
        api=FakeApi();result=run(api)
        self.assertEqual(result['mutation_count'],1);self.assertFalse(result['effect_ack_done'])
        self.assertIn('environmentPatchCommitStaged',api.mutations[0][0])
        with self.assertRaisesRegex(deploy.Hold,'ALREADY_CLAIMED'):run(api)
        self.assertEqual(len(api.mutations),1)

    def test_lost_mutation_response_survives_as_claim_and_never_retries(self):
        api=FakeApi();api.lost_response=True
        with self.assertRaisesRegex(deploy.Hold,'TRANSPORT_UNVERIFIED'):run(api)
        api.lost_response=False
        with self.assertRaisesRegex(deploy.Hold,'ALREADY_CLAIMED'):run(api)
        self.assertEqual(len(api.mutations),1)

    def test_current_success_is_readback_only_without_lock_or_mutation(self):
        api=FakeApi(observation(pending=False,exact=True))
        result=run(api)
        self.assertEqual(result['state'],'PUBLIC_RUNTIME_READBACK_VERIFIED')
        self.assertEqual(result['mutation_count'],0);self.assertIsNone(api.lock)

    def test_admitted_attempt_reaches_public_readback_without_second_mutation(self):
        api=FakeApi();dispatch=run(api)
        applying=observation();applying['environmentStagedChanges']['status']='APPLYING'
        api.data=applying
        timer=FakeClock(api,[observation(pending=False,exact=True,status='BUILDING'),observation(pending=False,exact=True)])
        result=wait(api,dispatch,timer)
        self.assertEqual(result['state'],'PUBLIC_RUNTIME_READBACK_VERIFIED')
        self.assertEqual(result['mutation_count'],1);self.assertEqual(result['dispatch_receipt'],dispatch)
        self.assertEqual(len(api.mutations),1);self.assertEqual(timer.sleeps,[5,5])

    def test_readback_timeout_is_bounded_and_preserves_admitted_mutation(self):
        api=FakeApi();dispatch=run(api);timer=FakeClock(api)
        result=wait(api,dispatch,timer)
        self.assertEqual(result['state'],'HOLD_DEPLOYMENT_DISPATCHED_READBACK_TIMEOUT')
        self.assertLessEqual(result['observation_attempts'],36);self.assertLessEqual(timer.now,180)
        self.assertEqual(result['mutation_count'],1);self.assertEqual(result['lock_ref'],dispatch['lock_ref'])
        self.assertEqual(len(api.mutations),1);self.assertFalse(result['effect_ack_done'])

    def test_readback_permission_error_stops_immediately_without_retry(self):
        api=FakeApi();dispatch=run(api)
        api.observe=lambda:(_ for _ in ()).throw(deploy.Hold('HOLD_API_HTTP_403'))
        timer=FakeClock(api);result=wait(api,dispatch,timer)
        self.assertEqual(result['state'],'HOLD_API_HTTP_403');self.assertEqual(result['mutation_count'],1)
        self.assertEqual(timer.sleeps,[]);self.assertEqual(len(api.mutations),1)

    def test_readback_configuration_drift_stops_without_sleep_or_mutation(self):
        api=FakeApi();dispatch=run(api)
        api.data['environmentStagedChanges']['patch']['services'][deploy.SERVICE]['source']['commitSha']='f'*40
        timer=FakeClock(api);result=wait(api,dispatch,timer)
        self.assertEqual(result['state'],'HOLD_RAILWAY_CONFIGURATION_DRIFT')
        self.assertEqual(timer.sleeps,[]);self.assertEqual(len(api.mutations),1)

    def test_platform_success_then_delayed_client_readback_never_redeploys(self):
        api=FakeApi();dispatch=run(api);api.data=observation(pending=False,exact=True);timer=FakeClock(api)
        answers=iter([False,True])
        def readback(_):
            if not next(answers):raise deploy.Hold('HOLD_PUBLIC_OR_INDEPENDENT_CLIENT_READBACK')
            return {'verified':True}
        result=wait(api,dispatch,timer,readback)
        self.assertEqual(result['state'],'PUBLIC_RUNTIME_READBACK_VERIFIED')
        self.assertEqual(timer.sleeps,[5]);self.assertEqual(len(api.mutations),1)

    def test_successful_platform_status_cannot_replace_public_readback(self):
        api=FakeApi(observation(pending=False,exact=True))
        def fail(_):raise deploy.Hold('HOLD_PUBLIC_OR_INDEPENDENT_CLIENT_READBACK')
        with self.assertRaises(deploy.Hold):deploy.execute(api,{},apply=True,executor_head=deploy.SOURCE_HEAD,
            ref='main',readback=fail)
        self.assertEqual(api.mutations,[])

    def test_live_bound_config_uses_explicit_commit_deploy_without_new_service(self):
        api=FakeApi(observation(pending=False));run(api)
        self.assertIn('serviceInstanceDeployV2',api.mutations[0][0])
        self.assertEqual(api.mutations[0][1]['commitSha'],deploy.SOURCE_HEAD)
        self.assertNotIn('serviceCreate',api.mutations[0][0])

    def test_active_platform_deployment_stops_before_claim(self):
        api=FakeApi(observation(status='BUILDING'))
        with self.assertRaisesRegex(deploy.Hold,'IN_PROGRESS'):run(api)
        self.assertIsNone(api.lock);self.assertEqual(api.mutations,[])

    def test_verify_mode_has_no_dispatch_path(self):
        api=FakeApi()
        with self.assertRaisesRegex(deploy.Hold,'NOT_OBSERVED'):deploy.execute(api,{},apply=False,executor_head='',ref='')
        self.assertIsNone(api.lock);self.assertEqual(api.mutations,[])

    def test_drift_and_unrelated_changes_fail_before_claim(self):
        variants=[
            lambda d:d['environment'].update(projectId='other'),
            lambda d:d['environmentStagedChanges'].update(id='other'),
            lambda d:d['environmentStagedChanges']['patch']['services'].update(other={}),
            lambda d:d['environmentStagedChanges']['patch'].update(sharedVariables={'SECRET':{'value':'x'}}),
            lambda d:d['environmentStagedChanges']['patch']['services'][deploy.SERVICE]['deploy'].update(restartPolicyType='NEVER'),
            lambda d:d['environmentStagedChanges']['patch']['services'][deploy.SERVICE]['source'].update(commitSha='f'*40),
            lambda d:d['environmentStagedChanges']['patch']['services'][deploy.SERVICE].update(isDeleted=True),
            lambda d:d['environmentStagedChanges']['patch']['volumes'][deploy.VOLUME].update(sizeMB=999),
            lambda d:d['environmentStagedChanges']['patch']['services'][deploy.SERVICE]['variables']['QIKVRT_MONITOR_STATE_DIR'].update(value='/tmp/volatile'),
        ]
        for change in variants:
            with self.subTest(change=change):
                data=observation();change(data);api=FakeApi(data)
                with self.assertRaises(deploy.Hold):run(api)
                self.assertIsNone(api.lock);self.assertEqual(api.mutations,[])

    def test_second_observation_drift_consumes_claim_but_not_railway_mutation(self):
        api=FakeApi();api.change=lambda d:d['serviceInstance']['latestDeployment'].update(id='competitor')
        with self.assertRaisesRegex(deploy.Hold,'STATE_CHANGED'):run(api)
        self.assertIsNotNone(api.lock);self.assertEqual(api.mutations,[])

    def test_existing_claim_wrong_source_fails_closed(self):
        api=FakeApi();api.lock={'object':{'sha':'f'*40}}
        with self.assertRaisesRegex(deploy.Hold,'LOCK_BINDING'):run(api)
        self.assertEqual(api.mutations,[])

    def test_live_volume_is_required(self):
        data=observation(pending=False);data['environment']['volumeInstances']['edges']=[]
        with self.assertRaisesRegex(deploy.Hold,'VOLUME_NOT_PROVISIONED'):run(FakeApi(data))

    def test_exact_source_contract_verifies_six_artifacts(self):
        self.assertEqual(len(deploy.source_contract()['artifact_files_sha256']),6)

    def test_cli_missing_credential_returns_hold_receipt_without_secrets(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',{},clear=True),patch('sys.stdout',new_callable=io.StringIO) as out:
            target=Path(tmp)/'receipt.json'
            self.assertEqual(deploy.main(['--apply','--wait-readback','--output',str(target)]),20)
            value=json.loads(target.read_text());self.assertEqual(value['state'],'HOLD_RAILWAY_SERVER_CREDENTIAL_UNAVAILABLE')
            self.assertFalse(value['effect_ack_done']);self.assertEqual(json.loads(out.getvalue()),value)

    def test_raw_api_errors_and_credentials_are_never_reflected(self):
        import urllib.error
        api=deploy.Api({'RAILWAY_TOKEN':'fixture-project-token'})
        api.opener=unittest.mock.Mock()
        api.opener.open.side_effect=urllib.error.HTTPError(deploy.API,403,'fixture-project-token',{},io.BytesIO(b'fixture-project-token'))
        with self.assertRaises(deploy.Hold) as context:api.gql('query fixture {}',{})
        self.assertEqual(str(context.exception),'HOLD_API_HTTP_403')


if __name__=='__main__':unittest.main()
