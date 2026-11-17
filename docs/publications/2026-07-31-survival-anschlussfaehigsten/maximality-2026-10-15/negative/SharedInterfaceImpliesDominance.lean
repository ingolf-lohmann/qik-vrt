-- EXPECTED FAILURE: MAX-005 supplies the opposite dominance direction.
import QIKVRTFormalization.Process.ConnectabilityMaximality
open QIKVRT.V2.ConnectabilityMaximality
example : Dominates limited extended := by
  exact MAX005_shared_interface_does_not_imply_greatest.2.2.1
