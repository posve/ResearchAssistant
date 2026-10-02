import unittest
from db import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(":memory:")

    def tearDown(self):
        self.db.close()

    def test_get_indexed_filepaths_empty(self):
        filepaths = self.db.get_indexed_filepaths()
        self.assertEqual(filepaths, set())

    def test_get_indexed_filepaths_populated(self):
        doc1 = "/path/to/doc1.pdf"
        doc2 = "/path/to/doc2.pdf"
        self.db.add_document(doc1, "doc1.pdf", {"title": "Doc 1"}, "Text 1")
        self.db.add_document(doc2, "doc2.pdf", {"title": "Doc 2"}, "Text 2")

        filepaths = self.db.get_indexed_filepaths()
        self.assertEqual(filepaths, {doc1, doc2})

    def test_is_indexed(self):
        doc1 = "/path/to/doc1.pdf"
        self.assertFalse(self.db.is_indexed(doc1))
        self.db.add_document(doc1, "doc1.pdf", {"title": "Doc 1"}, "Text 1")
        self.assertTrue(self.db.is_indexed(doc1))


if __name__ == "__main__":
    unittest.main()
