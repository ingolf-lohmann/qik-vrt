// Copyright 2026 Ingolf Lohmann. Implementation contribution: Claude (Anthropic).
// Sandbox and evidence-error correction: OpenAI Codex.
// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
//
// Bounded reuse of already downloaded WebKit system packages.
//
// The package archive directory is only a transport cache. APT still resolves
// the package set from the runner's signed index and verifies every reused
// .deb against that index before installation; a stale or foreign archive is
// downloaded again. This module neither weakens APT authentication nor turns a
// cache hit into browser acceptance.
import { createHash } from 'node:crypto';
import { lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { isAbsolute, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const DEB = /^[A-Za-z0-9][A-Za-z0-9.+~_%-]*\.deb$/;
const FORBIDDEN_APT_KEYS = /AllowUnauthenticated|AllowInsecureRepositories|AllowDowngradeToInsecureRepositories|trusted\s*=|Check-Valid-Until|Verify-Peer|Sandbox::User/i;

export function aptCacheConfig(directory) {
  if (typeof directory !== 'string' || !isAbsolute(directory)) throw new Error('ARCHIVE_DIRECTORY_NOT_ABSOLUTE');
  if (/["\n\r;{}\\\0]/.test(directory)) throw new Error('ARCHIVE_DIRECTORY_UNSAFE_CHARACTER');
  const stripped = directory.replace(/\/+$/, '');
  if (!stripped || normalize(stripped) !== stripped || stripped.split('/').includes('..'))
    throw new Error('ARCHIVE_DIRECTORY_NOT_NORMALIZED');
  const archives = stripped + '/';
  const text = [
    `Dir::Cache::Archives "${archives}";`,
    'APT::Keep-Downloaded-Packages "true";',
    'Binary::apt::APT::Keep-Downloaded-Packages "true";',
    'Binary::apt-get::APT::Keep-Downloaded-Packages "true";',
    '',
  ].join('\n');
  if (FORBIDDEN_APT_KEYS.test(text)) throw new Error('APT_AUTHENTICATION_WEAKENED');
  return text;
}

export function cacheSummary(directory) {
  const packages = [];
  let entries = [];
  try { entries = readdirSync(directory); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  for (const name of entries.sort()) {
    if (!DEB.test(name)) continue;
    const path = join(directory, name);
    const info = lstatSync(path);
    if (!info.isFile()) continue;
    const bytes = readFileSync(path);
    packages.push({ name, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') });
  }
  return {
    schema: 'qikvrt-webkit-apt-archive-cache/v1',
    package_count: packages.length,
    total_bytes: packages.reduce((sum, item) => sum + item.bytes, 0),
    packages,
    integrity_authority: 'APT_SIGNED_INDEX_AT_INSTALL_TIME',
    browser_acceptance_established: false,
    effect_ack_done: false,
  };
}

export function main(argv) {
  const [command, directory, output] = argv;
  if (command === 'config' && directory) {
    const text = aptCacheConfig(directory);
    mkdirSync(join(directory, 'partial'), { recursive: true });
    process.stdout.write(text);
    return 0;
  }
  if (command === 'summary' && directory && output) {
    const summary = cacheSummary(directory);
    writeFileSync(output, JSON.stringify(summary, null, 2) + '\n', { flag: 'wx' });
    process.stdout.write(`apt_archive_packages=${summary.package_count}\napt_archive_bytes=${summary.total_bytes}\n`);
    return 0;
  }
  process.stderr.write('usage: webkit-apt-cache.mjs config <archive-dir> | summary <archive-dir> <new-output.json>\n');
  return 2;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { process.exitCode = main(process.argv.slice(2)); }
  catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
}
