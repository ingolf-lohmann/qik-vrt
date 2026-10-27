// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Read-only extension of the existing WebKit installation evidence path.
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import http from 'node:http';
import https from 'node:https';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { performance } from 'node:perf_hooks';

const MIRROR = 'azure.archive.ubuntu.com';
const PACKAGE = 'fonts-freefont-ttf';
const SAMPLE_BYTES = 1024 * 1024;
const TIMEOUT_MS = 30000;
const NUMBER_KEYS = new Set([
  'Acquire::http::Dl-Limit', 'Acquire::https::Dl-Limit', 'Acquire::Retries',
  'Acquire::http::Timeout', 'Acquire::https::Timeout',
  `Acquire::http::${MIRROR}::Dl-Limit`, `Acquire::https::${MIRROR}::Dl-Limit`,
]);

export function aptSettings(text, env = {}) {
  // Never persist the dump: proxy URLs and other fields may contain secrets.
  const numeric = {}, aptProxyConfigured = { http: false, https: false };
  for (const line of text.split('\n')) {
    const m = /^([^\s]+) "([^"\r\n]*)";$/.exec(line);
    if (!m) continue;
    if (NUMBER_KEYS.has(m[1])) numeric[m[1]] = /^\d{1,10}$/.test(m[2]) ? Number(m[2]) : 'INVALID_REDACTED';
    for (const scheme of ['http', 'https']) {
      if (m[1].startsWith(`Acquire::${scheme}::Proxy`)) aptProxyConfigured[scheme] ||= Boolean(m[2]);
    }
  }
  return {
    numeric, apt_proxy_configured: aptProxyConfigured,
    environment_present: Object.fromEntries([
      'APT_CONFIG', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy',
      'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
    ].map(key => [key, Boolean(env[key])])),
    scope: 'ROOT_APT_CONFIG_AFTER_ORIGINAL_INSTALL_ATTEMPT; PROXY_VALUES_WITHHELD',
  };
}

export function packageMetadata(text) {
  const fields = Object.fromEntries(text.trim().split(/\n\s*\n/)[0].split('\n')
    .map(line => /^([A-Za-z0-9-]+): (.*)$/.exec(line)).filter(Boolean).map(m => [m[1], m[2]]));
  const filename = fields.Filename ?? '';
  if (fields.Package !== PACKAGE || !/^[A-Za-z0-9.+:~_-]+$/.test(fields.Version ?? '')
      || !['all', 'amd64', 'arm64'].includes(fields.Architecture)
      || !/^pool\/[A-Za-z0-9_+~./-]+\.deb$/.test(filename)
      || filename.split('/').includes('..') || filename.split('/').includes('.')
      || !/^[a-f0-9]{64}$/.test(fields.SHA256 ?? '')
      || !/^[1-9][0-9]{0,8}$/.test(fields.Size ?? '') || Number(fields.Size) > 32 * 1024 * 1024) {
    throw new Error('PACKAGE_METADATA_INVALID');
  }
  return { package: PACKAGE, version: fields.Version, architecture: fields.Architecture,
    filename, size: Number(fields.Size), sha256: fields.SHA256 };
}

export function probe(url, metadata, timeoutMs = TIMEOUT_MS) {
  return new Promise(resolveResult => {
    const started = performance.now(), hash = createHash('sha256');
    const wanted = Math.min(SAMPLE_BYTES, metadata.size);
    const result = { url: url.href, requested_bytes: wanted, received_bytes: 0,
      status: 'UNVERIFIED', http_status: null, timings_ms: {}, remote_address: null,
      transport: 'NODE_NATIVE_DIRECT; NO_APT_OR_ENVIRONMENT_PROXY; NO_REDIRECTS',
      complete_package_sha256_verified: false };
    let finished = false;
    const elapsed = () => Math.round((performance.now() - started) * 1000) / 1000;
    const finish = (status, error = null) => {
      if (finished) return;
      finished = true; clearTimeout(timer);
      result.status = status; result.error = error; result.timings_ms.total = elapsed();
      result.bytes_per_second = Math.round(result.received_bytes * 1000 / Math.max(1, result.timings_ms.total));
      result.sample_sha256 = hash.digest('hex');
      result.complete_package_sha256_verified = status === 'SAMPLED'
        && result.received_bytes === metadata.size && result.sample_sha256 === metadata.sha256;
      if (status === 'SAMPLED' && result.received_bytes === metadata.size
          && !result.complete_package_sha256_verified) {
        result.status = 'UNVERIFIED'; result.error = 'COMPLETE_PACKAGE_DIGEST_MISMATCH';
      }
      resolveResult(result);
    };
    const request = (url.protocol === 'https:' ? https : http).get(url, {
      agent: false, maxHeaderSize: 16384,
      headers: { Range: `bytes=0-${wanted - 1}`, 'Accept-Encoding': 'identity', 'Cache-Control': 'no-cache' },
    }, response => {
      result.http_status = response.statusCode;
      result.remote_address = response.socket.remoteAddress ?? null;
      result.timings_ms.first_byte = elapsed();
      const range = response.headers['content-range'];
      if (![200, 206].includes(response.statusCode)
          || (response.headers['content-encoding'] && response.headers['content-encoding'] !== 'identity')
          || (response.statusCode === 206 && range !== `bytes 0-${wanted - 1}/${metadata.size}`)) {
        finish('UNVERIFIED', 'HTTP_RESPONSE_NOT_REQUESTED_PACKAGE_SAMPLE'); response.destroy(); return;
      }
      response.on('data', chunk => {
        if (finished) return;
        const part = chunk.subarray(0, wanted - result.received_bytes);
        hash.update(part); result.received_bytes += part.length;
        if (result.received_bytes === wanted) { finish('SAMPLED'); response.destroy(); }
      });
      response.on('end', () => { if (!finished) finish('UNVERIFIED', 'TRUNCATED_SAMPLE'); });
      response.on('error', () => finish('UNVERIFIED', 'RESPONSE_ERROR'));
      response.on('aborted', () => finish('UNVERIFIED', 'RESPONSE_ABORTED'));
    });
    request.on('socket', socket => {
      socket.once('lookup', () => { result.timings_ms.dns = elapsed(); });
      socket.once('connect', () => { result.timings_ms.connect = elapsed(); });
      socket.once('secureConnect', () => { result.timings_ms.tls = elapsed(); });
    });
    request.on('error', () => finish('UNVERIFIED', 'REQUEST_ERROR'));
    const timer = setTimeout(() => { finish('UNVERIFIED', 'WALL_TIMEOUT'); request.destroy(); }, timeoutMs);
  });
}

