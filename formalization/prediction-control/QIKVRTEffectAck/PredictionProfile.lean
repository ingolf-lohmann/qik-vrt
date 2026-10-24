/- SPDX-License-Identifier: CC-BY-NC-ND-4.0
   Copyright 2026 Ingolf Lohmann. -/
import QIKVRTEffectAck.Model

/-!
Finite observation profile for the C90 / native / emulated prediction control.
The existing abstract model is reused unchanged. Observation equality is a
bounded conformance statement, not a verified compiler or emulator theorem.
-/
namespace QIKVRT.EffectAck.V1.PredictionProfile

set_option maxRecDepth 100000
set_option maxHeartbeats 0

def maskBit (mask bit : Nat) : Bool := decide ((mask / 2 ^ bit) % 2 = 1)

def snapshot (mask : Nat) (decision : ConnectionDecision)
    (transport reception deadline : Bool) : Snapshot where
  transportAck := transport
  inputIdAvailable := transport && reception
  inputHashIsSha256Identifier := reception
  predecessorInvalid := false
  deadlineExceeded := deadline
  integrityFailure := false
  originChecked := maskBit mask 0
  contextChecked := maskBit mask 1
  semanticsReconstructed := maskBit mask 2
  effectAnticipated := maskBit mask 3
  riskClassified := maskBit mask 4
  responsibilityAssigned := maskBit mask 5
  policyAllowsRelease := maskBit mask 6
  riskKnown := maskBit mask 7
  responsibilityOwnerPresent := true
  connectionDecided := decide (decision ≠ .undecided)
  noOpenQuestions := true
  noNextRequiredChecks := true
  requiredEvidenceComplete := true
  connectionDecision := decision

def complete : Snapshot := snapshot 255 .release true true false

def faultSnapshots : List Snapshot :=
  [{ complete with responsibilityOwnerPresent := false },
   { complete with noOpenQuestions := false },
   { complete with noNextRequiredChecks := false },
   { complete with requiredEvidenceComplete := false },
   { complete with integrityFailure := true },
   { complete with integrityFailure := true },
   { complete with inputIdAvailable := false },
   { complete with integrityFailure := true }]

/-- 256 complete 40-case mask batches, followed by the eight fault cases. -/
def batchSnapshots (batch : Fin 257) : List Snapshot :=
  if batch.val < 256 then
    connectionDecisions.flatMap fun decision =>
      [false, true].flatMap fun transport =>
        [false, true].flatMap fun reception =>
          [false, true].map fun deadline =>
            snapshot batch.val decision transport reception deadline
  else faultSnapshots

def stateCode : State → Nat
  | .nack => 0
  | .continue => 1
  | .done => 2
  | .isolate => 3
  | .block => 4

def expectedBatchCodes (batch : Fin 257) : List Nat :=
  (batchSnapshots batch).map fun input => stateCode (selectState input)

theorem batchSize (batch : Fin 257) :
    (batchSnapshots batch).length = if batch.val < 256 then 40 else 8 := by
  by_cases h : batch.val < 256
  · simp [batchSnapshots, h, connectionDecisions]
  · simp [batchSnapshots, h, faultSnapshots]

theorem profileSize : 256 * 40 + 8 = 10248 := by decide

theorem onlyDoneHasCodeTwo (state : State) : stateCode state = 2 ↔ state = .done := by
  cases state <;> decide

#print axioms profileSize
#print axioms batchSize
#print axioms onlyDoneHasCodeTwo

end QIKVRT.EffectAck.V1.PredictionProfile
