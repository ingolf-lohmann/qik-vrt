# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Admission/failure controls with an explicit fake control plane; no paid effects."""
from __future__ import annotations
import base64
import copy
import datetime as dt
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.error

from tools import qikvrt_self_host_provider as provider

ROOT = Path(__file__).resolve().parents[1]
KEY = 'ssh-ed25519 ' + base64.b64encode(b'\0\0\0\x0bssh-ed25519\0\0\0\x20' + b'x' * 32).decode() + ' fixture-public-key'
KEY_SHA = provider.public_key(KEY)['sha256']


class FakeAPI(provider.API):
    def __init__(self, name='digitalocean'):
        binding = {'product': provider.PRODUCTS[name][0], 'principal_id': 'fixture-principal',
                   'principal_evidence_sha256': '1' * 64}
        super().__init__(name, 'fixture-only-token-no-live-provider', binding)
        self.resources = []; self.calls = []; self.posts = 0
        self.account = {'status': 'active', 'status_message': '', 'droplet_limit': 3,
                        'team': {'uuid': 'fixture-principal'}}
        self.key_values = [{'id': 9, 'public_key': KEY}]
        self.fail_after_create = False; self.crash_before_create = False
        self.inspect_before_post = None
        self.price = {'currency': 'EUR', 'server_types': [{'name':'cx-fixture','prices':[
            {'location':'fsn1','price_hourly':{'net':'0.005','gross':'0.006'},'price_monthly':{'net':'3.50','gross':'4.20'}}]}],
            'primary_ips':[{'type':'ipv4','prices':[{'location':'fsn1','price_hourly':{'net':'0.0006','gross':'0.00072'},
                'price_monthly':{'net':'0.50','gross':'0.60'}}]}]}

    def collection(self, path, key, ionos=False):
        self.calls.append(('GET', path))
        if path.startswith('/droplets'): return copy.deepcopy(self.resources if 'type=droplets' in path else [])
        if path == '/servers': return copy.deepcopy(self.resources)
        if path in ('/account/keys','/ssh_keys'): return copy.deepcopy(self.key_values)
        if path == '/regions': return [{'slug':'fra1','available':True,'sizes':['s-1vcpu-1gb']}]
        if path == '/sizes': return [{'slug':'s-1vcpu-1gb','available':True,'price_monthly':6,'price_hourly':0.00893,'regions':['fra1'],'transfer':1}]
        if path == '/locations': return [{'id':1,'name':'fsn1'}]
        if path == '/server_types': return [{'id':1,'name':'cx-fixture','locations':[{'name':'fsn1','deprecation':None}]}]
        if path.startswith('/images'): return [{'id':101,'slug':'ubuntu-24-04-x64','name':'ubuntu-24.04','regions':['fra1'],'type':'system'}]
        if path.startswith('/datacenters?'): return [{'id':'dc-fixture','properties':{'location':'de/fra'}}]
        if '/servers?' in path: return copy.deepcopy(self.resources)
        if '/lans?' in path: return [{'id':'1','properties':{'public':True}}]
        if path.startswith('/locations?'): return [{'id':'de/fra','properties':{'name':'Frankfurt'}}]
        if path.startswith('/templates?'): return []
        raise AssertionError('unexpected collection: ' + path)

    def call(self, path, body=None):
        self.calls.append(('POST' if body is not None else 'GET',path))
        self.reads.append({'method':'POST' if body is not None else 'GET','path':path,'response_sha256':'e'*64})
        if path == '/account': return {'account':copy.deepcopy(self.account)}
        if path == '/pricing': return {'pricing':copy.deepcopy(self.price)}
        if path.startswith('/contracts'): return {'properties':{'contractNumber':42}}
        if body is not None:
            if self.inspect_before_post: self.inspect_before_post()
            if self.crash_before_create: raise SystemExit('fixture process crash before send')
            self.posts += 1
            if self.provider == 'digitalocean':
                value = {'id':77,'name':body['name'],'region':{'slug':body['region']},'size_slug':body['size'],
                         'status':'active','networks':{'v4':[{'type':'public','ip_address':'93.184.216.34'}]}}
                self.resources.append(value)
                response = {'droplet':value}
            elif self.provider == 'hetzner':
                value = {'id':77,'name':body['name'],'location':{'name':body['location']},'server_type':{'name':body['server_type']},
                         'status':'running','public_net':{'ipv4':{'ip':'93.184.216.34'}}}
                self.resources.append(value)
                response = {'server':value,'action':{'id':81}}
            else:
                value = {'id':'server-fixture','properties':dict(body['properties'],vmState='RUNNING'),
                         'metadata':{'state':'AVAILABLE'},'entities':copy.deepcopy(body['entities'])}
                value['entities']['nics']['items'][0]['properties']['ips']=['93.184.216.34']
                self.resources.append(value)
                response = value
            if self.fail_after_create: raise provider.ProviderError(0,'HOLD_PROVIDER_TRANSPORT_OUTCOME_UNKNOWN')
            return response
        if path.startswith('/droplets/') or path.startswith('/servers/') or '/servers/' in path:
            return {'droplet':copy.deepcopy(self.resources[0])} if self.provider=='digitalocean' else {'server':copy.deepcopy(self.resources[0])} if self.provider=='hetzner' else copy.deepcopy(self.resources[0])
        raise AssertionError('unexpected GET: '+path)


