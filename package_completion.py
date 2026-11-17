#!/usr/bin/env python3
"""Package this exact frozen candidate without live dependencies or Git internals.
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""
from pathlib import Path
import argparse, hashlib, json, zipfile

ROOT = Path(__file__).resolve().parent
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,default=ROOT.parent/'QIKVRT_RealEnergy_Completion_20261103.zip')
    args=ap.parse_args()
    assert not args.output.resolve().is_relative_to(ROOT), 'Output must be outside the payload tree'
    files=[p for p in sorted(ROOT.rglob('*')) if p.is_file() and not any(n in ('.git','.lake','vendor','__pycache__') for n in p.relative_to(ROOT).parts)]
    with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            info=zipfile.ZipInfo(str(p.relative_to(ROOT)),date_time=(2026,11,3,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(args.output) as z:
        assert z.testzip() is None
        for p in files: assert z.read(str(p.relative_to(ROOT)))==p.read_bytes()
    print(json.dumps({'path':str(args.output),'bytes':args.output.stat().st_size,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),'payload_files':len(files),'all_bytes_equal':True}))

if __name__=='__main__':main()
