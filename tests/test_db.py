import unittest
import sqlite3
from db import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Use in-memory SQLite database for test isolation
        self.db = DatabaseManager(db_path=":memory:")

    def tearDown(self):
        self.db.close()

    def test_init_and_table_creation(self):
        cursor = self.db.conn.cursor()

        # Check if 'documents' table exists
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='documents';"
        )
        self.assertIsNotNone(cursor.fetchone())

        # Check if 'document_texts' FTS5 table exists
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='document_texts';"
        )
        self.assertIsNotNone(cursor.fetchone())

    def test_add_document_success(self):
        filepath = "/path/to/doc.pdf"
        filename = "doc.pdf"
        metadata = {
            "title": "Sample Title",
            "author": "John Doe",
            "year": "2023",
            "doi": "10.1234/5678"
        }
        full_text = "This is a sample document for testing database ops."

        doc_id = self.db.add_document(filepath, filename, metadata, full_text)
        self.assertEqual(doc_id, 1)

        # Verify document in documents table
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["filepath"], filepath)
        self.assertEqual(row["filename"], filename)
        self.assertEqual(row["title"], "Sample Title")
        self.assertEqual(row["authors"], "John Doe")
        self.assertEqual(row["year"], "2023")
        self.assertEqual(row["doi"], "10.1234/5678")

        # Verify full_text in document_texts table
        cursor.execute(
            "SELECT * FROM document_texts WHERE doc_id = ?",
            (doc_id,)
        )
        fts_row = cursor.fetchone()
        self.assertIsNotNone(fts_row)
        self.assertEqual(fts_row["full_text"], full_text)

    def test_add_document_partial_metadata(self):
        filepath = "/path/to/partial.pdf"
        filename = "partial.pdf"
        metadata = {}  # Empty metadata dict
        full_text = "Partial metadata test content."

        doc_id = self.db.add_document(filepath, filename, metadata, full_text)
        self.assertIsNotNone(doc_id)

        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        self.assertEqual(row["filepath"], filepath)
        self.assertIsNone(row["title"])
        self.assertIsNone(row["authors"])
        self.assertIsNone(row["year"])
        self.assertIsNone(row["doi"])

    def test_add_document_duplicate_filepath(self):
        filepath = "/path/to/unique.pdf"
        filename = "unique.pdf"
        metadata = {"title": "Unique"}
        full_text = "Content 1"

        doc_id1 = self.db.add_document(
            filepath, filename, metadata, full_text
        )
        self.assertIsNotNone(doc_id1)

        # Inserting second document with same filepath should return None
        doc_id2 = self.db.add_document(
            filepath, filename, metadata, "Content 2"
        )
        self.assertIsNone(doc_id2)

        # Ensure only 1 document is in the table
        all_docs = self.db.get_all_documents()
        self.assertEqual(len(all_docs), 1)

    def test_is_indexed(self):
        filepath = "/path/to/check.pdf"
        self.assertFalse(self.db.is_indexed(filepath))

        self.db.add_document(filepath, "check.pdf", {}, "Some content")
        self.assertTrue(self.db.is_indexed(filepath))

    def test_get_all_documents(self):
        self.assertEqual(self.db.get_all_documents(), [])

        self.db.add_document(
            "/path/1.pdf", "1.pdf", {"title": "Doc 1"}, "Text 1"
        )
        self.db.add_document(
            "/path/2.pdf", "2.pdf", {"title": "Doc 2"}, "Text 2"
        )

        docs = self.db.get_all_documents()
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0]["filename"], "1.pdf")
        self.assertEqual(docs[1]["filename"], "2.pdf")

    def test_search_success(self):
        self.db.add_document(
            "/path/quantum.pdf",
            "quantum.pdf",
            {"title": "Quantum Computing", "author": "Alice"},
            "Quantum computing uses quantum mechanics for complex problems."
        )
        self.db.add_document(
            "/path/classical.pdf",
            "classical.pdf",
            {"title": "Classical Computing", "author": "Bob"},
            "Classical computers use binary bits to perform computations."
        )

        results = self.db.search("quantum")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["filename"], "quantum.pdf")
        self.assertEqual(results[0]["title"], "Quantum Computing")
        self.assertIn("<b>Quantum</b>", results[0]["context"])

    def test_search_no_match(self):
        self.db.add_document(
            "/path/doc.pdf",
            "doc.pdf",
            {"title": "General Topic"},
            "This document covers basic topic information."
        )

        results = self.db.search("nonexistentword")
        self.assertEqual(results, [])

    def test_close(self):
        db = DatabaseManager(db_path=":memory:")
        db.close()
        # Expect programming error when attempting to query closed connection
        with self.assertRaises(sqlite3.ProgrammingError):
            db.conn.cursor()


if __name__ == "__main__":
    unittest.main()
