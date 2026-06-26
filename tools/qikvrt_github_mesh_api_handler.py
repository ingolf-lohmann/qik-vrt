#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Origin: QIK-VRT V38 remote format repair and dispatch attestation kit
# Rights-Holder: Ingolf Lohmann
# Project: QIK-VRT
# Source-Code-License: Apache-2.0
# Non-Source-Code-License: CC BY-NC 4.0 for non-code repository materials
# Notice: See RIGHTS.md / QIKVRT_LICENSE_AND_RIGHTS.md, LICENSE, NOTICE, and .q/lic/.
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from qikvrt_api_handler import main
raise SystemExit(main())
