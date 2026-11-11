import QIKVRTEffectAck.CausalDistance

/-!
# Causal order and Round-Trip reconstruction bridge

This module integrates the existing weighted directed-path kernel with the
VRTCore distinction between observed sequence and causally licensed relation.

It proves order-theoretic and information-preservation statements only.
Acyclicity and local finiteness are explicit model hypotheses. No physical
interpretation, Lorentzian manifold, metric, light cone, or empirical
correspondence is derived here.
-/

namespace QIKVRT.CausalGeometry.V1

open QIKVRT.CausalDistance.V1

universe u v

/-- Strict causal precedence induced by a positive-cost directed path. -/
def Before {V : Type u} (g : Graph V) (a b : V) : Prop :=
  ∃ n, 0 < n ∧ Path g a b n

/-- A directed weighted graph is acyclic when no nontrivial path returns
    to its starting point. -/
def Acyclic {V : Type u} (g : Graph V) : Prop :=
  ∀ {a n}, Path g a a n → n = 0

theorem before_transitive {V : Type u} {g : Graph V} {a b c : V}
    (hab : Before g a b) (hbc : Before g b c) :
    Before g a c := by
  rcases hab with ⟨n, hn, hp⟩
  rcases hbc with ⟨m, hm, hq⟩
  exact ⟨n + m, by omega, path_append hp hq⟩

theorem before_irreflexive {V : Type u} {g : Graph V}
    (hacyclic : Acyclic g) (a : V) :
    ¬ Before g a a := by
  rintro ⟨n, hn, hp⟩
  have hz := hacyclic hp
  omega

theorem before_asymmetric {V : Type u} {g : Graph V}
    (hacyclic : Acyclic g) {a b : V}
    (hab : Before g a b) (hba : Before g b a) :
    False := by
  rcases hab with ⟨n, hn, hp⟩
  rcases hba with ⟨m, hm, hq⟩
  have hz := hacyclic (path_append hp hq)
  omega

/-- A strict partial-order certificate over the event carrier. -/
structure CausalOrder (V : Type u) where
  graph : Graph V
  acyclic : Acyclic graph

theorem causalOrder_strictPartialOrder {V : Type u}
    (order : CausalOrder V) :
    (∀ a, ¬ Before order.graph a a) ∧
    (∀ a b c, Before order.graph a b →
      Before order.graph b c → Before order.graph a c) :=
  ⟨before_irreflexive order.acyclic, fun _ _ _ => before_transitive⟩

/-- Local finiteness is witnessed by a finite list and an exact membership
    specification. A list may contain each event at most once by convention;
    the equivalence below fixes the represented interval as a set. -/
structure LocalFinite {V : Type u} (r : V → V → Prop) where
  interval : V → V → List V
  mem_interval_iff : ∀ a b x,
    x ∈ interval a b ↔ r a x ∧ r x b

/-- Causal order plus an explicit local-finiteness premise. -/
structure LocallyFiniteCausalOrder (V : Type u) extends CausalOrder V where
  locallyFinite : LocalFinite (Before graph)

def causalInterval {V : Type u} (order : LocallyFiniteCausalOrder V)
    (a b : V) : List V :=
  order.locallyFinite.interval a b

theorem causalInterval_membership {V : Type u}
    (order : LocallyFiniteCausalOrder V) (a b x : V) :
    x ∈ causalInterval order a b ↔
      Before order.graph a x ∧ Before order.graph x b :=
  order.locallyFinite.mem_interval_iff a b x

/-- The causal interval has a finite, explicitly enumerable list
    representation. Local finiteness is a supplied model hypothesis, not a
    consequence of acyclicity alone. -/
theorem causalInterval_finite {V : Type u}
    (order : LocallyFiniteCausalOrder V) (a b : V) :
    ∃ xs : List V, xs = causalInterval order a b :=
  ⟨causalInterval order a b, rfl⟩

/-- A typed Round-Trip pair. decode is total; canonical restricts the
    right-inverse law to representations admitted as canonical. -/
structure RoundTrip (α : Type u) (β : Type v) where
  encode : α → β
  decode : β → α
  canonical : β → Prop
  decode_encode : ∀ x, decode (encode x) = x
  encode_decode : ∀ y, canonical y → encode (decode y) = y

theorem roundTrip_leftInverse {α : Type u} {β : Type v}
    (rt : RoundTrip α β) (x : α) :
    rt.decode (rt.encode x) = x :=
  rt.decode_encode x

theorem roundTrip_rightInverse_onCanonical {α : Type u} {β : Type v}
    (rt : RoundTrip α β) {y : β} (hy : rt.canonical y) :
    rt.encode (rt.decode y) = y :=
  rt.encode_decode y hy

theorem roundTrip_encode_injective {α : Type u} {β : Type v}
    (rt : RoundTrip α β) :
    ∀ {x y}, rt.encode x = rt.encode y → x = y := by
  intro x y h
  calc
    x = rt.decode (rt.encode x) := (rt.decode_encode x).symm
    _ = rt.decode (rt.encode y) := congrArg rt.decode h
    _ = y := rt.decode_encode y

/-- A relation is preserved and reflected by the encoded representation.
    This is a separate obligation from byte-level round-trip identity. -/
structure RelationRoundTrip (α : Type u) (β : Type v) where
  roundTrip : RoundTrip α β
  relation : α → α → Prop
  encodedRelation : β → β → Prop
  preserves : ∀ {x y}, relation x y →
    encodedRelation (roundTrip.encode x) (roundTrip.encode y)
  reflects : ∀ {x y}, encodedRelation (roundTrip.encode x)
    (roundTrip.encode y) → relation x y

theorem roundTrip_relation_iff {α : Type u} {β : Type v}
    (rt : RelationRoundTrip α β) (x y : α) :
    rt.relation x y ↔
      rt.encodedRelation (rt.roundTrip.encode x)
        (rt.roundTrip.encode y) :=
  ⟨rt.preserves, rt.reflects⟩

theorem roundTrip_relation_preserved {α : Type u} {β : Type v}
    (rt : RelationRoundTrip α β) {x y : α}
    (h : rt.relation x y) :
    rt.encodedRelation (rt.roundTrip.encode x)
      (rt.roundTrip.encode y) :=
  rt.preserves h

/-- Minimal countermodel: an empty directed graph has distinct incomparable
    events. Thus a graph/event carrier does not imply a total time order. -/
def emptyGraph : Graph Bool where
  edge := fun _ _ _ => False
  positive := by
    intro a b n h
    exact False.elim h

theorem emptyGraph_path_endpoints {a b : Bool} {n : Nat}
    (p : Path emptyGraph a b n) : a = b := by
  cases p with
  | refl => rfl
  | snoc _ h => exact False.elim h

theorem emptyGraph_distinct_events_incomparable :
    ¬ Before emptyGraph false true ∧
    ¬ Before emptyGraph true false := by
  constructor
  · rintro ⟨n, _, p⟩
    have h := emptyGraph_path_endpoints p
    cases h
  · rintro ⟨n, _, p⟩
    have h := emptyGraph_path_endpoints p
    cases h

end QIKVRT.CausalGeometry.V1
