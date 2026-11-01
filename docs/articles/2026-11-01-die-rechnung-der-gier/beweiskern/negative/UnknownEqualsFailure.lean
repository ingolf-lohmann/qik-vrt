import QIKVRT.ZeroOneObservation

-- Expected rejection: absence of observation is not an observed negative result.
example : (none : Option Bool) = some false := by rfl
