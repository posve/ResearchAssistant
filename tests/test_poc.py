import sys
import unittest
from unittest.mock import patch, MagicMock

# Mock PyQt6 to avoid GUI missing library issues
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

from poc import PDFProcessorThread  # noqa: E402


class TestPoCFetchCrossrefMetadata(unittest.TestCase):
    def setUp(self):
        self.processor = PDFProcessorThread(folder_path="dummy")

    @patch('poc.requests.get')
    def test_fetch_crossref_metadata_sanitizes_doi(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Test Title"],
                "author": [{"family": "Doe", "given": "John"}],
                "created": {"date-parts": [[2024, 1, 1]]}
            }
        }
        mock_get.return_value = mock_response

        # Traversal / special characters in DOI
        raw_doi = "10.1234/../secret/path/test?query=1#fragment"
        result = self.processor.fetch_crossref_metadata(raw_doi)

        expected_encoded_doi = (
            "10.1234%2F..%2Fsecret%2Fpath%2Ftest%3Fquery%3D1%23fragment"
        )
        expected_url = f"https://api.crossref.org/works/{expected_encoded_doi}"

        mock_get.assert_called_once_with(expected_url, timeout=5)
        self.assertIsNotNone(result)
        self.assertEqual(result["doi"], raw_doi)

    @patch('poc.requests.get')
    def test_fetch_crossref_metadata_standard_doi(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Sample Paper"],
                "author": [{"family": "Smith", "given": "Alice"}],
                "published-print": {"date-parts": [[2023, 6, 12]]}
            }
        }
        mock_get.return_value = mock_response

        doi = "10.1000/182"
        result = self.processor.fetch_crossref_metadata(doi)

        expected_url = "https://api.crossref.org/works/10.1000%2F182"
        mock_get.assert_called_once_with(expected_url, timeout=5)
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Sample Paper")
        self.assertEqual(result["author"], "Alice Smith")
        self.assertEqual(result["year"], "2023")


if __name__ == '__main__':
    unittest.main()
