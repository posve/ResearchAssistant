import unittest
from unittest.mock import patch, MagicMock

# Mock heavy dependencies before importing main
import sys

mock_llm = MagicMock()
sys.modules['llm'] = mock_llm

mock_rag = MagicMock()
sys.modules['rag'] = mock_rag

mock_db = MagicMock()
sys.modules['db'] = mock_db

# Mock PyQt6 to avoid missing GUI libraries and to avoid turning
# our threads into MagicMocks which would overwrite our methods!
mock_pyqt = MagicMock()
sys.modules['PyQt6'] = mock_pyqt
sys.modules['PyQt6.QtWidgets'] = mock_pyqt

class MockQThread:
    def __init__(self, *args, **kwargs):
        pass

def mock_pyqtsignal(*args, **kwargs):
    return MagicMock()

class MockQtCore:
    QThread = MockQThread
    pyqtSignal = mock_pyqtsignal
    Qt = MagicMock()

sys.modules['PyQt6.QtCore'] = MockQtCore()

import requests
from main import PDFProcessorThread

class TestFetchCrossrefMetadata(unittest.TestCase):
    def setUp(self):
        self.processor = PDFProcessorThread(
            folder_path="dummy",
            db_manager=MagicMock(),
            rag_manager=MagicMock()
        )

    @patch('main.requests.get')
    def test_fetch_crossref_metadata_success_published_print(self, mock_get):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["A Great Paper"],
                "author": [
                    {"family": "Doe", "given": "John"},
                    {"family": "Smith", "given": "Jane"}
                ],
                "published-print": {
                    "date-parts": [[2023, 5, 1]]
                }
            }
        }
        mock_get.return_value = mock_response

        doi = "10.1234/abcd"
        result = self.processor.fetch_crossref_metadata(doi)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "A Great Paper")
        self.assertEqual(result["author"], "John Doe, Jane Smith")
        self.assertEqual(result["year"], "2023")
        self.assertEqual(result["doi"], doi)

        mock_get.assert_called_once_with(f"https://api.crossref.org/works/{doi}", timeout=5)

    @patch('main.requests.get')
    def test_fetch_crossref_metadata_success_created_date(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Another Great Paper"],
                "author": [
                    {"family": "Doe", "given": "John"}
                ],
                "created": {
                    "date-parts": [[2022, 1, 1]]
                }
            }
        }
        mock_get.return_value = mock_response

        doi = "10.1234/efgh"
        result = self.processor.fetch_crossref_metadata(doi)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Another Great Paper")
        self.assertEqual(result["author"], "John Doe")
        self.assertEqual(result["year"], "2022")
        self.assertEqual(result["doi"], doi)

    @patch('main.requests.get')
    def test_fetch_crossref_metadata_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        doi = "10.1234/timeout"
        result = self.processor.fetch_crossref_metadata(doi)

        self.assertIsNone(result)

    @patch('main.requests.get')
    def test_fetch_crossref_metadata_non_200_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        doi = "10.1234/notfound"
        result = self.processor.fetch_crossref_metadata(doi)

        self.assertIsNone(result)

    @patch('main.requests.get')
    def test_fetch_crossref_metadata_missing_fields(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # No title, no author, no date
        mock_response.json.return_value = {
            "message": {}
        }
        mock_get.return_value = mock_response

        doi = "10.1234/missing"
        result = self.processor.fetch_crossref_metadata(doi)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Unknown Title")
        self.assertEqual(result["author"], "Unknown Author")
        self.assertEqual(result["year"], "Unknown Year")
        self.assertEqual(result["doi"], doi)

    @patch('main.requests.get')
    def test_fetch_crossref_metadata_partial_author_info(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "author": [
                    {"family": "OnlyFamily"}, # missing given
                    {"given": "OnlyGiven"}    # missing family
                ]
            }
        }
        mock_get.return_value = mock_response

        doi = "10.1234/partialauthor"
        result = self.processor.fetch_crossref_metadata(doi)

        self.assertIsNotNone(result)
        # Check logic in main.py:
        # if family and given: author_names.append(f"{given} {family}")
        # elif family: author_names.append(family)
        self.assertEqual(result["author"], "OnlyFamily")

    @patch('main.requests.get')
    def test_fetch_crossref_metadata_invalid_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        doi = "10.1234/invalidjson"
        result = self.processor.fetch_crossref_metadata(doi)

        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
