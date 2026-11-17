#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Actual archive GET and native-journal boundary regressions; no live Zenodo."""
from __future__ import annotations

import copy
import contextlib
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
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
    def test_recovery_allows_fresh_verification_but_old_response_cannot_regrant_a_later_failure(self):
        self.fail_once()
        path=self.retry()
        with patch.object(probe.urllib.request,'urlopen',return_value=Response(b'recovered')) as opener:
            self.assertEqual(self.fetch(opener),b'recovered')
            self.assertEqual(opener.call_count,1)
        os.environ['QIKVRT_ARCHIVE_RETRY_EVIDENCE_FILE']=''
        with patch.object(probe.urllib.request,'urlopen',side_effect=self.failure()) as opener:
            with self.assertRaisesRegex(probe.E,'HTTP 504'):self.fetch(opener)
            self.assertEqual(opener.call_count,1)
        os.environ['QIKVRT_ARCHIVE_RETRY_EVIDENCE_FILE']=str(path)
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'ALREADY_CONSUMED'):self.fetch(opener)
            opener.assert_not_called()
        self.assertEqual(len(self.history()),3)
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
    def test_preflight_retains_shared_failure_without_get_or_remote_write(self):
        api=GitDataFixture()
        self.journal=probe.ArchiveJournal(self.root/'one',repository='ingolf-lohmann/qik-vrt',token='fixture',head=HEAD,api=api,seed=self.seed)
        self.fail_once()
        tags=copy.deepcopy(api.tags);refs=copy.deepcopy(api.refs);api.calls.clear()
        successor=probe.ArchiveJournal(self.root/'two',repository='ingolf-lohmann/qik-vrt',token='fixture',head='b'*40,api=api,seed=self.seed)
        with patch.object(probe.urllib.request,'urlopen') as opener:
            result=successor.preflight([(URL,'application/json',1024,INPUT)])
            opener.assert_not_called()
        self.assertEqual(result['state'],'NOOP')
        self.assertFalse(result['materialization_admitted'])
        self.assertEqual(result['external_get_count'],0)
        self.assertEqual(result['requests'][0]['attempts'][0]['result']['http_status'],504)
        self.assertEqual(api.tags,tags);self.assertEqual(api.refs,refs)
        self.assertTrue(all(call[0]=='GET' for call in api.calls))
        self.assertEqual(json.loads((successor.root/'OBSERVATION.json').read_bytes()),result)
    def test_preflight_ready_does_not_replace_late_shared_fence(self):
        request=(URL,'application/json',1024,INPUT)
        ready=self.journal.preflight([request])
        self.assertEqual(ready['state'],'READY')
        self.assertTrue(ready['materialization_admitted'])
        self.assertFalse(ready['new_archive_readback'])
        self.fail_once()
        with patch.object(probe.urllib.request,'urlopen') as opener:
            with self.assertRaisesRegex(probe.E,'NOOP'):self.fetch(opener)
            opener.assert_not_called()
    def test_preflight_does_not_hide_invalid_retry_or_journal_drift(self):
        self.fail_once();request=(URL,'application/json',1024,INPUT)
        with self.assertRaisesRegex(probe.E,'NOT_BOUND'):
            self.journal.preflight([request],{'schema':'invalid'})
        with patch.object(self.journal,'history',side_effect=probe.E('ARCHIVE_JOURNAL_CHAIN_DRIFT')):
            with self.assertRaisesRegex(probe.E,'CHAIN_DRIFT'):self.journal.preflight([request])
    def test_preflight_qualified_recovery_and_unchanged_status_reuse_admit(self):
        self.fail_once();request=(URL,'application/json',1024,INPUT)
        self.retry(http_status=504)
        unchanged=self.journal.preflight([request],probe.retry_evidence())
        self.assertEqual(unchanged['reason'],'NOOP_UNCHANGED_EXTERNAL_HTTP_STATUS')
        self.retry()
        ready=self.journal.preflight([request],probe.retry_evidence())
        self.assertEqual(ready['state'],'READY')
        self.assertEqual(len(self.history()),1)
    def test_materialize_cli_noop_never_enters_archive_work_or_changes_sources(self):
        from tools import qikvrt_content_disposition_batch_003_remaining_archives as disposition
        journal=probe.ArchiveJournal(self.root/'state',repository='',head=HEAD)
        original=probe.JOURNAL_SEED.read_bytes()
        with patch.object(probe,'journal',return_value=journal),patch.object(probe.urllib.request,'urlopen') as opener,patch.object(disposition,'materialize') as work,patch.object(disposition,'verify_materialized') as verify,patch.object(sys,'argv',['disposition','--materialize','--json']),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(disposition.main(),0)
        result=json.loads(output.getvalue())
        self.assertEqual(result['state'],'NOOP')
        for key in ('pass','final_pass','effect_ack_done','zenodo_mutation_authorized','proof_corpus_published_on_zenodo','materialization_started','new_archive_readback'):
            self.assertIs(result[key],False)
        work.assert_not_called();verify.assert_not_called();opener.assert_not_called()
        self.assertEqual(probe.JOURNAL_SEED.read_bytes(),original)
    def test_materialize_cli_reports_new_probe_error_as_failure(self):
        from tools import qikvrt_content_disposition_batch_003_remaining_archives as disposition
        with patch.object(probe,'materialization_preflight',side_effect=probe.E('ARCHIVE_JOURNAL_CHAIN_DRIFT')),patch.object(sys,'argv',['disposition','--materialize']),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(disposition.main(),2)
        result=json.loads(output.getvalue())
        self.assertEqual(result['state'],'BLOCK')
        self.assertEqual(result['reason'],'ARCHIVE_JOURNAL_CHAIN_DRIFT')
    def test_materialize_cli_new_failure_after_admission_remains_failure(self):
        from tools import qikvrt_content_disposition_batch_003_remaining_archives as disposition
        with patch.object(probe,'materialization_preflight',return_value={'materialization_admitted':True}),patch.object(disposition,'materialize',side_effect=probe.E('GET failed: HTTP 502')),patch.object(sys,'argv',['disposition','--materialize']),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(disposition.main(),2)
        self.assertEqual(json.loads(output.getvalue())['state'],'BLOCK')
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
        self.assertEqual(publisher.PRODUCTION_REPOSITORY,'ingolf-lohmann/qik-vrt')
        path='/repos/Goldkelch/qik-vrt/git/matching-refs/tags/qikvrt-archive-get/'
        response=Response(b'[]','https://api.github.com'+path)
        with patch.object(publisher.urllib.request,'build_opener') as build:
            build.return_value.open.return_value=response
            self.assertEqual(publisher._github_api_request('GET',path,'t'*24,repository='Goldkelch/qik-vrt'),(200,[]))
            request=build.return_value.open.call_args.args[0]
            self.assertEqual(request.get_method(),'GET')
            self.assertEqual(request.get_header('Authorization'),'Bearer '+'t'*24)
        with patch.object(publisher.urllib.request,'build_opener') as build:
            with self.assertRaises(publisher.zenodo.ZenodoError):
                publisher._github_api_request('GET',path,'t'*24)
            build.assert_not_called()
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

