#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Seed-bound durable Firefox witness on Windows/Linux; no product release acceptance."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import platform
import queue
import random
import shutil
from concurrent.futures import ThreadPoolExecutor
import socket
import struct
import statistics
import stat
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'policy/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.json'
CANONICAL_PRODUCT_URL = 'https://goldkelch.github.io/qik-vrt/'
PUBLIC_BODY_LIMIT = 2 * 1024 * 1024


class NoPublicRedirect(urllib.request.HTTPRedirectHandler):
    """A different URL must never stand in for the canonical product URL."""
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def public_http_readback(url, output):
    if url != CANONICAL_PRODUCT_URL:
        raise RuntimeError('CANONICAL_PRODUCT_URL_MISMATCH')
    result = {'requested_url': url, 'method': 'GET', 'redirects_followed': False,
              'started_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'status': None, 'final_url': None, 'body_sha256': None,
              'body_truncated': False, 'response_observed': False,
              'request_cache_control': 'no-cache', 'authenticated_request': False}
    request = urllib.request.Request(url, headers={
        'Cache-Control': 'no-cache', 'Pragma': 'no-cache',
        'User-Agent': 'QIKVRT-public-url-readback/1'})
    opener = urllib.request.build_opener(NoPublicRedirect())
    try:
        try:
            response = opener.open(request, timeout=30)
        except urllib.error.HTTPError as error:
            # 404 is evidence to retain, not a transport success or a test crash.
            response = error
        with response:
            body = response.read(PUBLIC_BODY_LIMIT + 1)
            result.update(status=response.code, final_url=response.geturl(),
                          response_observed=True, body_truncated=len(body) > PUBLIC_BODY_LIMIT,
                          body_bytes=len(body), body_sha256=hashlib.sha256(body).hexdigest(),
                          headers={name: response.headers.get(name) for name in (
                              'Date', 'Content-Type', 'ETag', 'Last-Modified', 'Server',
                              'Age', 'X-Cache', 'X-GitHub-Request-Id', 'Location')})
            artifact = output / 'PUBLIC_URL_HTTP.html'
            artifact.write_bytes(body)
            result['body_artifact'] = artifact.name
    except (OSError, urllib.error.URLError, ValueError) as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    result['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
    return result


def evaluate_public_url_readback(http, browser, expected_body_sha256, contract):
    """Accept only fresh canonical root bytes and DOM, never a full release."""
    reasons = []
    if http.get('error') or http.get('response_observed') is not True:
        reasons.append('HTTP_OBSERVATION_INCOMPLETE')
    if http.get('status') != 200:
        reasons.append('PUBLIC_HTTP_' + str(http.get('status') or 'UNOBSERVED'))
    if http.get('final_url') != contract['canonical_url']:
        reasons.append('CANONICAL_HTTP_URL_NOT_VERIFIED')
    if http.get('body_truncated') or http.get('body_sha256') != expected_body_sha256:
        reasons.append('CANDIDATE_DOCS_INDEX_BYTES_NOT_VERIFIED')
    if browser.get('url') != contract['canonical_url']:
        reasons.append('CANONICAL_BROWSER_URL_NOT_VERIFIED')
    if browser.get('github_pages_404'):
        reasons.append('GITHUB_PAGES_SITE_NOT_FOUND')
    if browser.get('error') or browser.get('extension_installed') is not False:
        reasons.append('UNINJECTED_BROWSER_OBSERVATION_NOT_VERIFIED')
    if (browser.get('title') != contract['expected_document_title']
            or browser.get('product_main_present') is not True):
        reasons.append('PRODUCT_BROWSER_DOM_NOT_VERIFIED')
    if browser.get('navigation_response_status') not in (None, 200):
        reasons.append('BROWSER_HTTP_STATUS_NOT_SUCCESSFUL')
    return {'state': 'HOLD' if reasons else 'PASS', 'unmet_conditions': reasons,
            'public_url_fresh_readback': not reasons,
            'evidence_scope': 'CANONICAL_ROOT_DOCS_INDEX_BYTES_AND_BROWSER_DOM_ONLY',
            'deployed_candidate_head_tree_verified': False,
            'personal_release_effect_ack_done': False}


def observe_public_url(driver, contract, subject, output):
    acceptance = contract['public_url_acceptance']
    url = contract['terminal_url']
    if url != CANONICAL_PRODUCT_URL or acceptance['canonical_url'] != url:
        raise RuntimeError('CANONICAL_PRODUCT_URL_MISMATCH')
    expected = digest(ROOT / acceptance['source_file'])
    http = public_http_readback(url, output)
    browser = {'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
               'url': None, 'title': None, 'product_main_present': False,
               'navigation_response_status': None, 'extension_installed': False}
    try:
        # Observe the actual public page before the extension can inject a UI.
        driver.command('/url', {'url': url})
        browser.update(driver.script(
            'const n=performance.getEntriesByType("navigation")[0];'
            'const text=document.body?.innerText||"";'
            'return {url:location.href,title:document.title,'
            'navigation_response_status:n?.responseStatus||null,'
            'product_main_present:!!document.querySelector("main#main"),'
            'github_pages_404:document.title==="Site not found · GitHub Pages"||'
            'text.includes("There isn\\\'t a GitHub Pages site here."),'
            'body_text:text.slice(0,131072),body_text_truncated:text.length>131072};'))
        screenshot = output / 'PUBLIC_URL_BROWSER.png'
        screenshot.write_bytes(base64.b64decode(driver.command('/screenshot', method='GET')))
        browser.update(screenshot_artifact=screenshot.name, screenshot_sha256=digest(screenshot))
    except (OSError, RuntimeError) as error:
        browser['error'] = type(error).__name__ + ': ' + str(error)
    browser['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
    result = {'schema': 'qikvrt_public_url_fresh_readback_v1',
              'repository': os.environ.get('GITHUB_REPOSITORY', 'ingolf-lohmann/qik-vrt'),
              'head': subject['head'], 'tree': subject['tree'],
              'run_id': subject['run_id'], 'run_attempt': subject['run_attempt'],
              'job': subject['job'], 'policy_sha256': subject['policy_sha256'],
              'observer_sha256': digest(__file__), 'observed_at': http['started_at'],
              'canonical_url': url, 'candidate_source_file': acceptance['source_file'],
              'candidate_source_sha256': expected, 'http': http, 'browser': browser,
              'predecessor_evidence_transfer': False, 'external_effect': 'NONE',
              'authority_configuration_verified': False,
              'authority_capability_hold_ref': acceptance['authority_capability_hold_ref']}
    result.update(evaluate_public_url_readback(http, browser, expected, acceptance))
    path = output / 'PUBLIC_URL_READBACK.json'
    path.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return result, {'path': path.name, 'sha256': digest(path)}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pe_architecture(path):
    with Path(path).open('rb') as binary:
        binary.seek(0x3c)
        offset = struct.unpack('<I', binary.read(4))[0]
        binary.seek(offset)
        if binary.read(4) != b'PE\0\0':
            raise RuntimeError('INVALID_WINDOWS_EXECUTABLE')
        machine = struct.unpack('<H', binary.read(2))[0]
    return {0x8664: 'AMD64', 0xaa64: 'ARM64', 0x14c: 'X86'}.get(machine, hex(machine))


def target_matches(os_info, target, today=None):
    """Native OS data, not a runner label, decides the supported product scope."""
    today = today or dt.datetime.now(dt.timezone.utc).date().isoformat()
    return (os_info.get('product_type') == 1
            and os_info.get('build') == target['build']
            and os_info.get('display_version') == target['display_version']
            and os_info.get('edition') in target['editions']
            and os_info.get('architecture') in target['architectures']
            and target['supported_from'] <= today < target['support_until'])


def windows_identity():
    if sys.platform != 'win32':
        raise RuntimeError('WINDOWS_EXECUTION_REQUIRED')
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                        r'SOFTWARE\Microsoft\Windows NT\CurrentVersion') as key:
        values = {k: winreg.QueryValueEx(key, v)[0] for k, v in
                  [('edition', 'EditionID'), ('display_version', 'DisplayVersion'),
                   ('build', 'CurrentBuildNumber'), ('ubr', 'UBR')]}
    # ProductType 1 is client workstation; 2/3 are domain controller/server.
    product = subprocess.check_output(
        ['powershell', '-NoProfile', '-Command',
         '(Get-CimInstance Win32_OperatingSystem).ProductType'], text=True, timeout=30)
    # Read the native machine, including when Python itself is emulated.
    import ctypes
    from ctypes import wintypes
    native = wintypes.USHORT()
    process = wintypes.USHORT()
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.GetCurrentProcess.restype = wintypes.HANDLE
    api.IsWow64Process2.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.USHORT),
                                   ctypes.POINTER(wintypes.USHORT)]
    api.IsWow64Process2.restype = wintypes.BOOL
    if not api.IsWow64Process2(api.GetCurrentProcess(), ctypes.byref(process), ctypes.byref(native)):
        raise ctypes.WinError(ctypes.get_last_error())
    names = {0x8664: 'AMD64', 0xaa64: 'ARM64', 0x14c: 'X86'}
    values.update(product_type=int(product.strip()), build=int(values['build']),
                  architecture=names.get(native.value, hex(native.value)),
                  process_architecture=names.get(process.value or native.value, hex(process.value)),
                  architecture_method='IsWow64Process2_NATIVE_MACHINE', platform=platform.platform())
    return values


def provision_driver(contract, cache, architecture):
    item = contract['geckodriver']['archives'][architecture]
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / item['name']
    if not archive.exists() or digest(archive) != item['sha256']:
        archive.unlink(missing_ok=True)
        with urllib.request.urlopen(item['url'], timeout=60) as response:
            data = response.read(20 * 1024 * 1024 + 1)
        if len(data) > 20 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise RuntimeError('DRIVER_ARCHIVE_HASH_MISMATCH')
        archive.write_bytes(data)
    executable = cache / 'geckodriver.exe'
    # Re-extract the verified archive even on a warm cache; reject substitutions.
    with zipfile.ZipFile(archive) as bundle:
        executable.write_bytes(bundle.read('geckodriver.exe'))
    version = subprocess.check_output([str(executable), '--version'], text=True, timeout=20)
    if not version.startswith('geckodriver ' + contract['geckodriver']['version'] + ' '):
        raise RuntimeError('DRIVER_VERSION_MISMATCH')
    return executable


class WebDriver:
    def __init__(self, executable, log):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        self.base = f'http://127.0.0.1:{port}'
        self.session = None
        self.process = subprocess.Popen([str(executable), '--host', '127.0.0.1',
                                         '--port', str(port), '--allow-system-access'],
                                        stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                self.call('GET', '/status')
                return
            except (OSError, RuntimeError):
                if self.process.poll() is not None:
                    raise RuntimeError('DRIVER_EXITED')
                time.sleep(.2)
        raise RuntimeError('DRIVER_START_TIMEOUT')

    def call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data, method=method,
                                         headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)['value']
        if isinstance(result, dict) and result.get('error'):
            raise RuntimeError(result['error'])
        return result

    def command(self, path, body=None, method='POST'):
        return self.call(method, '/session/' + self.session + path, body)

    def script(self, script, args=None):
        return self.command('/execute/sync', {'script': script, 'args': args or []})

    def close(self):
        try:
            if self.session:
                self.command('', method='DELETE')
        finally:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)


def readback():
    with urllib.request.urlopen('http://127.0.0.1:8771/terminal/state', timeout=10) as r:
        return json.load(r)


def verify_effect_readback(before, after, prepared, request, subject):
    """Independently bind the observed backend event to actual prepared bytes."""
    def canonical_hash(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                         ensure_ascii=False).encode()).hexdigest()
    event = after.get('last_event') or {}
    record = dict(prepared['full_record'])
    record_hash = record.pop('record_hash')
    input_hash = canonical_hash(request)
    return (after['events'] == before['events'] + 1
            and event.get('text') == request['text']
            and event.get('record_hash') == prepared['effect_ack']['record_hash']
            and record_hash == 'sha256:' + canonical_hash(record)
            and record_hash == 'sha256:' + event['record_hash']
            and event.get('input_hash') == input_hash
            and record['input_hash'] == 'sha256:' + input_hash
            and after['repository_head'] == subject['head']
            and after['repository_tree'] == subject['tree'])


