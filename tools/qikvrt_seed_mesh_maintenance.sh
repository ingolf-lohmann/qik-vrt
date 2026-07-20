#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
set -eu
exec python3 -B tools/qikvrt_seed_common.py maintenance --root .
