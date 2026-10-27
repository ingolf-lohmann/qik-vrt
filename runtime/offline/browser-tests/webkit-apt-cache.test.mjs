// Copyright 2026 Ingolf Lohmann. Implementation contribution: Claude (Anthropic).
// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Local fixtures and workflow-source contracts only; no hosted runner or cache
// service is exercised and no browser acceptance is claimed.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { aptCacheConfig, cacheSummary, fetchedArchives } from './webkit-apt-cache.mjs';

const MODULE = new URL('./webkit-apt-cache.mjs', import.meta.url).pathname;
const sha = raw => createHash('sha256').update(raw).digest('hex');
const workflow = () => readFileSync(new URL('../../../.github/workflows/qikvrt_ci.yml', import.meta.url), 'utf8');
const webkitLeg = () => workflow().split('\n  offline_browser:\n')[1].split('\n  amo_unlisted:\n')[0];
const step = (leg, name) => {
  const start = leg.indexOf(`      - name: ${name}\n`);
  assert.notEqual(start, -1, `missing step ${name}`);
  const next = leg.indexOf('\n      - ', start + 1);
  return leg.slice(start, next === -1 ? undefined : next);
};
const shellRun = block => block.split('\n        run: |\n')[1]
  .split('\n').map(line => line.replace(/^          /, '')).join('\n');

test('APT configuration only relocates the archive cache and never weakens authentication', () => {
  const text = aptCacheConfig('/var/cache/qikvrt-webkit-apt/archives');
  assert.match(text, /^Dir::Cache::Archives "\/var\/cache\/qikvrt-webkit-apt\/archives\/";$/m);
  assert.match(text, /^APT::Keep-Downloaded-Packages "true";$/m);
  assert.doesNotMatch(text, /AllowUnauthenticated|AllowInsecure|trusted|Check-Valid-Until|Verify-Peer|Sandbox::/i);
  assert.equal(aptCacheConfig('/tmp/a/'), aptCacheConfig('/tmp/a'));
});

