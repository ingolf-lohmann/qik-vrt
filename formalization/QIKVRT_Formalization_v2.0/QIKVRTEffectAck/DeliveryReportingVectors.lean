/- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann. -/
import QIKVRTEffectAck.DeliveryReporting
import Lean

open QIKVRT.DeliveryReporting Lean

def observationJson (o : Observation) : Json := Json.mkObj [
  ("target", toJson (match o.target with | .local => "local" | .authority h => h)),
  ("status", toJson o.status), ("subjectRef", toJson o.subjectRef),
  ("observationId", toJson o.observationId), ("utc", toJson o.utc)]

def vectorJson (r : Report) : Json := Json.mkObj [
  ("claim", toJson (if r.claim = .pending then "pending" else "delivered")),
  ("authorityHost", toJson r.authorityHost), ("subjectRef", toJson r.subjectRef),
  ("observations", toJson (r.observations.map observationJson)),
  ("completedUtc", toJson r.completedUtc), ("closedUtc", toJson r.closedUtc),
  ("provenanceBound", toJson r.provenanceBound),
  ("verdict", toJson (if QIKVRT.DeliveryReporting.decide r = .accept then "accept" else "reject"))]

def workCodes (text : String) : List Nat := text.toList.map Char.toNat

def workText (codes : List Nat) : String := String.mk (codes.map Char.ofNat)

def workVectorJson (r : WorkReport) : Json := Json.mkObj [
  ("workCompletion", Json.mkObj [
    ("requiredTarget", toJson (workText r.requiredTarget)), ("observedTarget", toJson (workText r.observedTarget)),
    ("requiredEffect", toJson (workText r.requiredEffect)), ("observedEffect", toJson (workText r.observedEffect)),
    ("origin", toJson (workText r.origin)), ("checker", toJson (workText r.checker)),
    ("requiredSha256", toJson (workText r.requiredSha256)),
    ("observedSha256", toJson (workText r.observedSha256)),
    ("fromCache", toJson r.fromCache), ("completedUtc", toJson r.completedUtc),
    ("observedUtc", toJson r.observedUtc), ("closedUtc", toJson r.closedUtc)]),
  ("verdict", toJson (if workDecide r = .accept then "accept" else "reject"))]

def main : IO Unit := do
  let mut vectors : Array Json := #[]
  for claim in [Claim.pending, .delivered] do
    for target in [Target.local, .authority "raumzeitterminal.de", .authority "foreign.example"] do
      for status in [200, 201, 403, 525] do
        for subject in ["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"] do
          for utc in [1, 2, 3, 4] do
            for provenance in [true, false] do
              let o : Observation := ⟨target, status, subject, "observation-1", utc⟩
              for observations in [[], [o], [o, o]] do
                let r : Report := ⟨claim, "raumzeitterminal.de",
                  "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", observations, 1, 3, provenance⟩
                vectors := vectors.push (vectorJson r)
  for effect in ["ARTIFACT_INSTALLATION", "DATA_READBACK"] do
    for target in ["https://artifact.example/leitstand", "https://artifact.example/private-copy"] do
      for observedEffect in [effect, "JOURNAL_WRITE"] do
        for origin in ["DIRECT_TOOL_READBACK", "RELAYED_REPORT"] do
          for checker in ["VERIFIED", "UNAVAILABLE"] do
            for utc in [1, 2] do
              for digest in ["5555555555555555555555555555555555555555555555555555555555555555", "507abcf7..."] do
                for cached in [false, true] do
                  let r : WorkReport := ⟨workCodes "https://artifact.example/leitstand", workCodes target,
                    workCodes effect, workCodes observedEffect, workCodes origin, workCodes checker,
                    workCodes "5555555555555555555555555555555555555555555555555555555555555555",
                    workCodes digest, cached, 1, utc, 3⟩
                  vectors := vectors.push (workVectorJson r)
  -- ASCII boundaries, lengths, Unicode and a 64-byte non-ASCII value.
  for digest in ["0000000000000000000000000000000000000000000000000000000000000000",
      "9999999999999999999999999999999999999999999999999999999999999999",
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
      "////////////////////////////////////////////////////////////////",
      "::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::",
      "````````````````````````````````````````````````````````````````",
      "gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg",
      "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
      "５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５５",
      "😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀",
      "555555555555555555555555555555555555555555555555555555555555555",
      "55555555555555555555555555555555555555555555555555555555555555555",
      "",
      "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "555555555555555555555555555555555555555555555555555555555555555\n"] do
    let r : WorkReport := ⟨workCodes "https://artifact.example/leitstand",
      workCodes "https://artifact.example/leitstand", workCodes "ARTIFACT_INSTALLATION",
      workCodes "ARTIFACT_INSTALLATION", workCodes "DIRECT_TOOL_READBACK", workCodes "VERIFIED",
      workCodes digest, workCodes digest, false, 1, 2, 3⟩
    vectors := vectors.push (workVectorJson r)
  IO.println (Json.compress (Json.arr vectors))
