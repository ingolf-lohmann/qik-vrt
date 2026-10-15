-- EXPECTED FAILURE: MAX-006 establishes greatestness of extended, not limited.
import QIKVRTFormalization.Process.ConnectabilityMaximality
open QIKVRT.V2.ConnectabilityMaximality
example : GreatestIn limited counterexampleFamily := by
  exact MAX006_extended_greatest_in_any_bool_family counterexampleFamily
