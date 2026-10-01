/-
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann.
-/
import Replay
import Lean.Util.CollectAxioms

open Lean

/- The producer's imported environment is data. Project declarations are
   replayed into a separately loaded Std environment at trust level zero.
   No project initializer or environment extension is loaded by this process. -/
def main (args : List String) : IO UInt32 := do
  let [input] := args | throw <| IO.userError "expected one kernel plan"
  initSearchPath (← findSysroot)
  let plan ← IO.ofExcept <| Json.parse (← IO.FS.readFile input)
  let claims ← IO.ofExcept <| plan.getObjValAs? (Array Json) "claims"
  let producer ← importModules #[{module := `QIKVRTFormalization}, {module := `QIKVRTEffectAck}]
    {} 0 (loadExts := false)
  let base ← importModules #[{module := `Std}] {} 0 (loadExts := false)
  let mut project : Std.HashMap Name ConstantInfo := {}
  for (name, info) in producer.constants.toList do
    -- Compiler-only unsafe/partial auxiliaries are not logical declarations.
    -- They are excluded, as in the upstream replay routine, and therefore
    -- cannot be selected as proof, statement or registry constants below.
    if (base.find? name).isNone && !info.isUnsafe && !info.isPartial then
      project := project.insert name info
  if project.isEmpty then throw <| IO.userError "empty project environment"
  let checked ← base.replay' project
  let mut results : Array Json := #[]
  for claim in claims do
    let cid ← IO.ofExcept <| claim.getObjValAs? String "claim_id"
    let proofs ← IO.ofExcept <| claim.getObjValAs? (Array String) "proof_constants"
    let constants ← IO.ofExcept <| claim.getObjValAs? (Array String) "constants"
    let origins ← IO.ofExcept <| claim.getObjVal? "constant_modules"
    let mut observations : Array Json := #[]
    for constant in constants do
      let name := (constant.splitOn ".").foldl Name.str Name.anonymous
      let some info := checked.toKernelEnv.find? name
        | throw <| IO.userError s!"missing constant: {name}"
      if !project.contains name then throw <| IO.userError s!"non-project constant: {name}"
      let expectedModule ← IO.ofExcept <| origins.getObjValAs? String constant
      let some index := producer.getModuleIdxFor? name
        | throw <| IO.userError s!"missing constant module: {name}"
      let actualModule := producer.header.moduleNames[index.toNat]!.toString
      if actualModule != expectedModule then
        throw <| IO.userError s!"wrong constant source module: {name}: {actualModule}"
      if proofs.contains constant then
        match info with
        | .thmInfo _ => pure ()
        | _ => throw <| IO.userError s!"proof is not a theorem: {name}"
      let (_, state) := ((CollectAxioms.collect name).run checked).run {}
      let axioms := state.axioms.map toString |>.qsort (· < ·)
      for axiomName in axioms do
        if !["Classical.choice", "Quot.sound", "propext"].contains axiomName then
          throw <| IO.userError s!"forbidden axiom: {name}: {axiomName}"
      observations := observations.push <| Json.mkObj [
        ("constant", toJson constant), ("module", toJson actualModule), ("axioms", toJson axioms),
        ("type", toJson (toString info.type))]
    results := results.push <| Json.mkObj [
      ("claim_id", toJson cid), ("constants", toJson observations)]
  IO.println <| (Json.mkObj [
    ("schema", toJson "qikvrt_independent_lean_kernel_v1"),
    ("trust_level", toJson (0 : Nat)),
    ("project_declarations_rechecked", toJson project.size),
    ("claims", toJson results)]).compress
  return 0
