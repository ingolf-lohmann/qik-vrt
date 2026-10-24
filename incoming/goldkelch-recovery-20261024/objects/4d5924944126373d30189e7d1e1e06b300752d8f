# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTINUATION = ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml"


class AutonomousPRContinuationNoopDispatchTests(unittest.TestCase):
    def test_clean_current_head_still_reaches_exact_head_dispatch(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        noop_guard = (
            'if test "$merge_created" = false && '
            '! test -s /tmp/qikvrt-pr-self-heal-paths; then'
        )
        start = source.index(noop_guard)
        dispatch = source.index(
            'event_type\': \'qikvrt_autonomous_exact_head_verify\'',
            start,
        )
        between = source[start:dispatch]
        self.assertNotIn("exit 0", between)
        self.assertIn(
            'test -z "$(git status --porcelain=v1 --untracked-files=all)"',
            between,
        )
        self.assertIn('candidate_head="$(git rev-parse --verify HEAD^{commit})"', between)
        self.assertIn('test "$live_head_before_push" = "$EXPECTED_HEAD"', between)
        self.assertIn('repos/${GITHUB_REPOSITORY}/dispatches', source[dispatch:])


if __name__ == "__main__":
    unittest.main()
