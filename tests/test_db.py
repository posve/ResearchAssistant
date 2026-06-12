import unittest
import sqlite3
import os
from db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Use an in-memory database for testing
        self.db = DatabaseManager(db_path=":memory:")

    def tearDown(self):
        self.db.close()

    def test_initialization(self):
        """Verify that the documents and document_texts tables are correctly created."""
        cursor = self.db.conn.cursor()

        # Check for documents table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        self.assertIsNotNone(cursor.fetchone())

        # Check for document_texts FTS5 table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_texts'")
        self.assertIsNotNone(cursor.fetchone())

    def test_add_document_success(self):
        """Verify that a document can be added successfully."""
        filepath = "/path/to/test.pdf"
        filename = "test.pdf"
        metadata = {
            'title': 'Test Title',
            'author': 'Test Author',
            'year': '2023',
            'doi': '10.1234/test'
        }
        full_text = "This is a test document full text content."

        doc_id = self.db.add_document(filepath, filename, metadata, full_text)

        self.assertIsInstance(doc_id, int)

        # Verify metadata
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['filepath'], filepath)
        self.assertEqual(row['filename'], filename)
        self.assertEqual(row['title'], metadata['title'])
        self.assertEqual(row['authors'], metadata['author'])
        self.assertEqual(row['year'], metadata['year'])
        self.assertEqual(row['doi'], metadata['doi'])

        # Verify full text
        cursor.execute("SELECT full_text FROM document_texts WHERE doc_id = ?", (doc_id,))
        fts_row = cursor.fetchone()
        self.assertIsNotNone(fts_row)
        self.assertEqual(fts_row['full_text'], full_text)

    def test_add_document_duplicate(self):
        """Verify that adding a document with the same filepath returns None."""
        filepath = "/path/to/test.pdf"
        filename = "test.pdf"
        metadata = {'title': 'Test'}
        full_text = "Content"

        id1 = self.db.add_document(filepath, filename, metadata, full_text)
        self.assertIsNotNone(id1)

        id2 = self.db.add_document(filepath, filename, metadata, full_text)
        self.assertIsNone(id2)

    def test_is_indexed(self):
        """Verify is_indexed accurately reports existence of a document."""
        filepath = "/path/to/test.pdf"

        self.assertFalse(self.db.is_indexed(filepath))

        self.db.add_document(filepath, "test.pdf", {}, "content")

        self.assertTrue(self.db.is_indexed(filepath))

    def test_search(self):
        """Verify that the search method correctly performs full-text search."""
        self.db.add_document(
            "/path/1.pdf", "1.pdf",
            {'title': 'Search Test 1'},
            "The quick brown fox jumps over the lazy dog"
        )
        self.db.add_document(
            "/path/2.pdf", "2.pdf",
            {'title': 'Search Test 2'},
            "Python is a great programming language"
        )

        # Search for keyword in first doc
        results = self.db.search("fox")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Search Test 1')
        self.assertIn("<b>fox</b>", results[0]['context'])

        # Search for keyword in second doc
        results = self.db.search("Python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Search Test 2')
        self.assertIn("<b>Python</b>", results[0]['context'])

    def test_get_all_documents(self):
        """Verify get_all_documents returns all documents."""
        self.db.add_document("/path/1.pdf", "1.pdf", {'title': 'T1'}, "C1")
        self.db.add_document("/path/2.pdf", "2.pdf", {'title': 'T2'}, "C2")

        docs = self.db.get_all_documents()
        self.assertEqual(len(docs), 2)

        titles = [d['title'] for d in docs]
        self.assertIn('T1', titles)
        self.assertIn('T2', titles)

    def test_close(self):
        """Verify that close method closes the connection."""
        self.db.close()
        with self.assertRaises(sqlite3.ProgrammingError):
            self.db.conn.cursor()

if __name__ == '__main__':
    unittest.main()