class TerminalProcess:
    """Bounded supervision of the actual durable CLI, also reused by regressions."""
    def __init__(self, state_root, seed, *, port=0, command=None, ring=False):
        arguments = ['--ring-root' if ring else '--state-root', str(state_root),
                     '--seed', str(seed), '--port', str(port)]
        self.process = subprocess.Popen(
            (command or [sys.executable, '-B', str(ROOT / 'src/qikvrt_effect_ack_http_terminal.py')]) + arguments,
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ready = queue.Queue()
        threading.Thread(target=lambda: ready.put(self.process.stdout.readline()), daemon=True).start()
        try:
            line = ready.get(timeout=15)
            if not line:
                raise RuntimeError('TERMINAL_PROCESS_START_FAILED: ' + self.process.stderr.read(4096))
            self.ready = json.loads(line)
            if self.ready.get('persistence_scope') != 'FSYNCED_ATOMIC_SNAPSHOT_RESTART_SAFE':
                raise RuntimeError('TERMINAL_PROCESS_NOT_DURABLE')
            self.port = self.ready['port']
        except BaseException:
            self.close()
            raise

    def request(self, path, body=None, field=None):
        data = None if body is None else json.dumps(body, ensure_ascii=False, sort_keys=True,
                                                  separators=(',', ':'), allow_nan=False).encode('utf-8')
        request = urllib.request.Request('http://127.0.0.1:' + str(self.port) + path, data=data,
            headers={'Content-Type': 'application/json', 'Cache-Control': 'no-cache',
                     **({'Effect-Ack-Request': field} if field else {})})
        try:
            response = urllib.request.urlopen(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, json.load(response)

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=15)
        self.process.stdout.close()
        self.process.stderr.close()


def lossless_scale_consolidation_controls(terminal, ring_root, seed, *, workload=16):
    """Expand actual POSIX processes 1/2/4; consolidate unchanged stores in one.

    Every preparation retains its origin. No token, key, record or event is
    rewritten; concurrent retries and wrong-origin commits must be refused.
    Measurements include equivalent request counts but differing retained state,
    and therefore do not by themselves claim a speedup.
    """
    if type(workload) is not int or not 4 <= workload <= 64 or workload % 4:
        raise ValueError('workload must be 4..64 and divisible by four')
    if ring_root.exists():
        raise RuntimeError('NEW_RING_ROOT_REQUIRED_NO_STATE_RESET')
    ring_root.mkdir(parents=True)
    processes = []
    consolidated = None
    consumed = []
    pending = []
    timings = []

    def prepare(client, payload, prefix=''):
        status, prepared = client.request(prefix + '/terminal/prepare', payload, 'v=1, mode=prepare')
        if status != 200 or prepared.get('ordinary_release') is not False:
            raise RuntimeError('RING_PREPARE_NOT_CONFIRMED')
        field = ('v=1, mode=commit, token=' + terminal.sf_bytes(prepared['commit_token'].encode('ascii'))
                 + ', hash=' + terminal.sf_bytes(bytes.fromhex(prepared['record_hash'])))
        return field

    def read(client, node, prefix=''):
        status, snapshot = client.request(prefix + '/terminal/events')
        if status != 200 or snapshot['events_sha256'] != terminal.sha256(terminal.canonical_json(snapshot['events'])):
            raise RuntimeError('RING_EVENT_SNAPSHOT_INVALID')
        records = {}
        for event in snapshot['events']:
            for digest in (event['record_hash'], event['effect_record_hash']):
                path = '/effect-ack/records/' + digest
                status, record = client.request(prefix + path)
                projection = {key: value for key, value in record.items() if key != 'record_hash'}
                if status != 200 or record.get('record_hash') != 'sha256:' + terminal.sha256(terminal.canonical_json(projection)):
                    raise RuntimeError('RING_EFFECT_RECORD_INVALID')
                records[path] = record
        return {'node_id': node, 'snapshot': snapshot, 'records': records}

    def transfer_unchanged(before, after):
        if before != after:
            raise RuntimeError('RING_ORIGIN_EVENTS_OR_EFFECT_RECORDS_CHANGED')

    try:
        for workers in (1, 2, 4):
            retained = [read(p, 'node-' + str(i)) for i, p in enumerate(processes)]
            old_bytes = [(ring_root / ('node-' + str(i)) / '.qikvrt/api/terminal.json').read_bytes()
                         for i in range(len(processes))]
            for i in range(len(processes), workers):
                processes.append(TerminalProcess(ring_root / ('node-' + str(i)), seed))
            transfer_unchanged(retained, [read(p, 'node-' + str(i))
                                         for i, p in enumerate(processes[:len(retained)])])
            if old_bytes != [(ring_root / ('node-' + str(i)) / '.qikvrt/api/terminal.json').read_bytes()
                             for i in range(len(retained))]:
                raise RuntimeError('SCALE_REWROTE_RETAINED_STORE')
            tasks = [(index % workers, {'schema': 'qikvrt_terminal_input_v1',
                      'text': 'scale-' + str(workers) + '-' + str(index) + '-' + os.urandom(12).hex()})
                     for index in range(workload)]
            def commit(task):
                node, payload = task
                field = prepare(processes[node], payload)
                status, result = processes[node].request('/terminal/commit', payload, field)
                if status != 200 or result.get('ordinary_release') is not True:
                    raise RuntimeError('RING_COMMIT_NOT_CONFIRMED')
                return node, payload, field
            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=4) as pool:
                consumed.extend(pool.map(commit, tasks))
            elapsed = time.perf_counter() - started
            views = [read(p, 'node-' + str(i)) for i, p in enumerate(processes)]
            texts = [event['text'] for view in views for event in view['snapshot']['events']]
            expected = [payload['text'] for _, payload, _ in consumed]
            if len(texts) != len(expected) or sorted(texts) != sorted(expected):
                raise RuntimeError('SCALE_LOST_OR_DUPLICATED_EVENT')
            timings.append({'processes': workers, 'process_ids': [p.process.pid for p in processes],
                            'requests': workload, 'parallel_clients': 4,
                            'elapsed_seconds': elapsed, 'confirmed_effects_per_second': workload / elapsed,
                            'retained_events': len(texts)})

        race_payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'scale-race-' + os.urandom(12).hex()}
        race_field = prepare(processes[0], race_payload)
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(lambda _: processes[0].request('/terminal/commit', race_payload, race_field)[0], range(8)))
        if sorted(statuses) != [200] + [409] * 7:
            raise RuntimeError('SCALED_RING_TOKEN_RACE_NOT_EXACTLY_ONCE')
        consumed.append((0, race_payload, race_field))
        for node, client in enumerate(processes):
            payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'pending-' + os.urandom(12).hex()}
            field = prepare(client, payload)
            if processes[(node + 1) % 4].request('/terminal/commit', payload, field)[0] != 409:
                raise RuntimeError('TOKEN_ACCEPTED_BY_WRONG_ORIGIN')
            pending.append((node, payload, field))
        before = [read(p, 'node-' + str(i)) for i, p in enumerate(processes)]
        raw_before = {('node-' + str(i)): (ring_root / ('node-' + str(i)) / '.qikvrt/api/terminal.json').read_bytes()
                      for i in range(4)}
        source_pids = [p.process.pid for p in processes]
        # All bounded requests have drained. Releasing locks then reacquiring
        # every original store is the explicit quiescent ownership transfer.
        for client in processes:
            client.close()
        processes = []
        consolidated = TerminalProcess(ring_root, seed, ring=True)
        after = [read(consolidated, 'node-' + str(i), '/nodes/node-' + str(i)) for i in range(4)]
        transfer_unchanged(before, after)
        if raw_before != {node: (ring_root / node / '.qikvrt/api/terminal.json').read_bytes() for node in raw_before}:
            raise RuntimeError('CONSOLIDATION_REWROTE_ORIGIN_STORE')
        if consolidated.ready['origin_nodes'] != list(raw_before) or consolidated.process.pid in source_pids:
            raise RuntimeError('ACTUAL_SINGLE_PROCESS_CONSOLIDATION_NOT_OBSERVED')
        for node, payload, field in consumed:
            status, response = consolidated.request('/nodes/node-' + str(node) + '/terminal/commit', payload, field)
            if status != 409 or response.get('ordinary_release') is not False:
                raise RuntimeError('CONSOLIDATION_REPLAY_CREATED_SECOND_EFFECT')
        with ThreadPoolExecutor(max_workers=8) as pool:
            concurrent_retries = list(pool.map(lambda _: consolidated.request(
                '/nodes/node-0/terminal/commit', race_payload, race_field)[0], range(8)))
        if concurrent_retries != [409] * 8:
            raise RuntimeError('CONCURRENT_CONSOLIDATED_REPLAY_NOT_REFUSED')
        transfer_unchanged(before, [read(consolidated, 'node-' + str(i), '/nodes/node-' + str(i)) for i in range(4)])
        if raw_before != {node: (ring_root / node / '.qikvrt/api/terminal.json').read_bytes() for node in raw_before}:
            raise RuntimeError('REPLAY_CHANGED_CONSOLIDATED_SNAPSHOT')
        status, aggregate = consolidated.request('/terminal/events')
        expected_aggregate = [{'node_id': view['node_id'], 'event': event}
                              for view in before for event in view['snapshot']['events']]
        if status != 200 or aggregate['events'] != expected_aggregate or aggregate['events_sha256'] != terminal.sha256(terminal.canonical_json(expected_aggregate)):
            raise RuntimeError('CONSOLIDATED_GLOBAL_READBACK_NOT_LOSSLESS')
        for node, payload, field in pending:
            prefix = '/nodes/node-' + str(node)
            with ThreadPoolExecutor(max_workers=8) as pool:
                statuses = list(pool.map(lambda _: consolidated.request(prefix + '/terminal/commit', payload, field)[0], range(8)))
            if sorted(statuses) != [200] + [409] * 7:
                raise RuntimeError('RETAINED_PREPARATION_LOST_OR_REPLAYED')
        final = [read(consolidated, 'node-' + str(i), '/nodes/node-' + str(i)) for i in range(4)]
        for original, current in zip(before, final):
            if (current['snapshot']['events'][:-1] != original['snapshot']['events']
                    or any(current['records'].get(path) != record for path, record in original['records'].items())):
                raise RuntimeError('OLD_EVENT_OR_RECORD_CHANGED_AFTER_NEW_CONSOLIDATED_EFFECT')
        return {'schema': 'qikvrt_linux_scale_consolidation_readback_v1',
                'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                'process_scale': [1, 2, 4], 'measurements': timings,
                'quiescent_transfer': True, 'source_process_ids': source_pids,
                'consolidated_process_id': consolidated.process.pid, 'consolidated_process_count': 1,
                'origin_nodes_retained': 4, 'origin_snapshot_sha256': {node: terminal.sha256(raw) for node, raw in raw_before.items()},
                'readback_before': before, 'readback_after': after, 'aggregate_readback': aggregate,
                'final_readback': final, 'retained_preparations_committed_once': 4,
                'confirmed_events_before': len(expected_aggregate),
                'confirmed_events_after_new_work': sum(v['snapshot']['event_count'] for v in final),
                'scaled_token_race': {'clients': 8, 'effects': 1, 'refusals': 7},
                'concurrent_retry_statuses': concurrent_retries, 'replay_second_effects': 0,
                'lossless_scope': 'BOUNDED_LOCAL_POSIX_ORIGIN_STORES_PROCESS_SCALE_AND_CONSOLIDATION',
                'external_service_requests': 0, 'external_api_quotas_bypassed': False,
                'cross_host_replication_verified': False, 'live_migration_verified': False,
                'network_loss_injected': False, 'unbounded_scalability_proved': False,
                'comparative_speedup_proved': False, 'private_state_exported': False, 'external_effect': 'NONE'}
    finally:
        for client in processes:
            client.close()
        if consolidated is not None:
            consolidated.close()


def benchmark_distribution(values, *, allow_negative=False):
    """Sample dispersion and linearly interpolated empirical percentiles."""
    ordered = sorted(values)
    if not ordered or any(not math.isfinite(value) or (value < 0 and not allow_negative) for value in ordered):
        raise ValueError('finite nonnegative measurements required')
    def percentile(fraction):
        position = fraction * (len(ordered) - 1)
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    mean = statistics.mean(ordered)
    deviation = statistics.stdev(ordered) if len(ordered) > 1 else 0.0
    return {'n': len(ordered), 'mean': mean, 'sample_stdev': deviation,
            'coefficient_of_variation': deviation / mean if mean else None,
            'min': ordered[0], 'max': ordered[-1],
            'p25': percentile(.25), 'p50': percentile(.5), 'p75': percentile(.75),
            'p95': percentile(.95), 'p99': percentile(.99)}


def benchmark_speedup(baseline, candidate):
    """Conservative paired, bounded observation; never a scalability theorem."""
    if len(baseline) != len(candidate) or len(baseline) < 3:
        raise ValueError('at least three paired repetitions required')
    if any(not math.isfinite(value) or value <= 0 for value in baseline + candidate):
        raise ValueError('positive finite wall times required')
    ratios = [left / right for left, right in zip(baseline, candidate)]
    logs = [math.log(value) for value in ratios]
    generator = random.Random(443)
    samples = sorted(math.exp(statistics.mean(generator.choices(logs, k=len(logs))))
                     for _ in range(5000))
    # Two declared comparisons: Bonferroni-adjusted 97.5% percentile intervals.
    interval = [samples[int(.0125 * (len(samples) - 1))],
                samples[int(.9875 * (len(samples) - 1))]]
    return {'paired_wall_time_ratios': ratios, 'ratio_distribution': benchmark_distribution(ratios),
            'geometric_mean_ratio': math.exp(statistics.mean(logs)),
            'bootstrap_percentile_interval_97_5': interval,
            'bootstrap_resamples': 5000, 'bootstrap_seed': 443,
            'all_repetitions_faster': min(ratios) > 1,
            'minimum_repetitions_for_speedup_claim': 6,
            'speedup_supported': len(ratios) >= 6 and min(ratios) > 1 and interval[0] > 1,
            'scope': 'THIS_HOST_IDENTICAL_PRELOAD_WORKLOAD_AND_FOUR_CLIENTS_ONLY',
            'inference_limit': 'Small paired sample; percentile bootstrap is approximate, not independent replication.'}


def benchmark_persistence_union(intervals, start_ns, end_ns):
    """Union of actual persist intervals; concurrent writes count once in wall time."""
    spans = sorted((max(start_ns, row['start_ns']), min(end_ns, row['end_ns']))
                   for row in intervals if row['end_ns'] > start_ns and row['start_ns'] < end_ns)
    total, right = 0, start_ns
    for left, end in spans:
        total += max(0, end - max(left, right))
        right = max(right, end)
    return total / 1e9


def benchmark_observation(path, parser=lambda value: value.strip()):
    """Unavailable/malformed kernel telemetry is never replaced by a zero."""
    try:
        return {'source': str(path), 'state': 'OBSERVED', 'value': parser(Path(path).read_text())}
    except (OSError, ValueError, IndexError) as error:
        return {'source': str(path), 'state': 'UNAVAILABLE', 'reason': type(error).__name__,
                'errno': getattr(error, 'errno', None)}


def benchmark_keyed_counters(text):
    return {parts[0].rstrip(':'): int(parts[1]) for line in text.splitlines()
            if len(parts := line.split()) == 2}


def benchmark_pressure(text):
    return {parts[0]: {key: (int(value) if key == 'total' else float(value))
            for key, value in (field.split('=', 1) for field in parts[1:])}
            for line in text.splitlines() if (parts := line.split())}


def benchmark_io_stat(text):
    return {parts[0]: {key: int(value) for key, value in
            (field.split('=', 1) for field in parts[1:])}
            for line in text.splitlines() if (parts := line.split())}


def benchmark_mountinfo(text):
    def unescape(value):
        for code, char in (('040', ' '), ('011', '\t'), ('012', '\n'), ('134', '\\')):
            value = value.replace('\\' + code, char)
        return value
    mounts = []
    for line in text.splitlines():
        left, right = line.split(' - ', 1)
        a, b = left.split(), right.split()
        mounts.append({'mount_id': a[0], 'device': a[2], 'root': unescape(a[3]),
                       'mount_point': unescape(a[4]), 'mount_options': a[5],
                       'filesystem': b[0], 'source': unescape(b[1]), 'super_options': b[2]})
    return mounts


def benchmark_cgroup_locations(membership, mounts):
    """Resolve actual membership against mount roots, never assume cgroup root."""
    groups = []
    for line in membership.splitlines():
        _, controllers, member = line.split(':', 2)
        kind = 'v1' if controllers else 'v2'
        selected = [m for m in mounts if m['filesystem'] == ('cgroup' if controllers else 'cgroup2')
                    and (not controllers or set(controllers.split(',')) <= set(m['super_options'].split(',')))]
        for mount in selected:
            try:
                relative = Path(member).relative_to(mount['root'])
            except ValueError:
                groups.append({'version': kind, 'controllers': controllers, 'membership': member,
                               'state': 'UNAVAILABLE', 'reason': 'MEMBERSHIP_OUTSIDE_VISIBLE_MOUNT_ROOT'})
                continue
            leaf = Path(mount['mount_point']) / relative
            if '..' in relative.parts:
                groups.append({'version': kind, 'controllers': controllers, 'membership': member,
                               'state': 'UNAVAILABLE', 'reason': 'MEMBERSHIP_OUTSIDE_VISIBLE_MOUNT_ROOT'})
                continue
            paths, path = [], leaf
            for _ in range(64):
                paths.append(str(path))
                if path == Path(mount['mount_point']):
                    break
                path = path.parent
            else:
                raise ValueError('cgroup ancestry exceeds bounded observability')
            groups.append({'version': kind, 'controllers': controllers, 'membership': member,
                           'mount': mount, 'leaf': str(leaf), 'visible_ancestors': paths,
                           'state': 'OBSERVED', 'host_ancestors_outside_mount_observed': False})
    return groups


