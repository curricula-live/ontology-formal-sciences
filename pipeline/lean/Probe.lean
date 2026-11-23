import Inspect

namespace FormalSciences

theorem booleanDeMorgan (x y : Bool) : (!(x && y)) = (!x || !y) :=
  Bool.not_and x y

theorem wordAppendAssoc {α : Type} (x y z : List α) :
    (x ++ y) ++ z = x ++ (y ++ z) :=
  List.append_assoc x y z

end FormalSciences

#inspect_ontology_theorem FormalSciences.booleanDeMorgan
#inspect_ontology_theorem FormalSciences.wordAppendAssoc
