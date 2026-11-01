import QIKVRT.ZeroOneObservation
open QIKVRT.ZeroOneObservation

-- Expected rejection: neutral-element laws permit the one-element arithmetic.
example : trivialArithmetic.zero ≠ trivialArithmetic.one := by decide
