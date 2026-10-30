# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Measurement: OpenAI Codex.
"""Five warm-cache paired trials of the existing native/reference archive CLIs.

Run from repository root: python -B MEASUREMENT.py PROOF_DIRECTORY OUTPUT.json
The proof directory must have been produced by qikvrt_native_archive.py.
No package installation, network access, runtime admission or default switch.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path.cwd()))
from tools.qikvrt_native_archive import compile_native, file_digest


def measured(command):
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter_ns()
    result = subprocess.run(command, capture_output=True, timeout=900)
    wall = time.perf_counter_ns() - start
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    row = {"command": command, "exit": result.returncode, "wall_ns": wall,
           "child_user_cpu_ns": round((after.ru_utime-before.ru_utime)*1e9),
           "child_system_cpu_ns": round((after.ru_stime-before.ru_stime)*1e9),
           "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
           "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()}
    if result.returncode:
        raise RuntimeError(row)
    return row


def main():
    proof, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    original = json.loads((proof/'EVIDENCE.json').read_text())
    archive, wire, binary = [proof/name for name in
                            ('repository.zip', 'repository.qikvrt', 'qikvrt-archive')]
    expected = {archive: original['archive_sha256'], wire: original['wire_sha256'],
                binary: original['build']['binary_sha256']}
    for path, digest in expected.items():
        if file_digest(path) != digest:
            raise ValueError('PROOF_INPUT_CHANGED: '+str(path))
    with tempfile.TemporaryDirectory(prefix='qikvrt-codec-measurement-') as directory:
        scratch = Path(directory)
        # Compilation is measured separately, never charged to a codec trial.
        cpu0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        start = time.perf_counter_ns()
        build = compile_native(scratch/'compiled')
        compile_ns = time.perf_counter_ns()-start
        cpu1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        if build['binary_sha256'] != expected[binary]:
            raise ValueError('MEASURED_BINARY_DIFFERS_FROM_PROOF')
        startup = {"native": [], "python": []}
        for _ in range(5):
            startup['native'].append(measured([str(binary), '--version']))
            startup['python'].append(measured([sys.executable, '-B', '-c',
                                               'from src import qikvrt_codec']))
        io = []
        for _ in range(3):
            start = time.perf_counter_ns()
            with archive.open('rb') as source, (scratch/'io-copy').open('wb') as target:
                shutil.copyfileobj(source, target, 1024*1024)
                target.flush(); os.fsync(target.fileno())
            io.append({'operation':'buffered_copy_with_fsync',
                       'wall_ns':time.perf_counter_ns()-start,
                       'bytes':archive.stat().st_size})
        (scratch/'io-copy').unlink()
        trials = []
        for pair in range(5):
            # Alternation reduces systematic order effects. Hash validation
            # warms inputs; the series does not make a cold-cache claim.
            for operation in ('encode', 'decode'):
                for implementation in (('python','native') if pair%2==0
                                       else ('native','python')):
                    destination = scratch/'result'
                    source = archive if operation=='encode' else wire
                    if implementation=='native':
                        args = ([str(binary), 'encode', 'balanced', str(source), str(destination)]
                                if operation=='encode' else
                                [str(binary), 'decode', str(source), str(destination)])
                    else:
                        args = [sys.executable, '-B', '-m', 'src.qikvrt_codec', operation,
                                str(source), str(destination), '--max-output-bytes', str(2**31-1)]
                    row = measured(args)
                    wanted = original['wire_sha256' if operation=='encode' else 'archive_sha256']
                    actual = file_digest(destination)
                    if actual != wanted:
                        raise ValueError('TIMED_RESULT_MISMATCH')
                    row.update(pair=pair,operation=operation,implementation=implementation,
                               result_bytes=destination.stat().st_size,result_sha256=actual)
                    trials.append(row)
                    destination.unlink()
                    print(json.dumps({k:row[k] for k in ('pair','operation','implementation','wall_ns')}),flush=True)
        summary = {}
        for operation in ('encode','decode'):
            medians = {}
            for impl in ('python','native'):
                rows=[r for r in trials if r['operation']==operation and r['implementation']==impl]
                medians[impl]={'wall_ns':statistics.median(r['wall_ns'] for r in rows),
                               'cpu_ns':statistics.median(r['child_user_cpu_ns']+r['child_system_cpu_ns'] for r in rows)}
            summary[operation]={'median':medians,
                'python_over_native_wall_ratio':medians['python']['wall_ns']/medians['native']['wall_ns']}
        for path,digest in expected.items():
            if file_digest(path)!=digest: raise ValueError('PROOF_INPUT_CHANGED_DURING_MEASUREMENT')
        result={'schema':'qikvrt-native-archive-paired-measurement/v1',
                'scope':'COMPLETE_SELECTED_ARCHIVE_CODEC_CLI_WARM_CACHE_NOT_FULL_CI',
                'source':original['source'],'archive_bytes':archive.stat().st_size,
                'archive_sha256':expected[archive], 'wire_sha256':expected[wire],
                'binary_sha256':expected[binary],
                'source_sha256':{**original['build']['sources_sha256'],
                    'src/qikvrt_codec.py':file_digest(Path.cwd()/'src/qikvrt_codec.py')},
                'build':build,'compile_wall_ns':compile_ns,
                'compile_child_cpu_ns':round((cpu1.ru_utime+cpu1.ru_stime-cpu0.ru_utime-cpu0.ru_stime)*1e9),
                'host':{'platform':platform.platform(),'machine':platform.machine(),
                        'cpu_affinity':sorted(os.sched_getaffinity(0)),
                        'python':sys.version,'uname_node_sha256':hashlib.sha256(platform.node().encode()).hexdigest()},
                'repeats':5,'order':'alternating Python/native by pair',
                'timing':'wall and child user/system CPU include CLI startup, I/O and fsync; compilation, startup baseline and I/O baseline reported separately without subtraction',
                'io_baseline':io,'startup_baseline':startup,'trials':trials,'summary':summary,
                'limitations':['warm cache only; no cold-cache or full-CI speedup claim',
                               'Python reference additionally calculates a raw payload digest',
                               'buffered I/O baseline does not isolate all filesystem effects',
                               'shared host; no claim of exclusive hardware allocation'],
                'native_default_changed':False,'effect_ack_done':False}
        output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
