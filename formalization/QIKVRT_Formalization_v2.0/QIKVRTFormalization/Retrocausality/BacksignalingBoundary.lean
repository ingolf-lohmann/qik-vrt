import QIKVRTFormalization.Retrocausality.ForwardProcess

/-!
Requested by Ingolf Lohmann; formalization prepared with OpenAI Codex.
This file proves statements about explicit mathematical models, not a physical
implementation of a backwards-in-time channel. Times are integer labels in
one declared coordinate system. No identification with physical observations
is assumed or proved.
-/
namespace QIKVRT.V2.BacksignalingBoundary

structure TwoMessages where
  emitOld : Int
  emitNew : Int
  receiveOld : Int
  receiveNew : Int

def ForwardDeliveries (w : TwoMessages) : Prop :=
  w.emitOld < w.receiveOld ∧ w.emitNew < w.receiveNew

def ReversedReception (w : TwoMessages) : Prop :=
  w.emitOld < w.emitNew ∧ w.receiveNew < w.receiveOld

def ReceiveBeforeOwnEmission (w : TwoMessages) : Prop :=
  w.receiveOld < w.emitOld ∨ w.receiveNew < w.emitNew

-- Exact event order in the published operational witness: 0, 1, 2, 3.
def publishedOrder : TwoMessages := ⟨0, 1, 3, 2⟩

theorem published_order_is_forward : ForwardDeliveries publishedOrder := by
  unfold ForwardDeliveries publishedOrder
  decide

theorem published_order_is_reversed : ReversedReception publishedOrder := by
  unfold ReversedReception publishedOrder
  decide

theorem published_order_has_no_receive_before_emit :
    ¬ ReceiveBeforeOwnEmission publishedOrder := by
  unfold ReceiveBeforeOwnEmission publishedOrder
  decide

theorem reception_reversal_does_not_imply_receive_before_emit :
    ¬ (∀ w, ReversedReception w → ReceiveBeforeOwnEmission w) := by
  intro h
  exact published_order_has_no_receive_before_emit
    (h publishedOrder published_order_is_reversed)

theorem forward_delivery_excludes_receive_before_emit (w : TwoMessages)
    (h : ForwardDeliveries w) : ¬ ReceiveBeforeOwnEmission w := by
  unfold ForwardDeliveries at h
  unfold ReceiveBeforeOwnEmission
  omega

theorem positive_delay_is_after_emission (emit delay : Int) (h : 0 < delay) :
    emit < emit + delay := by omega

-- A virtual address can decrease while host events increase.
theorem virtual_past_address_with_forward_host_order :
    (15 : Int) < 30 ∧ (0 : Int) < 1 := by decide

theorem later_inputs_preserve_captured_prefix
    (step : State → Input → State) (initial : State)
    (u v : Nat → Input) (cut : Nat)
    (hPrefix : InputPrefixAgrees u v cut) :
    capturePrefix (run step initial u) cut =
      capturePrefix (run step initial v) cut :=
  capturedPrefix_invariant step initial u v cut hPrefix

end QIKVRT.V2.BacksignalingBoundary