test('an unreadable archive inventory is an error rather than an empty cache', () => {
  const dir = mkdtempSync(join(tmpdir(), 'qikvrt-webkit-apt-inventory-'));
  try {
    const file = join(dir, 'not-a-directory');
    writeFileSync(file, 'not an archive directory');
    assert.throws(() => cacheSummary(file), { code: 'ENOTDIR' });
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('the actual install shell retains install failures and rejects missing after-evidence on success', () => {
  const script = shellRun(step(webkitLeg(), 'Install WebKit system dependencies (bounded diagnosis)'));
  for (const [installStatus, existingAfter, expected] of [[0, true, 1], [124, true, 124], [0, false, 0]]) {
    const dir = mkdtempSync(join(tmpdir(), 'qikvrt-webkit-apt-shell-'));
    try {
      const evidence = join(dir, 'evidence'), bin = join(dir, 'bin');
      mkdirSync(evidence); mkdirSync(bin);
      writeFileSync(join(bin, 'timeout'), '#!/bin/sh\nexit "$QIKVRT_TEST_INSTALL_STATUS"\n', { mode: 0o755 });
      if (existingAfter) writeFileSync(join(evidence, 'APT_CACHE_AFTER.json'), 'original receipt');
      const result = spawnSync('bash', ['-c', script], {
        cwd: new URL('../../../', import.meta.url), encoding: 'utf8',
        env: { ...process.env, PATH: bin + ':' + process.env.PATH, HOME: dir, RUNNER_TEMP: dir,
          QIKVRT_TEST_INSTALL_STATUS: String(installStatus), QIKVRT_OFFLINE_EVIDENCE_DIR: evidence },
      });
      assert.equal(result.status, expected, result.stdout + result.stderr);
      assert.match(readFileSync(join(evidence, 'INSTALL_PHASE_SYSTEM_DEPS.txt'), 'utf8'),
        new RegExp(`^exit_status=${installStatus}$`, 'm'));
      if (existingAfter) assert.equal(readFileSync(join(evidence, 'APT_CACHE_AFTER.json'), 'utf8'), 'original receipt');
      if (installStatus === 124) assert.match(result.stdout, /WEBKIT_SYSTEM_DEPENDENCIES_TIMEOUT/);
    } finally { rmSync(dir, { recursive: true, force: true }); }
  }
});

test('missing runner image identity stops before any privileged configuration or cache creation', () => {
  const script = shellRun(step(webkitLeg(), 'Bind WebKit package and browser caches'));
  const dir = mkdtempSync(join(tmpdir(), 'qikvrt-webkit-apt-binding-'));
  try {
    for (const [imageOS, imageVersion] of [['', '20261026.1.0'], ['ubuntu24', '']]) {
      const result = spawnSync('bash', ['-c', script], { encoding: 'utf8',
        env: { ...process.env, HOME: dir, RUNNER_TEMP: dir, ImageOS: imageOS, ImageVersion: imageVersion } });
      assert.notEqual(result.status, 0);
      assert.match(result.stderr, /RUNNER_IMAGE_(OS|VERSION)_REQUIRED/);
      assert.equal(existsSync(join(dir, 'qikvrt-webkit-apt')), false);
    }
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('unsafe archive paths are rejected before they can reach root APT configuration', () => {
  for (const bad of ['relative/dir', '/tmp/a"; APT::Get::AllowUnauthenticated "true', '/tmp/a\nX', '/tmp/../etc',
    '/tmp/./a', '/tmp//a', '/', '/tmp/a{b}', '/tmp/a;b', '/tmp/a\\b', undefined]) {
    assert.throws(() => aptCacheConfig(bad), /ARCHIVE_DIRECTORY/, String(bad));
  }
});

test('summary binds only regular .deb files and ignores partial downloads, locks and links', () => {
  const dir = mkdtempSync(join(tmpdir(), 'qikvrt-webkit-apt-'));
  try {
    const a = Buffer.from('package a'), b = Buffer.from('package bb');
    writeFileSync(join(dir, 'libb_1.0_amd64.deb'), b);
    writeFileSync(join(dir, 'liba_2%3a1.0_amd64.deb'), a);
    writeFileSync(join(dir, 'lock'), '');
    writeFileSync(join(dir, 'notes.txt'), 'x');
    mkdirSync(join(dir, 'partial'));
    writeFileSync(join(dir, 'partial', 'libc_1_amd64.deb'), 'incomplete');
    symlinkSync(join(dir, 'liba_2%3a1.0_amd64.deb'), join(dir, 'link_1_amd64.deb'));
    const summary = cacheSummary(dir);
    assert.deepEqual(summary.packages.map(p => p.name), ['liba_2%3a1.0_amd64.deb', 'libb_1.0_amd64.deb']);
    assert.equal(summary.packages[0].sha256, sha(a));
    assert.equal(summary.total_bytes, a.length + b.length);
    assert.equal(summary.integrity_authority, 'APT_SIGNED_INDEX_AT_INSTALL_TIME');
    assert.equal(summary.browser_acceptance_established, false);
    assert.equal(summary.effect_ack_done, false);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('a missing archive directory is an empty cache, and receipts are never overwritten', () => {
  const dir = mkdtempSync(join(tmpdir(), 'qikvrt-webkit-apt-cli-'));
  try {
    const out = join(dir, 'APT_CACHE_BEFORE.json');
    const run = () => spawnSync(process.execPath, [MODULE, 'summary', join(dir, 'missing'), out], { encoding: 'utf8' });
    const first = run();
    assert.equal(first.status, 0, first.stderr);
    assert.match(first.stdout, /^apt_archive_packages=0$/m);
    assert.equal(JSON.parse(readFileSync(out, 'utf8')).package_count, 0);
    assert.equal(run().status, 1, 'existing receipt must not be replaced');
    const config = spawnSync(process.execPath, [MODULE, 'config', join(dir, 'archives')], { encoding: 'utf8' });
    assert.equal(config.status, 0, config.stderr);
    assert.match(config.stdout, /Dir::Cache::Archives/);
    assert.equal(spawnSync(process.execPath, [MODULE, 'config', 'relative'], { encoding: 'utf8' }).status, 1);
    assert.equal(spawnSync(process.execPath, [MODULE], { encoding: 'utf8' }).status, 2);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test('workflow restores caches before installation and keeps the bounded original install path', () => {
  const leg = webkitLeg();
  const order = ['Bind WebKit package and browser caches', 'Restore WebKit system package cache',
    'Restore WebKit browser binary cache', 'Install WebKit system dependencies (bounded diagnosis)',
    'Save WebKit system package cache', 'Observe root APT limits and same-package HTTP HTTPS transfer',
    'Install exact package-bound WebKit binary (bounded diagnosis)', 'Save WebKit browser binary cache',
    'Fresh offline and full browser-process restart controls'];
  const positions = order.map(name => leg.indexOf(`      - name: ${name}\n`));
  assert.ok(positions.every(p => p >= 0), JSON.stringify(positions));
  assert.deepEqual([...positions].sort((x, y) => x - y), positions);
  const partial = leg.indexOf('sudo install -d -o _apt -g root -m 0700 "$archives/partial"');
  assert.ok(partial >= 0 && partial < positions[1], 'sandbox partial directory must exist before cache restore');
  const install = step(leg, 'Install WebKit system dependencies (bounded diagnosis)');
  assert.match(install, /timeout --signal=TERM --kill-after=30s 12m .*playwright install-deps webkit/);
  assert.match(install, /if \[ "\$status" -eq 124 \]; then[^\n]*\n\s*exit "\$status"/);
  assert.match(install, /apt_cache_exact_hit=/);
});

test('caches are keyed to runner image and lockfile, use repository-pinned actions and only save verified results', () => {
  const leg = webkitLeg();
  const restoreApt = step(leg, 'Restore WebKit system package cache');
  assert.match(restoreApt, /actions\/cache\/restore@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6\.1\.0/);
  assert.match(restoreApt, /key: qikvrt-webkit-apt-v2-.*steps\.webkit_cache_binding\.outputs\.image.*hashFiles\('runtime\/offline\/browser-tests\/package-lock\.json'\)/);
  assert.doesNotMatch(restoreApt, /qikvrt-webkit-apt-v1-/);
  assert.match(restoreApt, /path: \/var\/cache\/qikvrt-webkit-apt\/archives\/\*\.deb$/m);
  const saveApt = step(leg, 'Save WebKit system package cache');
  assert.match(saveApt, /actions\/cache\/save@0057852bfaa89a56745cba8c7296529d2fc39830 # v4\.3\.0/);
  assert.match(saveApt, /steps\.webkit_system_deps\.outcome == 'success'/);
  assert.match(saveApt, /steps\.webkit_apt_cache\.outputs\.cache-hit != 'true'/);
  const saveBrowser = step(leg, 'Save WebKit browser binary cache');
  assert.match(saveBrowser, /steps\.webkit_browser_binary\.outcome == 'success'/);
  assert.match(saveBrowser, /path: ~\/\.cache\/ms-playwright\/webkit-\*$/m);
  for (const block of [restoreApt, saveApt, saveBrowser, step(leg, 'Restore WebKit browser binary cache')]) {
    assert.doesNotMatch(block, /secrets\.|GITHUB_TOKEN|\.ssh|\.gnupg/);
    assert.match(block, /if: matrix\.engine == 'webkit'/);
  }
  const bind = step(leg, 'Bind WebKit package and browser caches');
  assert.match(bind, /webkit-apt-cache\.mjs config/);
  assert.match(bind, /sudo tee \/etc\/apt\/apt\.conf\.d\/99qikvrt-webkit-archive-cache/);
  assert.match(bind, /sudo install -d -o "\$\(id -un\)" -g "\$\(id -gn\)" -m 0755 "\$archives"/);
  assert.match(bind, /sudo install -d -o _apt -g root -m 0700 "\$archives\/partial"/);
  assert.match(bind, /sudo -u _apt test -w "\$archives\/partial"/);
  assert.match(step(leg, 'Restore WebKit browser binary cache'), /key: qikvrt-webkit-browser-v1-.*steps\.webkit_cache_binding\.outputs\.image.*hashFiles/);
  assert.match(leg, /APT_CACHE_\*\.json/);
});

test('fetched-archive evidence is exact only for a single APT "0 B" line and UNKNOWN otherwise', () => {
  assert.deepEqual(fetchedArchives('Reading package lists...\nNeed to get 0 B/117 MB of archives.\nDone\n'),
    { bytes_fetched: '0', exact: true, line: 'Need to get 0 B/117 MB of archives.', matches: 1 });
  assert.equal(fetchedArchives('Need to get 117 MB of archives.\n').bytes_fetched, 'ROUNDED:117 MB');
  assert.equal(fetchedArchives('Need to get 1,234 kB/117 MB of archives.\n').bytes_fetched, 'ROUNDED:1,234 kB');
  assert.equal(fetchedArchives('Need to get 117 MB of archives.\n').exact, false);
  for (const text of ['', 'no apt line here', 'Need to get 0 B of archives.\nNeed to get 0 B of archives.',
    'Need to get lots of archives.', 'Need to get 0 B/117 MB of archives. extra', undefined]) {
    const result = fetchedArchives(text);
    assert.equal(result.bytes_fetched, 'UNKNOWN', JSON.stringify(text));
    assert.equal(result.exact, false);
  }
});

test('the actual install shell records the APT fetch line and keeps the install exit status', () => {
  const script = shellRun(step(webkitLeg(), 'Install WebKit system dependencies (bounded diagnosis)'));
  for (const [line, installStatus, expectedField] of [
    ['Need to get 0 B/117 MB of archives.', 0, 'apt_archive_bytes_fetched=0'],
    ['Need to get 117 MB of archives.', 0, 'apt_archive_bytes_fetched=ROUNDED:117 MB'],
    ['', 23, 'apt_archive_bytes_fetched=UNKNOWN']]) {
    const dir = mkdtempSync(join(tmpdir(), 'qikvrt-webkit-apt-fetched-'));
    try {
      const evidence = join(dir, 'evidence'), bin = join(dir, 'bin');
      mkdirSync(evidence); mkdirSync(bin);
      writeFileSync(join(bin, 'timeout'),
        '#!/bin/sh\nprintf \'%s\\n\' "$QIKVRT_TEST_APT_LINE"\nexit "$QIKVRT_TEST_INSTALL_STATUS"\n', { mode: 0o755 });
      const result = spawnSync('bash', ['-c', script], {
        cwd: new URL('../../../', import.meta.url), encoding: 'utf8',
        env: { ...process.env, PATH: bin + ':' + process.env.PATH, HOME: dir, RUNNER_TEMP: dir,
          QIKVRT_TEST_APT_LINE: line, QIKVRT_TEST_INSTALL_STATUS: String(installStatus),
          QIKVRT_OFFLINE_EVIDENCE_DIR: evidence },
      });
      const receipt = readFileSync(join(evidence, 'INSTALL_PHASE_SYSTEM_DEPS.txt'), 'utf8');
      assert.match(receipt, new RegExp(`^${expectedField}$`, 'm'), receipt);
      assert.match(receipt, new RegExp(`^exit_status=${installStatus}$`, 'm'));
      assert.equal(result.status, installStatus, result.stdout + result.stderr);
    } finally { rmSync(dir, { recursive: true, force: true }); }
  }
});
