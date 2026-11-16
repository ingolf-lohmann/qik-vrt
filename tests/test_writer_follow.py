"""Fail-closed successor-following contract tests."""
import unittest

from tools.qikvrt_writer_follow import verify_chain

A = "a" * 40
B = "b" * 40
C = "c" * 40
D = "d" * 40


class WriterFollowTests(unittest.TestCase):
    def test_valid_successor_and_fixpoint(self):
        log = (
            f"QIKVRT_REENTRY_SUBJECT iteration=0 head={A} tree={C}\n"
            f"QIKVRT_SUCCESSOR_REENTRY iteration=0 predecessor={A} successor={B} "
            f"successor_tree={D} readback_head={B} readback_tree={D}\n"
            f"QIKVRT_FIXPOINT_REACHED iteration=1 head={B} tree={D}\n"
        )
        chain = verify_chain(log, A)
        self.assertTrue(chain.fixpoint_reached)
        self.assertEqual(chain.latest_head, B)
        self.assertEqual(chain.successor_count, 1)

    def test_in_progress_does_not_imply_completion(self):
        chain = verify_chain(f"QIKVRT_REENTRY_SUBJECT iteration=0 head={A} tree={C}", A)
        self.assertFalse(chain.fixpoint_reached)

    def test_wrong_readback_fails_closed(self):
        log = (
            f"QIKVRT_SUCCESSOR_REENTRY iteration=0 predecessor={A} successor={B} "
            f"successor_tree={D} readback_head={A} readback_tree={D}\n"
            f"QIKVRT_FIXPOINT_REACHED iteration=1 head={B} tree={D}\n"
        )
        self.assertFalse(verify_chain(log, A).fixpoint_reached)

    def test_disconnected_predecessor_fails_closed(self):
        log = (
            f"QIKVRT_SUCCESSOR_REENTRY iteration=0 predecessor={B} successor={C} "
            f"successor_tree={D} readback_head={C} readback_tree={D}\n"
            f"QIKVRT_FIXPOINT_REACHED iteration=1 head={C} tree={D}\n"
        )
        self.assertFalse(verify_chain(log, A).fixpoint_reached)

    def test_no_success_without_fixpoint(self):
        log = (
            f"QIKVRT_SUCCESSOR_REENTRY iteration=0 predecessor={A} successor={B} "
            f"successor_tree={D} readback_head={B} readback_tree={D}"
        )
        self.assertFalse(verify_chain(log, A).fixpoint_reached)


if __name__ == "__main__":
    unittest.main()
