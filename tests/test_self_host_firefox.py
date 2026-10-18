# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Actual immutable candidate export + Firefox/X11/VNC/WebSocket runtime.

No provider network, no borrowed production profile, no deployed/public claim.
Run only in the declared Firefox dependency carrier. Missing tools are errors.
"""
from __future__ import annotations
import base64
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from tests.test_self_host_temdd import NativeStandaloneTests
from tests.test_self_host import host, ROOT


class FirefoxAMOUnlistedTests(unittest.TestCase):
    """Real six-file Git input; mocked AMO HTTP is never Mozilla signature proof."""
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.root = Path(cls.fixture.name) / 'source'; cls.root.mkdir()
        cls.names = ('manifest.json','background.js','content.js','options.html','options.js','terminal.css')
        for relative in [*("browser/firefox/qikvrt-terminal/" + name for name in cls.names),
                'policy/CANONICAL_UPSTREAM_REMOTE_V1.json']:
            path = cls.root / relative; path.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/relative,path)
        (cls.root/'browser/firefox/qikvrt-terminal/README.md').write_text('excluded documentation')
        (cls.root/'personal').mkdir();(cls.root/'personal/private.txt').write_text('must never be uploaded')
        def git(*args):
            return subprocess.check_output(['git','-C',str(cls.root),*args],stderr=subprocess.DEVNULL).decode().strip()
        git('init');git('add','.')
        git('-c','user.name=Local fixture','-c','user.email=fixture@example.invalid','commit','-m','local test fixture')
        cls.head=git('rev-parse','HEAD');cls.tree=git('rev-parse','HEAD^{tree}')

    @classmethod
    def tearDownClass(cls): cls.fixture.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name)/'output';self.state=Path(self.temp.name)/'state'
        from unittest import mock
        self.mock=mock
        self.env={'WEB_EXT_API_KEY':'test-only-issuer','WEB_EXT_API_SECRET':'test-only-secret-32-characters-long'}
        self.environment=mock.patch.dict(os.environ,self.env,clear=True);self.environment.start()
        self.addCleanup(self.environment.stop)

    def invoke(self,submit=True):
        return host.firefox_amo_unlisted(self.root,self.output,self.head,self.tree,self.state,submit)

    def signed(self,changed=False,extra=None):
        import io,zipfile
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            def write(name,raw):
                # Separate mocked AMO responses must bind the same fixture
                # bytes even when their creation crosses a ZIP clock tick.
                info=zipfile.ZipInfo(name,(2000,1,1,0,0,0))
                info.external_attr=0o100644 << 16
                archive.writestr(info,raw)
            for name in self.names:
                raw=(self.root/'browser/firefox/qikvrt-terminal'/name).read_bytes()
                write(name,raw+b'wrong source' if changed and name=='content.js' else raw)
            write('META-INF/mozilla.rsa',b'fixture only; not a Mozilla signature')
            if extra:write(extra,b'foreign or duplicate bytes')
        return stream.getvalue()

    def response(self,signed=None,**changes):
        raw=signed if signed is not None else self.signed()
        value={'guid':'qikvrt-ai-terminal@goldkelch.local','version':'1.0.0',
            'processed':True,'valid':True,'reviewed':True,'passed_review':True,
            'files':[{'signed':True,'hash':'sha256:'+host.digest(raw),
                'download_url':'https://addons.mozilla.org/api/v4/downloads/file/123/standard.xpi'}]}
        value.update(changes);return json.dumps(value).encode()

    def test_exact_deterministic_six_committed_files_and_no_personal_or_readme(self):
        import io,zipfile
        first,binding=host.firefox_amo_input(self.root,self.head,self.tree)
        self.assertEqual(first,host.firefox_amo_input(self.root,self.head,self.tree)[0])
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertCountEqual(archive.namelist(),self.names)
        self.assertEqual(len(binding['source_files']),6);self.assertEqual(binding['strict_min_version'],'158.0')
        self.assertEqual(binding['source_head'],self.head)

    def test_wrong_head_tree_and_dirty_source_fail_before_http(self):
        with self.assertRaisesRegex(ValueError,'EXACT_HEAD_TREE'):
            host.firefox_amo_input(self.root,'0'*40,self.tree)
        path=self.root/'browser/firefox/qikvrt-terminal/content.js';raw=path.read_bytes()
        try:
            path.write_bytes(raw+b'changed')
            with self.mock.patch.object(host,'firefox_amo_transport',side_effect=AssertionError('no HTTP')):
                with self.assertRaisesRegex(ValueError,'DIRTY_STANDARD'):self.invoke()
        finally:path.write_bytes(raw)

    def test_missing_pair_or_no_submission_request_has_zero_http_effects(self):
        with self.mock.patch.object(host,'firefox_amo_transport',side_effect=AssertionError('no HTTP')):
            self.assertEqual(self.invoke(False)['state'],'HOLD_AMO_SUBMISSION_NOT_REQUESTED')
            with self.mock.patch.dict(os.environ,{'WEB_EXT_API_SECRET':''}):
                r=self.invoke();self.assertIn('CREDENTIAL_PAIR_UNAVAILABLE',r['state'])
                self.assertFalse(r['submission_attempted'])

    def test_readback_only_404_never_puts_even_without_a_surviving_journal(self):
        with self.mock.patch.object(host,'firefox_amo_transport',return_value=(404,b'{}')) as call:
            receipt=host.firefox_amo_unlisted(self.root,self.output,self.head,self.tree,self.state,
                submit=True,readback_only=True)
        self.assertEqual([item.args[1] for item in call.call_args_list],['GET'])
        self.assertFalse(receipt['submission_attempted'])
        self.assertTrue(receipt['readback_only'])
        self.assertEqual(receipt['state'],'HOLD_AMO_EXISTING_VERSION_NOT_OBSERVED_READBACK_ONLY')
        self.assertFalse((self.state/'AMO_ATTEMPT.json').exists())

    def test_jwt_hs256_short_expiry_fresh_nonce_and_header(self):
        import hashlib,hmac
        def decode(s):return base64.urlsafe_b64decode(s+'='*(-len(s)%4))
        with self.mock.patch.object(host.time,'time',return_value=1700000000):
            a=host.firefox_amo_jwt('test-only-issuer','synthetic-secret')
            b=host.firefox_amo_jwt('test-only-issuer','synthetic-secret')
        header,claims,signature=a.split('.');payload=json.loads(decode(claims))
        self.assertEqual(json.loads(decode(header))['alg'],'HS256')
        self.assertEqual(payload['exp']-payload['iat'],60)
        self.assertNotEqual(payload['jti'],json.loads(decode(b.split('.')[1]))['jti'])
        self.assertEqual(decode(signature),hmac.new(b'synthetic-secret',('.'.join(a.split('.')[:2])).encode(),hashlib.sha256).digest())

    def test_original_hash_source_binding_and_distinct_browser_acceptance(self):
        signed=self.signed()
        with self.mock.patch.object(host,'firefox_amo_transport',side_effect=[
                (404,b'{}'),(201,self.response()),(200,self.response()),(200,signed)]) as call:
            r=self.invoke()
        self.assertEqual([x.args[1] for x in call.call_args_list],['GET','PUT','GET','GET'])
        self.assertIn('%40',call.call_args_list[0].args[0])
        self.assertEqual((self.output/'standard-signed.xpi').read_bytes(),signed)
        self.assertEqual(r['xpi_sha256'],host.digest(signed));self.assertTrue(r['signed_original_returned'])
        for key in ('mozilla_signature_verified','extension_activation_verified','main_integration_verified','public_production_verified','effect_ack_done'):
            self.assertFalse(r[key])
        for path in [self.state/'AMO_ATTEMPT.json',self.output/'AMO_SIGNING_RECEIPT.json']:
            text=path.read_text();self.assertNotIn(self.env['WEB_EXT_API_KEY'],text)
            self.assertNotIn(self.env['WEB_EXT_API_SECRET'],text)

    def test_existing_version_is_read_back_without_put_or_version_bump(self):
        import zipfile
        before=(2026,10,18,16,44,0,6,291,-1)
        after=(2026,10,18,16,44,2,6,291,-1)
        with self.mock.patch.object(zipfile.time,'localtime',side_effect=[before]*7+[after]*7):
            response=self.response();signed=self.signed()
        with self.mock.patch.object(host,'firefox_amo_transport',side_effect=[(200,response),(200,signed)]) as call:
            r=self.invoke()
        self.assertFalse(r['submission_attempted']);self.assertEqual([x.args[1] for x in call.call_args_list],['GET','GET'])

    def test_pending_upload_and_resume_never_repeat_put(self):
        pending=self.response(processed=False,files=[])
        with self.mock.patch.object(host,'firefox_amo_transport',side_effect=[
                (404,b'{}'),(202,pending),(200,pending),(404,b'{}')]) as call:
            first=self.invoke();second=self.invoke()
        self.assertTrue(first['state'].startswith('PENDING_AMO'))
        self.assertIn('NO_RESUBMISSION',second['state'])
        self.assertEqual(sum(x.args[1]=='PUT' for x in call.call_args_list),1)

    def test_ambiguous_put_keeps_fsynced_journal_and_blocks_resubmission(self):
        with self.mock.patch.object(host,'firefox_amo_transport',side_effect=[(404,b'{}'),ValueError('AMO_TRANSPORT_OUTCOME_UNVERIFIED')]):
            with self.assertRaisesRegex(ValueError,'OUTCOME_UNVERIFIED'):self.invoke()
        self.assertTrue(json.loads((self.state/'AMO_ATTEMPT.json').read_bytes())['submission_attempted'])
        with self.mock.patch.object(host,'firefox_amo_transport',return_value=(404,b'{}')) as call:
            self.assertIn('NO_RESUBMISSION',self.invoke()['state']);self.assertEqual(call.call_count,1)

    def test_wrong_guid_validation_rejection_and_unsigned_response_do_not_download(self):
        for changes in ({'guid':'other@invalid'},{'valid':False},{'files':[]}):
            with self.subTest(changes=changes),self.mock.patch.object(host,'firefox_amo_transport',return_value=(200,self.response(**changes))) as call:
                if 'guid' in changes:
                    with self.assertRaisesRegex(ValueError,'SUBJECT_MISMATCH'):self.invoke()
                else:self.assertFalse(self.invoke()['extension_activation_verified'])
                self.assertEqual(call.call_count,1)

    def test_wrong_hash_changed_payload_and_personal_extra_are_rejected(self):
        for signed,expected in ((b'not matching','SHA256_MISMATCH'),
                (self.signed(changed=True),'SOURCE_BYTES_MISMATCH'),
                (self.signed(extra='personal/secret.json'),'PAYLOAD_FORBIDDEN')):
            response=self.response(signed if expected!='SHA256_MISMATCH' else None)
            with self.subTest(expected=expected),self.mock.patch.object(host,'firefox_amo_transport',side_effect=[(200,response),(200,signed)]):
                with self.assertRaisesRegex(ValueError,expected):self.invoke()
                self.assertFalse((self.output/'standard-signed.xpi').exists())

    def test_authentication_denial_is_hold_and_not_upload(self):
        for code in (401,403):
            with self.subTest(code=code),self.mock.patch.object(host,'firefox_amo_transport',return_value=(code,b'private error')) as call:
                r=self.invoke();self.assertEqual(r['amo_http_status'],code)
                self.assertFalse(r['submission_attempted']);self.assertEqual(call.call_count,1)

    def test_authenticated_put_is_explicit_unlisted_multipart(self):
        import io
        class Response(io.BytesIO):
            code=201;headers={}
        opener=self.mock.Mock();opener.open.return_value=Response(b'{}')
        with self.mock.patch.object(host.urllib.request,'build_opener',return_value=opener):
            host.firefox_amo_transport('https://addons.mozilla.org/api/v4/addons/test%40example/versions/1.0/',
                'PUT',b'original-standard-xpi','test-only-issuer','synthetic-secret')
        request=opener.open.call_args.args[0]
        self.assertEqual(request.method,'PUT');self.assertIn(b'\r\nunlisted\r\n',request.data)
        self.assertIn(b'original-standard-xpi',request.data)
        self.assertTrue(request.get_header('Authorization').startswith('JWT '))

    def test_download_redirect_drops_jwt_and_foreign_origin_is_refused(self):
        import io
        class Response(io.BytesIO):
            def __init__(self,code,location=''):
                super().__init__(b'original');self.code=code;self.headers={'Location':location}
        for target,allowed in [('https://addons.cdn.mozilla.net/standard.xpi',True),('https://attacker.invalid/xpi',False)]:
            opener=self.mock.Mock();opener.open.side_effect=[Response(302,target),Response(200)]
            with self.subTest(target=target),self.mock.patch.object(host.urllib.request,'build_opener',return_value=opener):
                args=('https://addons.mozilla.org/api/v4/downloads/file/123/standard.xpi','GET',None,'synthetic-issuer','synthetic-secret')
                if allowed:
                    self.assertEqual(host.firefox_amo_transport(*args,download=True)[0],200)
                    self.assertIsNone(opener.open.call_args_list[1].args[0].get_header('Authorization'))
                else:
                    with self.assertRaisesRegex(ValueError,'OFFICIAL_HTTPS_ORIGIN'):host.firefox_amo_transport(*args,download=True)
                    self.assertEqual(opener.open.call_count,1)

    def test_signing_helpers_cannot_admit_an_unchanged_s1_runtime_retry(self):
        source=(ROOT/'tools/qikvrt_self_host.py').read_bytes()
        baseline=host.firefox_amo_runtime_fingerprint(source)
        self.assertEqual(baseline,host.firefox_amo_runtime_fingerprint(source.replace(
            b'AMO_BOUNDED_STANDARD_XPI_REQUIRED',b'AMO_CHANGED_SIGNING_DIAGNOSTIC')))
        self.assertNotEqual(baseline,host.firefox_amo_runtime_fingerprint(source.replace(
            b'"signatures_required"',b'"tampered_signatures_required"')))

    def test_container_cli_changes_cannot_retry_the_same_firefox_failure(self):
        source=(ROOT/'tools/qikvrt_self_host.py').read_bytes()
        baseline=host.firefox_amo_runtime_fingerprint(source)
        self.assertEqual(baseline,host.firefox_amo_runtime_fingerprint(source.replace(
            b'non-secret container evidence output',b'changed unrelated container diagnostic')))
        self.assertEqual(baseline,host.firefox_amo_runtime_fingerprint(source.replace(
            b'.execute(args)\n        elif args.operation.startswith("provider-")',
            b'.execute(args, changed_container_option=True)\n        elif args.operation.startswith("provider-")')))
        self.assertNotEqual(baseline,host.firefox_amo_runtime_fingerprint(source.replace(
            b'"FIREFOX_RELEASE_BELOW_OWNER_MINIMUM"',b'"CHANGED_FIREFOX_MINIMUM_GUARD"')))


class FirefoxExtensionAdmissionTests(unittest.TestCase):
    def accepted(self):
        return {"minimum_satisfied": True, "policy_active": True,
            "background_registered": True, "temporary_installation_used": False,
            "addon": {"isCompatible": True, "isActive": True, "appDisabled": False,
                "userDisabled": False, "temporarilyInstalled": False}}

    def test_live_persistent_compatible_registration_is_required(self):
        self.assertTrue(host.firefox_extension_accepted(self.accepted()))
        for field in ("minimum_satisfied", "policy_active", "background_registered"):
            with self.subTest(field=field):
                value=self.accepted();value[field]=False
                self.assertFalse(host.firefox_extension_accepted(value))

    def test_copied_missing_disabled_or_incompatible_xpi_is_not_activation(self):
        self.assertFalse(host.firefox_extension_accepted({}))
        value=self.accepted();value["addon"]=None
        self.assertFalse(host.firefox_extension_accepted(value))
        for field, bad in (("isCompatible",False),("isActive",False),
                ("appDisabled",True),("userDisabled",True),("temporarilyInstalled",True)):
            with self.subTest(field=field):
                value=self.accepted();value["addon"][field]=bad
                self.assertFalse(host.firefox_extension_accepted(value))
        value=self.accepted();value["temporary_installation_used"]=True
        self.assertFalse(host.firefox_extension_accepted(value))

    def test_reference_exception_does_not_override_minimum_version(self):
        value=self.accepted();value.update(minimum_satisfied=False,signatures_required=False)
        self.assertFalse(host.firefox_extension_accepted(value))

    def test_release_requires_real_mozilla_signature_and_default_enforcement(self):
        value=self.accepted();value.update(signatures_required=True,mozilla_signed=True)
        self.assertTrue(host.firefox_production_extension_accepted(value))
        for field in ('signatures_required','mozilla_signed'):
            for bad in (False,None,0,'true'):
                with self.subTest(field=field,bad=bad):
                    changed=dict(value);changed[field]=bad
                    self.assertFalse(host.firefox_production_extension_accepted(changed))

    def test_release_version_and_manifest_bound_browser_selection(self):
        for value in ('Mozilla Firefox 158.0','Mozilla Firefox 158.0.1','Mozilla Firefox 159.0'):
            self.assertTrue(host.firefox_release_minimum_satisfied(value))
        for value in ('Mozilla Firefox 153.4.0esr','Mozilla Firefox 157.9','158.0',''):
            self.assertFalse(host.firefox_release_minimum_satisfied(value))
        self.assertEqual(host.browser_commands('firefox')[0],'firefox')
        self.assertEqual(host.browser_commands()[0],'firefox-esr')
        with self.assertRaisesRegex(ValueError,'DECLARED_FIREFOX_PACKAGE'):
            host.browser_commands('/unbound/browser')

    def test_gecko_removed_xpi_is_retained_as_negative_observation(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"removed.xpi"
            self.assertEqual(host.firefox_profile_xpi_state(path),
                {"profile_xpi_present":False,"profile_xpi_sha256":None})
            path.write_bytes(b"original-package-bytes")
            self.assertEqual(host.firefox_profile_xpi_state(path),
                {"profile_xpi_present":True,"profile_xpi_sha256":host.digest(path.read_bytes())})
            path.unlink()
            self.assertFalse(host.firefox_profile_xpi_state(path)["profile_xpi_present"])

    def test_signature_metadata_cannot_replace_source_or_browser_verification(self):
        import zipfile
        source=ROOT/'browser/firefox/qikvrt-terminal'
        names=('manifest.json','background.js','content.js','options.html','options.js','terminal.css')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'candidate.xpi'
            for extra,changed in ((None,False),('META-INF/mozilla.rsa',False),
                    ('personal/credentials.json',False),(None,True)):
                with self.subTest(extra=extra,changed=changed):
                    with zipfile.ZipFile(path,'w') as archive:
                        for name in names:
                            raw=(source/name).read_bytes()
                            archive.writestr(name,raw+b'changed' if changed and name=='background.js' else raw)
                        if extra: archive.writestr(extra,b'not-a-Mozilla-signature')
                    if changed or extra=='personal/credentials.json':
                        with self.assertRaises(ValueError): host.firefox_xpi_source_binding(path,source)
                    else:
                        binding=host.firefox_xpi_source_binding(path,source)
                        self.assertFalse(binding['mozilla_signature_verified'])
                        self.assertEqual(binding['signature_metadata_present'],extra is not None)

    def test_framed_readback_is_fragment_safe_and_rejects_stale_response(self):
        import io
        class Connection:
            def __init__(self, values):
                raw=b""
                for value in values:
                    encoded=json.dumps(value).encode()
                    raw+=str(len(encoded)).encode()+b":"+encoded
                self.data=io.BytesIO(raw);self.sent=[]
            def recv(self,n): return self.data.read(min(n,3))
            def sendall(self,value): self.sent.append(value)
        connection=Connection([{"marionetteProtocol":3},[1,1,None,{"value":"bound"}]])
        client=host.FirefoxProbeConnection(connection)
        self.assertEqual(client.call("test",{}),{"value":"bound"})
        stale=host.FirefoxProbeConnection(Connection([{"marionetteProtocol":3},[1,2,None,{}]]))
        with self.assertRaisesRegex(ValueError,"RESPONSE_BINDING"):
            stale.call("test",{})

    def test_remote_error_or_unknown_protocol_cannot_be_pass(self):
        from unittest.mock import Mock
        connection=Mock();connection.recv.side_effect=[b"1",b":",b"{}"]
        with self.assertRaises((ValueError,json.JSONDecodeError)):
            host.FirefoxProbeConnection(connection)

    def test_existing_oci_repack_preserves_config_and_rejects_changed_layer(self):
        import io,gzip,tarfile,hashlib
        for corrupt in (False,True):
            with self.subTest(corrupt=corrupt),tempfile.TemporaryDirectory() as directory:
                directory=Path(directory);blobs={}
                def add(raw,media=None):
                    key="sha256:"+hashlib.sha256(raw).hexdigest()
                    blobs["blobs/sha256/"+key[7:]]=raw
                    value={"digest":key,"size":len(raw)}
                    if media: value["mediaType"]=media
                    return value
                layer=b"original-uncompressed-layer-bytes"
                layer_descriptor=add(gzip.compress(layer,mtime=0),"application/vnd.oci.image.layer.v1.tar+gzip")
                config=json.dumps({"architecture":"amd64","os":"linux","rootfs":{"type":"layers",
                    "diff_ids":["sha256:"+hashlib.sha256(layer).hexdigest()]}}).encode()
                config_descriptor=add(config)
                image=add(json.dumps({"config":config_descriptor,"layers":[layer_descriptor]}).encode())
                blobs["index.json"]=json.dumps({"manifests":[image]}).encode()
                if corrupt: blobs["blobs/sha256/"+layer_descriptor["digest"][7:]]=b"corrupt"
                source=directory/"source.tar";target=directory/"loaded.tar"
                with tarfile.open(source,"w") as output:
                    for name,raw in blobs.items():
                        entry=tarfile.TarInfo(name);entry.size=len(raw)
                        output.addfile(entry,io.BytesIO(raw))
                if corrupt:
                    with self.assertRaisesRegex(ValueError,"OCI_LAYER_BLOB_MISMATCH"):
                        host.oci_to_docker_archive(source,target,"qikvrt:test")
                else:
                    result=host.oci_to_docker_archive(source,target,"qikvrt:test")
                    self.assertFalse(result["rebuilt"]);self.assertFalse(result["config_rewritten"])
                    with tarfile.open(target) as archive:
                        manifest=json.loads(archive.extractfile("manifest.json").read())[0]
                        self.assertEqual(archive.extractfile(manifest["Config"]).read(),config)
                        self.assertEqual(archive.extractfile(manifest["Layers"][0]).read(),layer)


class FirefoxCarrierTests(NativeStandaloneTests):
    # The inherited native controls also execute against this browser profile.
    START_TIMEOUT = 60
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='qikvrt-firefox-exact-')
        cls.base = Path(cls.scratch.name)
        cls.source = ROOT
        cls.head = host.git(ROOT,'rev-parse','HEAD').decode()
        cls.tree = host.git(ROOT,'rev-parse','HEAD^{tree}').decode()
        cls.export = cls.base/'export'
        cls.receipt = host.freeze(ROOT,cls.export,cls.head,cls.tree,Path('/usr/share/novnc'),
            os.environ.get('QIKVRT_FIREFOX_PACKAGE','firefox-esr'))
        cls.pin = cls.receipt['manifest_sha256']
        cls.manifest = json.loads((cls.export/'MANIFEST.json').read_bytes())

    def setUp(self):
        super().setUp()
        def port():
            with socket.socket() as s:
                s.bind(('127.0.0.1',0)); return s.getsockname()[1]
        password = self.work/'vnc.password'; password.write_text('Test9Vnc'); password.chmod(0o600)
        self.config.update(terminal_profile='firefox',display=':'+str(100 + os.getpid()%5000),
            novnc_port=port(),vnc_port=port(),browser_password_file=str(password))
        self.save_config()

    def start(self,path=None):
        # Build-time Git is available, but no Git/gh/provider is in runtime PATH.
        binpath=self.work/'runtime-bin';binpath.mkdir(exist_ok=True)
        for name in ('node','python3','python3.12',*self.manifest['browser_runtime']['executables']):
            found=str(host.firefox_binary(name)) if name in {'firefox','firefox-esr'} else shutil.which(name)
            self.assertIsNotNone(found, name)
            if not (binpath/name).exists(): (binpath/name).symlink_to(found)
        self.assertIsNone(shutil.which('git',path=str(binpath)))
        self.assertIsNone(shutil.which('gh',path=str(binpath)))
        from tests.test_self_host import StandaloneTests
        try:
            return StandaloneTests.start(self,path=binpath)
        except AssertionError as exc:
            # These are isolated synthetic fixtures, never a production profile.
            # Retain bounded diagnostics before the private fixture is deleted.
            evidence = os.environ.get('QIKVRT_BROWSER_TEST_EVIDENCE')
            if evidence:
                p=Path(evidence);p.mkdir(parents=True,exist_ok=True)
                logs={f.name:f.read_bytes()[-65536:].decode('utf-8','replace').replace('Test9Vnc','<synthetic-password>')
                    for f in (self.volume/'browser/logs').glob('*.log')}
                (p/('FAILURE_'+self._testMethodName+'.json')).write_bytes(host.raw_json({
                    'source_head':self.head,'source_tree':self.tree,'manifest_sha256':self.pin,
                    'runtime_failure':str(exc),'fixture_component_logs':logs,'effect_ack_done':False}))
            raise

    def websocket_rfb_auth(self):
        with socket.create_connection(('127.0.0.1',self.config['novnc_port']),timeout=5) as s:
            key=base64.b64encode(b'QIKVRT-test-key16').decode()
            s.sendall(('GET /websockify HTTP/1.1\r\nHost: 127.0.0.1:'+str(self.config['novnc_port'])+
                '\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: '+key+
                '\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: binary\r\n\r\n').encode())
            f=s.makefile('rb')
            header=[]
            while True:
                line=f.readline();self.assertTrue(line)
                if line==b'\r\n':break
                header.append(line)
            self.assertIn(b'101',header[0])
            def frame():
                first=f.read(2);self.assertEqual(len(first),2)
                length=first[1]&127
                if length==126:length=int.from_bytes(f.read(2),'big')
                if length==127:length=int.from_bytes(f.read(8),'big')
                self.assertLess(length,65536)
                data=f.read(length);self.assertEqual(len(data),length)
                return data
            banner=frame();self.assertEqual(banner,b'RFB 003.008\n')
            mask=b'QIKV';payload=b'RFB 003.008\n'
            s.sendall(bytes([0x82,0x80|len(payload)])+mask+bytes(v^mask[i%4] for i,v in enumerate(payload)))
            schemes=frame();self.assertGreater(len(schemes),1)
            count=schemes[0];self.assertEqual(len(schemes),count+1)
            self.assertIn(2,schemes[1:]);self.assertNotIn(1,schemes[1:])
            f.close()
            return {'websocket_status':101,'rfb_version':banner.decode().strip(),'vnc_authentication_required':True}

    def kernel_listeners(self):
        listeners=[]
        for name in ('tcp','tcp6'):
            for line in Path('/proc/net/'+name).read_text().splitlines()[1:]:
                row=line.split()
                if row[3] != '0A': continue
                address,port=row[1].split(':')
                self.assertEqual(name, 'tcp', 'The IPv4-only carrier must have no extra IPv6 listener')
                self.assertEqual(address, '0100007F', 'All carrier listeners must be loopback')
                listeners.append({'address':'127.0.0.1','port':int(port,16)})
        self.assertEqual({e['port'] for e in listeners}, {self.config[k] for k in ('port','terminal_port','novnc_port','vnc_port')})
        return sorted(listeners,key=lambda e:e['port'])

    def test_actual_firefox_window_novnc_websocket_and_candidate_binding(self):
        interfaces = sorted(name for _, name in socket.if_nameindex())
        self.assertEqual(interfaces, ['lo'], 'This acceptance requires the declared network-none carrier')
        init_name=Path('/proc/1/comm').read_text().strip()
        self.assertIn(init_name, ('docker-init','tini'), 'The declared container must have a real child reaper')
        init_binding={'name':init_name,'executable_sha256':host.digest(Path('/proc/1/exe').read_bytes())}
        runtime=self.start()
        self.assertTrue(runtime['browser_startup_verified'])
        self.assertTrue(runtime['native_terminal_daemon_available'])
        self.assertEqual(runtime['source_head'], self.head)
        self.assertFalse((self.export/'.git').exists())
        readback=self.websocket_rfb_auth()
        listeners=self.kernel_listeners()
        prepared,event=self.commit_input()
        terminal=self.get('/api/terminal')[1]
        self.assertEqual(terminal['subject'],event['subject'])
        evidence=os.environ.get('QIKVRT_BROWSER_TEST_EVIDENCE')
        if evidence:
            p=Path(evidence);p.mkdir(parents=True,exist_ok=True)
            receipt={'schema':'qikvrt-self-host-firefox-runtime-readback/v1',
                'observed_at':datetime.now(timezone.utc).isoformat(),'source_head':self.head,'source_tree':self.tree,
                'manifest_sha256':self.pin,'config_sha256':host.digest(self.config_path.read_bytes()),
                'native_subject':terminal['subject'],'ledger_id':terminal['ledger_id'],
                'native_durable_event':event,'firefox_version':self.manifest['browser_runtime']['firefox_version'],
                'browser_executables':self.manifest['browser_runtime']['executables'],'transport':readback,
                'firefox_navigator_window_observed':True,'git_in_runtime_path':False,'gh_in_runtime_path':False,
                'native_terminal_document_title_observed':True,
                'outbound_network':'DOCKER_NETWORK_NONE','observed_network_interfaces':interfaces,
                'observed_listeners':listeners,'container_init':init_binding,
                'scope':'ACTUAL_EXACT_CANDIDATE_RUNTIME_IN_CI_CONTAINER',
                'independent_host_identity_verified':False,'public_https_readback_verified':False,
                'deployment_performed':False,'effect_ack_done':False}
            (p/'FIREFOX_NATIVE_READBACK.json').write_bytes(host.raw_json(receipt))
            (p/'MANIFEST.json').write_bytes((self.export/'MANIFEST.json').read_bytes())
            (p/'DISTRIBUTION_PACKAGES.tsv').write_bytes(Path('/usr/local/share/qikvrt-distribution-packages.tsv').read_bytes())

    def test_display_generation_survives_last_readiness_client_disconnect(self):
        # A real X11 atom is deleted by a server reset. Exercise the launcher's
        # command, with the previous reset behavior as a causal control; neither
        # a static argv assertion nor a persistent observer can establish this.
        x11 = ctypes.CDLL('libX11.so.6')
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x11.XInternAtom.restype = ctypes.c_ulong
        x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        display = self.config['display'].encode()
        name = ('QIKVRT_LAST_CLIENT_' + str(os.getpid())).encode()

        def atom(only_if_exists, process):
            until = time.monotonic() + 5
            while time.monotonic() < until:
                self.assertIsNone(process.poll(), 'Xvfb exited before X11 readback')
                connection = x11.XOpenDisplay(display)
                if connection:
                    try:
                        value = x11.XInternAtom(connection, name, only_if_exists)
                        x11.XSync(connection, 0)
                        return value
                    finally:
                        x11.XCloseDisplay(connection)
                time.sleep(.025)
            self.fail('X11 connection unavailable for display-generation readback')

        command = host._xvfb_command(self.config['display'])
        for preserve in (False, True):
            with self.subTest(preserve=preserve):
                argv = command if preserve else [x for x in command if x != '-noreset']
                log = self.work / ('x11-generation-' + str(preserve) + '.log')
                with log.open('wb') as output:
                    process = subprocess.Popen(argv, stdout=output, stderr=output)
                    try:
                        original = atom(0, process)
                        self.assertNotEqual(original, 0)
                        observed = original
                        until = time.monotonic() + 5
                        probes = 0
                        while time.monotonic() < until:
                            # No X11 client is connected during this interval.
                            time.sleep(.1)
                            observed = atom(1, process)
                            probes += 1
                            if preserve:
                                self.assertEqual(observed, original)
                                if probes == 3: break
                            elif observed == 0: break
                        self.assertEqual(observed, original if preserve else 0)
                    finally:
                        process.terminate()
                        process.wait(timeout=5)

    def test_crash_restart_preserves_firefox_profile_and_acknowledged_native_bytes(self):
        self.start(); prepared,event=self.commit_input()
        marker=self.volume/'browser/profile/qikvrt-test-restart-marker'
        marker.write_bytes(b'private fixture marker; no credentials')
        before=self.sql('SELECT binding,source,native_id,native_digest,body,body_digest FROM events')
        old_xvfb=[]
        for p in Path('/proc').glob('[0-9]*'):
            try:
                if p.joinpath('comm').read_text().strip()=='Xvfb' and os.getpgid(int(p.name))==self.process.pid:
                    old_xvfb.append(int(p.name))
            except (OSError,ValueError): pass
        self.assertEqual(len(old_xvfb),1)
        self.stop(abrupt=True);self.start()
        self.assertTrue(all(not Path('/proc/'+str(pid)).exists() for pid in old_xvfb))
        listeners_after_restart=self.kernel_listeners()
        self.assertEqual(marker.read_bytes(),b'private fixture marker; no credentials')
        self.assertEqual(self.sql('SELECT binding,source,native_id,native_digest,body,body_digest FROM events'),before)
        code,readback=self.cli('durable-readback',prepared)
        self.assertEqual(code,0,readback);self.assertEqual(readback['durable_readback'],event)
        self.websocket_rfb_auth()
        evidence=os.environ.get('QIKVRT_BROWSER_TEST_EVIDENCE')
        if evidence:
            (Path(evidence)/'FIREFOX_NATIVE_RESTART_READBACK.json').write_bytes(host.raw_json({
                'schema':'qikvrt-self-host-firefox-restart-readback/v1','source_head':self.head,'source_tree':self.tree,
                'manifest_sha256':self.pin,'native_durable_event':event,'profile_marker_preserved':True,
                'native_original_rows_preserved':True,'crashed_xvfb_pids':old_xvfb,
                'crashed_xvfb_reaped':True,'observed_listeners_after_restart':listeners_after_restart,
                'public_https_readback_verified':False,'effect_ack_done':False}))

    # The inherited adversarial native controls apply to this actual browser
    # variant too. They exercise the same kernel, with actual GUI children.


if __name__=='__main__':unittest.main()

