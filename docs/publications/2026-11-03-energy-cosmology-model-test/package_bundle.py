# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Freeze and verify the bounded research package; no publication or host writes."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent
EXCLUDED={'visual_qa','__pycache__'}


def included():
    return [p for p in sorted(ROOT.rglob('*')) if p.is_file()
            and not any(x in EXCLUDED for x in p.relative_to(ROOT).parts)]


def main():
    entries=[]
    for p in included():
        if p.name in {'ARTIFACT_MANIFEST.json','SHA256SUMS.txt'}:continue
        raw=p.read_bytes();entries.append({'path':p.relative_to(ROOT).as_posix(),
            'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    manifest={'schema':'qikvrt_research_artifact_manifest_v1',
        'scope':'This research package only; no global repository, publication or host acceptance.',
        'files':entries,'file_count':len(entries),'effect_ack_done':False}
    (ROOT/'ARTIFACT_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'SHA256SUMS.txt').write_text(''.join(e['sha256']+'  '+e['path']+'\n' for e in entries))
    archive=ROOT.parent/'QIKVRT_Energie_Raumzeit_Pruefpaket_20261103.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in included():
            info=zipfile.ZipInfo(p.relative_to(ROOT).as_posix(),date_time=(2026,11,3,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(archive) as z:
        for e in entries:
            raw=z.read(e['path'])
            assert len(raw)==e['bytes'] and hashlib.sha256(raw).hexdigest()==e['sha256']
    print(json.dumps({'archive':archive.name,'payloads_verified':len(entries),
        'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()},indent=2))


if __name__=='__main__':main()
