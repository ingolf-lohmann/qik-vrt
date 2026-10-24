# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
python3 - <<'PYTEST'
import os, sys
max_len = 0
bad = []
for root, dirs, files in os.walk('.'):
    if root.startswith('./build'):
        continue
    for name in files:
        rel = os.path.join(root, name)[2:]
        max_len = max(max_len, len(rel))
        if len(rel) > 80 or rel.startswith('/') or '..' in rel.split(os.sep) or (len(rel) > 1 and rel[1] == ':'):
            bad.append(rel)
if bad:
    print('FAIL short path bad entries:', bad[:10])
    sys.exit(1)
for req in ['README.md', 'Makefile', 'SHA256SUMS.txt']:
    if not os.path.isfile(req):
        print('FAIL missing root', req)
        sys.exit(1)
print('PASS short path gate max_internal_path_len=%d' % max_len)
PYTEST
grep -q 'qv211.zip' docs/SP.md
grep -q 'NO_LONG_ARCHIVE_BASENAME' docs/SP.md
grep -q 'NO_SHORT_PATH_FINAL_PASS_WITHOUT_EVIDENCE' docs/SP.md
grep -q 'SHORT_PATH_PACKAGE_COMPATIBILITY' qikvrt/gates/SP.json
echo 'PASS short path acceptance gate'
