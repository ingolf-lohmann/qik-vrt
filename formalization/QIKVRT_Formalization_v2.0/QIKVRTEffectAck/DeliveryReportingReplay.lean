/- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann. -/
import Lean.Replay

open Lean

def main : IO Unit := do
  initSearchPath (← findSysroot)
  let original ← importModules #[{ module := `QIKVRTEffectAck.DeliveryReporting }] {}
  let baseline ← importModules #[{ module := `Std }] {}
  let mut declarations : Std.HashMap Name ConstantInfo := {}
  for (name, info) in original.constants do
    unless baseline.contains name do
      declarations := declarations.insert name info
  let checked ← baseline.replay declarations
  for name in [`QIKVRT.DeliveryReporting.T1, `QIKVRT.DeliveryReporting.T2,
      `QIKVRT.DeliveryReporting.T3, `QIKVRT.DeliveryReporting.T4] do
    unless checked.contains name do
      throw (IO.userError s!"missing replayed theorem {name}")
  IO.println s!"DELIVERY_OLEAN_REPLAY_PASS declarations={declarations.size} theorems=4"
