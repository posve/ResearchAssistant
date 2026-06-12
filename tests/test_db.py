import unittest
import sqlite3
from db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Use an in-memory database for testing
        self.db_manager = DatabaseManager(":memory:")

    def tearDown(self):
        self.db_manager.close()

    def test_add_document_success(self):
        filepath = "test.pdf"
        filename = "test.pdf"
        metadata = {
            "title": "Test Title",
            "author": "Test Author",
            "year": "2023",
            "doi": "10.1234/test"
        }
        full_text = "This is a test document."

        doc_id = self.db_manager.add_document(filepath, filename, metadata, full_text)

        # Assert that the returned doc_id is an integer (success)
        self.assertIsInstance(doc_id, int)

        # Verify that the document exists in the documents table
        cursor = self.db_manager.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['filepath'], filepath)
        self.assertEqual(row['filename'], filename)
        self.assertEqual(row['title'], metadata['title'])
        self.assertEqual(row['authors'], metadata['author'])
        self.assertEqual(row['year'], metadata['year'])
        self.assertEqual(row['doi'], metadata['doi'])

        # Verify that the text exists in the document_texts table
        cursor.execute("SELECT * FROM document_texts WHERE doc_id = ?", (doc_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['full_text'], full_text)

    def test_add_document_duplicate_filepath(self):
        filepath = "duplicate.pdf"
        filename = "duplicate.pdf"
        metadata = {"title": "First", "author": "Author", "year": "2023", "doi": "10.1234"}
        full_text = "First document text."

        # Add the document the first time
        doc_id1 = self.db_manager.add_document(filepath, filename, metadata, full_text)
        self.assertIsInstance(doc_id1, int)

        # Add the document a second time with the same filepath
        doc_id2 = self.db_manager.add_document(filepath, "other.pdf", {"title": "Second"}, "Second text")

        # Assert that the second call returns None due to IntegrityError (unique filepath)
        self.assertIsNone(doc_id2)

        # Verify that the documents table still contains only the original entry
        cursor = self.db_manager.conn.cursor()
        cursor.execute("SELECT count(*) as count FROM documents")
        row = cursor.fetchone()
        self.assertEqual(row['count'], 1)

if __name__ == '__main__':
    unittest.main()
