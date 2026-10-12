#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Actual archive GET and native-journal boundary regressions; no live Zenodo."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import pathlib
import tempfile
import unittest
import urllib.error
import zipfile
from unittest.mock import patch

from tools import qikvrt_batch003_remaining_archive_probe as probe
from tools import qikvrt_zenodo_publish as publisher

URL='https://zenodo.org/api/records/123456'
INPUT=probe.digest({'expected':'original bytes'})
HEAD='a'*40

class Response(io.BytesIO):
    status=200
    def __init__(self,data,url=URL):
        super().__init__(data)
        self.url=url
    def geturl(self):return self.url

class GitDataFixture:
    """Independent persistent Git-Data shape, including atomic create-only refs."""
    def __init__(self):
        self.tags={}
        self.refs={}
        self.calls=[]
        self.ambiguous=False
    def __call__(self,method,path,token,*,repository,payload=None,accept=(200,)):
        self.calls.append((method,path,payload))
        suffix=path.split('/git/',1)[1]
        if method=='GET' and suffix.startswith('matching-refs/'):
            prefix='refs/'+suffix.removeprefix('matching-refs/')
            return 200,[self.ref(k) for k in sorted(self.refs) if k.startswith(prefix)]
        if method=='GET' and suffix.startswith('ref/'):
            return 200,self.ref('refs/'+suffix.removeprefix('ref/'))
        if method=='GET' and suffix.startswith('tags/'):
            return 200,self.tags[suffix.removeprefix('tags/')]
        if method=='POST' and suffix=='tags':
            sha=hashlib.sha1(probe.canonical(payload)).hexdigest()
            self.tags[sha]={**payload,'sha':sha,'object':{'type':'commit','sha':payload['object']}}
            return 201,self.tags[sha]
        if method=='POST' and suffix=='refs':
            name=payload['ref']
            if name in self.refs:return 422,{}
            self.refs[name]=payload['sha']
            if self.ambiguous:
                self.ambiguous=False
                raise OSError('connection lost after native ref creation')
            return 201,self.ref(name)
        raise AssertionError((method,path))
    def ref(self,name):return {'ref':name,'object':{'type':'tag','sha':self.refs[name]}}

class ArchiveCausalJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.tmp.name)
        self.seed=self.root/'original.json'
        self.seed.write_text(json.dumps({'schema':probe.JOURNAL_SCHEMA,'original_failures':[]}))
        self.journal=probe.ArchiveJournal(self.root/'state',repository='',head=HEAD,seed=self.seed)
        self.env=patch.dict(os.environ,{'QIKVRT_ARCHIVE_RETRY_EVIDENCE_FILE':''})
        self.env.start()
    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()
    def fetch(self,opener,*,input_key=INPUT,url=URL):
        with patch.object(probe,'journal',return_value=self.journal),patch.object(probe.urllib.request,'urlopen',opener):
            return probe.get(url,'application/json',1024,input_key=input_key)
    def failure(self):return urllib.error.HTTPError(URL,504,'Gateway Time-out',{},None)
    def fail_once(self):
        with patch.object(probe.urllib.request,'urlopen',side_effect=self.failure()) as opener:
            with self.assertRaisesRegex(probe.E,'HTTP 504'):self.fetch(opener)
            self.assertEqual(opener.call_count,1)
    def retry(self,status=200,**extra):
        body=self.root/'independently-observed-response.data'
        body.write_bytes(b'independent provider response')
        value={'schema':'qikvrt_archive_get_retry_evidence_v1','kind':'EXTERNAL_HTTP_RESPONSE',
               'url':URL,'input_key':INPUT,'previous_error_key':probe.error_key(504),
               'http_status':status,'body_sha256':hashlib.sha256(b'independent provider response').hexdigest(),
               'source':'https://zenodo.org/records/123456','response_body_path':str(body),**extra}
        path=self.root/'retry.json'
        path.write_text(json.dumps(value))
        os.environ['QIKVRT_ARCHIVE_RETRY_EVIDENCE_FILE']=str(path)
        return path
    def history(self):
        resource=probe.digest({'url':URL,'accept':'application/json','limit':1024})
        return self.journal.history(resource)
    def test_repeated_http504_uses_one_get_and_preserves_original_failure(self):
        self.fail_once()
        original=probe.canonical(self.history()[0])
        restarted=probe.ArchiveJournal(self.root/'state',repository='',head='b'*40,seed=self.seed)
        self.journal=restarted
        with patch.object(probe.urllib.request,'urlopen') as opener:
            for _ in range(5):
                with self.assertRaisesRegex(probe.E,'NOOP'):self.fetch(opener)
            opener.assert_not_called()
        self.assertEqual(probe.canonical(self.history()[0]),original)
        observation=json.loads((self.root/'state/OBSERVATION.json').read_bytes())
        self.assertEqual(observation['external_get_count'],0)
        self.assertFalse(observation['effect_ack_done'])
    def test_same_504_with_new_clock_body_or_source_is_not_a_new_cause(self):
        self.fail_once()
        self.retry(504,observed_at='2099-01-01T00:00:00Z',source='https://example.com/new-log')
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'UNCHANGED_EXTERNAL_HTTP_STATUS'):self.fetch(opener)
            opener.assert_not_called()
    def test_new_external_response_admits_one_attempt_and_retains_first_failure(self):
        self.fail_once()
        original=probe.canonical(self.history()[0])
        self.retry()
        with patch.object(probe.urllib.request,'urlopen',side_effect=self.failure()) as opener:
            with self.assertRaises(probe.E):self.fetch(opener)
            with self.assertRaisesRegex(probe.E,'ALREADY_CONSUMED'):self.fetch(opener)
            self.assertEqual(opener.call_count,1)
        self.assertEqual(probe.canonical(self.history()[0]),original)
        self.assertEqual(len(self.history()),2)
    def test_changed_evidence_timestamp_does_not_reconsume_causal_grant(self):
        self.fail_once()
        path=self.retry()
        with patch.object(probe.urllib.request,'urlopen',side_effect=self.failure()) as opener:
            with self.assertRaises(probe.E):self.fetch(opener)
            v=json.loads(path.read_text());v['observed_at']='2100-01-01T00:00:00Z';v['source']='https://example.com/another-source'
            path.write_text(json.dumps(v))
            with self.assertRaisesRegex(probe.E,'ALREADY_CONSUMED'):self.fetch(opener)
            self.assertEqual(opener.call_count,1)
    def test_successful_resumption_returns_real_response_bytes_without_scientific_claims(self):
        self.fail_once()
        self.retry()
        with patch.object(probe.urllib.request,'urlopen',return_value=Response(b'{"id":123456}')) as opener:
            self.assertEqual(self.fetch(opener),b'{"id":123456}')
            self.assertEqual(opener.call_count,1)
        result=self.history()[-1]['result']
        self.assertEqual(result['state'],'success')
        self.assertEqual(result['response']['sha256'],hashlib.sha256(b'{"id":123456}').hexdigest())
        for key in ('pass','final_pass','effect_ack_done'):self.assertIs(result[key],False)
    def test_changed_expected_input_can_resume_once_but_old_failure_cannot_be_bypassed(self):
        self.fail_once()
        changed=probe.digest({'expected':'changed bytes'})
        with patch.object(probe.urllib.request,'urlopen',side_effect=self.failure()) as opener:
            with self.assertRaises(probe.E):self.fetch(opener,input_key=changed)
            with self.assertRaisesRegex(probe.E,'NOOP'):self.fetch(opener,input_key=changed)
            with self.assertRaisesRegex(probe.E,'NOOP'):self.fetch(opener,input_key=INPUT)
            self.assertEqual(opener.call_count,1)
    def test_wrong_original_error_input_or_url_cannot_authorize_retry(self):
        self.fail_once()
        for change in ({'previous_error_key':'0'*64},{'input_key':'0'*64},{'url':URL+'/other'}):
            self.retry(**change)
            with patch.object(probe.urllib.request,'urlopen') as opener:
                with self.assertRaisesRegex(probe.E,'NOT_BOUND'):self.fetch(opener)
                opener.assert_not_called()
    def test_known_two_workflow_failures_are_suppressed_without_any_new_zenodo_get(self):
        self.journal=probe.ArchiveJournal(self.root/'state',repository='',head=HEAD)
        s=probe.SUBJECTS[0];r=s['records'][0]
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with patch.object(probe,'journal',return_value=self.journal):
                with self.assertRaisesRegex(probe.E,'NOOP'):probe.record(s,r,{})
            opener.assert_not_called()
        seed=json.loads(probe.JOURNAL_SEED.read_bytes())
        self.assertEqual({x['run_id'] for x in seed['original_failures'][0]['original_logs']},{38226630154,38226629752})
        for source in seed['original_failures'][0]['original_logs']:
            raw=(probe.ROOT/source['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),source['sha256'])
            self.assertIn(source['observed_error_line'].encode(),raw)
    def test_no_remote_or_local_journal_reset_on_missing_original_evidence(self):
        self.seed.unlink()
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'JOURNAL_MISSING'):self.fetch(opener)
            opener.assert_not_called()
    def test_symlink_journal_is_rejected_before_get(self):
        (self.root/'linked').symlink_to(self.root, target_is_directory=True)
        self.journal=probe.ArchiveJournal(self.root/'linked/state',repository='',head=HEAD,seed=self.seed)
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'SYMLINK'):self.fetch(opener)
            opener.assert_not_called()
    def test_public_byte_sha256_boundary_rejects_sha_only_drift_after_successful_get(self):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:z.writestr('article.md','A bounded technical source.')
        raw=buf.getvalue();pins=probe.dig(raw)
        rec={'id':123456,'doi':'10.5281/zenodo.123456','name':'source.zip'}
        subject={'subject_id':'TEST','records':[rec],'file':{k:pins[k] for k in ('bytes','md5','sha256')}}
        meta={'id':rec['id'],'doi':rec['doi'],'files':[{'key':rec['name'],'size':pins['bytes'],'checksum':'md5:'+pins['md5'],'links':{'content':'https://zenodo.org/api/records/123456/files/source.zip/content'}}]}
        for expected in (pins['sha256'],'0'*64):
            subject['file']['sha256']=expected
            with patch.object(probe,'get',side_effect=[json.dumps(meta).encode(),raw]):
                if expected==pins['sha256']:
                    cache={};observed=probe.record(subject,rec,cache)
                    self.assertEqual(observed['sha256'],pins['sha256'])
                    self.assertIn(pins['sha256'],cache)
                else:
                    with self.assertRaisesRegex(probe.E,'exact public byte mismatch 123456:sha256'):probe.record(subject,rec,{})
    def test_existing_zip_safety_boundary_is_unchanged(self):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:z.writestr('../escape.txt','bad')
        with self.assertRaisesRegex(probe.E,'unsafe ZIP path'):
            probe.inspect_zip(buf.getvalue(),'archive.zip',0,{'entries':0,'bytes':0},[])
    def test_download_bound_and_origin_still_block(self):
        with patch.object(probe.urllib.request,'urlopen',return_value=Response(b'x'*1025)) as opener:
            with self.assertRaises(probe.E):self.fetch(opener)
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'outside public Zenodo'):self.fetch(opener,url='https://example.com/archive.zip')
            opener.assert_not_called()
    def test_independent_workflows_share_remote_failed_attempt_and_original_bytes(self):
        api=GitDataFixture()
        first=probe.ArchiveJournal(self.root/'one',repository='ingolf-lohmann/qik-vrt',token='unused-fixture',head=HEAD,api=api,seed=self.seed)
        second=probe.ArchiveJournal(self.root/'two',repository='ingolf-lohmann/qik-vrt',token='unused-fixture',head='b'*40,api=api,seed=self.seed)
        self.journal=first;self.fail_once()
        original=copy.deepcopy(api.tags)
        self.journal=second
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'NOOP'):self.fetch(opener)
            opener.assert_not_called()
        self.assertEqual(api.tags,original)
        self.assertEqual(len(api.refs),2)
        self.retry()
        with patch.object(probe.urllib.request,'urlopen',return_value=Response(b'recovered')) as opener:
            self.assertEqual(self.fetch(opener),b'recovered')
        self.assertEqual(len(api.refs),4)
        for sha,value in original.items():self.assertEqual(api.tags[sha],value)
    def test_concurrent_native_slot_rejection_never_reaches_get(self):
        api=GitDataFixture()
        first=probe.ArchiveJournal(self.root/'one',repository='ingolf-lohmann/qik-vrt',token='fixture',head=HEAD,api=api,seed=self.seed)
        second=probe.ArchiveJournal(self.root/'two',repository='ingolf-lohmann/qik-vrt',token='fixture',head=HEAD,api=api,seed=self.seed)
        self.journal=first;self.fail_once()
        self.journal=second
        # Force the stale observation that a genuinely concurrent runner can see.
        with patch.object(second,'history',return_value=[]),patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'SLOT_ALREADY_RESERVED'):self.fetch(opener)
            opener.assert_not_called()
    def test_ambiguous_native_reservation_and_unresolved_predecessor_are_get_only(self):
        api=GitDataFixture();api.ambiguous=True
        self.journal=probe.ArchiveJournal(self.root/'one',repository='ingolf-lohmann/qik-vrt',token='fixture',head=HEAD,api=api,seed=self.seed)
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaises(OSError):self.fetch(opener)
            opener.assert_not_called()
        self.journal=probe.ArchiveJournal(self.root/'two',repository='ingolf-lohmann/qik-vrt',token='fixture',head=HEAD,api=api,seed=self.seed)
        posts=len([x for x in api.calls if x[0]=='POST'])
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'NOOP'):self.fetch(opener)
            opener.assert_not_called()
        self.assertEqual(posts,len([x for x in api.calls if x[0]=='POST']))
    def test_shared_rest_transport_keeps_publication_default_and_explicit_repository_pin(self):
        response=Response(b'[]','https://api.github.com/repos/ingolf-lohmann/qik-vrt/git/matching-refs/tags/qikvrt-archive-get/')
        with patch.object(publisher.urllib.request,'build_opener') as build:
            build.return_value.open.return_value=response
            self.assertEqual(publisher._github_api_request('GET','/repos/ingolf-lohmann/qik-vrt/git/matching-refs/tags/qikvrt-archive-get/','t'*24,repository='ingolf-lohmann/qik-vrt'),(200,[]))
            request=build.return_value.open.call_args.args[0]
            self.assertEqual(request.get_method(),'GET')
            self.assertEqual(request.get_header('Authorization'),'Bearer '+'t'*24)
        with self.assertRaises(publisher.zenodo.ZenodoError):
            publisher._github_api_request('GET','/repos/ingolf-lohmann/qik-vrt/git/ref/tags/wrong','t'*24)
    def test_digest_only_or_drifted_response_evidence_never_opens_the_get_gate(self):
        self.fail_once()
        path=self.retry()
        v=json.loads(path.read_text());del v['response_body_path'];path.write_text(json.dumps(v))
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'RESPONSE_BYTES_MISSING'):self.fetch(opener)
            opener.assert_not_called()
        path=self.retry()
        v=json.loads(path.read_text());v['body_sha256']='f'*64;path.write_text(json.dumps(v))
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'RESPONSE_DIGEST_DRIFT'):self.fetch(opener)
            opener.assert_not_called()
    def test_journal_capacity_fails_closed_without_eviction_or_get(self):
        self.fail_once()
        before=probe.canonical(self.history())
        with patch.object(probe,'MAX_ATTEMPTS',1),patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'ATTEMPT_BOUND'):self.fetch(opener,input_key='f'*64)
            opener.assert_not_called()
        self.assertEqual(probe.canonical(self.history()),before)
    def test_hosted_call_without_shared_binding_does_not_fall_back_to_a_new_local_attempt(self):
        with patch.object(probe,'_JOURNAL',None),patch.dict(os.environ,{'GITHUB_ACTIONS':'true','QIKVRT_ARCHIVE_JOURNAL_REPOSITORY':''}),patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'SHARED_JOURNAL_BINDING_MISSING'):probe.get(URL,'application/json',1024)
            opener.assert_not_called()

if __name__=='__main__':unittest.main()
