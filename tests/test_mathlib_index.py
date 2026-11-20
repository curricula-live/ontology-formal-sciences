import pytest

from pipeline.parse.mathlib import direct_imports


def test_import_header_only():
    header = """\ufeff/- copyright
/- nested import Mathlib.False -/
-/
module
prelude
public import Mathlib.Algebra.Group.Defs
public meta import Mathlib.Tactic.Basic /- explanation -/
import all Mathlib.NumberTheory.Height.Basic -- explanation
def example := "import Mathlib.Algebra.False"
import Mathlib.Ignored
"""
    assert list(direct_imports(header.removeprefix("\ufeff").splitlines(keepends=True))) == [
        "Mathlib.Algebra.Group.Defs", "Mathlib.Tactic.Basic", "Mathlib.NumberTheory.Height.Basic",
    ]


def test_unrecognized_import_is_explicit():
    with pytest.raises(ValueError, match="Unsupported Mathlib"):
        list(direct_imports(["import Mathlib.One Mathlib.Two"]))


def test_lean_header_index_keeps_textual_boundaries():
    from pipeline.parse.lean_index import headers

    source = """-- theorem omitted : False := sorry
/- ignore a nested /- theorem ignored : True := by trivial -/
theorem commented : True := trivial -/
@[simp] theorem target (x : Nat := 1) :
    x = x := by rfl
def inferType (n : Nat) := n
axiom «spaced name» : True
"""
    first, second, third = headers("Mathlib/Test.lean", source)
    assert (first["token"], first["kind"], first["line"], first["boundary"]) == (
        "target", "theorem", 4, ":="
    )
    assert first["has_explicit_result_type"]
    assert second["token"] == "inferType" and not second["has_explicit_result_type"]
    assert third["token"] == "«spaced name»" and third["boundary"] == "layout"