def request(api):
    region, size, image = ('fra1','s-1vcpu-1gb','ubuntu-24-04-x64') if api.provider=='digitalocean' else ('fsn1','cx-fixture','ubuntu-24.04')
    spec = None
    if api.provider=='ionos':
        region, image = 'de/fra','101'
        spec = {'datacenter_id':'dc-fixture','lan_id':'1','cores':1,'ram_mb':1024,'disk_gb':20,'disk_type':'SSD'}
        size = 'spec:'+provider.sha(provider.wire({'type':'VCPU','cores':1,'ram':1024}))
    return {'schema':provider.REQUEST,'operation_id':'fixture-operation-1','provider':api.provider,'node_id':'fixture-node',
        'source_repository':'ingolf-lohmann/qik-vrt','source_head':'a'*40,'source_tree':'b'*40,
        'manifest_sha256':'c'*64,'config_sha256':'d'*64,
        'principal_sha256':provider.sha(provider.wire({'provider':api.provider,'principal_id':api.binding['principal_id']})),
        'region':region,'size':size,'image':image,'resource_id':None,'ssh_key_sha256':KEY_SHA,
        'public_origin':'https://native.example.org','budget':{'currency':'USD' if api.provider=='digitalocean' else 'EUR',
        'max_hourly':'1','max_monthly':'10','variable_usage_authorized':True},'ionos_spec':spec}


def quote(req):
    return {'provider':'ionos','principal_sha256':req['principal_sha256'],'region':req['region'],'size':req['size'],
        'ionos_spec':req['ionos_spec'],'image':req['image'],'coverage':['compute','boot_disk','public_ipv4'],
        'source_evidence_sha256':'e'*64,'expires_at':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),
        'currency':'EUR','hourly':'0.01','monthly':'7','basis':'FIXTURE_CONTRACT_QUOTE_NOT_A_LIVE_PRICE'}


