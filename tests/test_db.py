import unittest
from db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Use an in-memory database for fast, isolated tests
        self.db = DatabaseManager(":memory:")

    def tearDown(self):
        self.db.close()

    def test_add_document_success(self):
        metadata = {
            "title": "Test Paper",
            "author": "Jane Doe",
            "year": "2024",
            "doi": "10.1234/test"
        }
        doc_id = self.db.add_document("/path/to/doc1.pdf", "doc1.pdf", metadata, "Sample full text content.")
        self.assertIsNotNone(doc_id)
        self.assertEqual(doc_id, 1)

        docs = self.db.get_all_documents()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["filepath"], "/path/to/doc1.pdf")
        self.assertEqual(docs[0]["filename"], "doc1.pdf")
        self.assertEqual(docs[0]["title"], "Test Paper")
        self.assertEqual(docs[0]["authors"], "Jane Doe")
        self.assertEqual(docs[0]["year"], "2024")
        self.assertEqual(docs[0]["doi"], "10.1234/test")

    def test_add_document_duplicate_integrity_error(self):
        metadata = {
            "title": "Test Paper",
            "author": "Jane Doe",
            "year": "2024",
            "doi": "10.1234/test"
        }
        # Insert initial document
        first_doc_id = self.db.add_document("/path/to/doc1.pdf", "doc1.pdf", metadata, "Sample full text content.")
        self.assertIsNotNone(first_doc_id)

        # Attempt to insert duplicate document with the same filepath
        duplicate_doc_id = self.db.add_document("/path/to/doc1.pdf", "doc1.pdf", metadata, "Duplicate content.")

        # Verify that add_document returns None on duplicate integrity error
        self.assertIsNone(duplicate_doc_id)

        # Verify that the database state was rolled back and still only contains 1 document
        docs = self.db.get_all_documents()
        self.assertEqual(len(docs), 1)

if __name__ == '__main__':
    unittest.main()
