import Lean

open Lean Elab Command

private def names (xs : Array Name) : Json :=
  toJson ((xs.map Name.toString).qsort (· < ·))

elab "#inspect_ontology_theorem " target:ident : command => do
  let name := target.getId
  let env ← getEnv
  let some (.thmInfo declaration) := env.checked.get.find? name
    | throwError "No kernel-checked theorem named {name}"
  let axioms ← collectAxioms name
  if axioms.contains `sorryAx then
    throwError "{name} depends on sorryAx"
  let typeText ← liftTermElabM do
    return (← Meta.ppExpr declaration.type).pretty
  let data := Json.mkObj [
    ("declaration", toJson name.toString),
    ("elaborated_type", toJson typeText),
    ("direct_type_constants", names declaration.type.getUsedConstants),
    ("direct_proof_constants", names declaration.value.getUsedConstants),
    ("transitive_axioms", names axioms)]
  liftIO <| IO.println data.compress