class ArchiveWorkflowContinuationTests(unittest.TestCase):
    """Execute existing shell steps; model only their bounded Actions conditions.

    Status-function semantics: https://docs.github.com/en/actions/reference/
    workflows-and-actions/expressions#status-check-functions
    Native exact-head job/step readback remains a separate execution witness.
    """
    WORKFLOWS = (
        probe.ROOT / '.github/workflows/qikvrt_batch04_integrity.yml',
        probe.ROOT / '.github/workflows/qikvrt_batch003_remaining_disposition.yml',
    )
    LOCAL_IDS = ('offline_disposition', 'repository_integrity', 'repository_gates')

    @staticmethod
    def steps(path):
        text = path.read_text(encoding='utf-8')
        starts = list(re.finditer(r'^      - ', text, re.M))
        result = {}
        for index, match in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
            block = text[match.start():end]
            identity = re.search(r'^        id: ([a-z_]+)$', block, re.M)
            name = block.splitlines()[0].removeprefix('      - name: ')
            result[identity.group(1) if identity else name] = block
        return result

    @staticmethod
    def condition(block):
        lines = block.splitlines()
        for index, line in enumerate(lines):
            if line.startswith('        if: '):
                value = line.removeprefix('        if: ')
                if value == '>-':
                    values = []
                    for following in lines[index + 1:]:
                        if not following.startswith('          '):
                            break
                        values.append(following.strip())
                    value = ' '.join(values)
                return value.removeprefix('${{').removesuffix('}}').strip()
        return 'success()'

    @classmethod
    def admitted(cls, block, outcomes, *, cancelled=False, archive_admitted=True):
        expression = cls.condition(block)
        success = not cancelled and not any(x == 'failure' for x in outcomes.values())
        if not re.search(r'\b(?:success|failure|always|cancelled)\(\)', expression) and not success:
            return False  # GitHub's implicit success() is the original defect.
        values = []
        for clause in expression.split(' && '):
            if clause == '!cancelled()':
                values.append(not cancelled)
            elif clause == 'always()':
                values.append(True)
            elif clause == 'success()':
                values.append(success)
            elif clause == "steps.archive_preflight.outputs.admitted == 'true'":
                values.append(archive_admitted is True)
            else:
                match = re.fullmatch(r"steps\.([a-z_]+)\.outcome == 'success'", clause)
                if match is None:
                    raise AssertionError('Unmodelled workflow condition: ' + clause)
                values.append(outcomes.get(match.group(1)) == 'success')
        return all(values)

    @staticmethod
    def shell(block):
        lines = block.split('        run: |\n', 1)[1].splitlines()
        body = []
        for line in lines:
            if line and not line.startswith('          '):
                break
            body.append(line[10:] if line else '')
        return '\n'.join(body) + '\n'

    def outcomes(self, steps):
        return {key: 'success' for key in ('checkout', 'target_binding', 'python') if key in steps}

    def run_shell(self, block, root, *, real_python=False, **exits):
        binaries = root / 'bin'
        binaries.mkdir(exist_ok=True)
        if real_python:
            python = f'#!{sys.executable}\n' + textwrap.dedent('''\
                import os, runpy, sys, urllib.request
                sys.path.insert(0, os.getcwd())
                def no_network(*args, **kwargs):
                    raise AssertionError('unexpected network in offline/NOOP regression')
                urllib.request.urlopen = no_network
                args = sys.argv[1:]
                if args[0] == '-B':
                    args.pop(0)
                if args[0] == '-m':
                    sys.argv = args[1:]
                    runpy.run_module(args[1], run_name='__main__')
                elif args[0] == '-':
                    sys.argv = args
                    exec(sys.stdin.read(), {'__name__': '__main__'})
                else:
                    sys.argv = args
                    runpy.run_path(args[0], run_name='__main__')
            ''')
        else:
            python = '''#!/bin/sh
printf 'python3 %s\n' "$*" >> "$CALLS"
case "$*" in
  *qikvrt_integrity.py*generate*) exit "$GENERATE_EXIT" ;;
  *qikvrt_integrity.py*verify*) exit "$VERIFY_EXIT" ;;
  *) exit "$OFFLINE_EXIT" ;;
esac
'''
        for name, source in (
            ('python3', python),
            ('make', '#!/bin/sh\nprintf "make %s\\n" "$*" >> "$CALLS"\nexit "$MAKE_EXIT"\n'),
        ):
            path = binaries / name
            path.write_text(source, encoding='utf-8')
            path.chmod(0o700)
        env = dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ['PATH'],
                   RUNNER_TEMP=str(root), CALLS=str(root / 'calls.log'),
                   GENERATE_EXIT='0', VERIFY_EXIT='0', OFFLINE_EXIT='0', MAKE_EXIT='0',
                   GITHUB_ACTIONS='false', QIKVRT_ARCHIVE_JOURNAL_REPOSITORY='',
                   QIKVRT_GITHUB_TOKEN='', QIKVRT_ARCHIVE_SOURCE_HEAD=HEAD,
                   QIKVRT_ARCHIVE_JOURNAL_DIR=str(root / 'journal'),
                   GITHUB_OUTPUT=str(root / 'github-output'),
                   QIKVRT_ARCHIVE_RETRY_EVIDENCE_FILE='')
        env.update({key: str(value) for key, value in exits.items()})
        return subprocess.run(['bash', '-c', self.shell(block)], cwd=probe.ROOT,
                              env=env, text=True, capture_output=True, timeout=45)

    def test_noop_runs_local_checks_but_never_admits_persistence(self):
        for path in self.WORKFLOWS:
            with self.subTest(workflow=path.name):
                steps = self.steps(path)
                outcomes = self.outcomes(steps)
                outcomes['archive_materialization'] = 'failure'
                archive = steps['archive_materialization']
                self.assertNotIn('continue-on-error:', archive)
                self.assertNotRegex(self.shell(archive), r'\|\|\s*(?:true|:)')
                for identity in self.LOCAL_IDS:
                    self.assertTrue(self.admitted(steps[identity], outcomes))
                    outcomes[identity] = 'success'
                persistence = next(block for name, block in steps.items()
                                   if name in ('Commit materialized repository evidence', 'Persist exact evidence head'))
                self.assertFalse(self.admitted(persistence, outcomes))
                self.assertIn('failure', outcomes.values())
                # Negative control: the predecessor's default condition skips.
                self.assertFalse(self.admitted('      - name: predecessor\n', outcomes))
                outcomes['archive_materialization'] = 'success'
                self.assertTrue(self.admitted(persistence, outcomes))
                outcomes['archive_materialization'] = 'skipped'
                self.assertFalse(self.admitted(archive,outcomes,archive_admitted=False))
                self.assertFalse(self.admitted(persistence,outcomes,archive_admitted=False))
                for identity in self.LOCAL_IDS:
                    self.assertTrue(self.admitted(steps[identity],outcomes,archive_admitted=False))

    def test_missing_prerequisite_or_cancellation_blocks_local_execution(self):
        for path in self.WORKFLOWS:
            steps = self.steps(path)
            ready = self.outcomes(steps)
            for identity in self.LOCAL_IDS:
                for required in ready:
                    for outcome in ('failure', 'skipped', 'cancelled', '', 'unknown'):
                        with self.subTest(workflow=path.name, gate=identity, required=required, outcome=outcome):
                            self.assertFalse(self.admitted(steps[identity], {**ready, required: outcome}))
                self.assertFalse(self.admitted(steps[identity], ready, cancelled=True))

    def test_other_local_failure_does_not_skip_independent_integrity_or_regressions(self):
        for path in self.WORKFLOWS:
            steps = self.steps(path)
            outcomes = {**self.outcomes(steps), 'archive_materialization': 'failure',
                        'offline_disposition': 'failure'}
            self.assertTrue(self.admitted(steps['repository_integrity'], outcomes))
            outcomes['repository_integrity'] = 'failure'
            self.assertTrue(self.admitted(steps['repository_gates'], outcomes))

    def test_real_preflight_noop_preserves_original_evidence_and_skips_work(self):
        original_paths = [probe.JOURNAL_SEED]
        seed = json.loads(probe.JOURNAL_SEED.read_bytes())
        original_paths.extend(probe.ROOT / row['path'] for failure in seed['original_failures']
                              for row in failure['original_logs'])
        original = {path: path.read_bytes() for path in original_paths}
        for path in self.WORKFLOWS:
            steps = self.steps(path)
            with tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                result = self.run_shell(steps['archive_preflight'], root, real_python=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('NOOP_UNCHANGED_ZENODO_FAILURE_OR_UNRESOLVED_GET', result.stdout + result.stderr)
                self.assertEqual((root/'github-output').read_text(),'admitted=false\n')
                self.assertFalse(self.admitted(steps['archive_materialization'],self.outcomes(steps),archive_admitted=False))
                observed = json.loads((root / 'journal/OBSERVATION.json').read_bytes())
                self.assertEqual(observed['external_get_count'], 0)
                self.assertIs(observed['effect_ack_done'], False)
        self.assertEqual(original, {path: path.read_bytes() for path in original})

    def test_real_offline_checks_preserve_archive_journal(self):
        for path in self.WORKFLOWS:
            steps = self.steps(path)
            with tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                admitted = self.run_shell(steps['archive_preflight'], root, real_python=True)
                self.assertEqual(admitted.returncode,0,admitted.stdout+admitted.stderr)
                journal_before = {p: p.read_bytes() for p in (root / 'journal').rglob('*') if p.is_file()}
                checked = self.run_shell(steps['offline_disposition'], root, real_python=True)
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
                for key in ('pass', 'final_pass', 'effect_ack_done',
                            'zenodo_mutation_authorized', 'proof_corpus_published_on_zenodo'):
                    self.assertIn('"' + key + '": false', checked.stdout)
                self.assertEqual(journal_before, {p: p.read_bytes() for p in (root / 'journal').rglob('*') if p.is_file()})

    def test_local_shell_failures_propagate_without_status_rewrite(self):
        cases = (('offline_disposition', 'OFFLINE_EXIT', 17),
                 ('repository_integrity', 'GENERATE_EXIT', 19),
                 ('repository_integrity', 'VERIFY_EXIT', 23),
                 ('repository_gates', 'MAKE_EXIT', 29))
        for path in self.WORKFLOWS:
            steps = self.steps(path)
            for identity, variable, code in cases:
                with self.subTest(workflow=path.name, gate=identity, failure=variable):
                    with tempfile.TemporaryDirectory() as tmp:
                        root = pathlib.Path(tmp)
                        result = self.run_shell(steps[identity], root, **{variable: code})
                        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                        if variable in ('GENERATE_EXIT', 'MAKE_EXIT'):
                            self.assertNotIn('qikvrt_integrity.py verify', (root / 'calls.log').read_text())

    def test_diagnostics_remain_always_and_checkout_is_exact_source_bound(self):
        for path in self.WORKFLOWS:
            steps = self.steps(path)
            diagnostics = steps['Preserve archive causal diagnostics even when access is blocked']
            self.assertTrue(self.admitted(diagnostics, {'checkout': 'failure'}, cancelled=True))
            self.assertIn('path: .qikvrt/runtime/archive-get-journal/**', diagnostics)
            self.assertIn('include-hidden-files: true', diagnostics)
            checkout = steps['checkout']
            source = 'EXPECTED_HEAD' if path.name == 'qikvrt_batch04_integrity.yml' else 'QIKVRT_ARCHIVE_SOURCE_HEAD'
            self.assertIn('ref: ${{ env.' + source + ' }}', checkout)


if __name__=='__main__':unittest.main()
