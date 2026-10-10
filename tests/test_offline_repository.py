# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import gzip
import hashlib
import json
import pathlib
import subprocess
import tempfile
import unittest
import zipfile
from tools import qikvrt_offline_repository as offline

class OfflineTransferTests(unittest.TestCase):
    def test_selected_git_bytes_are_independently_bound_and_gzip_is_stream_portable(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/'source.qikvrt.gz'
            receipt=offline.pack('HEAD',path,['AI','README.md'])
            with gzip.open(path,'rt',encoding='utf-8') as f:
                rows=[json.loads(line) for line in f]
            header=rows[0]
            snapshot=next(r for r in rows if r.get('type')=='snapshot')
            self.assertEqual(header['head'],hashlib.sha256(offline.canonical(snapshot['snapshot']).encode()).hexdigest())
            self.assertEqual(snapshot['snapshot']['source']['scope'],'SELECTED_GIT_FILES')
            self.assertEqual(snapshot['snapshot']['git_tree_sha1'],offline.tree_hash(snapshot['snapshot']['files']))
            for file in snapshot['snapshot']['files']:
                oid=subprocess.check_output(['git','rev-parse','HEAD:'+file['path']],cwd=offline.ROOT).decode().strip()
                self.assertEqual(file['git_blob_sha1'],oid)
            self.assertFalse(receipt['mobile_device_readback'])
            self.assertFalse(receipt['effect_ack_done'])

    def test_reused_react_production_bytes_and_license_match_exact_lock(self):
        lock=json.loads((offline.ROOT/'runtime/offline/REACT_LOCK.json').read_text())
        for item in (lock['bundle'],lock['license']):
            self.assertEqual(hashlib.sha256((offline.ROOT/item['path']).read_bytes()).hexdigest(),item['sha256'])
        self.assertEqual(lock['reuse_source_commit'],'53040b450853b0ab5a3d59765b86030b3bd0c978')

    def test_client_package_exports_committed_source_bytes_and_binding(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/'client.zip'
            receipt=offline.client_package('HEAD',path)
            with zipfile.ZipFile(path) as archive:
                binding=json.loads(archive.read('SOURCE.json'))
                self.assertEqual(binding['source_head'],receipt['source_head'])
                for name, item in binding['files'].items():
                    data=archive.read(name)
                    self.assertEqual(hashlib.sha256(data).hexdigest(),item['sha256'])
                    self.assertEqual(data,offline.git('show',receipt['source_head']+':docs/monitor/offline/'+name))
                self.assertNotIn('repository.qikvrt.gz',archive.namelist())
                self.assertFalse(binding['actual_iphone_devices_tested'])
            self.assertEqual(receipt['archive_sha256'],offline.file_hash(path))
            with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'): offline.client_package('HEAD',path)

    def test_pack_refuses_overwrite_and_missing_source_paths(self):
        with tempfile.TemporaryDirectory() as d:
            path=pathlib.Path(d)/'source.qikvrt'
            offline.pack('HEAD',path,['AI'])
            original=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'OUTPUT_ALREADY_EXISTS'): offline.pack('HEAD',path,['AI'])
            self.assertEqual(path.read_bytes(),original)
            with self.assertRaisesRegex(ValueError,'SELECTED_SOURCE_PATH_MISSING'): offline.pack('HEAD',pathlib.Path(d)/'missing.qikvrt',['missing-file'])

    def test_source_blob_and_directory_modes_reproduce_actual_git_tree(self):
        files=[]
        for line in offline.git('ls-tree','-rz','HEAD').split(b'\0'):
            if not line: continue
            meta,path=line.split(b'\t',1)
            mode,kind,sha=meta.decode().split()
            self.assertEqual(kind,'blob')
            files.append({'path':path.decode(),'mode':mode,'git_blob_sha1':sha})
        self.assertEqual(offline.tree_hash(files),offline.git('rev-parse','HEAD^{tree}').decode().strip())

    def test_committed_service_worker_pins_all_production_dependencies_and_no_user_data(self):
        hashes={name:hashlib.sha256((offline.CLIENT/name).read_bytes()).hexdigest() for name in offline.ASSETS}
        shell_id=hashlib.sha256(offline.canonical(hashes).encode()).hexdigest()
        expected=(offline.CLIENT/'service-worker.template.js').read_text().replace('__SHELL_ID__',shell_id).replace('__ASSETS__',offline.canonical(hashes))
        self.assertEqual((offline.CLIENT/'service-worker.js').read_text(),expected)
        self.assertNotIn('repository.qikvrt',offline.ASSETS)
        self.assertNotIn('monitor/observation.json',offline.ASSETS)

if __name__=='__main__': unittest.main()
