#!/usr/bin/env python3
"""Materialize the byte-locked original mathlib source, without a substitute Git identity.
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, tarfile, tempfile, urllib.request

def main():
    root = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(); ap.add_argument('--archive', type=Path)
    args = ap.parse_args()
    lock = json.loads((root/'SOURCE_LOCK.json').read_text())['mathlib']
    manifest_bytes = (root/'MATHLIB_SOURCE_MANIFEST.json').read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == lock['source_manifest_sha256']
    files = json.loads(manifest_bytes)
    def verify(directory):
        for name, expected in files.items():
            p = directory/name
            assert p.is_file() and p.stat().st_size == expected['bytes'], name
            assert hashlib.sha256(p.read_bytes()).hexdigest() == expected['sha256'], name
    target = root/'vendor/mathlib'
    if target.exists():
        verify(target); print('VERIFIED_EXISTING_ORIGINAL_MATHLIB_FILES=' + str(len(files))); return
    with tempfile.TemporaryDirectory(prefix='qikvrt-mathlib-') as temporary:
        temporary = Path(temporary); archive = args.archive or temporary/'mathlib.tar.gz'
        if args.archive is None:
            with urllib.request.urlopen(lock['archive_url'], timeout=90) as source, archive.open('wb') as out:
                shutil.copyfileobj(source,out,length=1024*1024)
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == lock['archive_sha256'], 'ARCHIVE_DIGEST_MISMATCH'
        extracted = temporary/'source'; extracted.mkdir()
        with tarfile.open(archive) as tar:
            assert tar.pax_headers.get('comment') == lock['revision'], 'ARCHIVE_REVISION_MISMATCH'
            for member in tar:
                parts = Path(member.name).parts[1:]
                if not parts: continue
                assert all(p not in ('..','.git') for p in parts)
                dest = extracted/Path(*parts)
                if member.isdir(): dest.mkdir(parents=True,exist_ok=True)
                elif member.isfile():
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    with tar.extractfile(member) as source, dest.open('wb') as out: shutil.copyfileobj(source,out)
                    dest.chmod(member.mode & 0o777)
                elif member.issym():
                    assert not Path(member.linkname).is_absolute()
                    assert (dest.parent/member.linkname).resolve().is_relative_to(extracted.resolve())
                    dest.symlink_to(member.linkname)
                else: raise ValueError('Unsupported archive member: '+member.name)
        verify(extracted)
        target.parent.mkdir(exist_ok=True)
        # Do not overwrite an existing source tree or adopt an unverified path.
        assert not target.exists()
        shutil.copytree(extracted,target,symlinks=True)
    print('VERIFIED_ORIGINAL_MATHLIB_FILES=' + str(len(files)))

if __name__ == '__main__': main()
