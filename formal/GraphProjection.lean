import Std

/-!
The N3-token projection used by ontology.py::graph_json.
Strings are already encoded RDF terms. Node order, relationship order and
duplicate occurrences are ignored by graph equivalence, as RDF graph
membership is set-like. N3 parsing and RDF semantic equivalence are outside
this model.
-/

namespace Onto

structure Statement where
  subject : String
  predicate : String
  object : String
  deriving DecidableEq, Repr

structure Relationship where
  start : String
  predicate : String
  finish : String
  deriving DecidableEq, Repr

structure PropertyGraph where
  nodes : List String
  relationships : List Relationship

def encodeRelationship (row : Statement) : Relationship :=
  ⟨row.subject, row.predicate, row.object⟩

def project (rows : List Statement) : PropertyGraph :=
  { nodes := (rows.flatMap (fun row => [row.subject, row.object])).eraseDups
    relationships := rows.map encodeRelationship }

def sameStatements (left right : List Statement) : Prop :=
  ∀ row, row ∈ left ↔ row ∈ right

def sameGraph (left right : PropertyGraph) : Prop :=
  (∀ node, node ∈ left.nodes ↔ node ∈ right.nodes) ∧
  (∀ rel, rel ∈ left.relationships ↔ rel ∈ right.relationships)

/-- Source, predicate and target cannot collapse into another relationship. -/
theorem relationship_injective (left right : Statement) :
    encodeRelationship left = encodeRelationship right ↔ left = right := by
  cases left
  cases right
  simp [encodeRelationship, Relationship.mk.injEq, Statement.mk.injEq]

/-- Every source statement and only a source statement appears in the graph. -/
theorem relationship_membership (rows : List Statement) (row : Statement) :
    encodeRelationship row ∈ (project rows).relationships ↔ row ∈ rows := by
  simp [project, List.mem_map, relationship_injective]

/-- Nodes are exactly the endpoints, including literals and self-loop nodes. -/
theorem node_membership (rows : List Statement) (node : String) :
    node ∈ (project rows).nodes ↔
      ∃ row ∈ rows, node = row.subject ∨ node = row.object := by
  simp [project]

/-- Every emitted relationship refers to two existing graph nodes. -/
theorem endpoints_present (rows : List Statement) (rel : Relationship)
    (member : rel ∈ (project rows).relationships) :
    rel.start ∈ (project rows).nodes ∧ rel.finish ∈ (project rows).nodes := by
  obtain ⟨row, present, rfl⟩ := List.mem_map.mp member
  constructor
  · exact (node_membership rows row.subject).mpr ⟨row, present, Or.inl rfl⟩
  · exact (node_membership rows row.object).mpr ⟨row, present, Or.inr rfl⟩

/-- Comparing projected graphs is equivalent to comparing directed RDF rows. -/
theorem graph_equivalence_iff (left right : List Statement) :
    sameGraph (project left) (project right) ↔ sameStatements left right := by
  constructor
  · intro same row
    simpa only [relationship_membership] using same.2 (encodeRelationship row)
  · intro same
    constructor
    · intro node
      simp only [node_membership]
      constructor
      · rintro ⟨row, member, endpoint⟩
        exact ⟨row, (same row).mp member, endpoint⟩
      · rintro ⟨row, member, endpoint⟩
        exact ⟨row, (same row).mpr member, endpoint⟩
    · intro rel
      simp only [project, List.mem_map]
      constructor
      · rintro ⟨row, member, encoded⟩
        exact ⟨row, (same row).mp member, encoded⟩
      · rintro ⟨row, member, encoded⟩
        exact ⟨row, (same row).mpr member, encoded⟩

/-- The same endpoints with different predicates remain different edges. -/
theorem parallel_predicates_preserved (source target first second : String)
    (different : first ≠ second) :
    encodeRelationship ⟨source, first, target⟩ ≠
      encodeRelationship ⟨source, second, target⟩ := by
  intro equal
  have same := (relationship_injective _ _).mp equal
  exact different (congrArg Statement.predicate same)

end Onto
