#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# Reuse the exact native artifact; run mandatory conformance again on every hit.
"${PYTHON:-python3}" "$ROOT/tools/qikvrt_tool_cache.py" native-prepare
