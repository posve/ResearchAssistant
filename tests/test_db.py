import unittest
import os
import sqlite3
from db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_library_search.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = DatabaseManager(self.db_path)

        # Seed some data
        self.db.add_document(
            "research_paper.pdf",
            "research_paper.pdf",
            {"title": "AI in Research", "author": "John Doe", "year": "2023", "doi": "10.1234/ai"},
            "This research paper discusses the role of an AI assistant in modern science."
        )

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_search_alphanumeric(self):
        """Verify that a standard query like 'research' returns the expected document."""
        results = self.db.search("research")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['filename'], "research_paper.pdf")
        self.assertIn("<b>research</b>", results[0]['context'])

    def test_search_unbalanced_quote(self):
        """Verify that a query containing only \" does not raise an error."""
        try:
            results = self.db.search('"')
            self.assertEqual(len(results), 0)
        except sqlite3.OperationalError:
            self.fail("DatabaseManager.search raised OperationalError on unbalanced quote")

    def test_search_phrase(self):
        """Verify that phrase searching still works."""
        results = self.db.search('"AI assistant"')
        self.assertEqual(len(results), 1)
        # FTS5 might highlight the whole phrase or individual words depending on configuration
        # but it should definitely find the document.
        self.assertIn("AI assistant", results[0]['context'])

    def test_search_multiple_terms(self):
        """Verify that multiple terms work as expected."""
        results = self.db.search('research assistant')
        self.assertEqual(len(results), 1)
        self.assertIn("<b>research</b>", results[0]['context'])
        self.assertIn("<b>assistant</b>", results[0]['context'])

if __name__ == "__main__":
    unittest.main()