def grant(admission, req):
    return {'schema':'qikvrt-exact-provider-create-authorization/v1','decision':'AUTHORIZE_EXACT_CREATE',
        **{k:admission[k] for k in ('request_sha256','admission_sha256','cost_quote_sha256')},
        'principal_sha256':req['principal_sha256'],'expires_at':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=1)).isoformat(),
        'payment_evidence_sha256':'e'*64,'accepted_terms_evidence_sha256':'f'*64,'authorization_evidence_sha256':'a'*64,
        'effects':['server_create','boot_disk_create','public_ipv4_allocate']}


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name); self.directory.chmod(0o700)
        self.receipts=provider.Receipts(self.directory)
        self.api=FakeAPI(); self.req=request(self.api)

    def test_conflicting_empty_account_blocks_before_quote_key_or_any_create(self):
        self.api.account.update(status='warning',status_message='Your team has created the maximum allowed number of Droplets. Please resolve this on the control panel.')
        self.api.key_values=[]
        snapshot=provider.collect(self.api)
        result=provider.plan(snapshot,self.req)
        self.assertEqual(result['first_boundary'],'HOLD_PROVIDER_ACCOUNT_INVENTORY_CONFLICT')
        self.assertNotIn('cost_quote',result)
        self.assertEqual(self.api.posts,0)

    def test_unknown_or_incomplete_inventory_is_not_an_empty_admission(self):
        snapshot=provider.collect(self.api)
        snapshot['complete']=False
        self.assertEqual(provider.plan(snapshot,self.req)['first_boundary'],'HOLD_PROVIDER_INVENTORY_INCOMPLETE')
        snapshot['authenticated']=False
        self.assertEqual(provider.plan(snapshot,self.req)['first_boundary'],'HOLD_PROVIDER_CREDENTIAL_UNBOUND')

    def test_warning_full_limit_bad_principal_and_duplicate_inventory_fail_closed(self):
        snapshot=provider.collect(self.api)
        snapshot['account']['status']='warning'
        self.assertEqual(provider.plan(snapshot,self.req)['first_boundary'],'HOLD_PROVIDER_ACCOUNT_NOT_ADMITTED')
        snapshot['account']['status']='active'; snapshot['account']['resource_limit']=0
        self.assertEqual(provider.plan(snapshot,self.req)['first_boundary'],'HOLD_PROVIDER_RESOURCE_LIMIT')
        changed=copy.deepcopy(self.req); changed['principal_sha256']='e'*64
        with self.assertRaisesRegex(ValueError,'PRINCIPAL_MISMATCH'): provider.plan(snapshot,changed)
        snapshot['resources']=[{'id':'77'},{'id':'77'}]
        with self.assertRaisesRegex(ValueError,'INVENTORY_DUPLICATE'): provider.validate_snapshot(snapshot)

    def test_current_region_size_price_and_existing_key_are_bound(self):
        result=provider.plan(provider.collect(self.api),self.req)
        self.assertEqual(result['state'],'CREATE_PLAN_BOUND_PENDING_AUTHORIZATION')
        self.assertEqual(result['cost_quote']['monthly'],'6')
        self.assertEqual(result['ssh_key']['id'],'9')
        self.assertEqual(result['provider_operation']['body']['ssh_keys'],['9'])
        self.assertFalse(result['provider_create_executed']); self.assertFalse(result['effect_ack_done'])

    def test_key_selection_uses_wire_identity_ignoring_comment_and_reported_fingerprint(self):
        self.api.key_values[0]['public_key']=KEY.split(' fixture')[0]+' a-different-comment'
        result=provider.plan(provider.collect(self.api),self.req)
        self.assertEqual(result['ssh_key']['sha256'],KEY_SHA)
        self.api.key_values=[]
        self.assertEqual(provider.plan(provider.collect(self.api),self.req)['first_boundary'],'HOLD_EXISTING_PUBLIC_SSH_KEY_REQUIRED')

    def test_missing_price_budget_bad_currency_or_over_budget_never_admits(self):
        for budget,code in [(None,'COST_BUDGET_BINDING'),({'currency':'EUR','max_hourly':'1','max_monthly':'10','variable_usage_authorized':True},'COST_BUDGET_BINDING'),
                            ({'currency':'USD','max_hourly':'1','max_monthly':'5','variable_usage_authorized':True},'EXCEEDS_AUTHORIZED'),
                            ({'currency':'USD','max_hourly':'1','max_monthly':'10','variable_usage_authorized':False},'VARIABLE_USAGE')]:
            req=copy.deepcopy(self.req); req['budget']=budget
            self.assertIn(code,provider.plan(provider.collect(self.api),req)['first_boundary'])
        for value in ['NaN','Infinity','-1',True]:
            with self.assertRaises(ValueError): provider.money(value)

    def test_no_grant_wrong_terms_payment_or_expired_grant_never_sends(self):
        result=provider.plan(provider.collect(self.api),self.req)
        good=grant(result,self.req)
        variants=[None]
        for field,value in [('accepted_terms_evidence_sha256',None),('payment_evidence_sha256','0'*64),
                            ('expires_at','2000-01-01T00:00:00Z'),('request_sha256','f'*64)]:
            bad=copy.deepcopy(good); bad[field]=value; variants.append(bad)
        for variant in variants:
            with self.assertRaises(ValueError): provider.apply(self.api,self.req,self.receipts,variant)
        self.assertEqual(self.api.posts,0)
        self.assertIsNone(self.receipts.get(self.req['operation_id'],'intent'))

    def test_intent_is_fsynced_and_restart_reuses_readback_without_duplicate_create(self):
        admission=provider.plan(provider.collect(self.api),self.req)
        def before():
            intent=self.receipts.get(self.req['operation_id'],'intent')
            self.assertEqual(intent['request_sha256'],admission['request_sha256'])
            self.assertEqual(self.receipts.path(self.req['operation_id'],'intent').stat().st_mode & 0o777,0o600)
        self.api.inspect_before_post=before
        first=provider.apply(self.api,self.req,self.receipts,grant(admission,self.req))
        self.assertIn('resource',first)
        restarted=provider.Receipts(self.directory)
        second=provider.apply(self.api,self.req,restarted,None)
        self.assertEqual(first,second); self.assertEqual(self.api.posts,1)
        changed=copy.deepcopy(self.req); changed['source_head']='e'*40
        with self.assertRaisesRegex(ValueError,'RECEIPT_CONFLICT|OPERATION_ID_CONFLICT'): provider.apply(self.api,changed,restarted)

    def test_lost_ack_is_resolved_by_actual_resource_get_never_repeated_post(self):
        self.api.fail_after_create=True
        admission=provider.plan(provider.collect(self.api),self.req)
        first=provider.apply(self.api,self.req,self.receipts,grant(admission,self.req))
        self.assertEqual(first['resource']['id'],'77'); self.assertEqual(self.api.posts,1)
        self.assertEqual(self.receipts.get(self.req['operation_id'],'transport')['state'],'OUTCOME_UNKNOWN_OR_REJECTED_READBACK_ONLY')
        provider.apply(self.api,self.req,self.receipts)
        self.assertEqual(self.api.posts,1)
        self.assertIn(('GET','/droplets/77'),self.api.calls)

    def test_crash_after_intent_before_send_holds_even_when_inventory_is_empty(self):
        self.api.crash_before_create=True
        admission=provider.plan(provider.collect(self.api),self.req)
        with self.assertRaises(SystemExit): provider.apply(self.api,self.req,self.receipts,grant(admission,self.req))
        result=provider.apply(self.api,self.req,provider.Receipts(self.directory))
        self.assertEqual(result['state'],'HOLD_CREATE_OUTCOME_UNKNOWN_READBACK_ONLY')
        self.assertFalse(result['create_retry_permitted']); self.assertEqual(self.api.posts,0)

    def test_rejected_payment_preserves_exact_status_and_does_not_retry(self):
        admission=provider.plan(provider.collect(self.api),self.req)
        original=self.api.call
        def reject(path,body=None):
            if body is not None: raise provider.ProviderError(403,'HOLD_PAYMENT_METHOD_REQUIRED')
            return original(path,body)
        self.api.call=reject
        result=provider.apply(self.api,self.req,self.receipts,grant(admission,self.req))
        self.assertEqual(result['state'],'HOLD_CREATE_OUTCOME_UNKNOWN_READBACK_ONLY')
        transport=self.receipts.get(self.req['operation_id'],'transport')
        self.assertEqual(transport['http_status'],403); self.assertEqual(transport['cause'],'HOLD_PAYMENT_METHOD_REQUIRED')

    def test_existing_resource_reused_explicitly_unknown_resources_retained_without_delete(self):
        self.api.resources=[{'id':77,'name':'owner-existing','region':{'slug':'fra1'},'size_slug':'s-1vcpu-1gb','status':'active','networks':{'v4':[]}}]
        self.req['resource_id']='77'
        result=provider.plan(provider.collect(self.api),self.req)
        self.assertEqual(result['unknown_resources_retained'],['77'])
        reused=provider.apply(self.api,self.req,self.receipts)
        self.assertEqual(reused['resource']['id'],'77'); self.assertEqual(self.api.posts,0)
        changed=copy.deepcopy(self.req); changed['node_id']='different-node'
        with self.assertRaisesRegex(ValueError,'RECEIPT_CONFLICT'): provider.apply(self.api,changed,self.receipts)
        self.assertTrue(all(method=='GET' for method,_ in self.api.calls))

    def test_hetzner_quotes_primary_ipv4_and_uses_locations_not_removed_datacenters(self):
        api=FakeAPI('hetzner'); req=request(api)
        snapshot=provider.collect(api); admission=provider.plan(snapshot,req)
        self.assertEqual(admission['cost_quote']['monthly'],'4.80')
        self.assertEqual(admission['provider_operation']['body']['location'],'fsn1')
        self.assertTrue(all('/datacenters' not in path for _,path in api.calls))
        provider.apply(api,req,self.receipts,grant(admission,req))
        self.assertEqual(api.posts,1)
        api.price['primary_ips']=[]
        self.assertIn('COMPLETE_COMPUTE_AND_IPV4',provider.plan(provider.collect(api),req)['first_boundary'])

    def test_ionos_keeps_exact_cloud_contract_spec_public_lan_quote_and_existing_key(self):
        api=FakeAPI('ionos'); req=request(api)
        snapshot=provider.collect(api,KEY)
        self.assertEqual(snapshot['keys'][0]['source'],'PINNED_EXISTING_OPERATOR_PUBLIC_KEY')
        self.assertIn('CONTRACT_PRICE_QUOTE',provider.plan(snapshot,req)['first_boundary'])
        q=quote(req); admission=provider.plan(snapshot,req,q)
        self.assertEqual(admission['provider_operation']['path'],'/datacenters/dc-fixture/servers')
        body=admission['provider_operation']['body']
        self.assertEqual(body['entities']['volumes']['items'][0]['properties']['sshKeys'],[provider.public_key(KEY)['public_key']])
        provider.apply(api,req,self.receipts,grant(admission,req),q,KEY)
        self.assertEqual(api.posts,1)
        self.assertTrue(all('sshkeys' not in path for _,path in api.calls))

    def test_stale_snapshot_conflicting_key_and_invalid_origin_refused(self):
        snapshot=provider.collect(self.api); snapshot['completed_at']='2000-01-01T00:00:00Z'
        with self.assertRaisesRegex(ValueError,'NOT_FRESH'): provider.plan(snapshot,self.req)
        snapshot=provider.collect(self.api); snapshot['keys'][0]['sha256']='e'*64
        with self.assertRaisesRegex(ValueError,'PUBLIC_KEY_MISMATCH'): provider.plan(snapshot,self.req)
        for url in ['http://native.example.org','https://127.0.0.1','https://user:secret@native.example.org','https://native..example.org','https://native.example.org/path']:
            with self.assertRaises(ValueError): provider.origin(url)

    def test_competing_cooperating_writer_is_fenced_without_a_second_create(self):
        with self.receipts.locked():
            with self.assertRaises(BlockingIOError): provider.apply(self.api,self.req,provider.Receipts(self.directory))
        self.assertEqual(self.api.posts,0)

    def test_price_or_inventory_change_invalidates_prior_create_authorization(self):
        admission=provider.plan(provider.collect(self.api),self.req)
        authorized=grant(admission,self.req)
        original=self.api.collection
        def changed(path,key,ionos=False):
            items=original(path,key,ionos)
            if path=='/sizes': items[0]['price_monthly']=7
            return items
        self.api.collection=changed
        with self.assertRaisesRegex(ValueError,'EXACT_CREATE_AUTHORIZATION'): provider.apply(self.api,self.req,self.receipts,authorized)
        self.assertEqual(self.api.posts,0)

    def test_independent_verifier_is_reused_with_ipv4_pin_and_without_provider_environment(self):
        self.api.resources=[{'id':77,'name':'owner-existing','region':{'slug':'fra1'},'size_slug':'s-1vcpu-1gb','status':'active',
                             'networks':{'v4':[{'type':'public','ip_address':'93.184.216.34'}]}}]
        self.req['resource_id']='77'
        config=self.directory/'config.json'
        config.write_bytes(provider.wire({k:self.req[k] for k in ('source_repository','source_head','source_tree','node_id')} | {'adapter':'none'})); config.chmod(0o600)
        self.req['config_sha256']=provider.sha(config.read_bytes())
        manifest={k:self.req[k] for k in ('source_repository','source_head','source_tree')}
        client={'state':'CLIENT_BYTE_READBACK_VERIFIED','public_url':self.req['public_origin'],'source_head':self.req['source_head'],
                'source_tree':self.req['source_tree'],'health_state':'HEALTHY','effect_ack_done':False,'readback_observed_at':provider.timestamp()}
        result=mock.Mock(returncode=0,timed_out=False,output_limit_exceeded=False,stdout=json.dumps(client))
        health={'ipv4':'93.184.216.34','state':'IPV4_HTTPS_HEALTH_VERIFIED_PENDING_INDEPENDENT_READBACK','effect_ack_done':False}
        with mock.patch.object(provider.host,'verify',return_value=manifest), mock.patch.object(provider,'https_health',return_value=health), \
             mock.patch.object(provider,'run_bounded',return_value=result) as child, \
             mock.patch.dict(os.environ,{'DIGITALOCEAN_TOKEN':'fixture-never-pass','NODE_OPTIONS':'fixture-never-pass'}):
            receipt=provider.independent_readback(self.api,self.req,ROOT,'c'*64,config,self.receipts)
            self.assertTrue(child.call_args.args[0][1].endswith('tools/qikvrt_mesh_monitor_readback.mjs'))
            self.assertEqual(child.call_args.args[0][-1],'93.184.216.34')
            self.assertNotIn('DIGITALOCEAN_TOKEN',child.call_args.kwargs['env']); self.assertNotIn('NODE_OPTIONS',child.call_args.kwargs['env'])
            self.assertFalse(receipt['host_admission_verified']); self.assertFalse(receipt['effect_ack_done'])
            client['source_head']='e'*40; result.stdout=json.dumps(client)
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_PUBLIC_CLIENT_BINDING'):
                provider.independent_readback(self.api,self.req,ROOT,'c'*64,config,self.receipts)

    def test_cli_returns_first_unbound_control_plane_without_accessing_credentials(self):
        for name in provider.PRODUCTS:
            command=[sys.executable,'-B',str(ROOT/'tools/qikvrt_self_host.py'),'provider-inventory','--provider',name]
            env=dict(os.environ); env.pop(provider.TOKEN_ENV[name],None)
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,env=env,timeout=10)
            self.assertEqual(result.returncode,2)
            self.assertEqual(json.loads(result.stdout)['cause'],'HOLD_EXACT_PROVIDER_PRODUCT_AND_PRINCIPAL_BINDING_REQUIRED')