def benchmark_telemetry_targets(pids):
    mount_observation = benchmark_observation('/proc/self/mountinfo', benchmark_mountinfo)
    mounts = mount_observation.get('value', [])
    processes = {}
    for pid in [os.getpid(), *pids]:
        membership = benchmark_observation('/proc/' + str(pid) + '/cgroup')
        try:
            groups = benchmark_cgroup_locations(membership['value'], mounts) if membership['state'] == 'OBSERVED' else []
        except (ValueError, IndexError):
            groups = []
        processes[str(pid)] = {'role': 'DRIVER' if pid == os.getpid() else 'SERVER',
                              'membership': membership, 'groups': groups,
                              'cgroup_resolution_state': 'OBSERVED' if any(g['state'] == 'OBSERVED' for g in groups) else 'UNAVAILABLE'}
    return processes


def benchmark_storage_identity(path):
    observation = benchmark_observation('/proc/self/mountinfo', benchmark_mountinfo)
    try:
        device = os.stat(path).st_dev
        number = str(os.major(device)) + ':' + str(os.minor(device))
        candidates = [m for m in observation.get('value', []) if m['device'] == number
                      and Path(path).absolute().is_relative_to(m['mount_point'])]
        mount = max(candidates, key=lambda m: len(m['mount_point'])) if candidates else None
        info = os.statvfs(path)
        sysdev = Path('/sys/dev/block') / number
        return {'state': 'OBSERVED', 'device': number, 'mount': mount,
                'block_device_sysfs': str(sysdev.resolve()) if sysdev.exists() else None,
                'visible_backing_slaves': sorted(p.name for p in (sysdev / 'slaves').iterdir())
                    if (sysdev / 'slaves').is_dir() else [],
                'backing_device_attribution': 'VISIBLE_BLOCK_DEVICE' if sysdev.exists() else 'UNRESOLVED_VIRTUAL_FILESYSTEM',
                'block_size': info.f_bsize, 'fragment_size': info.f_frsize,
                'available_bytes': info.f_bavail * info.f_frsize,
                'physical_storage_isolation_verified': False}
    except OSError as error:
        return {'state': 'UNAVAILABLE', 'reason': type(error).__name__, 'errno': error.errno}


def benchmark_diskstats(text):
    names = ('reads_completed', 'reads_merged', 'sectors_read', 'read_milliseconds',
             'writes_completed', 'writes_merged', 'sectors_written', 'write_milliseconds',
             'in_flight', 'io_milliseconds', 'weighted_io_milliseconds', 'discards_completed',
             'discards_merged', 'sectors_discarded', 'discard_milliseconds',
             'flushes_completed', 'flush_milliseconds')
    return {parts[0] + ':' + parts[1]: {'name': parts[2],
            **dict(zip(names, map(int, parts[3:])))}
            for line in text.splitlines() if len(parts := line.split()) >= 14}


