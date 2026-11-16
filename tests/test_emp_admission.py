import unittest
from runtime.emp.admission import AdmissionEvidence, production_admission


class ProductionAdmissionTests(unittest.TestCase):
    def test_default_is_blocked(self):
        admitted, missing = production_admission(AdmissionEvidence())
        self.assertFalse(admitted)
        self.assertEqual(len(missing), 8)

    def test_ci_alone_never_admits(self):
        admitted, missing = production_admission(
            AdmissionEvidence(exact_head_ci_passed=True))
        self.assertFalse(admitted)
        self.assertIn("independent_eap_readback_verified", missing)

    def test_no_eap_means_blocked(self):
        data = {name: True for name in AdmissionEvidence.__dataclass_fields__}
        data["independent_eap_readback_verified"] = False
        admitted, missing = production_admission(AdmissionEvidence(**data))
        self.assertFalse(admitted)
        self.assertEqual(missing, ("independent_eap_readback_verified",))

    def test_all_independently_verified_evidence_allows_admission(self):
        data = {name: True for name in AdmissionEvidence.__dataclass_fields__}
        admitted, missing = production_admission(AdmissionEvidence(**data))
        self.assertTrue(admitted)
        self.assertFalse(missing)


if __name__ == "__main__":
    unittest.main()
