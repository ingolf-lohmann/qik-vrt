-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Ingolf Lohmann. Formalization: OpenAI Codex.
import QIKVRTEffectAck.SeedArchitecture

/-!
Finite recovery and a growing common evidence view.
This module proves executable manifest collection and algebraic consequences
of exact source/target equality. It does not assert a live Goldkelch transfer,
credential availability, Zenodo publication, truth of arbitrary stored text,
physical volume or a quantum uncertainty relation. Those are not premises
manufactured by this formalization. Payloads may remain private.
-/
namespace QIKVRT.EvidenceRecovery.V1

abbrev Archive (Key Payload : Type) := Key → Option Payload

def FaithfulOn {Key Payload : Type} (keys : List Key)
    (source target : Archive Key Payload) : Prop :=
  ∀ key, key ∈ keys → target key = source key

def AvailableOn {Key Payload : Type} (keys : List Key)
    (source : Archive Key Payload) : Prop :=
  ∀ key, key ∈ keys → ∃ payload, source key = some payload

/-- Collect exactly the requested order; a missing entry aborts the result. -/
def collect {Key Payload : Type} (archive : Archive Key Payload) :
    List Key → Option (List Payload)
  | [] => some []
  | key :: rest => do
      let payload ← archive key
      let tail ← collect archive rest
      pure (payload :: tail)

theorem collect_eq_of_faithful {Key Payload : Type} (keys : List Key)
    (source target : Archive Key Payload) (h : FaithfulOn keys source target) :
    collect target keys = collect source keys := by
  induction keys with
  | nil => rfl
  | cons key rest ih =>
    have hk := h key (by simp)
    have hr : FaithfulOn rest source target := by
      intro k hm
      exact h k (by simp [hm])
    simp only [collect, hk, ih hr]

theorem collect_exists_of_available {Key Payload : Type} (keys : List Key)
    (source : Archive Key Payload) (h : AvailableOn keys source) :
    ∃ payloads, collect source keys = some payloads := by
  induction keys with
  | nil => exact ⟨[], rfl⟩
  | cons key rest ih =>
    obtain ⟨p, hp⟩ := h key (by simp)
    have hr : AvailableOn rest source := by
      intro k hm
      exact h k (by simp [hm])
    obtain ⟨ps, hps⟩ := ih hr
    exact ⟨p :: ps, by simp [collect, hp, hps]⟩

theorem recovered_publication_inputs {Key Payload : Type} (keys : List Key)
    (source target : Archive Key Payload) (ha : AvailableOn keys source)
    (hf : FaithfulOn keys source target) :
    ∃ payloads, collect source keys = some payloads ∧
      collect target keys = some payloads := by
  obtain ⟨ps, hs⟩ := collect_exists_of_available keys source ha
  exact ⟨ps, hs, (collect_eq_of_faithful keys source target hf).trans hs⟩

/-- Equality of deterministic preparation outputs, not external publication. -/
theorem deterministic_preparation_equal {Key Payload Output : Type}
    (keys : List Key) (source target : Archive Key Payload)
    (prepare : List Payload → Output) (hf : FaithfulOn keys source target) :
    (collect target keys).map prepare = (collect source keys).map prepare := by
  rw [collect_eq_of_faithful keys source target hf]

theorem missing_required_entry_aborts {Key Payload : Type}
    (archive : Archive Key Payload) (keys : List Key) (key : Key)
    (hm : key ∈ keys) (hn : archive key = none) : collect archive keys = none := by
  induction keys with
  | nil => simp at hm
  | cons first rest ih =>
    simp only [List.mem_cons] at hm
    rcases hm with he | ht
    · subst first
      simp [collect, hn]
    · have hr := ih ht
      cases hfirst : archive first <;> simp [collect, hfirst, hr]

theorem faithful_transitive {Key Payload : Type} (keys : List Key)
    (a b c : Archive Key Payload) (hab : FaithfulOn keys a b)
    (hbc : FaithfulOn keys b c) : FaithfulOn keys a c := by
  intro k hm
  exact (hbc k hm).trans (hab k hm)

theorem faithful_restrict {Key Payload : Type} (small large : List Key)
    (a b : Archive Key Payload) (hs : ∀ k, k ∈ small → k ∈ large)
    (h : FaithfulOn large a b) : FaithfulOn small a b := by
  intro k hm
  exact h k (hs k hm)

/-- The original CanonicalCodec law suffices for each supplied payload. -/
theorem codec_recovery_exact {Payload Wire : Type}
    (codec : QIKVRT.StorageIntegrity.V1.CanonicalCodec Payload Wire)
    (payload : Payload) : codec.decode (codec.encode payload) = some payload := by
  exact codec.roundTrip payload

abbrev View (Claim : Type) := Claim → Prop
def Extends {Claim : Type} (before after : View Claim) : Prop :=
  ∀ claim, before claim → after claim
def Shared {Claim : Type} (left right : View Claim) : View Claim :=
  fun claim => left claim ∧ right claim
def Join {Claim : Type} (left right : View Claim) : View Claim :=
  fun claim => left claim ∨ right claim
def Sound {Claim : Type} (justified view : View Claim) : Prop :=
  ∀ claim, view claim → justified claim

theorem join_retains_left {Claim : Type} (a b : View Claim) : Extends a (Join a b) := by
  intro c hc
  exact Or.inl hc

theorem join_retains_right {Claim : Type} (a b : View Claim) : Extends b (Join a b) := by
  intro c hc
  exact Or.inr hc

theorem shared_grows_with_both {Claim : Type} (a a' b b' : View Claim)
    (ha : Extends a a') (hb : Extends b b') :
    Extends (Shared a b) (Shared a' b') := by
  intro c hc
  exact ⟨ha c hc.1, hb c hc.2⟩

theorem justified_join {Claim : Type} (valid a b : View Claim)
    (ha : Sound valid a) (hb : Sound valid b) : Sound valid (Join a b) := by
  intro c hc
  exact hc.elim (ha c) (hb c)

theorem join_replay_idempotent {Claim : Type} (a : View Claim) (c : Claim) :
    Join a a c ↔ a c := by
  constructor
  · intro h
    exact h.elim id id
  · intro h
    exact Or.inl h

theorem shared_new_member {Claim : Type} (a a' b b' : View Claim) (c : Claim)
    (ha : a' c) (hb : b' c) (hn : ¬ Shared a b c) :
    Shared a' b' c ∧ ¬ Shared a b c := by
  exact ⟨⟨ha, hb⟩, hn⟩

/-- Agreement alone cannot turn an unsupported proposition into evidence. -/
theorem shared_membership_needs_justification {Claim : Type}
    (valid a b : View Claim) (hs : Sound valid a) (c : Claim)
    (hc : Shared a b c) : valid c := by
  exact hs c hc.1

theorem concrete_collection_witness :
    collect (fun n : Nat => some (n + 10)) [2, 5, 2] =
      some [12, 15, 12] := by decide

end QIKVRT.EvidenceRecovery.V1
