import unittest
import os
import sqlite3
from db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.db_path = ":memory:"
        self.db = DatabaseManager(self.db_path)
        # Add some test data
        self.db.add_document(
            "test1.pdf",
            "test1.pdf",
            {"title": "Test Document 1", "author": "Author A", "year": "2021", "doi": "10.1000/1"},
            "This is the full text of the first test document."
        )
        self.db.add_document(
            "test2.pdf",
            "test2.pdf",
            {"title": "Test Document 2", "author": "Author B", "year": "2022", "doi": "10.1000/2"},
            "Another test document with different content."
        )

    def tearDown(self):
        self.db.close()

    def test_search_valid_query(self):
        results = self.db.search("content")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["filename"], "test2.pdf")

    def test_search_malformed_query(self):
        # This query would normally raise sqlite3.OperationalError
        results = self.db.search(' " ')
        self.assertEqual(results, [])

    def test_search_no_results(self):
        results = self.db.search("nonexistent")
        self.assertEqual(len(results), 0)

if __name__ == "__main__":
    unittest.main()
