#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Origin: QIK-VRT self-contained GitHub REST/TCP/IP deployment package
# Rights-Holder: Ingolf Lohmann
# Project: QIK-VRT
# Source-Code-License: Apache-2.0
# Non-Source-Code-License: CC BY-NC 4.0 for non-code repository materials
# Notice: See QIKVRT_LICENSE_AND_RIGHTS.md, LICENSE, NOTICE, and .qikvrt/license/.
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from qikvrt_api_handler import main
raise SystemExit(main())
