import QIKVRTEffectAck.PredictionProfile
set_option maxRecDepth 100000
set_option maxHeartbeats 0
namespace QIKVRTPredictionObservation256
open QIKVRT.EffectAck.V1.PredictionProfile
def observed256 : List Nat := [1,1,1,1,4,4,0,4]
theorem agreesBatch256 : observed256 = expectedBatchCodes ⟨256, by decide⟩ := by rfl
#print axioms agreesBatch256
end QIKVRTPredictionObservation256