export function persistReport(report, destination) {
  // Exit status describes collection, never HTTP/HTTPS transport acceptance.
  // A well-formed timeout observation must not suppress the browser gate.
  const collected = report.schema === 'qikvrt-webkit-apt-diagnosis/v1'
    && ['OBSERVED', 'UNVERIFIED'].includes(report.state)
    && Array.isArray(report.errors) && report.errors.length === 0
    && /^[a-f0-9]{40}$/.test(report.source_head ?? '')
    && /^[a-f0-9]{40}$/.test(report.source_tree ?? '')
    && report.apt && report.package && Number.isInteger(report.package.size) && report.package.size > 0
    && Array.isArray(report.probes) && report.probes.length === 2
    && report.probes.every((p, index) => p
      && p.url === `${['http', 'https'][index]}://${MIRROR}/ubuntu/${report.package.filename}`
      && ['SAMPLED', 'UNVERIFIED'].includes(p.status)
      && p.requested_bytes === Math.min(SAMPLE_BYTES, report.package.size)
      && Number.isInteger(p.received_bytes) && p.received_bytes >= 0 && p.received_bytes <= p.requested_bytes
      && (p.status !== 'SAMPLED' || p.received_bytes === p.requested_bytes)
      && Number.isFinite(p.timings_ms?.total) && p.timings_ms.total >= 0
      && /^[a-f0-9]{64}$/.test(p.sample_sha256 ?? ''))
    && report.identical_prefix_verified === (report.probes.every(p => p.status === 'SAMPLED')
      && report.probes[0].sample_sha256 === report.probes[1].sample_sha256)
    && report.state === (report.identical_prefix_verified ? 'OBSERVED' : 'UNVERIFIED');
  report.collection_state = collected ? 'RECORDED' : 'FAILED';
  report.collection_exit_status = collected ? 0 : 1;
  mkdirSync(dirname(destination), { recursive: true });
  writeFileSync(destination, JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
  console.log(JSON.stringify(report, null, 2));
  return report.collection_exit_status;
}

export async function main(destination) {
  const report = { schema: 'qikvrt-webkit-apt-diagnosis/v1', observed_at: new Date().toISOString(),
    state: 'UNVERIFIED', mirror: MIRROR, request_timeout_ms: TIMEOUT_MS,
    sample_limit_bytes: SAMPLE_BYTES, probes: [], errors: [],
    effect_ack_done: false, browser_acceptance_established: false, apt_sources_modified: false };
  const command = (name, args) => execFileSync(name, args, { encoding: 'utf8', timeout: 5000,
    maxBuffer: 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'] });
  try {
    report.source_head = command('git', ['rev-parse', 'HEAD']).trim();
    report.source_tree = command('git', ['rev-parse', 'HEAD^{tree}']).trim();
    if (!/^[a-f0-9]{40}$/.test(process.env.EXPECTED_HEAD ?? '')
        || !/^[a-f0-9]{40}$/.test(process.env.EXPECTED_TREE ?? '')
        || report.source_head !== process.env.EXPECTED_HEAD
        || report.source_tree !== process.env.EXPECTED_TREE) report.errors.push('SOURCE_BINDING_UNVERIFIED');
  } catch { report.errors.push('SOURCE_READ_UNAVAILABLE'); }
  try {
    const raw = process.getuid?.() === 0 ? command('apt-config', ['dump'])
      : command('sudo', ['-n', 'apt-config', 'dump']);
    report.apt = aptSettings(raw, process.env);
  } catch { report.errors.push('ROOT_APT_CONFIG_UNAVAILABLE'); }
  try {
    report.package = packageMetadata(command('apt-cache', ['show', '--no-all-versions', PACKAGE]));
    for (const scheme of ['http', 'https']) {
      report.probes.push(await probe(new URL(`${scheme}://${MIRROR}/ubuntu/${report.package.filename}`), report.package));
    }
    report.identical_prefix_verified = report.probes.every(p => p.status === 'SAMPLED')
      && report.probes[0].sample_sha256 === report.probes[1].sample_sha256;
    if (report.identical_prefix_verified && report.errors.length === 0) report.state = 'OBSERVED';
  } catch { report.errors.push('PACKAGE_METADATA_UNAVAILABLE_OR_INVALID'); }
  report.interpretation = 'BOUNDED_DIRECT_TRANSFER_OBSERVATION; NO_THROTTLE_OR_MIRROR_CAUSE_ESTABLISHED; NOT_AN_APT_RETRY';
  return persistReport(report, destination);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main(resolve(process.argv[2] ?? 'APT_DIAGNOSIS.json'));
}
