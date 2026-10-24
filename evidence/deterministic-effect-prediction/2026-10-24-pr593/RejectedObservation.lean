import QIKVRTEffectAck.PredictionProfile
set_option maxRecDepth 100000
set_option maxHeartbeats 0
namespace QIKVRTPredictionNegative
open QIKVRT.EffectAck.V1.PredictionProfile
def observed0 : List Nat := [1,4,0,4,0,4,1,4,0,4,0,4,0,4,1,4,0,4,0,4,0,4,1,4,0,4,0,4,0,4,3,4,0,4,0,4,0,4,4,4]
theorem agreesBatch0 : observed0 = expectedBatchCodes ⟨0, by decide⟩ := by rfl
#print axioms agreesBatch0
end QIKVRTPredictionNegative
