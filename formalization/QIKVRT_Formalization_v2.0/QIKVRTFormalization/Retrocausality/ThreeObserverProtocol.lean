import QIKVRTFormalization.Retrocausality.BacksignalingBoundary

/-!
A and B are transceivers. C is a retrospective, passive audit projection of
the whole trace, not an assumed physical observer outside spacetime.
Integer event labels have no experimentally established physical calibration.
Both forward and explicitly past-directed toy traces are representable.
-/
namespace QIKVRT.V2.ThreeObserverProtocol

structure Trace where
  querySentA : Int
  queryReceivedB : Int
  choiceB : Int
  replySentB : Int
  replyReceivedA : Int
  chosenBitB : Bool
  receivedBitA : Bool

def LocalBOrder (t : Trace) : Prop :=
  t.queryReceivedB < t.choiceB ∧ t.choiceB < t.replySentB

def ForwardTransport (t : Trace) : Prop :=
  t.querySentA < t.queryReceivedB ∧ t.replySentB < t.replyReceivedA

def EarlyCorrectReply (t : Trace) : Prop :=
  t.replyReceivedA < t.querySentA ∧ t.receivedBitA = t.chosenBitB

-- C observes both endpoints' records; no trace is rewritten by observation.
def viewC (t : Trace) : Trace := t
def viewA (t : Trace) : Int × Int × Bool :=
  (t.querySentA, t.replyReceivedA, t.receivedBitA)

theorem C_preserves_A_record (t : Trace) : viewA (viewC t) = viewA t := rfl

theorem forward_round_trip_returns_after_query (t : Trace)
    (localB : LocalBOrder t) (transport : ForwardTransport t) :
    t.querySentA < t.replyReceivedA := by
  unfold LocalBOrder at localB
  unfold ForwardTransport at transport
  omega

theorem forward_model_excludes_early_reply (t : Trace)
    (localB : LocalBOrder t) (transport : ForwardTransport t) :
    ¬ EarlyCorrectReply t := by
  intro early
  have later := forward_round_trip_returns_after_query t localB transport
  unfold EarlyCorrectReply at early
  omega

-- This is an explicit hypothesis witness. The return edge runs from label 4
-- to label 0. Its physical implementability is NOT a premise or a conclusion.
def assumedPastDirectedTrace : Trace := ⟨1, 2, 3, 4, 0, true, true⟩

theorem abstract_past_directed_trace_is_representable :
    ∃ t, LocalBOrder t ∧ EarlyCorrectReply t := by
  refine ⟨assumedPastDirectedTrace, ?_⟩
  unfold LocalBOrder EarlyCorrectReply assumedPastDirectedTrace
  decide

theorem assumed_trace_violates_forward_transport :
    ¬ ForwardTransport assumedPastDirectedTrace := by
  unfold ForwardTransport assumedPastDirectedTrace
  decide

theorem C_observation_preserves_early_reply_predicate (t : Trace) :
    EarlyCorrectReply (viewC t) ↔ EarlyCorrectReply t := Iff.rfl

-- Arbitrarily many relays, with the future-directed premise kept explicit.
inductive ForwardPath : Int → Int → Prop where
  | single {a b : Int} : a < b → ForwardPath a b
  | extend {a b c : Int} : ForwardPath a b → b < c → ForwardPath a c

theorem any_finite_forward_path_returns_later {a b : Int}
    (path : ForwardPath a b) : a < b := by
  induction path with
  | single later => exact later
  | extend _ edge ih => omega

theorem adding_forward_relays_cannot_close_a_cycle {a : Int} :
    ¬ ForwardPath a a := by
  intro path
  have later := any_finite_forward_path_returns_later path
  omega

end QIKVRT.V2.ThreeObserverProtocol