class TransportTests(unittest.TestCase):
    def api(self,opener):
        return provider.API('digitalocean','fixture-secret-do-not-print',{'product':'digitalocean-v2','principal_id':'fixture-principal','principal_evidence_sha256':'a'*64},opener)

    def test_pagination_covers_all_pages_and_refuses_duplicates_incomplete_metadata_and_limits(self):
        api=self.api(mock.Mock())
        replies=[{'droplets':[{'id':1}],'meta':{'total':2},'links':{'pages':{'next':'ignored-untrusted-url'}}},
                 {'droplets':[{'id':2}],'meta':{'total':2},'links':{}}]
        api.call=mock.Mock(side_effect=replies)
        self.assertEqual([v['id'] for v in api.collection('/droplets','droplets')],[1,2])
        self.assertTrue(api.call.call_args_list[1].args[0].endswith('page=2'))
        for replies in [[{'droplets':[]}], [{'droplets':[{'id':1}],'meta':{'total':2}},{'droplets':[],'meta':{'total':2}}],
                        [{'droplets':[{'id':1}],'meta':{'total':2}},{'droplets':[{'id':1}],'meta':{'total':2}}]]:
            api.call=mock.Mock(side_effect=replies)
            with self.assertRaises(ValueError): api.collection('/droplets','droplets')

    def test_fixed_origin_no_delete_no_redirect_no_credential_in_error(self):
        opener=mock.Mock(); api=self.api(opener)
        with self.assertRaises(ValueError): api.call('//evil.example/steal')
        with self.assertRaises(ValueError): api.call('/account/keys',{})
        error=urllib.error.HTTPError(api.base+'/droplets',403,'forbidden',{},io.BytesIO(b'Payment method required; fixture-secret-do-not-print'))
        opener.open.side_effect=error
        with self.assertRaisesRegex(provider.ProviderError,'PAYMENT_METHOD_REQUIRED') as raised: api.call('/droplets',{})
        self.assertNotIn('fixture-secret',str(raised.exception))
        provider.NoRedirect().redirect_request
        with self.assertRaisesRegex(ValueError,'REDIRECT_FORBIDDEN'): provider.NoRedirect().redirect_request(None,None,302,'',{},'https://evil.example')

    def test_no_fake_legacy_ionos_or_missing_product_is_admitted(self):
        with self.assertRaisesRegex(ValueError,'PRODUCT_AND_PRINCIPAL'):
            provider.API('ionos','fixture-only-token',{'product':'1and1-cloud-panel','principal_id':'42','principal_evidence_sha256':'a'*64})

    def test_public_ipv4_and_https_dns_health_source_fail_closed(self):
        api=FakeAPI(); req=request(api)
        observed={'state':'active','public_ipv4':['93.184.216.34']}
        for address in ['127.0.0.1','10.0.0.1','::1','192.0.2.1',None]:
            with self.assertRaises(ValueError): provider.ipv4(address)
        with mock.patch.object(socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))]):
            with self.assertRaisesRegex(ValueError,'DNS_PROVIDER_IPV4'): provider.https_health(req,observed)
        observed['state']='off'
        with self.assertRaisesRegex(ValueError,'NOT_RUNNING'): provider.https_health(req,observed)

    def test_ipv4_pinned_tls_preserves_sni_and_requires_fresh_exact_source_health(self):
        api=FakeAPI(); req=request(api); observed={'state':'active','public_ipv4':['93.184.216.34']}
        health={k:req[k] for k in ('source_repository','source_head','source_tree','node_id')}
        health.update(schema='qikvrt-monitor-binding/v1',health={'state':'HEALTHY'},observed_at=provider.timestamp())
        response=mock.Mock(status=200); response.read.return_value=provider.wire(health)
        connection=mock.Mock(); connection.getresponse.return_value=response
        context=mock.Mock()
        with mock.patch.object(socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))]), \
             mock.patch.object(socket,'create_connection',return_value=mock.Mock()) as connect, \
             mock.patch.object(provider.ssl,'create_default_context',return_value=context), \
             mock.patch.object(provider.http.client,'HTTPSConnection',return_value=connection):
            result=provider.https_health(req,observed)
            self.assertEqual(result['ipv4'],'93.184.216.34')
            self.assertEqual(connect.call_args.args[0],('93.184.216.34',443))
            self.assertEqual(context.wrap_socket.call_args.kwargs['server_hostname'],'native.example.org')
            health['source_tree']='e'*40; response.read.return_value=provider.wire(health)
            with self.assertRaisesRegex(ValueError,'HTTPS_SOURCE_OR_HEALTH'): provider.https_health(req,observed)

    def test_duplicate_json_and_nonfinite_values_refused(self):
        for data in [b'{"a":1,"a":2}',b'{"a":NaN}']:
            with self.assertRaises(ValueError): provider.decode(data)


