import unittest
from runtime.emp.repository_plan import plan, STEPS


class RepositoryPlanTests(unittest.TestCase):
    def test_initial_step_is_observation(self):
        result = plan([], authorized=True, writer_admitted=True)
        self.assertEqual(result["ready"], ["observe"])
        self.assertFalse(result["effect_ack_done"])

    def test_no_effect_without_writer_admission(self):
        result = plan(["observe", "diagnose"], authorized=True,
                      writer_admitted=False)
        self.assertNotIn("temdd_repair", result["ready"])
        self.assertEqual(result["held"][0]["reason"], "effect_admission_required")

    def test_next_step_after_ci(self):
        result = plan(["observe", "diagnose", "temdd_repair", "exact_head_ci"],
                      authorized=True, writer_admitted=True)
        self.assertEqual(result["ready"], ["governance"])

    def test_external_block_is_fail_closed(self):
        result = plan([], authorized=True, writer_admitted=True,
                      external_blocks=["ADMITTED_MESH_RUNTIME_ENDPOINT"])
        self.assertEqual(result["ready"], [])
        self.assertEqual(result["held"][0]["reason"], "external_blocker")

    def test_unknown_completion_rejected(self):
        with self.assertRaises(ValueError):
            plan(["invented_success"], authorized=True, writer_admitted=True)

    def test_full_plan_does_not_claim_global_ack(self):
        result = plan([s.key for s in STEPS], authorized=True,
                      writer_admitted=True)
        self.assertTrue(result["verified"])
        self.assertFalse(result["effect_ack_done"])


if __name__ == "__main__":
    unittest.main()
