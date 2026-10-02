import unittest
from db import DatabaseManager


class TestDatabaseManagerSearch(unittest.TestCase):
    def setUp(self):
        # Use an in-memory database for testing
        self.db = DatabaseManager(db_path=":memory:")
        self.doc_id = self.db.add_document(
            filepath="/path/to/doc1.pdf",
            filename="doc1.pdf",
            metadata={
                "title": "Quantum Computing Essentials",
                "author": "Alice Bob",
                "year": "2023",
                "doi": "10.1000/182"
            },
            full_text=(
                "Quantum computing is a rapidly-emerging technology "
                "that harnesses laws of quantum mechanics."
            )
        )

    def tearDown(self):
        self.db.close()

    def test_search_valid_query(self):
        results = self.db.search("quantum mechanics")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["filename"], "doc1.pdf")
        self.assertIn("quantum", results[0]["context"].lower())
        self.assertIn("mechanics", results[0]["context"].lower())

    def test_search_malformed_fts_query_unmatched_quote(self):
        # Unmatched double quotes cause sqlite3.OperationalError in FTS5
        results = self.db.search('"quantum mechanics')
        self.assertEqual(results, [])

    def test_search_malformed_fts_query_invalid_operator(self):
        # Malformed boolean / FTS syntax
        results = self.db.search("AND OR NOT")
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
