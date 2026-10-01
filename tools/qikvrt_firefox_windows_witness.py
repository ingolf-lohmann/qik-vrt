#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Real Firefox/Windows witness; local bridge evidence never accepts a release."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'policy/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.json'


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


def wait_script(driver, script):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = driver.script(script)
        if result:
            return result
        time.sleep(.2)
    raise RuntimeError('BROWSER_FUNCTIONAL_TIMEOUT')


def witness(output, headless=False):
    output.mkdir(parents=True, exist_ok=True)
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    contract = policy['windows_acceptance']
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
               'personal_release_effect_ack_done': False, 'state': 'HOLD'}
    driver = None
    server = None
    try:
        expected = os.environ.get('QIKVRT_EXPECTED_HEAD')
        if expected and expected != receipt['head']:
            raise RuntimeError('EXACT_HEAD_MISMATCH')
        if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT):
            raise RuntimeError('DIRTY_CANDIDATE')
        receipt['os'] = windows_identity()
        if sys.version_info[:3] != (3, 13, 15):
            raise RuntimeError('WINDOWS_WITNESS_INTERPRETER_VERSION_MISMATCH')
        receipt['python_version'] = platform.python_version()
        receipt['product_target_verified'] = target_matches(receipt['os'], contract['product_target'])
        gecko = provision_driver(contract, output / 'driver-cache', receipt['os']['architecture'])
        receipt['driver_sha256'] = digest(gecko)
        firefox = Path(os.environ.get('QIKVRT_FIREFOX_BINARY',
                                     r'C:\Program Files\Mozilla Firefox\firefox.exe'))
        receipt['firefox_binary_sha256'] = digest(firefox)
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
        terminal.STATE = terminal.State()
        requests = []
        class ObservedHandler(terminal.Handler):
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
            if session['capabilities']['browserVersion'] != contract['firefox']['version']:
                raise RuntimeError('FIREFOX_VERSION_MISMATCH')
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
                'e.activePermissions.origins.includes("http://127.0.0.1:8771/*")};')
            receipt['permissions_before'] = driver.script(permission_script, [addon])
            receipt['test_host_permission_granted'] = False
            if not receipt['permissions_before']['loopback_allowed']:
                origin = 'http://127.0.0.1:8771/*'
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
            receipt.update(local_effect_readback=True, replay_rejected=True,
                           readback_before=before, readback_after=after,
                           effect_scope='LOCAL_LOOPBACK_TERMINAL_EVENT_ONLY',
                           external_effect='NONE', windows_witness_test='PASS',
                           reason='HOLD_PERSONAL_CAPABILITY_AUTHENTICATED_RUNTIME_AND_RELEASE_INSTALL_REQUIRED')
            if not receipt['product_target_verified']:
                receipt['reason'] = 'HOLD_SUPPORTED_WINDOWS_11_CLIENT_WITNESS_REQUIRED'
        return 0
    except Exception as error:
        receipt['reason'] = type(error).__name__ + ': ' + str(error)
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
        return 1
    finally:
        if driver:
            try:
                driver.close()
            except Exception as error:
                receipt['cleanup_error'] = type(error).__name__
        if server:
            server.shutdown()
            server.server_close()
        (output / 'RECEIPT.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--headless', action='store_true')
    args = parser.parse_args()
    sys.exit(witness(args.output.resolve(), args.headless))
