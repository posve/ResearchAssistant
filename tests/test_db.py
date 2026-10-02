import unittest
from db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Use in-memory SQLite database for fast unit testing
        self.db = DatabaseManager(":memory:")

    def tearDown(self):
        self.db.close()

    def test_add_documents_batch_and_get_indexed_filepaths(self):
        docs = [
            {
                "filepath": "/path/doc1.pdf",
                "filename": "doc1.pdf",
                "metadata": {"title": "Doc 1", "author": "Author A", "year": "2023", "doi": "10.1000/1"},
                "full_text": "Content of document 1 regarding quantum physics."
            },
            {
                "filepath": "/path/doc2.pdf",
                "filename": "doc2.pdf",
                "metadata": {"title": "Doc 2", "author": "Author B", "year": "2024", "doi": "10.1000/2"},
                "full_text": "Content of document 2 regarding machine learning."
            }
        ]

        added_ids = self.db.add_documents_batch(docs)
        self.assertEqual(len(added_ids), 2)

        indexed = self.db.get_indexed_filepaths()
        self.assertIn("/path/doc1.pdf", indexed)
        self.assertIn("/path/doc2.pdf", indexed)

        results = self.db.search("quantum")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["filename"], "doc1.pdf")

if __name__ == "__main__":
    unittest.main()
