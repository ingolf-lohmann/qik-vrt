/- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann. -/
import Lean.Replay

open Lean

unsafe def main : IO Unit := do
  initSearchPath (← findSysroot)
  let path ← findOLean `QIKVRTEffectAck.DeliveryReporting
  let (payload, region) ← readModuleData path
  -- An environment diff also includes declarations already loaded by the
  -- replay program. Replay only the selected original module payload.
  let baseline ← importModules payload.imports {}
  let mut declarations : Std.HashMap Name ConstantInfo := {}
  for name in payload.constNames, info in payload.constants do
    if baseline.contains name then
      throw (IO.userError s!"module payload overlaps its imports: {name}")
    declarations := declarations.insert name info
  let checked ← baseline.replay declarations
  for name in [`QIKVRT.DeliveryReporting.T1, `QIKVRT.DeliveryReporting.T2,
      `QIKVRT.DeliveryReporting.T3, `QIKVRT.DeliveryReporting.T4] do
    unless checked.contains name do
      throw (IO.userError s!"missing replayed theorem {name}")
  IO.println s!"DELIVERY_OLEAN_REPLAY_PASS declarations={declarations.size} theorems=4"
  region.free
