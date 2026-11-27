"""Keep stored RDF literal spellings through the real exchange decoder."""

import unittest
from unittest.mock import patch

import ontology

try:
    import rdflib
    from rdflib import Graph, Literal, URIRef, XSD
except ModuleNotFoundError:
    Graph = None


@unittest.skipUnless(Graph is not None, "optional exchange dependency rdflib is not installed")
class LexicalExchangeTests(unittest.TestCase):
    def roundtrip(self, literals):
        graph = Graph()
        for literal in literals:
            graph.add((URIRef("urn:synthetic:subject"), URIRef("urn:synthetic:value"), literal))
        rows = ontology.statements(graph)
        with patch.object(ontology, "arcade", return_value=rows):
            restored = ontology.transfer("arcade", "synthetic-lexical")
        self.assertEqual(set(restored), set(graph))
        self.assertEqual(ontology.statements(restored), rows)
        return restored

    def test_noncanonical_numeric_boolean_and_date_literals_keep_their_spelling(self):
        values = (
            ("01", XSD.integer), ("+01", XSD.integer), ("-0", XSD.integer),
            ("01.00", XSD.decimal), ("+1.00", XSD.decimal),
            ("1.00E+00", XSD.double), ("-0.0", XSD.double),
            ("1", XSD.boolean), ("0", XSD.boolean),
            ("2020-01-01T00:00:00Z", XSD.dateTime),
        )
        for lexical, datatype in values:
            with self.subTest(lexical=lexical, datatype=str(datatype)):
                self.roundtrip([Literal(lexical, datatype=datatype, normalize=False)])

    def test_equal_values_with_different_lexical_forms_are_not_duplicate_triples(self):
        literals = [Literal(value, datatype=XSD.integer, normalize=False)
                    for value in ("01", "+1", "1")]
        self.assertEqual({term.value for term in literals}, {1})
        restored = self.roundtrip(literals)
        self.assertEqual(len(restored), 3)
        self.assertEqual({str(term) for term in restored.objects()}, {"01", "+1", "1"})

    def test_language_datatype_unicode_and_escaping_survive_the_parser(self):
        lexicals = (
            "", "plain", "日本語 😀", 'single " quote', 'triple """ quote',
            "backslash \\", "literal \\n and \\u0041", "line\nnext\n", "tab\treturn\r",
            'slash-quote \\"', 'line\n"""\\\nend',
        )
        for lexical in lexicals:
            for attributes in ({}, {"lang": "ja"}, {"lang": "EN-gb"},
                               {"datatype": XSD.string}, {"datatype": URIRef("urn:synthetic:type")}):
                with self.subTest(lexical=lexical, attributes=attributes):
                    self.roundtrip([Literal(lexical, normalize=False, **attributes)])

    def test_invalid_typed_lexical_form_is_preserved_without_claiming_validity(self):
        with self.assertLogs("rdflib.term", level="WARNING"):
            literal = Literal("not-an-integer", datatype=XSD.integer, normalize=False)
        self.assertTrue(literal.ill_typed)
        with self.assertLogs("rdflib.term", level="WARNING"):
            restored = self.roundtrip([literal])
        term = next(restored.objects())
        self.assertTrue(term.ill_typed)
        self.assertIsNone(term.value)
        self.assertEqual(str(term), "not-an-integer")

    def test_other_rdflib_callers_keep_their_normalization_policy(self):
        setting = rdflib.NORMALIZE_LITERALS
        default = Literal("01", datatype=XSD.integer)
        self.roundtrip([Literal("01", datatype=XSD.integer, normalize=False)])
        self.assertIs(rdflib.NORMALIZE_LITERALS, setting)
        self.assertEqual(Literal("01", datatype=XSD.integer), default)

    def test_duplicate_rows_still_fail_instead_of_being_silently_merged(self):
        graph = Graph()
        graph.add((URIRef("urn:s"), URIRef("urn:p"),
                   Literal("01", datatype=XSD.integer, normalize=False)))
        rows = ontology.statements(graph)
        with patch.object(ontology, "arcade", return_value=rows + rows):
            with self.assertRaisesRegex(ValueError, "Duplicate database relationship"):
                ontology.transfer("arcade", "synthetic-lexical")

    def test_one_database_row_cannot_smuggle_additional_statements(self):
        for object_token in (
            '"one" . <urn:other> <urn:p> "two"',
            '"one" . <urn:s> <urn:p> "one"',
        ):
            with self.subTest(object_token=object_token):
                rows = [{"subject": "<urn:s>", "predicate": "<urn:p>", "object": object_token}]
                with patch.object(ontology, "arcade", return_value=rows):
                    with self.assertRaisesRegex(ValueError, "one RDF statement"):
                        ontology.transfer("arcade", "synthetic-lexical")

    def test_invalid_n3_is_not_accepted_as_a_literal(self):
        rows = [{"subject": "<urn:s>", "predicate": "<urn:p>", "object": '"unterminated'}]
        with patch.object(ontology, "arcade", return_value=rows):
            with self.assertRaisesRegex(ValueError, "Invalid stored RDF statement"):
                ontology.transfer("arcade", "synthetic-lexical")


if __name__ == "__main__":
    unittest.main()
