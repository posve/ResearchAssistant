import unittest
from db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Use an in-memory database for testing
        self.db = DatabaseManager(":memory:")

    def tearDown(self):
        self.db.close()

    def test_add_document_success(self):
        filepath = "test.pdf"
        filename = "test.pdf"
        metadata = {
            "title": "Test Title",
            "author": "Test Author",
            "year": "2023",
            "doi": "10.1234/test"
        }
        full_text = "This is some test text."

        doc_id = self.db.add_document(filepath, filename, metadata, full_text)

        self.assertIsNotNone(doc_id)
        self.assertIsInstance(doc_id, int)

        # Verify documents table
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['filepath'], filepath)
        self.assertEqual(row['title'], "Test Title")
        self.assertEqual(row['authors'], "Test Author") # Matches 'author' in metadata due to add_document mapping
        self.assertEqual(row['year'], "2023")
        self.assertEqual(row['doi'], "10.1234/test")

        # Verify document_texts table
        cursor.execute("SELECT * FROM document_texts WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['full_text'], full_text)

    def test_add_document_duplicate_filepath(self):
        filepath = "duplicate.pdf"
        filename = "duplicate.pdf"
        metadata = {
            "title": "First",
            "author": "Author 1",
            "year": "2021",
            "doi": "doi1"
        }
        full_text = "First text"

        # First insertion
        doc_id1 = self.db.add_document(filepath, filename, metadata, full_text)
        self.assertIsNotNone(doc_id1)

        # Second insertion with same filepath
        metadata2 = {
            "title": "Second",
            "author": "Author 2",
            "year": "2022",
            "doi": "doi2"
        }
        full_text2 = "Second text"
        doc_id2 = self.db.add_document(filepath, filename, metadata2, full_text2)

        self.assertIsNone(doc_id2)

        # Verify only one document exists in documents table
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT count(*) as count FROM documents")
        self.assertEqual(cursor.fetchone()['count'], 1)

        # Verify only one document exists in document_texts table
        cursor.execute("SELECT count(*) as count FROM document_texts")
        self.assertEqual(cursor.fetchone()['count'], 1)

if __name__ == '__main__':
    unittest.main()
