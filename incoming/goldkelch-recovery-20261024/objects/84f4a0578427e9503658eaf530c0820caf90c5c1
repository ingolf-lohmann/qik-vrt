#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Current-Mirror-main overlay for the owner-authorized PR249 constructor.

The original request was frozen before the temporary constructor infrastructure
was promoted to Mirror main.  That promotion advanced Mirror main from
``afcd0255...`` to ``c2a6e75...`` without changing the Authority target.  This
entrypoint preserves the exact Authority bindings and exact-byte manifest
verification while rebinding only the history-preserving sole parent and target
branch to the now-current Mirror main.  It constructs a candidate only; it does
not promote Mirror main or authorize any later effect.
"""
from __future__ import annotations

import pathlib

from tools import qikvrt_construct_history_preserving_mirror_candidate_pr249_exact_bytes as exact

base = exact.base
ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUEST = ROOT / "work-units/HISTORY_PRESERVING_MIRROR_SYNC_REQUEST_PR249_CURRENT_MAIN_C2A6.json"
PRE_INFRASTRUCTURE_PARENT = "afcd0255aab6bc5ad18275a2d91516688a41e302"
CURRENT_MIRROR_PARENT = "c2a6e75eb24721029865a9dd5fd94fa55590a955"
TARGET_BRANCH = "sync/six-corrected-candidates-authority-7d87a600-from-c2a6e75-v1"
CANDIDATE_TIMESTAMP = "2026-07-30T08:10:00Z"

base.REQUEST_PATH = REQUEST
base.MIRROR_PARENT = CURRENT_MIRROR_PARENT
base.TARGET_BRANCH = TARGET_BRANCH
base.CANDIDATE_TIMESTAMP = CANDIDATE_TIMESTAMP

_original_load = base.load_and_validate_request


def load_current_request(path: pathlib.Path = REQUEST):
    value = _original_load(path)
    mirror = value.get("mirror", {})
    if mirror.get("pre_infrastructure_main") != PRE_INFRASTRUCTURE_PARENT:
        raise base.ConstructionError("pre-infrastructure Mirror provenance drift")
    if mirror.get("infrastructure_promotion_pr") != 134:
        raise base.ConstructionError("constructor infrastructure promotion binding drift")
    return value


base.load_and_validate_request = load_current_request


if __name__ == "__main__":
    raise SystemExit(base.main())
