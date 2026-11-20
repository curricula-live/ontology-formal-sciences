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
