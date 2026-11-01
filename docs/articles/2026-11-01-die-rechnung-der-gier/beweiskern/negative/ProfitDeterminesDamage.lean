import QIKVRT.ZeroOneObservation
open QIKVRT.ZeroOneObservation

-- Expected rejection: equal profit flags need not imply equal damage flags.
example : (⟨true, false⟩ : EconomicOutcome).damageOccurred =
    (⟨true, true⟩ : EconomicOutcome).damageOccurred := by decide
