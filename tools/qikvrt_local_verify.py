#!/usr/bin/env python3
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
print('QIKVRT V45.4 optional Python local verify')
required = ['VERSION','README.md','QIKVRT_V45_4_RUN_LOCAL_VERIFY.cmd','tools/qikvrt_local_verify_windows.ps1']
for rel in required:
    if not (root/rel).exists():
        print('BLOCK missing', rel); sys.exit(1)
print('PASS required files present')
print('REMOTE_RELEASE_STATUS = BLOCK_UNTIL_LIVE_GITHUB_EVIDENCE')
print('LOCAL_VERIFY_STATUS = PASS_OPTIONAL_PYTHON')
sys.exit(0)
