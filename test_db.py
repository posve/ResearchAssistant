import unittest
import sqlite3
from db import DatabaseManager

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        # Use an in-memory database for testing
        self.db = DatabaseManager(":memory:")

    def tearDown(self):
        self.db.close()

    def test_initialization(self):
        # Ensure tables are created
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertIn("documents", tables)
        self.assertIn("document_texts", tables)

    def test_add_and_get_all_documents(self):
        # Test adding a document
        metadata = {
            'title': 'Test Title',
            'author': 'Test Author',
            'year': '2023',
            'doi': '10.1234/test'
        }
        doc_id = self.db.add_document('test/path.pdf', 'path.pdf', metadata, 'This is the full text of the document.')
        self.assertIsNotNone(doc_id)

        # Test getting all documents
        docs = self.db.get_all_documents()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]['filepath'], 'test/path.pdf')
        self.assertEqual(docs[0]['title'], 'Test Title')
        self.assertEqual(docs[0]['authors'], 'Test Author')

    def test_is_indexed(self):
        # Should be false initially
        self.assertFalse(self.db.is_indexed('test/path.pdf'))

        # Add document
        self.db.add_document('test/path.pdf', 'path.pdf', {}, 'text')

        # Should be true now
        self.assertTrue(self.db.is_indexed('test/path.pdf'))

    def test_add_duplicate_document(self):
        # Add a document
        doc_id1 = self.db.add_document('test/path.pdf', 'path.pdf', {}, 'text1')
        self.assertIsNotNone(doc_id1)

        # Attempt to add the same document again (same filepath)
        doc_id2 = self.db.add_document('test/path.pdf', 'path.pdf', {}, 'text2')
        self.assertIsNone(doc_id2)

        # Ensure only one document exists
        docs = self.db.get_all_documents()
        self.assertEqual(len(docs), 1)

    def test_search(self):
        # Add documents
        self.db.add_document('doc1.pdf', 'doc1.pdf', {'title': 'Python Guide'}, 'Python is a great programming language.')
        self.db.add_document('doc2.pdf', 'doc2.pdf', {'title': 'Java Guide'}, 'Java is also a popular language.')

        # Search for Python
        results = self.db.search('Python')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Python Guide')
        self.assertIn('<b>Python</b>', results[0]['context'])

        # Search for language
        results = self.db.search('language')
        self.assertEqual(len(results), 2)

if __name__ == '__main__':
    unittest.main()
