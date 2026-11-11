# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import unittest
from tools.qikvrt_universal_transputer import (
    TransputerInvariantError, append, project,
)


class UniversalTransputerTests(unittest.TestCase):
    def event(self, ident, state="RUNNING", evidence=None):
        return {"id": ident, "source": "github", "subject": "PR#727",
                "state": state, "observed_at": "2026-11-10T15:00:00Z",
                "head": "f" * 40, "evidence": evidence or {}}

    def test_four_views_preserve_identical_evidence(self):
        chain = append([], self.event("start"))
        chain = append(chain, self.event("step", "FAILED"))
        for view in ("chat", "terminal", "dashboard", "repository"):
            projected = project(chain, view)
            self.assertEqual([x["sha256"] for x in projected],
                             [x["sha256"] for x in chain])
            self.assertEqual([x["state"] for x in projected],
                             ["RUNNING", "FAILED"])

    def test_tamper_and_reorder_fail_closed(self):
        chain = append(append([], self.event("a")), self.event("b"))
        with self.assertRaises(TransputerInvariantError):
            project(chain[::-1], "chat")
        chain[0]["state"] = "VERIFIED"
        with self.assertRaises(TransputerInvariantError):
            project(chain, "terminal")

    def test_no_unverified_ack(self):
        with self.assertRaises(TransputerInvariantError):
            append([], self.event("ack", "EFFECT_ACK_DONE"))
        chain = append([], self.event(
            "ack", "EFFECT_ACK_DONE", {"independent_readback": True}))
        self.assertEqual(project(chain, "chat")[0]["state"], "EFFECT_ACK_DONE")

    def test_no_duplicate_event(self):
        chain = append([], self.event("same"))
        with self.assertRaises(TransputerInvariantError):
            append(chain, self.event("same"))


if __name__ == "__main__":
    unittest.main()
