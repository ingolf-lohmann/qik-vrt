#!/usr/bin/env python3
"""Fail-closed verifier for a QIK-VRT mini-internet evidence bundle.

Only establishes local integrity and consistency; never grants EAP or production admission.
"""
import argparse
import hashlib
import pathlib
import sys
import zipfile

REQUIRED = (
    "mini_internet.py", "c90_math_verifier.c", "setup_pki.sh",
    "web/app.jsx", "out/run1.log", "out/run2.log",
    "out/mini-internet-e2e-evidence.json",
    "out/cert-thread.txt", "out/cert-process.txt",
    "out/cert-interrupt.txt", "out/cert-network.txt",
    "SHA256SUMS",
)

def verify(archive):
    with zipfile.ZipFile(archive) as z:
        listing = z.namelist()
        if len(listing) != len(set(listing)):
            raise ValueError('duplicate ZIP member')
        names = set(listing)
        if any(n.startswith('/') or '..' in pathlib.PurePosixPath(n).parts or '\\' in n for n in names):
            raise ValueError('unsafe ZIP path')
        missing = set(REQUIRED) - names
        if missing:
            raise ValueError("missing files: " + ", ".join(sorted(missing)))
        entries = {}
        for line in z.read("SHA256SUMS").decode("utf-8").splitlines():
            digest, separator, path = line.partition("  ")
            path = path.removeprefix('./')
            if not separator or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest) or path in entries:
                raise ValueError("malformed or duplicate SHA256SUMS entry")
            entries[path] = digest
        for name in names:
            if name.endswith("/") or name == "SHA256SUMS":
                continue
            if name not in entries:
                raise ValueError("unhashed payload: " + name)
            actual = hashlib.sha256(z.read(name)).hexdigest()
            if actual != entries[name]:
                raise ValueError("hash mismatch: " + name)
        if set(entries) != names - {"SHA256SUMS"} - {n for n in names if n.endswith("/")}:
            raise ValueError("manifest coverage mismatch")
        for name in ("out/run1.log", "out/run2.log"):
            log = z.read(name).decode("utf-8")
            if "RESULT PASS 33 / 33" not in log:
                raise ValueError("missing claimed test summary: " + name)
        print("PASS: ZIP hash coverage and bundled log claims; NOT a re-execution")
        print("BLOCKED: EAP release, Lean-kernel admission, native network re-execution")
        return 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=pathlib.Path)
    args = parser.parse_args()
    try:
        return verify(args.archive)
    except (ValueError, OSError, zipfile.BadZipFile, UnicodeError) as exc:
        print("REJECTED:", exc, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
