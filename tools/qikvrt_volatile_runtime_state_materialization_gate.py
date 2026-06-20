#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Compatibility wrapper: V38 materialization gate delegates to V40 delivery ZIP gate."""
from __future__ import annotations
import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import qikvrt_volatile_runtime_state_delivery_zip_gate as v40_gate

def main(argv=None):
    """Run V40 gate."""
    return v40_gate.main(argv or [])

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
