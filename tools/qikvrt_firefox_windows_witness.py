#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Real Firefox witness on Windows or seed-bound Linux; local evidence never accepts a release."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
from concurrent.futures import ThreadPoolExecutor
import socket
import struct
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
    values.update(product_type=int(product.strip()), build=int(values['build']),
                  architecture=os.environ.get('PROCESSOR_ARCHITEW6432') or
                  os.environ.get('PROCESSOR_ARCHITECTURE'), platform=platform.platform())
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
            'event_snapshot': snapshot, 'lossless_scope': 'PROCESS_LIFETIME_EVENT_SNAPSHOT_ONLY',
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
               'run_id': os.environ.get('GITHUB_RUN_ID'),
               'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
               'job': os.environ.get('GITHUB_JOB'),
               'runner_image': os.environ.get('ImageOS'),
               'runner_image_version': os.environ.get('ImageVersion'),
               'headless': headless, 'predecessor_evidence_transfer': False,
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
        seed = ROOT / contract['seed_path'] if linux else None
        terminal.STATE = terminal.State(seed)
        if linux:
            receipt['seed_binding'] = terminal.STATE.seed_binding
            original = seed.read_bytes()
            bad_seed = output / 'altered-seed.bin'
            bad_seed.write_bytes(bytes([original[0] ^ 1]) + original[1:])
            try:
                terminal.State(bad_seed)
            except ValueError:
                receipt['altered_seed_start_refused'] = True
            else:
                raise RuntimeError('ALTERED_SEED_NOT_REFUSED')
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
            nonce = 'windows-witness-' + os.urandom(16).hex()
            driver.script('document.querySelector("#qv-command").value=arguments[0];'
                          'document.querySelector("[data-act=prepare]").click();', [nonce])
            wait_script(driver, 'return !document.querySelector("[data-act=commit]").disabled;')
            prepared = driver.script('return JSON.parse(document.querySelector("[data-role=output]").textContent);')
            if prepared.get('record_validated') is not True or readback()['events'] != before['events']:
                raise RuntimeError('PREPARE_BINDING_OR_NO_EFFECT_FAILED')
            if linux and prepared['full_record'].get('seed_binding') != receipt['seed_binding']:
                raise RuntimeError('FIREFOX_SEED_RECORD_BINDING_FAILED')
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
        return 0
    except Exception as error:
        receipt['reason'] = type(error).__name__ + ': ' + str(error)
        receipt['windows_witness_test'] = 'FAIL'
        if linux:
            receipt['linux_ring_test'] = 'FAIL'
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
        (output / 'RECEIPT.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--linux-ring', action='store_true', help='Use declared Linux runner tools and require canonical seed')
    args = parser.parse_args()
    sys.exit(witness(args.output.resolve(), args.headless, args.linux_ring))
