#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate deterministic, complete cache coverage for the declared QIK-VRT runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "runtime/toolchains/TOOLCHAIN.lock.tsv"
REGISTRY_PATH = ROOT / "runtime/toolchains/CACHE_REGISTRY.json"
COVERAGE_PATH = ROOT / "runtime/toolchains/CACHE_COVERAGE.json"

REQUIRED_COMPONENT_FIELDS = {
    "version",
    "profiles",
    "cache_class",
    "provider",
    "cache_locations",
    "authority_files",
    "verification",
    "trusted_save",
}
FORBIDDEN_CACHE_TOKENS = {
    "gh_token",
    "github_token",
    "credential",
    "cookie",
    ".ssh",
    "private_key",
    "auth login",
}


class ContractError(RuntimeError):
    """Raised when the runtime cache contract is incomplete or inconsistent."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_lock() -> dict[str, dict[str, list[str]]]:
    if not LOCK_PATH.is_file():
        raise ContractError(f"missing toolchain lock: {LOCK_PATH.relative_to(ROOT)}")
    records: dict[str, dict[str, set[str]]] = {}
    for line_number, raw in enumerate(
        LOCK_PATH.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not raw or raw.startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 7:
            raise ContractError(
                f"invalid lock row {line_number}: expected 7 tab-separated fields"
            )
        component, version, platform, _archive, _archive_hash, _license, purpose = fields
        if not component or not version or not platform or not purpose:
            raise ContractError(f"invalid empty field in lock row {line_number}")
        record = records.setdefault(
            component,
            {"versions": set(), "platforms": set(), "purposes": set()},
        )
        record["versions"].add(version)
        record["platforms"].add(platform)
        record["purposes"].add(purpose)

    normalized: dict[str, dict[str, list[str]]] = {}
    for component, record in records.items():
        versions = sorted(record["versions"])
        if len(versions) != 1:
            raise ContractError(f"{component}: multiple versions in lock: {versions}")
        normalized[component] = {
            "versions": versions,
            "platforms": sorted(record["platforms"]),
            "purposes": sorted(record["purposes"]),
        }
    if not normalized:
        raise ContractError("toolchain lock declares no components")
    return normalized


def read_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        raise ContractError(f"missing cache registry: {REGISTRY_PATH.relative_to(ROOT)}")
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"invalid cache registry JSON: {exc}") from exc
    if registry.get("schema") != "qikvrt-tool-cache-registry/1.0":
        raise ContractError("unsupported cache registry schema")
    if registry.get("lock_authority") != str(LOCK_PATH.relative_to(ROOT)):
        raise ContractError(
            "cache registry lock_authority does not identify TOOLCHAIN.lock.tsv"
        )
    if registry.get("coverage_authority") != str(COVERAGE_PATH.relative_to(ROOT)):
        raise ContractError(
            "cache registry coverage_authority does not identify CACHE_COVERAGE.json"
        )
    if not isinstance(registry.get("components"), dict):
        raise ContractError("cache registry components must be an object")
    return registry


def validate_registry(
    locked: dict[str, dict[str, list[str]]],
    registry: dict[str, Any],
) -> list[dict[str, Any]]:
    entries: dict[str, Any] = registry["components"]
    locked_names = set(locked)
    registry_names = set(entries)
    missing = sorted(locked_names - registry_names)
    extra = sorted(registry_names - locked_names)
    if missing:
        raise ContractError(
            f"cache registry misses locked components: {', '.join(missing)}"
        )
    if extra:
        raise ContractError(
            f"cache registry has undeclared components: {', '.join(extra)}"
        )

    allowed_classes = set(registry.get("cache_classes", []))
    if not allowed_classes:
        raise ContractError("cache registry defines no cache classes")

    coverage: list[dict[str, Any]] = []
    for component in sorted(locked):
        entry = entries[component]
        if not isinstance(entry, dict):
            raise ContractError(f"{component}: registry entry must be an object")
        absent_fields = sorted(REQUIRED_COMPONENT_FIELDS - set(entry))
        if absent_fields:
            raise ContractError(
                f"{component}: missing fields: {', '.join(absent_fields)}"
            )
        expected_version = locked[component]["versions"][0]
        if entry["version"] != expected_version:
            raise ContractError(
                f"{component}: registry version {entry['version']!r} "
                f"!= lock {expected_version!r}"
            )
        if entry["cache_class"] not in allowed_classes:
            raise ContractError(
                f"{component}: unsupported cache class {entry['cache_class']!r}"
            )
        for list_field in (
            "profiles",
            "cache_locations",
            "authority_files",
            "verification",
        ):
            value = entry[list_field]
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                raise ContractError(
                    f"{component}: {list_field} must be a non-empty string list"
                )
        if not isinstance(entry["provider"], str) or not entry["provider"].strip():
            raise ContractError(f"{component}: provider must be non-empty")
        if not isinstance(entry["trusted_save"], bool):
            raise ContractError(f"{component}: trusted_save must be boolean")

        for authority in entry["authority_files"]:
            authority_path = ROOT / authority
            if not authority_path.is_file():
                raise ContractError(
                    f"{component}: missing authority file: {authority}"
                )

        joined_locations = "\n".join(entry["cache_locations"]).lower()
        forbidden = sorted(
            token for token in FORBIDDEN_CACHE_TOKENS if token in joined_locations
        )
        if forbidden:
            raise ContractError(
                f"{component}: credential-bearing cache location token(s): "
                f"{', '.join(forbidden)}"
            )

        coverage.append(
            {
                "cache_class": entry["cache_class"],
                "component": component,
                "provider": entry["provider"],
                "version": expected_version,
            }
        )
    return coverage


def build_coverage() -> dict[str, Any]:
    locked = read_lock()
    registry = read_registry()
    components = validate_registry(locked, registry)
    lock_bytes = LOCK_PATH.read_bytes()
    registry_bytes = REGISTRY_PATH.read_bytes()
    total = len(locked)
    covered = len(components)
    if covered != total:
        raise ContractError(f"cache coverage is incomplete: {covered}/{total}")
    return {
        "schema": "qikvrt-tool-cache-coverage/1.0",
        "status": "PASS",
        "coverage_basis": (
            "unique components in runtime/toolchains/TOOLCHAIN.lock.tsv"
        ),
        "coverage_percent": 100,
        "declared_components": total,
        "covered_components": covered,
        "lock_sha256": sha256_bytes(lock_bytes),
        "registry_sha256": sha256_bytes(registry_bytes),
        "components": components,
        "rules": {
            "all_declared_tools_have_cache_strategy": True,
            "new_tool_must_extend_lock_and_registry_before_use": True,
            "credentials_forbidden_in_cache": True,
            "cold_and_warm_cache_semantics_equal": True,
            "cache_never_replaces_required_checks": True,
        },
    }


def render() -> None:
    document = build_coverage()
    COVERAGE_PATH.write_text(canonical_json(document), encoding="utf-8")
    print(
        f"PASS: rendered {document['covered_components']}/"
        f"{document['declared_components']} tool-cache coverage"
    )


def verify() -> None:
    expected = canonical_json(build_coverage())
    if not COVERAGE_PATH.is_file():
        raise ContractError(
            f"missing coverage authority: {COVERAGE_PATH.relative_to(ROOT)}"
        )
    actual = COVERAGE_PATH.read_text(encoding="utf-8")
    if actual != expected:
        raise ContractError(
            "CACHE_COVERAGE.json is stale; run "
            "'python3 tools/qikvrt_tool_cache.py render'"
        )
    document = json.loads(actual)
    print(
        f"PASS: {document['covered_components']}/"
        f"{document['declared_components']} declared tools have cache strategies "
        f"({document['coverage_percent']}%)"
    )


class NativeRuntime:
    """Extend the declared tool cache with local statically linked machine code."""
    def __init__(self, root: Path = ROOT, cache: Path | None = None, compiler: str | None = None, emit: Any = None):
        self.root = root.resolve()
        self.cache = (cache or self.root / '.qikvrt/toolchains/native/v1').absolute()
        self.compiler = compiler or os.environ.get('CC','cc')
        self.emit = emit or self.progress

    @staticmethod
    def progress(stage: str, **fields: Any) -> None:
        from qikvrt_runtime_logger import write_event
        print(json.dumps(write_event('native_runtime_step',stage=stage,**fields)),file=sys.stderr)

    @staticmethod
    def read(path: Path) -> bytes:
        if path.is_symlink() or not path.is_file(): raise ContractError('NATIVE_FILE_NOT_REGULAR: '+str(path))
        return path.read_bytes()

    def save(self, path: Path, value: Any) -> None:
        if path.parent.is_symlink(): raise ContractError('NATIVE_CACHE_SYMLINK')
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        descriptor,temporary = tempfile.mkstemp(dir=path.parent,prefix='.native-')
        try:
            with os.fdopen(descriptor,'wb') as output:
                output.write(canonical_json(value).encode()); output.flush(); os.fsync(output.fileno())
            os.replace(temporary,path)
            directory = os.open(path.parent,os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)

    @contextmanager
    def lock(self, key: str):
        if platform.system() != 'Linux': raise ContractError('NATIVE_STATIC_BACKEND_UNAVAILABLE')
        import fcntl
        self.cache.mkdir(parents=True,exist_ok=True,mode=0o700)
        if self.cache.is_symlink(): raise ContractError('NATIVE_CACHE_SYMLINK')
        descriptor = os.open(self.cache/('.'+key+'.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(descriptor,fcntl.LOCK_EX); yield
        finally: fcntl.flock(descriptor,fcntl.LOCK_UN); os.close(descriptor)

    def context(self, name: str) -> dict[str, Any]:
        manifest = json.loads(self.read(self.root/'runtime/toolchains/NATIVE_RECIPES.json'))
        if manifest.get('schema') != 'qikvrt-native-recipes/v1' or platform.system() not in manifest['platforms']:
            raise ContractError('NATIVE_STATIC_BACKEND_UNAVAILABLE')
        recipe = manifest['recipes'].get(name)
        if not recipe or recipe['kind'] not in ('core','hot_layer'): raise ContractError('NATIVE_RECIPE_NOT_REGISTERED')
        if '-static' not in manifest['flags']: raise ContractError('NATIVE_STATIC_LINKAGE_REQUIRED')
        if any(os.environ.get(k) for k in ('CPATH','C_INCLUDE_PATH','LIBRARY_PATH','GCC_EXEC_PREFIX','LD_PRELOAD')):
            raise ContractError('NATIVE_AMBIENT_COMPILER_OVERRIDE')
        inputs = {}
        for relative in recipe['inputs']:
            if Path(relative).is_absolute() or '..' in Path(relative).parts: raise ContractError('NATIVE_SOURCE_OUTSIDE_REPOSITORY')
            path = self.root/relative
            if not path.resolve().is_relative_to(self.root): raise ContractError('NATIVE_SOURCE_OUTSIDE_REPOSITORY')
            inputs[relative] = sha256_bytes(self.read(path))
        if any(path not in inputs for path in recipe['sources']): raise ContractError('NATIVE_UNBOUND_SOURCE')
        executable = shutil.which(self.compiler)
        if not executable: raise ContractError('NATIVE_COMPILER_UNAVAILABLE')
        executable = str(Path(executable).resolve())
        def identify(arg: str) -> str:
            return subprocess.check_output([executable,arg],timeout=10,env={**os.environ,'LC_ALL':'C'}).decode().strip()
        link = {}
        for library in ('libc.a','libgcc.a','crt1.o','crti.o','crtn.o'):
            path = Path(identify('-print-file-name='+library))
            if not path.is_absolute(): raise ContractError('NATIVE_STATIC_LINK_INPUT_UNAVAILABLE: '+library)
            link[library] = sha256_bytes(self.read(path.resolve()))
        scan = subprocess.run([executable,'-M','-I'+str(self.root/'include'),*[str(self.root/p) for p in recipe['sources']]],capture_output=True,timeout=10)
        if scan.returncode: raise ContractError('NATIVE_COMPILE_FAILED: '+scan.stderr.decode(errors='replace')[-1000:])
        dependencies = scan.stdout.decode().replace('\\\n','')
        system_headers = {p:sha256_bytes(self.read(Path(p).resolve())) for p in dependencies.split() if p.startswith('/') and not Path(p).resolve().is_relative_to(self.root)}
        binding = {'schema':'qikvrt-native-artifact/v1','recipe':name,'contract':recipe,'inputs':inputs,
          'flags':manifest['flags'],'compiler':{'path':executable,'sha256':sha256_bytes(self.read(Path(executable))),
          'version':identify('--version'),'target':identify('-dumpmachine')},'static_link_inputs':link,'system_headers':system_headers,
          'platform':{'os':platform.system(),'machine':platform.machine()},
          'toolchain_lock':sha256_bytes(self.read(self.root/'runtime/toolchains/TOOLCHAIN.lock.tsv')),
          'engine':sha256_bytes(self.read(Path(__file__).resolve()))}
        return {'key':sha256_bytes(canonical_json(binding).encode()),'binding':binding,'policy':manifest['policy']}

    @staticmethod
    def static_elf(data: bytes) -> None:
        if data[:4] != b'\x7fELF' or data[4] not in (1,2) or data[5] not in (1,2): raise ContractError('NATIVE_ELF_UNVERIFIED')
        endian = '<' if data[5]==1 else '>'
        offset = struct.unpack_from(endian+('Q' if data[4]==2 else 'I'),data,32 if data[4]==2 else 28)[0]
        size,count = struct.unpack_from(endian+'HH',data,54 if data[4]==2 else 42)
        if not count or size<4 or offset+size*count>len(data): raise ContractError('NATIVE_ELF_HEADERS_INVALID')
        if any(struct.unpack_from(endian+'I',data,offset+i*size)[0] in (2,3) for i in range(count)):
            raise ContractError('NATIVE_DYNAMIC_LINKAGE_REJECTED')

    def self_test(self, binary: Path, recipe: dict[str, Any]) -> str:
        reply = subprocess.run([str(binary),*recipe.get('self_test_args',[])],capture_output=True,timeout=30)
        if reply.returncode or recipe['self_test_marker'].encode() not in reply.stdout: raise ContractError('NATIVE_SELF_TEST_FAILED')
        return reply.stdout.decode().strip()

    def prepare(self, name: str, budget_ms: float = 60000) -> dict[str, Any]:
        start = time.perf_counter_ns()
        try:
            if not 0 < budget_ms <= 60000: raise ContractError('NATIVE_BUDGET_INVALID')
            context = self.context(name); key = context['key']; binding = context['binding']; recipe = binding['contract']
            self.emit('LOOKUP',recipe=name,key=key)
            with self.lock(key):
                directory = self.cache/key
                if directory.is_symlink(): raise ContractError('NATIVE_CACHE_SYMLINK')
                compiled = not directory.exists()
                if compiled:
                    self.emit('COMPILE',recipe=name,key=key,budget_ms=budget_ms)
                    with tempfile.TemporaryDirectory(dir=self.cache,prefix='.compile-') as temporary:
                        stage = Path(temporary)
                        for relative,digest in binding['inputs'].items():
                            raw = self.read(self.root/relative)
                            if sha256_bytes(raw)!=digest: raise ContractError('NATIVE_SOURCE_CHANGED')
                            path = stage/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
                        binary = stage/'native'; compile_start = time.perf_counter_ns()
                        reply = subprocess.run([binding['compiler']['path'],*binding['flags'],'-I'+str(stage/'include'),
                            *[str(stage/p) for p in recipe['sources']],'-o',str(binary)],capture_output=True,timeout=max(.001,budget_ms/1000))
                        if reply.returncode: raise ContractError('NATIVE_COMPILE_FAILED: '+reply.stderr.decode(errors='replace')[-1000:])
                        compile_ns = time.perf_counter_ns()-compile_start
                        data = self.read(binary); self.static_elf(data); self.self_test(binary,recipe)
                        if self.context(name)['key']!=key: raise ContractError('NATIVE_BINDING_CHANGED')
                        receipt = {'key':key,'binding':binding,'binary_sha256':sha256_bytes(data),'compile_ns':compile_ns}
                        os.chmod(binary,0o500)
                        with binary.open('rb') as payload: os.fsync(payload.fileno())
                        artifact = stage/'artifact'; artifact.mkdir(); os.rename(binary,artifact/'native')
                        self.save(artifact/'receipt.json',receipt); os.rename(artifact,directory)
                        parent = os.open(self.cache,os.O_RDONLY)
                        try: os.fsync(parent)
                        finally: os.close(parent)
                receipt = json.loads(self.read(directory/'receipt.json')); data = self.read(directory/'native')
                if receipt.get('key')!=key or receipt.get('binding')!=binding or sha256_bytes(data)!=receipt.get('binary_sha256'):
                    raise ContractError('NATIVE_BINARY_DIGEST_MISMATCH')
                self.static_elf(data); self.emit('SELF_TEST',recipe=name,key=key)
                output = self.self_test(directory/'native',recipe)
                if self.context(name)['key']!=key: raise ContractError('NATIVE_BINDING_CHANGED')
                result = {'schema':'qikvrt-native-runtime/v1','state':'READY','recipe':name,'key':key,'compiled':compiled,
                  'decision':'COMPILED' if compiled else 'EXACT_CACHE_HIT','binary':str(directory/'native'),
                  'binary_sha256':receipt['binary_sha256'],'static_linkage_verified':True,'compile_ns':receipt['compile_ns'],
                  'elapsed_ns':time.perf_counter_ns()-start,'self_test_output':output,
                  'observed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                  'cause':'Exact source/compiler/target binding and current native self-test passed.',
                  'whole_transputer_verified':False,'effect_ack_done':False}
                self.save(self.cache/'status.json',result); self.emit(result['decision'],recipe=name,key=key,elapsed_ns=result['elapsed_ns'])
                return result
        except (ContractError,OSError,ValueError,subprocess.SubprocessError,struct.error) as error:
            self.save(self.cache/'status.json',{'schema':'qikvrt-native-runtime/v1','state':'BLOCK','recipe':name,
              'cause':str(error),'whole_transputer_verified':False,'effect_ack_done':False})
            self.emit('BLOCK',recipe=name,cause=str(error)); raise ContractError(str(error)) from error

    def record_usage(self, name: str, baseline_ns: int, native_ns: int | None = None) -> None:
        if baseline_ns<=0 or native_ns is not None and native_ns<=0: raise ContractError('NATIVE_TIMING_INVALID')
        context = self.context(name)
        with self.lock('usage'):
            path = self.cache/'usage.json'
            usage = json.loads(self.read(path)) if path.exists() else {'schema':'qikvrt-native-usage/v1','profiles':{}}
            profile = usage['profiles'].setdefault(context['key'],{'recipe':name,'calls':0,'baseline_ns':0,'native_samples':0,'native_ns':0})
            profile['calls']+=1; profile['baseline_ns']+=baseline_ns
            if native_ns is not None: profile['native_samples']+=1; profile['native_ns']+=native_ns
            self.save(path,usage)
        self.emit('USAGE',recipe=name,key=context['key'],calls=profile['calls'])

    def plan(self, budget_ms: float | None = None) -> dict[str, Any]:
        manifest = json.loads(self.read(self.root/'runtime/toolchains/NATIVE_RECIPES.json')); policy=manifest['policy']
        budget = policy['compile_budget_ms'] if budget_ms is None else budget_ms
        if budget<=0: raise ContractError('NATIVE_BUDGET_INVALID')
        usage = self.cache/'usage.json'; profiles = json.loads(self.read(usage))['profiles'] if usage.exists() else {}
        candidates=[]
        for name,recipe in manifest['recipes'].items():
            if recipe['kind']!='hot_layer': continue
            context=self.context(name); profile=profiles.get(context['key'])
            if not profile or profile['calls']<policy['min_hot_calls'] or (self.cache/context['key']).exists(): continue
            saving = profile['baseline_ns']/profile['calls']-profile['native_ns']/profile['native_samples'] if profile['native_samples'] else None
            cost=policy['trial_cost_ms']*1000000
            benefit=saving*profile['calls']-cost if saving is not None else 0
            if saving is not None and (saving<=0 or benefit<=0): continue
            candidates.append({'recipe':name,'key':context['key'],'calls':profile['calls'],'projected_net_saving_ns':benefit,
              'reason':'MEASURED_AMORTIZATION' if saving is not None else 'BOUNDED_HOT_PATH_TRIAL',
              'estimated_compile_ms':cost/1000000,'break_even_calls':int(cost/saving)+1 if saving else None})
        candidates.sort(key=lambda c:(c['reason']=='MEASURED_AMORTIZATION',c['projected_net_saving_ns'],c['calls']),reverse=True)
        selected=[]; remaining=budget
        for candidate in candidates:
            if len(selected)>=policy['max_compilations']: break
            if candidate['estimated_compile_ms']<=remaining: selected.append(candidate); remaining-=candidate['estimated_compile_ms']
        result={'schema':'qikvrt-native-plan/v1','selected':selected,'budget_ms':budget,
          'assumption':'One further window with the recorded frequency; timing is not proof authority.','effect_ack_done':False}
        self.emit('PLAN',selected=[c['recipe'] for c in selected],budget_ms=budget); return result

    def optimize(self, budget_ms: float | None = None) -> dict[str, Any]:
        plan=self.plan(budget_ms); start=time.perf_counter_ns(); results=[]
        for candidate in plan['selected']:
            remaining=plan['budget_ms']-(time.perf_counter_ns()-start)/1000000
            if remaining<=0: break
            results.append(self.prepare(candidate['recipe'],remaining))
        return {'plan':plan,'results':results,'elapsed_ns':time.perf_counter_ns()-start,'effect_ack_done':False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("render", "verify", "native-prepare", "native-record", "native-plan", "native-optimize"))
    parser.add_argument('--recipe',default='effect-ack-core-conformance')
    parser.add_argument('--cache-dir',type=Path)
    parser.add_argument('--budget-ms',type=float)
    parser.add_argument('--baseline-ns',type=int)
    parser.add_argument('--native-ns',type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "render":
            render()
        elif args.command=='verify':
            verify()
        else:
            verify()
            runtime=NativeRuntime(cache=args.cache_dir)
            if args.command=='native-prepare': result=runtime.prepare(args.recipe,60000 if args.budget_ms is None else args.budget_ms)
            elif args.command=='native-plan': result=runtime.plan(args.budget_ms)
            elif args.command=='native-optimize': result=runtime.optimize(args.budget_ms)
            else:
                if args.baseline_ns is None: raise ContractError('NATIVE_TIMING_REQUIRED')
                runtime.record_usage(args.recipe,args.baseline_ns,args.native_ns); result={'recorded':True}
            print(json.dumps(result,sort_keys=True))
    except ContractError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