def benchmark_host_cpu(text):
    names = ('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'steal', 'guest', 'guest_nice')
    return dict(zip(names, map(int, text.splitlines()[0].split()[1:])))


def benchmark_process_status(text):
    return {key: int(value.strip()) for line in text.splitlines()
            for key, value in [line.split(':', 1)]
            if key in ('voluntary_ctxt_switches', 'nonvoluntary_ctxt_switches')}


def benchmark_host_snapshot(targets):
    """One before/after boundary read; no poller/tracer or writes to host controls."""
    started, cpu = time.perf_counter_ns(), time.process_time_ns()
    groups, processes = {}, {}
    for pid, target in targets.items():
        processes[pid] = {'role': target['role'],
            'cgroup_membership': benchmark_observation('/proc/' + pid + '/cgroup'),
            'io': benchmark_observation('/proc/' + pid + '/io', benchmark_keyed_counters),
            'main_thread_context_switches': benchmark_observation('/proc/' + pid + '/status', benchmark_process_status)}
        try:
            processes[pid]['affinity_cpus'] = {'state': 'OBSERVED', 'value': sorted(os.sched_getaffinity(int(pid)))}
        except OSError as error:
            processes[pid]['affinity_cpus'] = {'state': 'UNAVAILABLE', 'errno': error.errno}
        for group in target['groups']:
            if group['state'] != 'OBSERVED':
                continue
            for path in group['visible_ancestors']:
                if path in groups:
                    continue  # Shared ancestor is read once, never summed per PID.
                if group['version'] == 'v2':
                    files = {'cpu.max': None, 'cpu.stat': benchmark_keyed_counters,
                             'cpu.stat.local': benchmark_keyed_counters, 'cpu.weight': None,
                             'cpuset.cpus.effective': None, 'io.stat': benchmark_io_stat, 'io.max': None,
                             'cpu.pressure': benchmark_pressure, 'io.pressure': benchmark_pressure,
                             'memory.pressure': benchmark_pressure}
                else:
                    files = {'cpu.cfs_quota_us': None, 'cpu.cfs_period_us': None,
                             'cpu.stat': benchmark_keyed_counters, 'cpu.shares': None,
                             'cpuset.effective_cpus': None, 'blkio.throttle.io_service_bytes': None}
                groups[path] = {name: benchmark_observation(Path(path) / name, parser or (lambda v: v.strip()))
                                for name, parser in files.items()}
    return {'start_ns': started, 'end_ns': time.perf_counter_ns(),
            'observer_cpu_seconds': (time.process_time_ns() - cpu) / 1e9,
            'processes': processes, 'cgroups': groups,
            'host': {'cpu_jiffies': benchmark_observation('/proc/stat', benchmark_host_cpu),
                     'diskstats': benchmark_observation('/proc/diskstats', benchmark_diskstats),
                     'vmstat': benchmark_observation('/proc/vmstat', benchmark_keyed_counters),
                     'loadavg': benchmark_observation('/proc/loadavg'),
                     'meminfo': benchmark_observation('/proc/meminfo'),
                     'pressure': {name: benchmark_observation('/proc/pressure/' + name, benchmark_pressure)
                                  for name in ('cpu', 'io', 'memory')}},
            'scope': 'VISIBLE_HOST_AND_SHARED_CGROUP_COUNTERS_NOT_EXCLUSIVE_BENCHMARK_ACCOUNTING'}


def benchmark_counter_delta(before, after):
    """Keep missing fields and resets explicit, including decreasing iowait."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return {'state': 'UNAVAILABLE'}
    if 'state' in before or 'state' in after:
        if before.get('state') != 'OBSERVED' or after.get('state') != 'OBSERVED':
            return {'state': 'UNAVAILABLE', 'before_state': before.get('state'), 'after_state': after.get('state')}
        return benchmark_counter_delta(before.get('value'), after.get('value'))
    result = {}
    for key in sorted(before.keys() | after.keys()):
        if key.startswith('avg') or key in ('in_flight', 'nr_dirty', 'nr_writeback', 'nr_writeback_temp'):
            continue  # Gauge/trend, not a cumulative counter. Raw snapshots retained.
        left, right = before.get(key), after.get(key)
        if isinstance(left, dict) or isinstance(right, dict):
            result[key] = benchmark_counter_delta(left, right)
        elif type(left) is int and type(right) is int:
            result[key] = {'state': 'OBSERVED', 'delta': right - left} if right >= left else {
                'state': 'COUNTER_RESET_OR_DECREASE', 'before': left, 'after': right, 'delta': None}
        elif key not in before or key not in after:
            result[key] = {'state': 'UNAVAILABLE_FIELD', 'delta': None}
    return result


def benchmark_trial_diagnosis(before, after, intervals, storage):
    stages = [stage for row in intervals for stage in row['storage_operations']]
    stage_summary = {}
    for name in ('atomic_write', 'file_fsync', 'replace', 'directory_fsync'):
        rows = [row for row in stages if row['operation'] == name]
        stage_summary[name] = {'calls': len(rows),
            'wall_seconds': benchmark_distribution([(r['end_ns'] - r['start_ns']) / 1e9 for r in rows]) if rows else None,
            'wall_sum_seconds': sum((r['end_ns'] - r['start_ns']) / 1e9 for r in rows),
            'wall_union_seconds': benchmark_persistence_union(rows, min(r['start_ns'] for r in intervals),
                                                              max(r['end_ns'] for r in intervals)),
            'thread_cpu_sum_seconds': sum(r['thread_cpu_seconds'] for r in rows)}
    process_delta = {pid: {name: benchmark_counter_delta(value[name], after['processes'][pid][name])
                          for name in ('io', 'main_thread_context_switches')}
                     for pid, value in before['processes'].items()}
    cgroup_delta = {path: {name: benchmark_counter_delta(value[name], after['cgroups'].get(path, {}).get(name))
                          for name in value if name.endswith(('.stat', '.local', '.pressure'))}
                    for path, value in before['cgroups'].items()}
    return {'state': 'HOLD_CAUSAL_ISOLATION_UNVERIFIED', 'causal_identification_established': False,
            'telemetry_coverage': {
                'server_process_io': all(p['io']['state'] == 'OBSERVED' for p in before['processes'].values()
                                         if p['role'] == 'SERVER') and all(p['io']['state'] == 'OBSERVED'
                                         for p in after['processes'].values() if p['role'] == 'SERVER'),
                'host_diskstats': before['host']['diskstats']['state'] == after['host']['diskstats']['state'] == 'OBSERVED',
                'host_io_pressure': before['host']['pressure']['io']['state'] == after['host']['pressure']['io']['state'] == 'OBSERVED',
                'visible_cgroup_cpu_stat': bool(before['cgroups']) and any(g.get('cpu.stat', {}).get('state') == 'OBSERVED'
                                                                          for g in before['cgroups'].values())},
            'storage': storage, 'storage_operations': stage_summary,
            'serialized_snapshot_bytes': benchmark_distribution([row['snapshot_bytes'] for row in intervals]),
            'persist_outside_atomic_seconds': benchmark_distribution([
                ((row['end_ns'] - row['start_ns']) - sum(s['end_ns'] - s['start_ns']
                  for s in row['storage_operations'] if s['operation'] == 'atomic_write')) / 1e9 for row in intervals]),
            'atomic_other_seconds': benchmark_distribution([
                (sum(s['end_ns'] - s['start_ns'] for s in row['storage_operations'] if s['operation'] == 'atomic_write')
                 - sum(s['end_ns'] - s['start_ns'] for s in row['storage_operations'] if s['operation'] != 'atomic_write'))
                / 1e9 for row in intervals]),
            'persist_elapsed_minus_thread_cpu_seconds': benchmark_distribution([
                (row['end_ns'] - row['start_ns']) / 1e9 - row['thread_cpu_seconds'] for row in intervals], allow_negative=True),
            'persist_thread_resource_deltas': {key: sum(row['thread_resource_delta'][key] for row in intervals)
                for key in intervals[0]['thread_resource_delta']},
            'process_counter_deltas': process_delta, 'cgroup_counter_deltas': cgroup_delta,
            'host_counter_deltas': {name: benchmark_counter_delta(before['host'][name], after['host'][name])
                                   for name in ('cpu_jiffies', 'diskstats', 'vmstat', 'pressure')},
            'cgroup_membership_unchanged': all(value['cgroup_membership'] == after['processes'][pid]['cgroup_membership']
                                               for pid, value in before['processes'].items()),
            'limits': ['Boundary reads bracket execution but are sequential, not atomic.',
                      'Host/cgroup counters include driver, observers and other tasks; they are not additive across shared ancestors.',
                      'Elapsed minus thread CPU includes scheduler and other waits; it does not identify I/O wait.',
                      'Separate wall/thread clock boundaries can produce tiny signed elapsed-minus-CPU residuals; negatives are retained.',
                      'Storage/CPU stalls are diagnostic associations; causal runner attribution needs an isolated controlled intervention.',
                      'Cache policy, physical storage co-tenancy and hypervisor limits remain unverified.']}


def benchmark_next_measurement_contract():
    return {'schema': 'qikvrt_linux_scale_variance_next_measurement_v1',
            'state': 'PREPARED_NOT_EXECUTED', 'maximum_additional_unmodified_hosted_trials': 0,
            'subject': 'Exact successor HEAD/TREE, source/interpreter digests and raw receipt digests required.',
            'command': 'python3 -B tools/qikvrt_firefox_windows_witness.py --comparable-scale-benchmark --repetitions 6 --workload 64 --preload-per-origin 4 --output <new-private-directory>',
            'invariants': 'Four closed byte-identical origins, canonical seed, same 64 requests/four clients; 80 effects/160 records, full restart/consolidation and 80+4 replay refusals.',
            'admission': ['Dedicated host and durable local block volume with recorded storage/queue/filesystem identity and no competing I/O producers.',
                          'Fixed four usable CPU slots/affinity for every placement; visible cgroup membership and all effective ancestor quotas; driver placement disclosed.',
                          'Bind exact workload, snapshots, source/interpreter, kernel, mount, CPU governor and storage cache policy before measurement.',
                          'Collect available PSI totals, host disk/CPU counters, actual cgroup CPU/IO counters and persist operation intervals; unavailable means HOLD, never zero.',
                          'Record an external isolation attestation and collector overhead; a self-reported dedicated runner label is insufficient.'],
            'discriminating_control': 'On the isolated host, run one predeclared matched comparison without competing I/O and one with a bounded calibrated I/O interferer on the same volume. Keep payload/clients/origin bytes and durability invariant; record interferer parameters, measured I/O and CPU costs. No such interferer runs in the hosted diagnostic.',
            'cache_policy': 'Declare warm/cold policy before trials; no unrecorded cache reset, tmpfs substitution or disabling fsync.',
            'order_and_budget': 'Exactly six cyclic interleaved repetitions per predeclared condition; all samples retained. A new measurement contract is required before extending the budget.',
            'speedup_admission': 'Existing six-pair/all-pairs-faster/97.5%-interval-above-one rule unchanged. Do not pool environments or transfer predecessor evidence.',
            'return_boundary': 'If isolation/telemetry admission fails, preserve the exact capability boundary and stop repetitions. Causal scaling remains unproved.'}


def benchmark_persistence_observer(terminal):
    """Process-local hooks call the original writer/syscalls and propagate errors."""
    import resource
    intervals, lock = [], threading.Lock()
    context = threading.local()
    original = terminal.State.persist
    import qikvrt_api_handler as persistence
    atomic, fsync, replace = persistence.atomic_write_bytes, os.fsync, os.replace

    def measured_operation(name, function, *args, **kwargs):
        row = getattr(context, 'row', None)
        if row is None:
            return function(*args, **kwargs)
        start, cpu = time.perf_counter_ns(), time.thread_time_ns()
        success = False
        try:
            value = function(*args, **kwargs)
            success = True
            return value
        finally:
            row['storage_operations'].append({'operation': name, 'start_ns': start,
                'end_ns': time.perf_counter_ns(), 'thread_cpu_seconds': (time.thread_time_ns() - cpu) / 1e9,
                'success': success})

    def measured_atomic(path, data, **kwargs):
        row = getattr(context, 'row', None)
        if row is not None:
            row['snapshot_bytes'] = len(data)  # Never retain data, token/key material or file descriptors.
        return measured_operation('atomic_write', atomic, path, data, **kwargs)

    def measured_fsync(fd):
        if getattr(context, 'row', None) is None:
            return fsync(fd)
        name = 'directory_fsync' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file_fsync'
        return measured_operation(name, fsync, fd)

    def measured_replace(*args, **kwargs):
        return measured_operation('replace', replace, *args, **kwargs)

    def measured_persist(state):
        usage = resource.getrusage(resource.RUSAGE_THREAD)
        start, cpu = time.perf_counter_ns(), time.thread_time_ns()
        row = {'pid': os.getpid(), 'thread_id': threading.get_native_id(), 'start_ns': start,
               'snapshot_bytes': 0, 'storage_operations': []}
        context.row = row
        try:
            return original(state)
        finally:
            end, cpu_end = time.perf_counter_ns(), time.thread_time_ns()
            context.row = None
            after = resource.getrusage(resource.RUSAGE_THREAD)
            row.update(end_ns=end, thread_cpu_seconds=(cpu_end - cpu) / 1e9,
                       thread_resource_delta={name: getattr(after, name) - getattr(usage, name)
                           for name in ('ru_nvcsw', 'ru_nivcsw', 'ru_minflt', 'ru_majflt', 'ru_inblock', 'ru_oublock')})
            with lock:
                intervals.append(row)

    terminal.State.persist = measured_persist
    persistence.atomic_write_bytes = measured_atomic
    os.fsync, os.replace = measured_fsync, measured_replace
    def restore():
        terminal.State.persist = original
        persistence.atomic_write_bytes = atomic
        os.fsync, os.replace = fsync, replace
    return intervals, lock, restore


def benchmark_terminal_worker(terminal):
    """Instrument only this benchmark process; keep production handlers/persist intact."""
    import resource
    intervals, lock, _ = benchmark_persistence_observer(terminal)

    class MeasuredHandler(terminal.RingHandler):
        def do_GET(self):
            if self.path != '/benchmark/metrics':
                return super().do_GET()
            with lock:
                rows = list(intervals)
            usage = resource.getrusage(resource.RUSAGE_CHILDREN)
            self._json(200, {'pid': os.getpid(), 'persist_intervals': rows,
                            'children_cpu_seconds': usage.ru_utime + usage.ru_stime})

    terminal.RingHandler = MeasuredHandler
    return terminal.main()


def benchmark_worker_metrics(processes):
    result = []
    for client in processes:
        status, value = client.request('/benchmark/metrics')
        if status != 200 or value.get('pid') != client.process.pid:
            raise RuntimeError('BENCHMARK_WORKER_METRICS_UNAVAILABLE')
        result.append(value)
    return result


def benchmark_process_cpu(processes):
    """POSIX per-process CPU clocks include server threads, excluding startup."""
    import ctypes
    library = ctypes.CDLL(None)
    clock_for_process = library.clock_getcpuclockid
    clock_for_process.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    clock_for_process.restype = ctypes.c_int
    values = []
    for client in processes:
        clock = ctypes.c_int()
        if clock_for_process(client.process.pid, ctypes.byref(clock)) != 0:
            raise RuntimeError('BENCHMARK_SERVER_CPU_CLOCK_UNAVAILABLE')
        values.append(time.clock_gettime_ns(clock.value) / 1e9)
    return values


def benchmark_read_origin(terminal, client, origin, prefix=''):
    status, snapshot = client.request(prefix + '/terminal/events')
    if (status != 200 or snapshot['event_count'] != len(snapshot['events'])
            or snapshot['events_sha256'] != terminal.sha256(terminal.canonical_json(snapshot['events']))
            or snapshot['persistence_scope'] != 'FSYNCED_ATOMIC_SNAPSHOT_RESTART_SAFE'):
        raise RuntimeError('BENCHMARK_EVENT_READBACK_INVALID')
    records = {}
    for index, event in enumerate(snapshot['events'], 1):
        if event['event_id'] != index or event['seed_binding'] != snapshot['seed_binding']:
            raise RuntimeError('BENCHMARK_EVENT_ID_OR_SEED_INVALID')
        for field in ('record_hash', 'effect_record_hash'):
            digest_value = event[field]
            status, record = client.request(prefix + '/effect-ack/records/' + digest_value)
            projection = {key: value for key, value in record.items() if key != 'record_hash'}
            if (status != 200 or record.get('record_hash') != 'sha256:' + digest_value
                    or digest_value != terminal.sha256(terminal.canonical_json(projection))
                    or record.get('input_hash') != 'sha256:' + event['input_hash']
                    or record.get('seed_binding') != snapshot['seed_binding']
                    or record.get('state') != 'EFFECT_ACK_DONE'):
                raise RuntimeError('BENCHMARK_EFFECT_RECORD_INVALID')
            records[digest_value] = record
    if len(records) != 2 * len(snapshot['events']):
        raise RuntimeError('BENCHMARK_EFFECT_RECORD_CARDINALITY_INVALID')
    return {'origin': origin, 'snapshot': snapshot, 'records': records}


def comparable_scale_benchmark(terminal, output, seed, *, repetitions=6, workload=64,
                               preload_per_origin=4, clients=4):
    """Measure a fixed four-origin ring on 1/2/4 actual processes, separately.

    Templates are populated through real HTTP then closed. Every isolated run
    copies those exact private bytes, including four DISTINCT origin keys.
    Prepare+commit includes measured fsynced persistence. Setup, verification,
    restart/consolidation and replay have separate timing for EVERY run.
    """
    if sys.platform != 'linux':
        raise RuntimeError('COMPARABLE_SCALE_BENCHMARK_REQUIRES_LINUX_PROCESS_CPU_CLOCKS')
    if type(repetitions) is not int or repetitions not in (3, 6, 9, 12):
        raise ValueError('repetitions must be 3, 6, 9 or 12 for balanced order')
    if type(workload) is not int or not 4 <= workload <= 256 or workload % 4:
        raise ValueError('workload must be 4..256 and divisible by four')
    if type(preload_per_origin) is not int or not 1 <= preload_per_origin <= 16 or clients != 4:
        raise ValueError('preload must be 1..16 per origin; exactly four clients required')
    if output.exists():
        raise RuntimeError('NEW_BENCHMARK_ROOT_REQUIRED_NO_STATE_RESET')
    output.mkdir(parents=True)
    private = output / 'private-rings'
    template = private / 'template'
    evidence = output / 'measurements'
    evidence.mkdir()
    processes = []
    initial = []
    retained = []
    measurements = []
    paths = ('src/qikvrt_effect_ack_http_terminal.py', 'src/qikvrt_api_handler.py',
             'src/qikvrt_effect_ack.py', 'tools/qikvrt_firefox_windows_witness.py',
             'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin')
    sources = {path: digest(ROOT / path) for path in paths}
    subject = {'head': terminal.git_read('rev-parse', 'HEAD'),
               'tree': terminal.git_read('rev-parse', 'HEAD^{tree}')}
    expected_head = os.environ.get('QIKVRT_EXPECTED_HEAD')
    if expected_head and subject['head'] != expected_head:
        raise RuntimeError('BENCHMARK_EXACT_HEAD_MISMATCH')
    workload_bytes = [terminal.canonical_json({'schema': 'qikvrt_terminal_input_v1',
                      'text': 'comparable-scale-request-' + str(index).zfill(4)})
                      for index in range(workload)]
    workload_hash = terminal.sha256(terminal.canonical_json([value.decode('utf-8') for value in workload_bytes]))

    def execute(client, payload, prefix=''):
        status, prepared = client.request(prefix + '/terminal/prepare', payload, 'v=1, mode=prepare')
        if status != 200 or prepared.get('ordinary_release') is not False:
            raise RuntimeError('BENCHMARK_PREPARE_FAILED')
        field = ('v=1, mode=commit, token=' + terminal.sf_bytes(prepared['commit_token'].encode('ascii'))
                 + ', hash=' + terminal.sf_bytes(bytes.fromhex(prepared['record_hash'])))
        status, response = client.request(prefix + '/terminal/commit', payload, field)
        if (status != 200 or response.get('ordinary_release') is not True
                or response['post_effect']['input_hash'] != terminal.sha256(terminal.canonical_json(payload))
                or response['post_effect']['record_hash'] != prepared['record_hash']):
            raise RuntimeError('BENCHMARK_COMMIT_NOT_EXACT')
        return payload, field, response['post_effect']

    def views(routes):
        return [benchmark_read_origin(terminal, client, origin, prefix)
                for origin, (client, prefix) in enumerate(routes)]

    def raw_stores(stores):
        return [path.read_bytes() for path in stores]

    def close_all():
        for client in processes:
            client.close()
        processes.clear()

    try:
        template_started = time.perf_counter()
        for origin in range(4):
            client = TerminalProcess(template / ('node-' + str(origin)), seed)
            processes.append(client)
            for index in range(preload_per_origin):
                payload = {'schema': 'qikvrt_terminal_input_v1',
                           'text': 'identical-preload-' + str(origin) + '-' + str(index)}
                retained.append((origin, *execute(client, payload)))
            initial.append(benchmark_read_origin(terminal, client, origin))
        close_all()
        template_stores = [template / ('node-' + str(origin)) / '.qikvrt/api/terminal.json' for origin in range(4)]
        initial_bytes = raw_stores(template_stores)
        initial_hashes = [terminal.sha256(value) for value in initial_bytes]
        template_setup_seconds = time.perf_counter() - template_started
        for repetition in range(repetitions):
            order = (1, 2, 4)[repetition % 3:] + (1, 2, 4)[:repetition % 3]
            for workers in order:
                run_id = 'repeat-' + str(repetition + 1).zfill(2) + '-process-' + str(workers)
                setup_started = time.perf_counter()
                copy_seconds = launch_seconds = 0.0
                run_root = private / run_id
                run_root.mkdir()
                routes, origins = [], []
                per_process = 4 // workers
                for group in range(workers):
                    shard = run_root / ('shard-' + str(group))
                    for local in range(per_process):
                        origin = group * per_process + local
                        destination = shard / ('node-' + str(local))
                        copy_started = time.perf_counter()
                        shutil.copytree(template / ('node-' + str(origin)), destination)
                        copy_seconds += time.perf_counter() - copy_started
                        origins.append(destination)
                    command = [sys.executable, '-B', str(ROOT / 'tools/qikvrt_firefox_windows_witness.py'),
                               '--benchmark-terminal-worker',
                               '--ring-nodes', str(per_process)]
                    launch_started = time.perf_counter()
                    client = TerminalProcess(shard, seed, ring=True, command=command)
                    launch_seconds += time.perf_counter() - launch_started
                    processes.append(client)
                    routes.extend((client, '/nodes/node-' + str(local)) for local in range(per_process))
                stores = [origin / '.qikvrt/api/terminal.json' for origin in origins]
                admission_started = time.perf_counter()
                if raw_stores(stores) != initial_bytes or views(routes) != initial:
                    raise RuntimeError('BENCHMARK_STARTING_STATE_NOT_BYTE_IDENTICAL')
                admission_seconds = time.perf_counter() - admission_started
                process_ids = [client.process.pid for client in processes]
                telemetry_targets = benchmark_telemetry_targets(process_ids)
                storage_identities = [benchmark_storage_identity(store.parent) for store in stores]
                barrier = threading.Barrier(clients + 1, timeout=15)
                def client_work(client_number):
                    client, prefix = routes[client_number]
                    barrier.wait()
                    completed = []
                    for index in range(client_number, workload, clients):
                        started = time.perf_counter_ns()
                        payload, field, event = execute(client, json.loads(workload_bytes[index]), prefix)
                        completed.append((client_number, payload, field, event,
                                          (time.perf_counter_ns() - started) / 1e9))
                    return completed
                with ThreadPoolExecutor(max_workers=clients) as pool:
                    futures = [pool.submit(client_work, number) for number in range(clients)]
                    observability_before = benchmark_host_snapshot(telemetry_targets)
                    metrics_before = benchmark_worker_metrics(processes)
                    cpu_before = benchmark_process_cpu(processes)
                    setup_seconds = time.perf_counter() - setup_started
                    driver_before = time.process_time_ns()
                    wall_start = time.perf_counter_ns()
                    barrier.wait()
                    completed = [item for future in futures for item in future.result()]
                    wall_end = time.perf_counter_ns()
                    wall = (wall_end - wall_start) / 1e9
                    driver_cpu = (time.process_time_ns() - driver_before) / 1e9
                    cpu_after = benchmark_process_cpu(processes)
                    observability_after = benchmark_host_snapshot(telemetry_targets)
                    metrics_after = benchmark_worker_metrics(processes)
                server_cpu = [after - before for before, after in zip(cpu_before, cpu_after)]
                persist_intervals = [row for before, after in zip(metrics_before, metrics_after)
                                     for row in after['persist_intervals'][len(before['persist_intervals']):]]
                if (len(persist_intervals) != workload * 2
                        or any(row['start_ns'] < wall_start or row['end_ns'] > wall_end for row in persist_intervals)):
                    raise RuntimeError('BENCHMARK_PERSIST_MEASUREMENT_INCOMPLETE')
                for row in persist_intervals:
                    stages = row['storage_operations']
                    if (row['snapshot_bytes'] <= 0 or sorted(stage['operation'] for stage in stages) !=
                            ['atomic_write', 'directory_fsync', 'file_fsync', 'replace']
                            or any(not stage['success'] or not row['start_ns'] <= stage['start_ns']
                                   < stage['end_ns'] <= row['end_ns'] for stage in stages)):
                        raise RuntimeError('BENCHMARK_STORAGE_OPERATION_MEASUREMENT_INCOMPLETE')
                persistence_union = benchmark_persistence_union(persist_intervals, wall_start, wall_end)
                variance_diagnosis = benchmark_trial_diagnosis(observability_before, observability_after,
                                                               persist_intervals, storage_identities)
                children_cpu = [after['children_cpu_seconds'] - before['children_cpu_seconds']
                                for before, after in zip(metrics_before, metrics_after)]
                verification_started = time.perf_counter()
                after = views(routes)
                for origin, current in enumerate(after):
                    old = initial[origin]
                    expected = {item[3]['commit_token_sha256']: item[3] for item in completed if item[0] == origin}
                    events = current['snapshot']['events']
                    if (events[:preload_per_origin] != old['snapshot']['events']
                            or len(events) != preload_per_origin + workload // 4
                            or {event['commit_token_sha256']: event for event in events[preload_per_origin:]} != expected
                            or any(current['records'].get(key) != value for key, value in old['records'].items())):
                        raise RuntimeError('BENCHMARK_EFFECT_LOST_DUPLICATED_OR_RECORD_CHANGED')
                before_transfer = raw_stores(stores)
                verification_seconds = time.perf_counter() - verification_started
                consolidation_started = time.perf_counter()
                close_all()
                consolidated_root = run_root / 'consolidated'
                consolidated_root.mkdir()
                for origin, source in enumerate(origins):
                    source.rename(consolidated_root / ('node-' + str(origin)))
                consolidated = TerminalProcess(consolidated_root, seed, ring=True)
                processes.append(consolidated)
                consolidated_routes = [(consolidated, '/nodes/node-' + str(origin)) for origin in range(4)]
                new_stores = [consolidated_root / ('node-' + str(origin)) / '.qikvrt/api/terminal.json'
                              for origin in range(4)]
                if raw_stores(new_stores) != before_transfer or views(consolidated_routes) != after:
                    raise RuntimeError('BENCHMARK_RESTART_OR_CONSOLIDATION_CHANGED_STATE')
                consolidation_seconds = time.perf_counter() - consolidation_started
                consolidation_cpu = benchmark_process_cpu([consolidated])[0]
                replay_started = time.perf_counter()
                probes = retained + [item[:4] for item in completed]
                statuses = []
                for origin, payload, field, event in probes:
                    status, response = consolidated.request('/nodes/node-' + str(origin) + '/terminal/commit', payload, field)
                    if status != 409 or response.get('ordinary_release') is not False:
                        raise RuntimeError('BENCHMARK_REPLAY_CREATED_SECOND_EFFECT')
                    statuses.append(status)
                probe = probes[-1]
                with ThreadPoolExecutor(max_workers=clients) as pool:
                    races = list(pool.map(lambda _: consolidated.request('/nodes/node-' + str(probe[0])
                        + '/terminal/commit', probe[1], probe[2])[0], range(clients)))
                final = views(consolidated_routes)
                if races != [409] * clients or final != after or raw_stores(new_stores) != before_transfer:
                    raise RuntimeError('BENCHMARK_REPLAY_CHANGED_EVENT_RECORD_OR_PRIVATE_STATE')
                status, aggregate = consolidated.request('/terminal/events')
                expected_events = [{'node_id': 'node-' + str(origin), 'event': event}
                                   for origin, view in enumerate(after) for event in view['snapshot']['events']]
                if (status != 200 or aggregate['events'] != expected_events
                        or aggregate['events_sha256'] != terminal.sha256(terminal.canonical_json(expected_events))):
                    raise RuntimeError('BENCHMARK_AGGREGATE_READBACK_NOT_LOSSLESS')
                replay_seconds = time.perf_counter() - replay_started
                latencies = [item[4] for item in completed]
                measurement = {'run_id': run_id, 'repetition': repetition + 1, 'processes': workers,
                    'process_order': list(order), 'process_ids': process_ids, 'parallel_clients': clients,
                    'requests': workload, 'http_requests_in_measurement': workload * 2,
                    'initial_snapshot_sha256': initial_hashes, 'workload_sha256': workload_hash,
                    'wall_seconds': wall, 'server_cpu_seconds_by_process': server_cpu,
                    'server_cpu_seconds': sum(server_cpu), 'driver_cpu_seconds': driver_cpu,
                    'total_cpu_seconds': sum(server_cpu) + driver_cpu,
                    'server_children_cpu_seconds_by_process': children_cpu,
                    'server_process_tree_cpu_seconds': sum(server_cpu) + sum(children_cpu),
                    'phase_timing_seconds': {'setup': setup_seconds, 'snapshot_copy': copy_seconds,
                        'launch_restore': launch_seconds, 'admission_readback': admission_seconds,
                        'execution_including_persistence': wall, 'persistence_wall_union': persistence_union,
                        'persistence_wall_sum': sum((row['end_ns'] - row['start_ns']) / 1e9 for row in persist_intervals),
                        'persistence_thread_cpu': sum(row['thread_cpu_seconds'] for row in persist_intervals),
                        'execution_without_any_persist_active': wall - persistence_union,
                        'verification': verification_seconds, 'consolidation': consolidation_seconds,
                        'consolidation_server_cpu': consolidation_cpu, 'replay_controls': replay_seconds},
                    'persistence_calls': len(persist_intervals),
                    'variance_diagnosis': variance_diagnosis,
                    'confirmed_effects_per_second': workload / wall,
                    'effect_latency_seconds': latencies, 'latency_distribution_seconds': benchmark_distribution(latencies),
                    'effects': len(expected_events), 'referenced_records': sum(len(v['records']) for v in final),
                    'invariants': {'identical_initial_bytes': True, 'retained_effects_and_records_unchanged': True,
                        'lossless_restart_and_consolidation': True, 'replay_second_effects': 0,
                        'replay_refusals': len(statuses), 'concurrent_replay_statuses': races,
                        'post_replay_readback_and_snapshot_bytes_unchanged': True},
                    'readback_sha256': terminal.sha256(terminal.canonical_json(final))}
                run_receipt = measurement | {'readback_before': initial, 'readback_after': after,
                                              'telemetry_targets': telemetry_targets,
                                              'observability_before': observability_before,
                                              'observability_after': observability_after,
                                              'readback_after_restart_and_replay': final,
                                              'replay_statuses': statuses, 'aggregate_readback': aggregate,
                                              'execution_start_ns': wall_start, 'execution_end_ns': wall_end,
                                              'worker_metrics_before': metrics_before, 'worker_metrics_after': metrics_after}
                path = evidence / (run_id + '.json')
                path.write_text(json.dumps(run_receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
                measurement['evidence'] = {'path': path.relative_to(output).as_posix(),
                    'bytes': path.stat().st_size, 'sha256': digest(path)}
                measurements.append(measurement)
                close_all()
                print(json.dumps({'benchmark_run': run_id, 'state': 'PASS', 'wall_seconds': wall,
                                  'effects': len(expected_events)}), flush=True)
        if sources != {path: digest(ROOT / path) for path in paths} or subject != {
                'head': terminal.git_read('rev-parse', 'HEAD'), 'tree': terminal.git_read('rev-parse', 'HEAD^{tree}')}:
            raise RuntimeError('BENCHMARK_SOURCE_OR_SUBJECT_CHANGED_DURING_MEASUREMENT')
        summary = {}
        for workers in (1, 2, 4):
            rows = [row for row in measurements if row['processes'] == workers]
            summary[str(workers)] = {metric: benchmark_distribution([row[metric] for row in rows])
                for metric in ('wall_seconds', 'server_cpu_seconds', 'driver_cpu_seconds', 'total_cpu_seconds',
                               'server_process_tree_cpu_seconds', 'confirmed_effects_per_second')}
            summary[str(workers)]['phase_timing_seconds'] = {phase: benchmark_distribution(
                [row['phase_timing_seconds'][phase] for row in rows]) for phase in rows[0]['phase_timing_seconds']}
            summary[str(workers)]['pooled_effect_latency_seconds'] = benchmark_distribution(
                [value for row in rows for value in row['effect_latency_seconds']])
            summary[str(workers)]['per_run_p95_latency_seconds'] = benchmark_distribution(
                [row['latency_distribution_seconds']['p95'] for row in rows])
            summary[str(workers)]['storage_operation_max_seconds'] = {name: benchmark_distribution([
                row['variance_diagnosis']['storage_operations'][name]['wall_seconds']['max'] for row in rows])
                for name in ('atomic_write', 'file_fsync', 'replace', 'directory_fsync')}
        comparisons = {str(workers): benchmark_speedup(
            [row['wall_seconds'] for row in measurements if row['processes'] == 1],
            [row['wall_seconds'] for row in measurements if row['processes'] == workers]) for workers in (2, 4)}
        environment = {'host': platform.node(), 'machine': platform.machine(),
            'os': platform.platform(), 'python': sys.version, 'cpu_count': os.cpu_count(),
            'cpu_affinity_count': len(os.sched_getaffinity(0)),
            'cpu_accounting': 'clock_getcpuclockid(PID) + clock_gettime_ns; process CPU includes server threads',
            'server_cpu_resolution_seconds': time.get_clock_info('process_time').resolution,
            'driver_cpu_clock_resolution_seconds': time.get_clock_info('process_time').resolution,
            'wall_clock_resolution_seconds': time.get_clock_info('perf_counter').resolution}
        for name, path in (('cpu_model', '/proc/cpuinfo'),):
            try:
                value = Path(path).read_text()
                environment[name] = (next(line.split(':', 1)[1].strip() for line in value.splitlines()
                    if line.startswith('model name')) if name == 'cpu_model' else value.strip())
            except (OSError, StopIteration):
                environment[name] = 'UNAVAILABLE'
        environment['interpreter_binary_sha256'] = digest(sys.executable)
        environment['cpu_quota'] = {'source': 'Per-trial actual membership and visible ancestor files',
                                    'root_only_probe_used': False, 'outside_namespace_limits': 'UNOBSERVED'}
        firefox_path = shutil.which('firefox')
        firefox_identity = {'state': 'UNOBSERVED', 'execution_benchmarked': False}
        if firefox_path:
            firefox_identity.update(state='INSTALLED_BINARY_IDENTITY_OBSERVED', path=firefox_path,
                binary_sha256=digest(firefox_path),
                version=subprocess.check_output([firefox_path, '--version'], text=True, timeout=20).strip())
        return {'schema': 'qikvrt_linux_comparable_scale_benchmark_v1', 'state': 'PASS', **subject,
            'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'source_sha256': sources,
            'ci_provenance': {key: os.environ.get(key) for key in
                ('GITHUB_REPOSITORY', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB')},
            'environment': environment, 'firefox': firefox_identity,
            'template_setup_seconds': template_setup_seconds,
            'variance_observability': {
                'schema': 'qikvrt_linux_scale_variance_observability_v1',
                'state': 'HOLD_CAUSAL_ISOLATION_UNVERIFIED',
                'causal_runner_io_stall_proved': False, 'runner_independent_scaling_proved': False,
                'host_reads': 'Before/after only, outside execution; raw per-trial boundaries retained. No sampling poller.',
                'storage_operations': 'Original atomic writer and original file/directory fsync and replace syscalls, process-local hooks; serialization/write/flush/cleanup remain in inclusive persist/atomic residuals.',
                'observer_overhead': 'Boundary read wall/driver process CPU observed; syscall hook overhead is included in execution and not independently calibrated.',
                'next_measurement_contract': benchmark_next_measurement_contract()},
            'timing_semantics': {
                'execution': 'Barrier release to last positive prepare/commit response, including fsynced persistence.',
                'persistence': 'Monotonic interval union counts overlapping State.persist calls once in wall time; thread CPU is additive.',
                'execution_without_any_persist_active': 'Wall intervals with no persist active, not a counterfactual run with persistence disabled.',
                'setup': 'Snapshot copy, actual process launch/restore, admission readback and precreated clients; excluded from execution.',
                'consolidation': 'Drained process termination, origin relocation, one-process reacquisition and complete unchanged readback.',
                'server_process_tree_cpu': 'Existing server-thread CPU clock plus reaped git child CPU, excluding observer/client CPU.',
                'firefox': 'Installed binary identity only; Firefox transport performance is not measured.'},
            'process_scale': [1, 2, 4], 'origins_in_every_run': 4,
            'repetitions_per_process_count': repetitions, 'workload': workload, 'parallel_clients': clients,
            'preloaded_effects': preload_per_origin * 4, 'initial_snapshot_sha256': initial_hashes,
            'workload_sha256': workload_hash, 'measurements': measurements, 'summary': summary,
            'comparisons_to_one_process': comparisons,
            'measurement_scope': 'BARRIER_RELEASE_TO_LAST_CONFIRMED_PREPARE_COMMIT_RESPONSE',
            'excluded_from_timing': ['startup', 'preload', 'readback', 'consolidation', 'replay_controls'],
            'client_schedule': 'four barrier-synchronized clients; one fixed origin per client; equal requests',
            'order_control': 'cyclic balanced 1/2/4, 2/4/1, 4/1/2; every run included, no outlier removal',
            'private_state_exported': False, 'external_service_requests': 0,
            'predecessor_evidence_transfer': False, 'unbounded_scalability_proved': False,
            'comparative_speedup_proved': any(value['speedup_supported'] for value in comparisons.values()),
            'personal_release_effect_ack_done': False,
            'limitations': ['Finite local Linux host and fixed workload only; no cross-host or unbounded claim.',
                'Process-local observation hooks add timing overhead; compare this instrumented mode only.',
                'Per-process CPU deltas include tiny untimed accounting boundaries around barrier release and completion.',
                'Native prepare generates fresh random tokens and timestamps; input payload bytes stay identical.',
                'Initial snapshots are byte-identical per origin, with distinct keys between the four origins.',
                'Ambient cache and host load are not isolated; balanced order reduces but does not remove drift.',
                'No warmup exclusion; pooled request percentiles are descriptive, runs are paired inference units.']}
    finally:
        close_all()


def initialize_seeded_terminal(terminal, contract, output):
    """Both native witnesses require the canonical seed and the same durable root."""
    seed = ROOT / contract['seed_path']
    if len(seed.read_bytes()) != 400 or digest(seed) != contract['seed_sha256']:
        raise RuntimeError('WITNESS_CANONICAL_SEED_BINDING_MISMATCH')
    state_root = output / 'terminal-state'
    terminal.STATE = terminal.State(seed, state_root=state_root)
    return seed, state_root


def durable_state_rejection_controls(terminal, state_root, seed, store):
    """Real CLI startups refuse invalid state without rewriting retained bytes."""
    valid = store.read_bytes()
    value = json.loads(valid)
    changed_seed_binding = dict(value, seed_binding=None)
    changed_seed_binding.pop('state_sha256')
    changed_seed_binding['state_sha256'] = terminal.sha256(terminal.canonical_json(changed_seed_binding))
    corruptions = {
        'empty_state': b'',
        'truncated_state': valid[:len(valid)//2],
        'missing_final_newline': valid[:-1],
        'corrupt_digest': valid.replace(b'TERMINAL_INPUT_ACCEPTED', b'TERMINAL_INPUT_ALTERED_'),
        'duplicate_json_key': valid.replace(b'{', b'{"schema":"duplicate",', 1),
        'state_seed_binding_mismatch': terminal.canonical_json(changed_seed_binding) + b'\n',
    }
    observations = {}
    def refused(name, seed_argument):
        command = [sys.executable, '-B', str(ROOT / 'src/qikvrt_effect_ack_http_terminal.py'),
                   '--state-root', str(state_root), '--port', '0']
        if seed_argument is not None:
            command += ['--seed', str(seed_argument)]
        result = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=15)
        if result.returncode == 0 or '"state": "READY"' in result.stdout:
            raise RuntimeError('INVALID_STATE_START_NOT_REFUSED_' + name)
        observations[name] = {'startup_refused': True, 'returncode': result.returncode,
                              'ready_observed': False, 'state_sha256': digest(store)}
    bad = state_root / 'altered-seed.bin'
    try:
        for name, raw in corruptions.items():
            store.write_bytes(raw)
            refused(name, seed)
            if store.read_bytes() != raw:
                raise RuntimeError('INVALID_STATE_SILENTLY_REWRITTEN_' + name)
        store.write_bytes(valid)
        original = seed.read_bytes()
        bad.write_bytes(bytes([original[0] ^ 1]) + original[1:])
        refused('altered_seed', bad)
        bad.write_bytes(original[:-1])
        refused('truncated_seed', bad)
        bad.unlink()
        refused('missing_seed', bad)
        refused('unseeded_restart', None)
        if store.read_bytes() != valid:
            raise RuntimeError('SEED_REJECTION_REWROTE_DURABLE_STATE')
    finally:
        store.write_bytes(valid)
        bad.unlink(missing_ok=True)
    # Confirm normal startup is still possible and a fresh readback is intact.
    process = TerminalProcess(state_root, seed)
    try:
        status, snapshot = process.request('/terminal/events')
        if status != 200 or snapshot['events'] != value['events'] or store.read_bytes() != valid:
            raise RuntimeError('VALID_STATE_NOT_RESTORED_AFTER_NEGATIVE_CONTROLS')
    finally:
        process.close()
    return {'schema': 'qikvrt_terminal_state_rejection_controls_v1',
            'native_platform': sys.platform, 'controls': observations,
            'valid_state_sha256': digest(store), 'retained_state_unchanged': True,
            'automatic_reset_or_partial_salvage': False, 'external_effect': 'NONE'}


def durable_restart_controls(terminal, state_root, seed, *, expected_snapshot=None, replay_probes=()):
    """Kill a real process without shutdown hooks; retain events/records and refuse replay."""
    first = second = None
    try:
        first = TerminalProcess(state_root, seed)
        status, original = first.request('/terminal/events')
        if status != 200 or (expected_snapshot is not None and original != expected_snapshot):
            raise RuntimeError('PRIOR_RING_SNAPSHOT_NOT_RESTORED')
        payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'restart-' + os.urandom(16).hex()}
        status, prepared = first.request('/terminal/prepare', payload, 'v=1, mode=prepare')
        field = ('v=1, mode=commit, token=' + terminal.sf_bytes(prepared['commit_token'].encode('ascii'))
                 + ', hash=' + terminal.sf_bytes(bytes.fromhex(prepared['record_hash'])))
        if status != 200 or first.request('/terminal/commit', payload, field)[0] != 200:
            raise RuntimeError('RESTART_PROBE_COMMIT_NOT_CONFIRMED')
        status, before = first.request('/terminal/events')
        if status != 200 or before['events'][:-1] != original['events']:
            raise RuntimeError('PRIOR_RING_EVENTS_CHANGED')
        paths = sorted({'/effect-ack/records/' + digest for event in before['events']
                        for digest in (event['record_hash'], event['effect_record_hash'])})
        def records(process):
            result = {}
            for path in paths:
                status, record = process.request(path)
                if status != 200:
                    raise RuntimeError('RESTART_REFERENCED_RECORD_UNAVAILABLE')
                result[path] = record
            return result
        records_before = records(first)
        store = state_root / '.qikvrt/api/terminal.json'
        state_before = digest(store)
        first_pid = first.process.pid
        first.close()  # POSIX SIGKILL / Windows TerminateProcess; no shutdown/save hook.
        first = None
        second = TerminalProcess(state_root, seed)
        status, after = second.request('/terminal/events')
        records_after = records(second)
        if (status != 200 or after != before or records_after != records_before
                or digest(store) != state_before
                or after['events_sha256'] != terminal.sha256(terminal.canonical_json(after['events']))):
            raise RuntimeError('DURABLE_EVENTS_OR_EFFECT_RECORD_READBACK_CHANGED')
        for record in records_after.values():
            projection = {key: value for key, value in record.items() if key != 'record_hash'}
            if record['record_hash'] != 'sha256:' + terminal.sha256(terminal.canonical_json(projection)):
                raise RuntimeError('RESTART_RECORD_DIGEST_MISMATCH')
        replay_statuses = []
        for replay_payload, replay_field in [(payload, field), *replay_probes]:
            replay_status, replay = second.request('/terminal/commit', replay_payload, replay_field)
            status, final = second.request('/terminal/events')
            if (status != 200 or replay_status != 409 or replay.get('ordinary_release') is not False
                    or final != before or digest(store) != state_before or records(second) != records_before):
                raise RuntimeError('RESTART_REPLAY_CREATED_SECOND_EFFECT')
            replay_statuses.append(replay_status)
        return {'schema': 'qikvrt_terminal_durable_restart_readback_v1',
                'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                'first_process_pid': first_pid, 'restarted_process_pid': second.process.pid,
                'termination': ('WINDOWS_TERMINATE_PROCESS_WITHOUT_SHUTDOWN_HOOK' if sys.platform == 'win32'
                                else 'SIGKILL_WITHOUT_SHUTDOWN_HOOK'),
                'native_platform': sys.platform, 'actual_process_restart': True,
                'event_snapshot_before': before, 'event_snapshot_after': after,
                'effect_records_before': records_before, 'effect_records_after': records_after,
                'prior_ring_event_count': original['event_count'],
                'replay_http_status': replay_status, 'replay_http_statuses': replay_statuses,
                'replay_event_snapshot': final,
                'confirmed_events_and_records_unchanged': True, 'replay_second_effects': 0,
                'persistent_state_sha256_before': state_before,
                'persistent_state_sha256_after': digest(store),
                'canonical_record_bytes_sha256': terminal.sha256(terminal.canonical_json(records_after)),
                'persistence_scope': after['persistence_scope'],
                'lossless_scope': 'BOUNDED_LOCAL_FSYNCED_SNAPSHOT_ACROSS_PROCESS_RESTART',
                'authority_mirror_live_nodes_tested': False, 'network_loss_injected': False,
                'unbounded_scalability_proved': False, 'external_effect': 'NONE'}
    finally:
        if first is not None:
            first.close()
        if second is not None:
            second.close()


def interrupted_http_response(process, snapshot_path, path, body=None, field=None, *, mode):
    """One real loopback proxy cut; only an observed client transport error qualifies.

    The upstream is the unchanged durable CLI. Read its complete response and
    the persisted snapshot before cutting the downstream socket. No response
    exception is synthesized, and neither peer is killed or patched.
    """
    from http.server import BaseHTTPRequestHandler, HTTPServer
    if mode not in ('TCP_RST_BEFORE_RESPONSE', 'TRUNCATED_HTTP_BODY'):
        raise ValueError('unsupported transport cut')
    observation = {'path': path, 'method': 'GET' if body is None else 'POST',
                   'mode': mode, 'network_loss_injected': False}

    class CutHandler(BaseHTTPRequestHandler):
        def cut(self):
            try:
                self.connection.settimeout(15)
                length = int(self.headers.get('Content-Length', '0'))
                if (self.path != path or self.command != observation['method']
                        or not 0 <= length <= PUBLIC_BODY_LIMIT):
                    raise RuntimeError('TRANSPORT_PROXY_REQUEST_MISMATCH')
                data = self.rfile.read(length) if length else None
                if data is not None and len(data) != length:
                    raise RuntimeError('TRANSPORT_PROXY_REQUEST_TRUNCATED')
                headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-cache'}
                if self.headers.get('Effect-Ack-Request'):
                    headers['Effect-Ack-Request'] = self.headers['Effect-Ack-Request']
                upstream = http.client.HTTPConnection('127.0.0.1', process.port, timeout=15)
                try:
                    upstream.request(self.command, self.path, body=data, headers=headers)
                    response = upstream.getresponse()
                    payload = response.read(PUBLIC_BODY_LIMIT + 1)
                    if response.status != 200 or not 1 < len(payload) <= PUBLIC_BODY_LIMIT:
                        raise RuntimeError('TRANSPORT_PROXY_UPSTREAM_NOT_COMPLETE_200')
                    observation.update(upstream_http_status=response.status,
                        upstream_body_bytes=len(payload),
                        upstream_body_sha256=hashlib.sha256(payload).hexdigest(),
                        persisted_snapshot_sha256_before_cut=digest(snapshot_path),
                        upstream_response_observed_at=dt.datetime.now(dt.timezone.utc).isoformat())
                finally:
                    upstream.close()
                self.close_connection = True
                if mode == 'TCP_RST_BEFORE_RESPONSE':
                    # Abortive close sends RST, rather than discarding a reply
                    # that the client has already received successfully.
                    self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                               struct.pack('HH' if sys.platform == 'win32' else 'ii', 1, 0))
                    observation['downstream_body_bytes_sent'] = 0
                    self.connection.close()
                else:
                    prefix = payload[:len(payload) // 2]
                    self.send_response(200)
                    self.send_header('Content-Length', str(len(payload)))
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(prefix)
                    self.wfile.flush()
                    observation['downstream_body_bytes_sent'] = len(prefix)
                    self.connection.shutdown(socket.SHUT_WR)
            except Exception as error:
                # A proxy/setup/upstream failure cannot be promoted to the
                # intended post-persistence transport fault.
                observation['proxy_error'] = type(error).__name__ + ': ' + str(error)
                self.close_connection = True

        do_POST = do_GET = cut

        def log_message(self, *_):
            return

    with HTTPServer(('127.0.0.1', 0), CutHandler) as proxy:
        proxy.timeout = 15
        worker = threading.Thread(target=proxy.handle_request, daemon=True)
        worker.start()
        client = http.client.HTTPConnection('127.0.0.1', proxy.server_port, timeout=15)
        try:
            data = None if body is None else json.dumps(body, sort_keys=True,
                separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
            client.request(observation['method'], path, body=data,
                headers={'Content-Type': 'application/json',
                         **({'Effect-Ack-Request': field} if field else {})})
            response = client.getresponse()
            observation['client_http_status'] = response.status
            response.read()  # Read to Content-Length; short bodies must fail.
            observation['client_complete_response'] = True
        except (ConnectionResetError, http.client.RemoteDisconnected, http.client.IncompleteRead) as error:
            observation.update(client_error=type(error).__name__, client_errno=getattr(error, 'errno', None),
                               client_complete_response=False)
            if isinstance(error, http.client.IncompleteRead):
                observation.update(client_partial_bytes=len(error.partial),
                                   client_missing_bytes=error.expected)
        finally:
            client.close()
            worker.join(timeout=20)
        if worker.is_alive():
            raise RuntimeError('TRANSPORT_PROXY_DID_NOT_TERMINATE')
    if observation.get('proxy_error'):
        raise RuntimeError(observation['proxy_error'])
    expected_errors = (('ConnectionResetError', 'RemoteDisconnected') if mode == 'TCP_RST_BEFORE_RESPONSE'
                       else ('IncompleteRead',))
    if (observation.get('client_error') not in expected_errors
            or observation.get('upstream_http_status') != 200
            or observation.get('client_complete_response') is not False):
        raise RuntimeError('ACTUAL_CLIENT_TRANSPORT_FAULT_NOT_OBSERVED')
    observation.update(network_loss_injected=True,
                       observed_at=dt.datetime.now(dt.timezone.utc).isoformat())
    return observation


def network_loss_controls(terminal, state_root, seed, *, expected_snapshot=None, retry_clients=4):
    """Persist one effect, cut real sockets, refuse bounded retries and read back."""
    if not 1 <= retry_clients <= 8:
        raise ValueError('bounded retry requires 1..8 clients')
    snapshot_path = state_root / '.qikvrt/api/terminal.json'
    first = second = None
    try:
        first = TerminalProcess(state_root, seed)
        status, original = first.request('/terminal/events')
        if status != 200 or (expected_snapshot is not None and original != expected_snapshot):
            raise RuntimeError('NETWORK_PROBE_PRIOR_SNAPSHOT_MISMATCH')
        payload = {'schema': 'qikvrt_terminal_input_v1', 'text': 'network-loss-' + os.urandom(16).hex()}
        status, prepared = first.request('/terminal/prepare', payload, 'v=1, mode=prepare')
        if status != 200:
            raise RuntimeError('NETWORK_PROBE_PREPARE_FAILED')
        field = ('v=1, mode=commit, token=' + terminal.sf_bytes(prepared['commit_token'].encode('ascii'))
                 + ', hash=' + terminal.sf_bytes(bytes.fromhex(prepared['record_hash'])))
        commit_fault = interrupted_http_response(first, snapshot_path, '/terminal/commit', payload, field,
                                                 mode='TCP_RST_BEFORE_RESPONSE')
        persisted = snapshot_path.read_bytes()  # Private comparison only; never export keys/tokens.
        persisted_sha256 = hashlib.sha256(persisted).hexdigest()
        status, after_fault = first.request('/terminal/events')
        input_hash = terminal.sha256(terminal.canonical_json(payload))
        token_hash = terminal.sha256(prepared['commit_token'].encode('ascii'))
        matches = [event for event in after_fault['events'] if event['input_hash'] == input_hash
                   and event['text'] == payload['text'] and event['commit_token_sha256'] == token_hash]
        if (status != 200 or after_fault['event_count'] != original['event_count'] + 1
                or after_fault['events'][:-1] != original['events'] or len(matches) != 1
                or after_fault['persistence_scope'] != 'FSYNCED_ATOMIC_SNAPSHOT_RESTART_SAFE'
                or after_fault['events_sha256'] != terminal.sha256(terminal.canonical_json(after_fault['events']))
                or commit_fault['persisted_snapshot_sha256_before_cut'] != persisted_sha256):
            raise RuntimeError('NETWORK_FAULT_NOT_BOUND_TO_ONE_PERSISTED_EFFECT')
        paths = sorted({'/effect-ack/records/' + value for event in after_fault['events']
                        for value in (event['record_hash'], event['effect_record_hash'])})

        def records(process):
            result = {}
            for path in paths:
                code, record = process.request(path)
                projection = {key: value for key, value in record.items() if key != 'record_hash'}
                if (code != 200 or record.get('record_hash') != 'sha256:' + path.rsplit('/', 1)[-1]
                        or record['record_hash'] != 'sha256:' + terminal.sha256(terminal.canonical_json(projection))
                        or record.get('seed_binding') != after_fault['seed_binding']):
                    raise RuntimeError('NETWORK_FAULT_EFFECT_RECORD_BINDING_MISMATCH')
                result[path] = record
            return result

        records_after_fault = records(first)
        effect_path = '/effect-ack/records/' + matches[0]['effect_record_hash']
        effect = records_after_fault[effect_path]
        if (matches[0]['record_hash'] != prepared['record_hash']
                or effect['input_hash'] != 'sha256:' + input_hash
                or effect['ordinary_release'] is not True or effect['state'] != 'EFFECT_ACK_DONE'
                or sum(record['input_hash'] == 'sha256:' + input_hash
                       and record['reason'] == 'single-use exact-bound loopback commit executed'
                       for record in records_after_fault.values()) != 1):
            raise RuntimeError('NETWORK_FAULT_EFFECT_NOT_EXACTLY_ONCE')
        readback_faults = [interrupted_http_response(first, snapshot_path, path,
                            mode='TRUNCATED_HTTP_BODY') for path in ('/terminal/events', effect_path)]
        first_pid = first.process.pid
        if first.process.poll() is not None:
            raise RuntimeError('NETWORK_PROBE_SERVER_CRASHED')
        replay_status, replay = first.request('/terminal/commit', payload, field)
        barrier = threading.Barrier(retry_clients)

        def retry(_):
            barrier.wait(timeout=15)
            return first.request('/terminal/commit', payload, field)

        with ThreadPoolExecutor(max_workers=retry_clients) as pool:
            retries = list(pool.map(retry, range(retry_clients)))
        if (replay_status != 409 or replay.get('ordinary_release') is not False
                or any(code != 409 or result.get('ordinary_release') is not False for code, result in retries)):
            raise RuntimeError('NETWORK_RETRY_NOT_REFUSED')
        status, after_retry = first.request('/terminal/events')
        records_after_retry = records(first)
        if (status != 200 or after_retry != after_fault or records_after_retry != records_after_fault
                or snapshot_path.read_bytes() != persisted or first.process.poll() is not None
                or any(fault['persisted_snapshot_sha256_before_cut'] != persisted_sha256 for fault in readback_faults)):
            raise RuntimeError('NETWORK_RETRY_CHANGED_PERSISTED_EFFECT')
        first.close()
        first = None
        second = TerminalProcess(state_root, seed)
        restarted_status, restarted_replay = second.request('/terminal/commit', payload, field)
        status, after_restart = second.request('/terminal/events')
        records_after_restart = records(second)
        if (status != 200 or after_restart != after_fault or records_after_restart != records_after_fault
                or snapshot_path.read_bytes() != persisted or restarted_status != 409
                or restarted_replay.get('ordinary_release') is not False):
            raise RuntimeError('NETWORK_RETRY_RESTART_CHANGED_PERSISTED_EFFECT')
        return {'schema': 'qikvrt_terminal_network_loss_readback_v1',
                'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                'transport_faults': [commit_fault, *readback_faults],
                'network_loss_injected': all(fault['network_loss_injected'] for fault in (commit_fault, *readback_faults)),
                'fault_scope': 'BOUNDED_LOOPBACK_TCP_COMMIT_RESPONSE_AND_READBACK_INTERRUPTION',
                'server_alive_after_faults': True, 'first_process_pid': first_pid,
                'restarted_process_pid': second.process.pid, 'actual_process_restart': True,
                'prior_event_count': original['event_count'], 'probe_input_hash': input_hash,
                'probe_commit_token_sha256': token_hash, 'probe_effect_record_path': effect_path,
                'probe_effects': len(matches), 'replay_http_status': replay_status,
                'concurrent_retry': {'clients': retry_clients, 'http_statuses': [code for code, _ in retries],
                                     'refusals': len(retries), 'second_effects': 0},
                'restart_replay_http_status': restarted_status,
                'event_snapshot_after_fault': after_fault, 'event_snapshot_after_retry': after_retry,
                'event_snapshot_after_restart': after_restart,
                'effect_records_after_fault': records_after_fault, 'effect_records_after_retry': records_after_retry,
                'effect_records_after_restart': records_after_restart,
                'persisted_snapshot_sha256': persisted_sha256, 'persisted_snapshot_bytes': len(persisted),
                'persisted_snapshot_unchanged': True, 'private_state_uploaded': False,
                'replay_second_effects': 0, 'persistence_scope': after_fault['persistence_scope'],
                'authority_mirror_live_nodes_tested': False, 'unbounded_scalability_proved': False,
                'predecessor_evidence_transfer': False, 'personal_release_effect_ack_done': False,
                'external_effect': 'NONE'}
    finally:
        if first is not None:
            first.close()
        if second is not None:
            second.close()


def bounded_ring_controls(terminal):
    """Real HTTP effects; finite fanout is not general Mesh/runtime equivalence."""
    def request(path, body=None, field=None):
        req = urllib.request.Request('http://127.0.0.1:8771' + path,
            data=None if body is None else terminal.canonical_json(body),
            headers={'Content-Type': 'application/json',
                     **({'Effect-Ack-Request': field} if field else {})})
        try:
            response = urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, json.load(response)

    def prepare(payload):
        status, result = request('/terminal/prepare', payload, 'v=1, mode=prepare')
        if status != 200:
            raise RuntimeError('CONTROL_PREPARE_FAILED')
        status, record = request(result['record_url'])
        claimed = record.pop('record_hash')
        if (status != 200 or claimed != 'sha256:' + terminal.sha256(terminal.canonical_json(record))
                or record['seed_binding'] != terminal.STATE.seed_binding
                or record['input_hash'] != 'sha256:' + terminal.sha256(terminal.canonical_json(payload))):
            raise RuntimeError('CONTROL_FULL_RECORD_BINDING_FAILED')
        field = ('v=1, mode=commit, token=' + terminal.sf_bytes(result['commit_token'].encode('ascii'))
                 + ', hash=' + terminal.sf_bytes(bytes.fromhex(result['record_hash'])))
        return field

    def new_payload():
        return {'schema': 'qikvrt_terminal_input_v1', 'text': 'linux-ring-' + os.urandom(16).hex()}

    expected = {}
    measurements = []
    for count in (1, 2, 4, 8):
        payloads = [new_payload() for _ in range(count)]
        fields = [prepare(payload) for payload in payloads]
        before = readback()['events']
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=count) as pool:
            results = list(pool.map(lambda pair: request('/terminal/commit', *pair), zip(payloads, fields)))
        elapsed = time.monotonic() - started
        if any(status != 200 for status, _ in results) or readback()['events'] != before + count:
            raise RuntimeError('FANOUT_EFFECT_COUNT_MISMATCH')
        for payload in payloads:
            expected[payload['text']] = terminal.sha256(terminal.canonical_json(payload))
        measurements.append({'parallel_clients': count, 'accepted_events': count,
                             'elapsed_seconds': elapsed, 'transport': 'HTTP_CLIENTS_NOT_FIREFOX_FANOUT'})
    payload = new_payload()
    field = prepare(payload)
    before = readback()['events']
    with ThreadPoolExecutor(max_workers=8) as pool:
        races = list(pool.map(lambda _: request('/terminal/commit', payload, field), range(8)))
    if sorted(status for status, _ in races) != [200] + [409] * 7 or readback()['events'] != before + 1:
        raise RuntimeError('SHARED_TOKEN_RACE_NOT_SINGLE_USE')
    expected[payload['text']] = terminal.sha256(terminal.canonical_json(payload))
    # Discard the commit reply at the client; recover only by readback, never dispatch again.
    payload = new_payload()
    field = prepare(payload)
    request('/terminal/commit', payload, field)
    expected[payload['text']] = terminal.sha256(terminal.canonical_json(payload))
    status, snapshot = request('/terminal/events')
    events = snapshot['events']
    if (status != 200 or len(events) != readback()['events']
            or snapshot['events_sha256'] != terminal.sha256(terminal.canonical_json(events))
            or [event['event_id'] for event in events] != list(range(1, len(events) + 1))):
        raise RuntimeError('EVENT_SNAPSHOT_NOT_LOSSLESS')
    for text, digest in expected.items():
        matches = [event for event in events if event['text'] == text and event['input_hash'] == digest
                   and event['seed_binding'] == terminal.STATE.seed_binding]
        if len(matches) != 1:
            raise RuntimeError('NONCE_BOUND_EVENT_MISSING_OR_DUPLICATED')
    return {'fanout': measurements, 'shared_token_race': {'clients': 8, 'effects': 1, 'refusals': 7},
            'discarded_reply_readback': True, 'network_loss_injected': False,
            'event_snapshot': snapshot, 'lossless_scope': (
                'FSYNCED_LOCAL_EVENT_SNAPSHOT_ONLY' if terminal.STATE.store is not None
                else 'PROCESS_LIFETIME_EVENT_SNAPSHOT_ONLY'),
            'authority_mirror_live_nodes_tested': False, 'unbounded_scalability_proved': False}


def wait_script(driver, script):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = driver.script(script)
        if result:
            return result
        time.sleep(.2)
    raise RuntimeError('BROWSER_FUNCTIONAL_TIMEOUT')


def witness(output, headless=False, linux=False):
    output.mkdir(parents=True, exist_ok=True)
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    contract = policy['linux_ring_acceptance'] if linux else policy['windows_acceptance']
    receipt = {'schema': 'qikvrt_firefox_windows_witness_v1',
               'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
               'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'tree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
               'policy_sha256': digest(POLICY),
               'observer_sha256': digest(__file__),
               'terminal_source_sha256': digest(ROOT / 'src/qikvrt_effect_ack_http_terminal.py'),
               'run_id': os.environ.get('GITHUB_RUN_ID'),
               'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
               'job': os.environ.get('GITHUB_JOB'),
               'runner_image': os.environ.get('ImageOS'),
               'runner_image_version': os.environ.get('ImageVersion'),
               'headless': headless, 'predecessor_evidence_transfer': False,
               'network_loss_injected': False, 'authority_mirror_live_nodes_tested': False,
               'unbounded_scalability_proved': False,
               'hardware_required': False, 'extension_loaded': False,
               'terminal_functional_readback': False, 'local_effect_readback': False,
               'product_target_verified': False, 'authenticated_runtime_readback': False,
               'public_url_fresh_readback': False,
               'personal_release_effect_ack_done': False, 'state': 'HOLD'}
    if linux:
        receipt.update(schema='qikvrt_firefox_linux_seed_ring_witness_v1',
                       operating_system_built_from_seed=False, productive_mesh_runtime_verified=False)
    driver = None
    server = None
    terminal = None
    try:
        expected = os.environ.get('QIKVRT_EXPECTED_HEAD')
        if expected and expected != receipt['head']:
            raise RuntimeError('EXACT_HEAD_MISMATCH')
        if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT):
            raise RuntimeError('DIRTY_CANDIDATE')
        if linux:
            if sys.platform != 'linux':
                raise RuntimeError('LINUX_EXECUTION_REQUIRED')
            receipt['os'] = {'platform': platform.platform(), 'architecture': platform.machine(),
                             'distribution': platform.freedesktop_os_release()}
        else:
            receipt['os'] = windows_identity()
            receipt['architecture_evidence_scope'] = receipt['os']['architecture']
            receipt['architecture_evidence_transfer'] = False
            receipt['python_binary_architecture'] = pe_architecture(sys.executable)
            if receipt['python_binary_architecture'] != receipt['os']['architecture']:
                raise RuntimeError('NATIVE_WINDOWS_INTERPRETER_ARCHITECTURE_REQUIRED')
        if not linux and sys.version_info[:3] != (3, 13, 15):
            raise RuntimeError('WINDOWS_WITNESS_INTERPRETER_VERSION_MISMATCH')
        receipt['python_version'] = platform.python_version()
        receipt['product_target_verified'] = False if linux else target_matches(receipt['os'], contract['product_target'])
        if linux:
            gecko_path = shutil.which('geckodriver')
            if not gecko_path and os.environ.get('GECKOWEBDRIVER'):
                candidate = Path(os.environ['GECKOWEBDRIVER']) / 'geckodriver'
                if candidate.is_file():
                    gecko_path = str(candidate)
            firefox_path = shutil.which('firefox')
            if not gecko_path or not firefox_path:
                raise RuntimeError('DECLARED_LINUX_RUNNER_FIREFOX_OR_GECKODRIVER_UNAVAILABLE')
            gecko = Path(gecko_path).resolve()
            firefox = Path(firefox_path).resolve()
            receipt['driver_version'] = subprocess.check_output([str(gecko), '--version'], text=True, timeout=20)
            if not receipt['driver_version'].startswith('geckodriver ' + contract['geckodriver_version'] + ' '):
                raise RuntimeError('GECKODRIVER_COMMAND_CONTRACT_FAILED')
        else:
            gecko = provision_driver(contract, output / 'driver-cache', receipt['os']['architecture'])
            receipt['driver_binary_architecture'] = pe_architecture(gecko)
            if receipt['driver_binary_architecture'] != receipt['os']['architecture']:
                raise RuntimeError('NATIVE_WINDOWS_DRIVER_ARCHITECTURE_REQUIRED')
        receipt['driver_sha256'] = digest(gecko)
        if not linux:
            firefox = Path(os.environ.get('QIKVRT_FIREFOX_BINARY',
                                         r'C:\Program Files\Mozilla Firefox\firefox.exe'))
        receipt['firefox_binary_sha256'] = digest(firefox)
        if not linux:
            receipt['firefox_binary_architecture'] = pe_architecture(firefox)
            receipt['browser_execution_mode'] = ('NATIVE' if receipt['firefox_binary_architecture'] ==
                                                 receipt['os']['architecture'] else 'WINDOWS_EMULATION')
        xpi = output / 'standard.xpi'
        package = policy['standard_firefox_package']
        with zipfile.ZipFile(xpi, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in package['files']:
                info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, (ROOT / package['root'] / name).read_bytes())
        receipt['xpi_sha256'] = digest(xpi)
        receipt['installation_mode'] = 'TEMPORARY_UNSIGNED_TEST_ADDON'
        receipt['persistent_signed_installation_verified'] = False
        # Reuse the real local terminal backend; no mock DONE responder.
        sys.path.insert(0, str(ROOT / 'src'))
        import qikvrt_effect_ack_http_terminal as terminal
        from http.server import ThreadingHTTPServer
        seed, state_root = initialize_seeded_terminal(terminal, contract, output)
        receipt['seed_binding'] = terminal.STATE.seed_binding
        receipt['persistence_scope'] = terminal.STATE.persistence_scope
        requests = []
        http_paths = []
        class ObservedHandler(terminal.Handler):
            def do_GET(self):
                http_paths.append({"method": "GET", "path": self.path})
                super().do_GET()

            def do_POST(self):
                http_paths.append({"method": "POST", "path": self.path})
                super().do_POST()

            def _prepare(self, body):
                requests.append(body)
                super()._prepare(body)
        server = ThreadingHTTPServer(('127.0.0.1', 8771), ObservedHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with (output / 'geckodriver.log').open('w', encoding='utf-8') as log:
            driver = WebDriver(gecko, log)
            session = driver.call('POST', '/session', {'capabilities': {'alwaysMatch': {
                'browserName': 'firefox', 'moz:firefoxOptions': {
                    'binary': str(firefox), 'args': ['-headless'] if headless else []}}}})
            driver.session = session['sessionId']
            receipt['browser_capabilities'] = session['capabilities']
            if linux:
                if not session['capabilities']['browserVersion'].startswith(contract['firefox_version_prefix']):
                    raise RuntimeError('DECLARED_LINUX_FIREFOX_VERSION_MISMATCH')
                pid = int(session['capabilities']['moz:processID'])
                executable = Path('/proc') / str(pid) / 'exe'
                receipt['firefox_runtime_executable_sha256'] = digest(executable)
                receipt['firefox_runtime_executable'] = str(executable.resolve())
            if not linux and session['capabilities']['browserVersion'] != contract['firefox']['version']:
                raise RuntimeError('FIREFOX_VERSION_MISMATCH')
            if not linux:
                public, public_artifact = observe_public_url(driver, contract, receipt, output)
                receipt['public_url_readback'] = public
                receipt['public_url_readback_artifact'] = public_artifact
                receipt['public_url_fresh_readback'] = public['public_url_fresh_readback']
            addon = driver.command('/moz/addon/install', {'path': str(xpi.resolve()), 'temporary': True})
            if addon != 'qikvrt-ai-terminal@goldkelch.local':
                raise RuntimeError('ADDON_ID_MISMATCH')
            receipt['extension_loaded'] = True
            # Temporary installation omits the normal install-time consent UI.
            # Observe and grant only the already-declared loopback test origin,
            # through Firefox's own permission store, in the throwaway profile.
            driver.command('/moz/context', {'context': 'chrome'})
            permission_script = (
                'const e=WebExtensionPolicy.getByID(arguments[0]).extension;'
                'return {active:e.activePermissions,loopback_allowed:'
                'e.activePermissions.origins.includes("http://127.0.0.1/*")};')
            receipt['permissions_before'] = driver.script(permission_script, [addon])
            receipt['test_host_permission_granted'] = False
            if not receipt['permissions_before']['loopback_allowed']:
                origin = 'http://127.0.0.1/*'
                manifest = json.loads((ROOT / package['root'] / 'manifest.json').read_text())
                if origin not in manifest['host_permissions']:
                    raise RuntimeError('TEST_ORIGIN_NOT_DECLARED')
                driver.command('/execute/async', {'script':
                    'const done=arguments[arguments.length-1];'
                    'const {ExtensionPermissions}=ChromeUtils.importESModule('
                    '"resource://gre/modules/ExtensionPermissions.sys.mjs");'
                    'ExtensionPermissions.add(arguments[0],{permissions:[],origins:[arguments[1]]},'
                    'WebExtensionPolicy.getByID(arguments[0]).extension).then(()=>done(true),'
                    'error=>done({error:String(error)}));', 'args': [addon, origin]})
                receipt['test_host_permission_granted'] = True
            receipt['permissions_after'] = driver.script(permission_script, [addon])
            if not receipt['permissions_after']['loopback_allowed']:
                raise RuntimeError('DECLARED_LOOPBACK_HOST_PERMISSION_REQUIRED')
            receipt['production_permission_consent_verified'] = False
            driver.command('/moz/context', {'context': 'content'})
            driver.command('/url', {'url': contract['terminal_url']})
            wait_script(driver, 'return !!document.querySelector("#qikvrt-ai-terminal-host");')
            receipt['terminal_functional_readback'] = True
            before = readback()
            nonce = ('linux-witness-' if linux else 'windows-witness-') + os.urandom(16).hex()
            driver.script('document.querySelector("#qv-command").value=arguments[0];'
                          'document.querySelector("[data-act=prepare]").click();', [nonce])
            wait_script(driver, 'return !document.querySelector("[data-act=commit]").disabled;')
            prepared = driver.script('return JSON.parse(document.querySelector("[data-role=output]").textContent);')
            if prepared.get('record_validated') is not True or readback()['events'] != before['events']:
                raise RuntimeError('PREPARE_BINDING_OR_NO_EFFECT_FAILED')
            if prepared['full_record'].get('seed_binding') != receipt['seed_binding']:
                raise RuntimeError('FIREFOX_SEED_RECORD_BINDING_FAILED')
            receipt['prepared_record'] = prepared['full_record']
            receipt['prepared_request'] = requests[-1]
            driver.script('document.querySelector("[data-act=commit]").click();')
            deadline = time.monotonic() + 30
            after = readback()
            while after['events'] == before['events'] and time.monotonic() < deadline:
                time.sleep(.2)
                after = readback()
            if not verify_effect_readback(before, after, prepared, requests[-1], receipt):
                raise RuntimeError('FRESH_EFFECT_READBACK_FAILED')
            # Exact same token/payload must be rejected after the first commit.
            (output / 'screenshot.png').write_bytes(base64.b64decode(driver.command('/screenshot', method='GET')))
            driver.command('/moz/context', {'context': 'chrome'})
            uuid = driver.script('return JSON.parse(Services.prefs.getStringPref("extensions.webextensions.uuids"))[arguments[0]];', [addon])
            driver.command('/moz/context', {'context': 'content'})
            driver.command('/url', {'url': 'moz-extension://' + uuid + '/options.html'})
            replay = driver.command('/execute/async', {'script':
                'browser.runtime.sendMessage({kind:"COMMIT_EFFECT",payload:arguments[0]}).then(arguments[arguments.length-1]);',
                'args': [{'confirmed': True, 'prepared': prepared, 'request': requests[-1]}]})
            if replay.get('ordinary_release') is not False or replay.get('http_status') != 409 or readback()['events'] != after['events']:
                raise RuntimeError('REPLAY_NOT_REJECTED')
            if linux:
                receipt['ring_controls'] = bounded_ring_controls(terminal)
            expected_snapshot = receipt['ring_controls']['event_snapshot'] if linux else None
            if not linux:
                with urllib.request.urlopen('http://127.0.0.1:8771/terminal/events', timeout=10) as response:
                    expected_snapshot = json.load(response)
            receipt['observed_http_paths'] = http_paths
            server.shutdown()
            server.server_close()
            server = None
            terminal.STATE.close()
            firefox_field = ('v=1, mode=commit, token='
                + terminal.sf_bytes(prepared['effect_ack']['commit_token'].encode('ascii'))
                + ', hash=' + terminal.sf_bytes(bytes.fromhex(prepared['effect_ack']['record_hash'])))
            receipt['restart_controls'] = durable_restart_controls(
                terminal, state_root, seed, expected_snapshot=expected_snapshot,
                replay_probes=[(requests[-1], firefox_field)])
            if linux:
                receipt['network_loss_controls'] = network_loss_controls(
                    terminal, state_root, seed,
                    expected_snapshot=receipt['restart_controls']['replay_event_snapshot'])
                receipt['network_loss_injected'] = receipt['network_loss_controls']['network_loss_injected']
            receipt['state_rejection_controls'] = durable_state_rejection_controls(
                terminal, state_root, seed, terminal.STATE.store)
            receipt['altered_seed_start_refused'] = True
            receipt['persistent_state_sha256'] = digest(terminal.STATE.store)
            if linux:
                receipt['scale_consolidation_controls'] = lossless_scale_consolidation_controls(
                    terminal, output / 'scaled-ring', seed)
                receipt['linux_ring_test'] = 'PASS'
            receipt.update(local_effect_readback=True, replay_rejected=True,
                           readback_before=before, readback_after=after,
                           effect_scope='LOCAL_LOOPBACK_TERMINAL_EVENT_ONLY',
                           external_effect='NONE', windows_witness_test='PASS',
                           reason='HOLD_PERSONAL_CAPABILITY_AUTHENTICATED_RUNTIME_AND_RELEASE_INSTALL_REQUIRED')
            if not receipt['public_url_fresh_readback']:
                receipt['reason'] = 'HOLD_PUBLIC_URL_AND_SEPARATE_PERSONAL_RELEASE_GATES'
            if not receipt['product_target_verified']:
                receipt['reason'] = 'HOLD_SUPPORTED_WINDOWS_11_CLIENT_WITNESS_REQUIRED'
                if not linux:
                    receipt['windows_witness_test'] = 'HOLD'
            if not linux and receipt['browser_execution_mode'] != 'NATIVE':
                receipt['windows_witness_test'] = 'HOLD'
                receipt['reason'] = 'HOLD_NATIVE_WINDOWS_ARCHITECTURE_EXECUTION_REQUIRED'
            if linux:
                receipt.pop('windows_witness_test', None)
                receipt['reason'] = 'HOLD_COMPLETE_MESH_LINUX_CLOSURE_LIVE_NODES_AND_RELEASE_GATES'
        return 0
    except Exception as error:
        receipt['reason'] = type(error).__name__ + ': ' + str(error)
        if linux:
            receipt['linux_ring_test'] = 'FAIL'
        else:
            receipt['windows_witness_test'] = 'FAIL'
        if driver and driver.session:
            try:
                receipt['terminal_diagnostics'] = driver.script(
                    'return {url:location.href,status:document.querySelector("[data-role=status]")?.textContent,'
                    'output:document.querySelector("[data-role=output]")?.textContent};')
                (output / 'screenshot.png').write_bytes(base64.b64decode(
                    driver.command('/screenshot', method='GET')))
            except Exception as diagnostic_error:
                receipt['diagnostics_error'] = type(diagnostic_error).__name__
            try:
                driver.command('/moz/context', {'context': 'chrome'})
                receipt['firefox_security_diagnostics'] = driver.script(
                    'return Services.console.getMessageArray().map(m=>m.message)'
                    '.filter(m=>/loopback|localhost|127\\.0\\.0\\.1|network access|Content Security|CSP|mixed content/i.test(m)).slice(-20);')
            except Exception as diagnostic_error:
                receipt['security_diagnostics_error'] = type(diagnostic_error).__name__
        return 1
    finally:
        if driver:
            try:
                driver.close()
            except Exception as error:
                receipt['cleanup_error'] = type(error).__name__
        if server:
            receipt['observed_http_paths'] = http_paths
            server.shutdown()
            server.server_close()
        if terminal is not None:
            terminal.STATE.close()
        (output / 'RECEIPT.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    if '--benchmark-terminal-worker' in sys.argv:
        sys.argv.remove('--benchmark-terminal-worker')
        sys.path.insert(0, str(ROOT / 'src'))
        import qikvrt_effect_ack_http_terminal as terminal
        sys.exit(benchmark_terminal_worker(terminal))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--repetitions', type=int, default=6,
                        help='Comparable benchmark repetitions per process count (3/6/9/12)')
    parser.add_argument('--workload', type=int, default=64,
                        help='Identical comparable benchmark effect count (4..256, divisible by 4)')
    parser.add_argument('--preload-per-origin', type=int, default=4,
                        help='Identical preloaded effects per origin in the separate benchmark')
    profiles = parser.add_mutually_exclusive_group()
    profiles.add_argument('--linux-ring', dest='profile', action='store_const', const='linux',
                          help='Primary Linux Firefox reference with canonical seed')
    profiles.add_argument('--windows-witness', dest='profile', action='store_const', const='windows',
                          help='Independent Windows extension acceptance')
    profiles.add_argument('--local-ring-only', dest='profile', action='store_const', const='local',
                          help='Actual Linux process scale/consolidation without an external service')
    profiles.add_argument('--comparable-scale-benchmark', dest='profile', action='store_const', const='benchmark',
                          help='Separate repeated 1/2/4-process comparison with identical preloaded stores')
    parser.set_defaults(profile='linux' if sys.platform == 'linux' else 'windows')
    args = parser.parse_args()
    if args.profile == 'benchmark':
        output = args.output.absolute()
        if output.exists():
            parser.error('new benchmark output required; existing state is never reset or overwritten')
        sys.path.insert(0, str(ROOT / 'src'))
        import qikvrt_effect_ack_http_terminal as terminal
        try:
            receipt = comparable_scale_benchmark(terminal, output,
                ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin', repetitions=args.repetitions,
                workload=args.workload, preload_per_origin=args.preload_per_origin)
        except Exception as error:
            receipt = {'schema': 'qikvrt_linux_comparable_scale_benchmark_v1', 'state': 'HOLD',
                'head': terminal.git_read('rev-parse', 'HEAD'), 'tree': terminal.git_read('rev-parse', 'HEAD^{tree}'),
                'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'reason': str(error),
                'comparative_speedup_proved': False, 'unbounded_scalability_proved': False,
                'personal_release_effect_ack_done': False}
            output.mkdir(parents=True, exist_ok=True)
        (output / 'RECEIPT.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({key: value for key, value in receipt.items() if key != 'measurements'}, sort_keys=True))
        sys.exit(0 if receipt['state'] == 'PASS' else 2)
    if args.profile == 'local':
        output = args.output.absolute()
        output.mkdir(parents=True, exist_ok=False)
        sys.path.insert(0, str(ROOT / 'src'))
        import qikvrt_effect_ack_http_terminal as terminal
        receipt = {'schema': 'qikvrt_linux_local_runtime_witness_v1',
                   'head': terminal.git_read('rev-parse', 'HEAD'),
                   'tree': terminal.git_read('rev-parse', 'HEAD^{tree}'),
                   'runtime_profile': 'LINUX_RING_PRIMARY_REFERENCE',
                   'predecessor_evidence_transfer': False,
                   'personal_release_effect_ack_done': False,
                   'source_sha256': {path: digest(ROOT / path) for path in (
                       'src/qikvrt_effect_ack_http_terminal.py', 'tools/qikvrt_firefox_windows_witness.py',
                       'policy/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.json')}}
        try:
            receipt['scale_consolidation_controls'] = lossless_scale_consolidation_controls(
                terminal, output / 'scaled-ring', ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin')
            receipt['state'] = 'PASS'
        except Exception as error:
            receipt.update(state='HOLD', reason=str(error))
        (output / 'RECEIPT.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(receipt, sort_keys=True))
        sys.exit(0 if receipt['state'] == 'PASS' else 2)
    sys.exit(witness(args.output.resolve(), args.headless, args.profile == 'linux'))
