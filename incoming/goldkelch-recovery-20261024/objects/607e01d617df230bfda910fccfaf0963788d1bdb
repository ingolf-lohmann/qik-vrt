# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from tools.qikvrt_tool_cache import ROOT, ContractError, NativeRuntime


class NativeCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'repo'; self.root.mkdir()
        manifest = json.loads((ROOT/'runtime/toolchains/NATIVE_RECIPES.json').read_text())
        for recipe in manifest['recipes'].values():
            for relative in recipe['inputs']:
                dest=self.root/relative; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes((ROOT/relative).read_bytes())
        dest=self.root/'runtime/toolchains'; dest.mkdir(parents=True,exist_ok=True)
        (dest/'NATIVE_RECIPES.json').write_text(json.dumps(manifest))
        (dest/'TOOLCHAIN.lock.tsv').write_bytes((ROOT/'runtime/toolchains/TOOLCHAIN.lock.tsv').read_bytes())
        self.frames=[]
        self.runtime=NativeRuntime(self.root,Path(self.tmp.name)/'cache',emit=lambda stage,**kw:self.frames.append((stage,kw)))
        self.recipe='effect-ack-core-conformance'

    def test_compile_once_reuse_self_test_and_source_update(self):
        one=self.runtime.prepare(self.recipe); two=self.runtime.prepare(self.recipe)
        self.assertTrue(one['compiled']); self.assertFalse(two['compiled'])
        self.assertEqual(one['key'],two['key']); self.assertTrue(two['static_linkage_verified'])
        self.assertIn('PASS (',two['self_test_output'])
        source=self.root/'src/effect_ack_core.c'; source.write_text(source.read_text()+'\n/* Version update. */\n')
        three=self.runtime.prepare(self.recipe)
        self.assertTrue(three['compiled']); self.assertNotEqual(one['key'],three['key'])

    def test_concurrent_first_use_compiles_once(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:self.runtime.prepare(self.recipe),range(4)))
        self.assertEqual(sum(result['compiled'] for result in results),1)
        self.assertEqual(len({result['key'] for result in results}),1)

    def test_corruption_blocks_without_silent_recompile(self):
        good=self.runtime.prepare(self.recipe); binary=Path(good['binary']); binary.chmod(0o700)
        binary.write_bytes(binary.read_bytes()+b'altered')
        with self.assertRaisesRegex(ContractError,'NATIVE_BINARY_DIGEST_MISMATCH'): self.runtime.prepare(self.recipe)
        status=json.loads((self.runtime.cache/'status.json').read_text())
        self.assertEqual(status['state'],'BLOCK'); self.assertFalse(status['effect_ack_done'])
        self.assertEqual(sum(frame[0]=='COMPILE' for frame in self.frames),1)

    def test_platform_compiler_and_flags_change_keys(self):
        original=self.runtime.context(self.recipe)['key']
        with patch('tools.qikvrt_tool_cache.platform.machine',return_value='different-target'):
            self.assertNotEqual(original,self.runtime.context(self.recipe)['key'])
        manifest_path=self.root/'runtime/toolchains/NATIVE_RECIPES.json'; manifest=json.loads(manifest_path.read_text())
        manifest['flags'].append('-fno-inline'); manifest_path.write_text(json.dumps(manifest))
        self.assertNotEqual(original,self.runtime.context(self.recipe)['key'])
        manifest['flags'].remove('-static'); manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ContractError,'STATIC_LINKAGE_REQUIRED'): self.runtime.prepare(self.recipe)

    def test_hot_layers_are_bounded_and_measured_savings_prioritized(self):
        manifest_path=self.root/'runtime/toolchains/NATIVE_RECIPES.json'; manifest=json.loads(manifest_path.read_text())
        for name in ('hot','cold','slower'):
            manifest['recipes'][name]={**manifest['recipes'][self.recipe],'kind':'hot_layer'}
        manifest_path.write_text(json.dumps(manifest))
        context=self.runtime.context('hot'); key=context['key']
        profiles={key:{'recipe':'hot','calls':100,'baseline_ns':3000000000,'native_samples':10,'native_ns':10000000},
          self.runtime.context('cold')['key']:{'recipe':'cold','calls':2,'baseline_ns':3000000000,'native_samples':0,'native_ns':0},
          self.runtime.context('slower')['key']:{'recipe':'slower','calls':100,'baseline_ns':100000000,'native_samples':10,'native_ns':300000000}}
        self.runtime.save(self.runtime.cache/'usage.json',{'schema':'qikvrt-native-usage/v1','profiles':profiles})
        plan=self.runtime.plan()
        self.assertEqual([item['recipe'] for item in plan['selected']],['hot'])
        self.assertEqual(plan['selected'][0]['reason'],'MEASURED_AMORTIZATION')
        self.assertEqual(self.runtime.plan(50)['selected'],[])
        optimized=self.runtime.optimize(); self.assertEqual(len(optimized['results']),1)
        self.assertTrue(optimized['results'][0]['compiled']); self.assertEqual(self.runtime.plan()['selected'],[])
        self.runtime.record_usage('hot',1200,500)
        usage=json.loads((self.runtime.cache/'usage.json').read_text()); self.assertEqual(usage['profiles'][key]['calls'],101)

    def test_compile_error_does_not_activate_previous_version(self):
        good=self.runtime.prepare(self.recipe)
        path=self.root/'src/effect_ack_core.c'; path.write_text(path.read_text()+'\n#error forced compile failure\n')
        with self.assertRaisesRegex(ContractError,'NATIVE_COMPILE_FAILED'): self.runtime.prepare(self.recipe)
        status=json.loads((self.runtime.cache/'status.json').read_text())
        self.assertEqual(status['state'],'BLOCK'); self.assertNotIn('binary',status)
        self.assertTrue(Path(good['binary']).exists())


if __name__=='__main__': unittest.main()
