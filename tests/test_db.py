import unittest
from db import DatabaseManager


class TestDatabaseManagerAddDocument(unittest.TestCase):
    def setUp(self):
        # Use an in-memory database for fast, isolated test runs
        self.db = DatabaseManager(db_path=":memory:")

    def tearDown(self):
        self.db.close()

    def test_add_document_success(self):
        filepath = "/docs/paper1.pdf"
        filename = "paper1.pdf"
        metadata = {
            "title": "Quantum Computing Essentials",
            "author": "Alice Smith",
            "year": "2023",
            "doi": "10.1000/182"
        }
        full_text = ("This paper discusses quantum state superposition "
                     "and entanglement.")

        doc_id = self.db.add_document(filepath, filename, metadata, full_text)

        self.assertIsNotNone(doc_id)
        self.assertIsInstance(doc_id, int)

        # Verify document exists in documents table
        docs = self.db.get_all_documents()
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertEqual(doc["id"], doc_id)
        self.assertEqual(doc["filepath"], filepath)
        self.assertEqual(doc["filename"], filename)
        self.assertEqual(doc["title"], "Quantum Computing Essentials")
        self.assertEqual(doc["authors"], "Alice Smith")
        self.assertEqual(doc["year"], "2023")
        self.assertEqual(doc["doi"], "10.1000/182")

        # Verify FTS indexing
        search_results = self.db.search("superposition")
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0]["id"], doc_id)
        self.assertIn("superposition", search_results[0]["context"])

    def test_add_document_duplicate_filepath(self):
        filepath = "/docs/duplicate.pdf"
        filename = "duplicate.pdf"
        metadata = {"title": "First Version", "author": "Bob"}
        full_text = "Initial content"

        doc_id1 = self.db.add_document(filepath, filename, metadata,
                                       full_text)
        self.assertIsNotNone(doc_id1)

        # Attempt to insert a second document with identical filepath
        metadata_duplicate = {"title": "Second Version", "author": "Bob"}
        doc_id2 = self.db.add_document(filepath, filename,
                                       metadata_duplicate, "New content")

        self.assertIsNone(doc_id2)

        # Ensure database state was rolled back and still contains original
        docs = self.db.get_all_documents()
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["title"], "First Version")

    def test_add_document_missing_metadata(self):
        filepath = "/docs/no_meta.pdf"
        filename = "no_meta.pdf"
        empty_metadata = {}
        full_text = "Text without metadata."

        doc_id = self.db.add_document(filepath, filename, empty_metadata,
                                      full_text)

        self.assertIsNotNone(doc_id)
        docs = self.db.get_all_documents()
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertIsNone(doc["title"])
        self.assertIsNone(doc["authors"])
        self.assertIsNone(doc["year"])
        self.assertIsNone(doc["doi"])

    def test_is_indexed(self):
        filepath = "/docs/indexed.pdf"
        self.assertFalse(self.db.is_indexed(filepath))

        self.db.add_document(filepath, "indexed.pdf", {"title": "Indexed"},
                             "Some text")

        self.assertTrue(self.db.is_indexed(filepath))


if __name__ == "__main__":
    unittest.main()
