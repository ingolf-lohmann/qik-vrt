// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Local fixtures exercise the diagnostic checker; no public runner claim.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import http from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { aptSettings, packageMetadata, probe } from './apt-diagnosis.mjs';

const bytes = Buffer.from('original package fixture bytes');
const sha = raw => createHash('sha256').update(raw).digest('hex');
const metadataText = `Package: fonts-freefont-ttf
Version: 20211204+svn4273-2
Architecture: all
Filename: pool/main/f/fonts-freefont/fonts-freefont-ttf_20211204+svn4273-2_all.deb
Size: ${bytes.length}
SHA256: ${sha(bytes)}
`;
const metadata = packageMetadata(metadataText);

async function withOrigin(handler, run) {
  const server = http.createServer(handler);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  try { await run(new URL(`http://127.0.0.1:${server.address().port}/same-package.deb`)); }
  finally { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
}

test('APT proxy credentials and unrelated secret-bearing fields never reach the report', () => {
  const result = aptSettings(`Acquire::http::Dl-Limit "50";
Acquire::http::azure.archive.ubuntu.com::Dl-Limit "60";
Acquire::https::Timeout "30";
Acquire::http::Proxy "http://person:TOP_SECRET@proxy.example/";
Unrelated "TOP_SECRET";
Acquire::Retries "TOP_SECRET";
`, { https_proxy: 'http://person:TOP_SECRET@proxy.example/', APT_CONFIG: '/private/TOP_SECRET' });
  assert.equal(result.numeric['Acquire::http::Dl-Limit'], 50);
  assert.equal(result.numeric['Acquire::http::azure.archive.ubuntu.com::Dl-Limit'], 60);
  assert.equal(result.numeric['Acquire::Retries'], 'INVALID_REDACTED');
  assert.equal(result.apt_proxy_configured.http, true);
  assert.equal(result.environment_present.https_proxy, true);
  assert.equal(JSON.stringify(result).includes('TOP_SECRET'), false);
});

test('metadata rejects wrong packages, traversal, invalid digests and oversized objects', () => {
  for (const bad of [
    metadataText.replace('Package: fonts-freefont-ttf', 'Package: unrelated'),
    metadataText.replace('pool/main/', 'pool/../'),
    metadataText.replace(sha(bytes), 'not-a-digest'),
    metadataText.replace(`Size: ${bytes.length}`, 'Size: 99999999'),
  ]) assert.throws(() => packageMetadata(bad), /PACKAGE_METADATA_INVALID/);
});

test('the requested exact range is measured and a complete small package is hash-checked', async () => {
  await withOrigin((req, res) => {
    assert.equal(req.headers.range, `bytes=0-${bytes.length - 1}`);
    assert.equal(req.headers['accept-encoding'], 'identity');
    res.writeHead(206, { 'Content-Range': `bytes 0-${bytes.length - 1}/${bytes.length}` });
    res.end(bytes);
  }, async url => {
    const result = await probe(url, metadata, 500);
    assert.equal(result.status, 'SAMPLED');
    assert.equal(result.complete_package_sha256_verified, true);
    assert.equal(result.sample_sha256, metadata.sha256);
    assert.equal(result.received_bytes, bytes.length);
    assert.equal(result.remote_address, '127.0.0.1');
    assert.ok(result.timings_ms.total >= result.timings_ms.first_byte);
  });
});

test('a live heartbeat without useful body progress hits the wall timeout', async () => {
  await withOrigin((_req, res) => { res.writeHead(200); res.flushHeaders(); }, async url => {
    const result = await probe(url, metadata, 60);
    assert.equal(result.status, 'UNVERIFIED');
    assert.equal(result.error, 'WALL_TIMEOUT');
    assert.equal(result.received_bytes, 0);
    assert.ok(result.timings_ms.total < 1000);
  });
});

test('redirects, wrong ranges and truncated bodies cannot become successful observations', async () => {
  for (const mode of ['redirect', 'wrong-range', 'truncated']) {
    await withOrigin((_req, res) => {
      if (mode === 'redirect') { res.writeHead(302, { Location: 'http://unrelated.invalid/' }); res.end(); }
      if (mode === 'wrong-range') { res.writeHead(206, { 'Content-Range': `bytes 1-${bytes.length}/${bytes.length}` }); res.end(bytes); }
      if (mode === 'truncated') res.end(bytes.subarray(0, 2));
    }, async url => {
      const result = await probe(url, metadata, 500);
      assert.equal(result.status, 'UNVERIFIED', mode);
      assert.equal(result.complete_package_sha256_verified, false);
    });
  }
});

test('identical complete but wrong bytes fail the package digest check', async () => {
  await withOrigin((_req, res) => res.end(Buffer.alloc(bytes.length)), async url => {
    const result = await probe(url, metadata, 500);
    assert.equal(result.status, 'UNVERIFIED');
    assert.equal(result.error, 'COMPLETE_PACKAGE_DIGEST_MISMATCH');
  });
});

test('large transfers are bounded to the prefix and never claim whole-package verification', async () => {
  const large = Buffer.alloc(2 * 1024 * 1024, 42);
  await withOrigin((_req, res) => res.end(large), async url => {
    const result = await probe(url, { ...metadata, size: large.length, sha256: sha(large) }, 1000);
    assert.equal(result.status, 'SAMPLED');
    assert.equal(result.received_bytes, 1024 * 1024);
    assert.equal(result.complete_package_sha256_verified, false);
  });
});

test('the original workflow retains installation failure and always uploads the diagnostic', () => {
  const workflow = readFileSync(new URL('../../../.github/workflows/qikvrt_ci.yml', import.meta.url), 'utf8');
  const leg = workflow.split('  offline_browser:')[1].split('  amo_unlisted:')[0];
  assert.match(leg, /if: \$\{\{ !cancelled\(\) && matrix.engine == 'webkit' \}\}/);
  assert.match(leg, /timeout --signal=TERM --kill-after=30s 12m .*playwright install-deps webkit/);
  assert.match(leg, /if \[ "\$status" -eq 124 \]; then[^\n]*\n\s*exit "\$status"/);
  assert.match(leg, /if: always\(\)[\s\S]*\/APT_DIAGNOSIS.json/);
  assert.match(leg, /EXPECTED_HEAD: \$\{\{ needs.test.outputs.tested_head \}\}/);
  assert.equal((leg.match(/name: Observe root APT/g) ?? []).length, 1);
});

test('wrong source and unavailable checker remain unverified, without leaking command output', () => {
  const directory = mkdtempSync(join(tmpdir(), 'qikvrt-apt-checker-'));
  try {
    for (const [name, script] of Object.entries({
      git: `echo ${'c'.repeat(40)}`,
      'apt-config': 'echo PRIVATE_COMMAND_OUTPUT >&2; exit 1',
      sudo: 'echo PRIVATE_COMMAND_OUTPUT >&2; exit 1',
      'apt-cache': 'echo PRIVATE_COMMAND_OUTPUT >&2; exit 1',
    })) writeFileSync(join(directory, name), '#!/bin/sh\n' + script + '\n', { mode: 0o755 });
    const output = join(directory, 'receipt.json');
    const run = () => spawnSync(process.execPath, [new URL('./apt-diagnosis.mjs', import.meta.url).pathname, output], {
      encoding: 'utf8', timeout: 3000,
      env: { PATH: directory, EXPECTED_HEAD: 'a'.repeat(40), EXPECTED_TREE: 'b'.repeat(40) },
    });
    const first = run();
    assert.equal(first.status, 1);
    const original = readFileSync(output);
    const report = JSON.parse(original);
    assert.equal(report.state, 'UNVERIFIED');
    assert.ok(report.errors.includes('SOURCE_BINDING_UNVERIFIED'));
    assert.ok(report.errors.includes('ROOT_APT_CONFIG_UNAVAILABLE'));
    assert.equal(report.probes.length, 0);
    assert.equal((first.stdout + first.stderr + original).includes('PRIVATE_COMMAND_OUTPUT'), false);
    assert.equal(run().status, 1);
    assert.deepEqual(readFileSync(output), original, 'a stale receipt cannot be overwritten');
  } finally { rmSync(directory, { recursive: true, force: true }); }
});
