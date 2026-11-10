# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import unittest

from tools.qikvrt_recursive_priority_queue import (
    QueueInvariantError, consolidate, select_next,
)


def unit(ident, priority="P1", state="QUEUED", dependencies=None, last_attempt=0):
    return dict(id=ident, dedupe_key="cause:" + ident, priority=priority,
                state=state, dependencies=dependencies or [],
                last_attempt=last_attempt, head="a" * 40)


class PriorityQueueTests(unittest.TestCase):
    def test_priority_then_fairness(self):
        units = [unit("a", "P2"), unit("b", "P1", last_attempt=8),
                 unit("c", "P1", last_attempt=3)]
        self.assertEqual(select_next(units, writer_available=True,
                                     exact_head="a" * 40)["id"], "c")

    def test_writer_fencing(self):
        self.assertIsNone(select_next([unit("a")], writer_available=False,
                                      exact_head="a" * 40))

    def test_exact_head(self):
        self.assertIsNone(select_next([unit("a")], writer_available=True,
                                      exact_head="b" * 40))

    def test_blocked_p0_does_not_starve_independent_p1(self):
        units = [unit("p0", "P0", "HOLD"), unit("p1", "P1")]
        self.assertEqual(select_next(units, writer_available=True,
                                     exact_head="a" * 40)["id"], "p1")

    def test_dependency_must_be_verified(self):
        units = [unit("a", "P0", "HOLD"), unit("b", "P1", dependencies=["a"])]
        self.assertIsNone(select_next(units, writer_available=True,
                                      exact_head="a" * 40))
        units[0]["state"] = "VERIFIED"
        self.assertEqual(select_next(units, writer_available=True,
                                     exact_head="a" * 40)["id"], "b")

    def test_cycles_fail_closed(self):
        with self.assertRaises(QueueInvariantError):
            select_next([unit("a", dependencies=["b"]),
                         unit("b", dependencies=["a"])],
                        writer_available=True, exact_head="a" * 40)

    def test_duplicate_work_unit_fails_closed(self):
        with self.assertRaises(QueueInvariantError):
            select_next([unit("a"), unit("a")], writer_available=True,
                        exact_head="a" * 40)

    def test_identical_event_replay_is_idempotent(self):
        event = {"event_id": "one", "evidence_sha256": "f" * 64}
        self.assertEqual(consolidate([event, event]), [event])

    def test_conflicting_event_replay_fails_closed(self):
        with self.assertRaises(QueueInvariantError):
            consolidate([{"event_id": "one", "value": 1},
                         {"event_id": "one", "value": 2}])


if __name__ == "__main__":
    unittest.main()