class RepositoryIONOSReadonlyTests(unittest.TestCase):
    """Real request construction against a fake wire; never a live provider."""
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / 'receipts'
        self.directory.mkdir(mode=0o700)
        self.binding = {'product': 'ionos-cloud-v6', 'principal_id': '424242', 'principal_evidence_sha256': '1' * 64}
        self.binding_bytes = provider.wire(self.binding)
        self.environment = {'IONOS_TOKEN': 'fixture-ionos-token-never-live',
            'IONOS_BINDING_SECRET_NAME': 'EXISTING_FIXTURE_BINDING',
            'IONOS_BINDING_JSON': self.binding_bytes.decode(),
            'IONOS_BINDING_SHA256': provider.sha(self.binding_bytes)}
        self.subject = {'repository': 'ingolf-lohmann/qik-vrt', 'ref': 'refs/heads/main',
            'head': 'a' * 40, 'tree': 'b' * 40, 'run_id': '123', 'run_attempt': '1'}
        self.calls = []
        self.contracts = [{'properties': {'contractNumber': 424242, 'owner': 'PRIVATE_OWNER'}}]
        self.failure = None

    def open(self, request, timeout):
        self.calls.append(request)
        self.assertEqual(request.get_method(), 'GET')
        self.assertIsNone(request.data)
        self.assertEqual(dict((k.lower(), v) for k, v in request.header_items())['x-contract-number'], '424242')
        self.assertTrue(request.full_url.startswith(provider.PRODUCTS['ionos'][1] + '/'))
        if self.failure: raise self.failure
        path = request.full_url[len(provider.PRODUCTS['ionos'][1]):].split('&')[0]
        values = {
            '/datacenters?depth=1': {'items': [{'id': 'dc-fixture', 'properties': {'location': 'de/fra'}}]},
            '/datacenters/dc-fixture/servers?depth=3': {'items': [{'id': 'server-fixture',
                'properties': {'name': 'PRIVATE_RESOURCE_NAME', 'vmState': 'RUNNING', 'cores': 1, 'ram': 1024},
                'metadata': {'state': 'AVAILABLE'}, 'entities': {'nics': {'items': [{'properties': {'ips': ['93.184.216.34']}}]}}}]},
            '/datacenters/dc-fixture/lans?depth=1': {'items': [{'id': '1', 'properties': {'public': True}}]},
            '/contracts?depth=1': {'items': self.contracts, 'PRIVATE_PROVIDER_BODY': 'DO_NOT_PERSIST'},
            '/locations?depth=1': {'items': [{'id': 'de/fra'}]},
            '/templates?depth=1': {'items': []},
            '/images?depth=1': {'items': [{'id': 'image-fixture', 'name': 'PRIVATE_IMAGE_NAME'}]},
        }
        self.assertIn(path, values)
        class Response(io.BytesIO):
            status = 200
            def geturl(self): return request.full_url
        return Response(provider.wire(values[path]))

    def observe(self, environment=None):
        opener = mock.Mock(open=self.open)
        with mock.patch.dict(os.environ, self.environment if environment is None else environment, clear=True), \
                mock.patch.object(provider.urllib.request, 'build_opener', return_value=opener):
            return provider.repository_readonly(self.directory, self.subject)

    def test_missing_deliveries_name_every_binding_without_any_network(self):
        result = self.observe({})
        self.assertEqual(result['first_boundary'], 'HOLD_IONOS_READONLY_BINDING_UNAVAILABLE')
        self.assertEqual(len(result['missing_bindings']), 4)
        self.assertTrue(any('secrets.IONOS_TOKEN' in item for item in result['missing_bindings']))
        self.assertEqual(self.calls, [])
        self.assertEqual(provider.decode((self.directory / 'receipt.json').read_bytes()), result)

    def test_real_contract_and_original_independent_pin_are_required_before_network(self):
        for change in [{'principal_id': None}, {'principal_evidence_sha256': None}, {'product': None}]:
            with self.subTest(change=change):
                binding = dict(self.binding, **change)
                env = dict(self.environment, IONOS_BINDING_JSON=provider.wire(binding).decode(),
                    IONOS_BINDING_SHA256=provider.sha(provider.wire(binding)))
                result = self.observe(env)
                self.assertEqual(result['state'], 'HOLD')
                self.assertTrue(result['missing_bindings'])
                (self.directory / 'receipt.json').unlink()
        env = dict(self.environment, IONOS_BINDING_JSON=self.binding_bytes.decode() + '\n')
        self.assertEqual(self.observe(env)['first_boundary'], 'HOLD_IONOS_PROVIDER_BINDING_PIN_MISMATCH')
        self.assertEqual(self.calls, [])

    def test_wrong_source_or_branch_does_not_deliver_any_provider_request(self):
        self.subject['ref'] = 'refs/heads/candidate/unreviewed'
        result = self.observe()
        self.assertEqual(result['first_boundary'], 'HOLD_IONOS_EXACT_SOURCE_SUBJECT_REQUIRED')
        self.assertNotIn('subject', result)
        self.assertEqual(self.calls, [])

    def test_both_operations_fresh_readback_and_receipt_exclude_private_provider_bytes(self):
        result = self.observe()
        self.assertEqual(result['state'], 'INVENTORY_READ_ADMITTED_PENDING_REQUEST_BINDING')
        self.assertTrue(result['inventory_completed'] and result['classification_completed'])
        self.assertTrue(result['fresh_private_readback_verified'])
        self.assertFalse(result['provider_create_executed'] or result['payment_executed'] or result['terms_accepted'] or result['effect_ack_done'])
        self.assertEqual(result['inventory_metadata']['resources_count'], 1)
        self.assertEqual(result['inventory_metadata']['reads_count'], len(self.calls))
        self.assertEqual(len(self.calls), 7)
        persisted = (self.directory / 'receipt.json').read_text()
        for private in ['424242', self.environment['IONOS_TOKEN'], 'PRIVATE_OWNER', 'PRIVATE_PROVIDER_BODY',
                        'PRIVATE_RESOURCE_NAME', 'PRIVATE_IMAGE_NAME', 'server-fixture', 'dc-fixture', '93.184.216.34']:
            self.assertNotIn(private, persisted)
        self.assertEqual(provider.decode(persisted), result)
        self.assertEqual(list(self.directory.iterdir()), [self.directory / 'receipt.json'])
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [self.directory])
        self.assertEqual((self.directory / 'receipt.json').stat().st_mode & 0o777, 0o600)

    def test_wrong_duplicate_or_missing_provider_contract_never_admits(self):
        for contracts in [[], [{'properties': {'contractNumber': 999}}], self.contracts * 2, [{'properties': None}]]:
            with self.subTest(contracts=contracts):
                self.contracts = contracts
                result = self.observe()
                self.assertEqual(result['first_boundary'], 'HOLD_IONOS_CONTRACT_PRINCIPAL_UNCONFIRMED')
                self.assertFalse(result['classification_completed'])
                (self.directory / 'receipt.json').unlink()
        self.assertTrue(all(request.get_method() == 'GET' for request in self.calls))

    def test_http_failure_or_arbitrary_exception_never_leaks_provider_body_or_retries(self):
        for failure, expected in [
                (urllib.error.HTTPError('https://api.ionos.com/cloudapi/v6', 403, 'PRIVATE_MESSAGE', {}, io.BytesIO(b'PRIVATE_BODY')),
                 'HOLD_PROVIDER_PERMISSION'),
                (ValueError('PRIVATE_BODY_AND_TOKEN'), 'HOLD_IONOS_READONLY_EXECUTION_FAILED')]:
            with self.subTest(expected=expected):
                self.failure = failure
                before = len(self.calls)
                result = self.observe()
                self.assertEqual(result['first_boundary'], expected)
                self.assertEqual(len(self.calls) - before, 1)
                self.assertNotIn('PRIVATE', (self.directory / 'receipt.json').read_text())
                self.assertFalse(result['classification_completed'])
                self.assertEqual(list(Path(self.temporary.name).iterdir()), [self.directory])
                (self.directory / 'receipt.json').unlink()

    def test_readonly_capability_rejects_create_and_noninventory_paths_before_transport(self):
        api = provider.ReadOnlyIONOSAPI('ionos', self.environment['IONOS_TOKEN'], self.binding)
        with mock.patch.object(api.opener, 'open') as opened:
            for path, body in [('/datacenters/dc-fixture/servers', {}), ('/billing', None), ('/servers', None),
                               ('/contracts?depth=1', {}), ('//other.example', None)]:
                with self.subTest(path=path, body=body), self.assertRaises(ValueError): api.call(path, body)
            opened.assert_not_called()

    def test_inventory_changed_after_classification_refuses_fresh_readback_and_cleans_private_bytes(self):
        original = provider.execute
        def tamper(args, **kwargs):
            result = original(args, **kwargs)
            if args.operation == 'provider-classify': args.provider_inventory.write_bytes(b'PRIVATE_TAMPERED_BYTES')
            return result
        with mock.patch.object(provider, 'execute', side_effect=tamper):
            result = self.observe()
        self.assertEqual(result['first_boundary'], 'PROVIDER_INPUT_PIN_MISMATCH')
        self.assertTrue(result['inventory_completed'] and result['classification_completed'])
        self.assertFalse(result['fresh_private_readback_verified'])
        self.assertEqual(len(self.calls), 7)
        self.assertNotIn('PRIVATE', (self.directory / 'receipt.json').read_text())
        self.assertEqual(list(Path(self.temporary.name).iterdir()), [self.directory])


if __name__=='__main__': unittest.main()
