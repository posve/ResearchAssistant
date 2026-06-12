import unittest
import sqlite3
from db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Use an in-memory database for testing
        self.db_manager = DatabaseManager(db_path=":memory:")

    def tearDown(self):
        self.db_manager.close()

    def test_add_document_success(self):
        filepath = "test.pdf"
        filename = "test.pdf"
        metadata = {"title": "Test Title", "author": "Test Author", "year": "2023", "doi": "10.1234/test"}
        full_text = "This is a test document full text."

        doc_id = self.db_manager.add_document(filepath, filename, metadata, full_text)

        self.assertIsNotNone(doc_id)
        self.assertTrue(self.db_manager.is_indexed(filepath))

        docs = self.db_manager.get_all_documents()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]['filepath'], filepath)
        self.assertEqual(docs[0]['title'], "Test Title")

    def test_add_document_duplicate_filepath(self):
        """Test that adding a document with a duplicate filepath returns None (IntegrityError)."""
        filepath = "test.pdf"
        filename = "test.pdf"
        metadata = {"title": "Test Title", "author": "Test Author", "year": "2023", "doi": "10.1234/test"}
        full_text = "This is a test document full text."

        # First insertion should succeed
        doc_id1 = self.db_manager.add_document(filepath, filename, metadata, full_text)
        self.assertIsNotNone(doc_id1)

        # Second insertion with same filepath should return None due to IntegrityError
        doc_id2 = self.db_manager.add_document(filepath, filename, metadata, full_text)
        self.assertIsNone(doc_id2)

        # Ensure only one document is in the database
        docs = self.db_manager.get_all_documents()
        self.assertEqual(len(docs), 1)

    def test_is_indexed(self):
        filepath = "not_indexed.pdf"
        self.assertFalse(self.db_manager.is_indexed(filepath))

        self.db_manager.add_document(filepath, "not_indexed.pdf", {}, "text")
        self.assertTrue(self.db_manager.is_indexed(filepath))

    def test_search(self):
        self.db_manager.add_document("doc1.pdf", "doc1.pdf", {"title": "First"}, "The quick brown fox")
        self.db_manager.add_document("doc2.pdf", "doc2.pdf", {"title": "Second"}, "Jumps over the lazy dog")

        results = self.db_manager.search("fox")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['filename'], "doc1.pdf")
        self.assertIn("<b>fox</b>", results[0]['context'])

        results = self.db_manager.search("lazy")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['filename'], "doc2.pdf")
        self.assertIn("<b>lazy</b>", results[0]['context'])

if __name__ == '__main__':
    unittest.main()
