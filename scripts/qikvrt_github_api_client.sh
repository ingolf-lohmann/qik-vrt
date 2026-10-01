#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
# A GitHub workflow dispatch is a mutation even with dry_run=true in its payload.
echo 'NO_BYPASS: direct GitHub dispatch disabled; use current Authority broker' >&2
exit 78
