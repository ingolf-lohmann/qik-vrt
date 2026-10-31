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
  ("verdict", toJson (if decide r = .accept then "accept" else "reject"))]

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
  IO.println (Json.compress (Json.arr vectors))
