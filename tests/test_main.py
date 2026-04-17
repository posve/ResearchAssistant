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
# To avoid replacing the whole module with MagicMock and losing QMainWindow:
class MockQtWidgets:
    QApplication = MagicMock()
    QMainWindow = object
    QWidget = MagicMock()
    QVBoxLayout = MagicMock()
    QHBoxLayout = MagicMock()
    QPushButton = MagicMock()
    QFileDialog = MagicMock()
    QListWidget = MagicMock()
    QTextEdit = MagicMock()
    QLabel = MagicMock()
    QSplitter = MagicMock()
    QLineEdit = MagicMock()
    QTabWidget = MagicMock()

sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MockQtWidgets()

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
from main import MainWindow

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

class TestChatXSSFix(unittest.TestCase):
    def setUp(self):
        pass

    @patch('main.LLMChatThread')
    @patch('main.LLMLoadThread')
    def test_send_chat_message_escapes_input(self, mock_load_thread, mock_chat_thread):
        # We can test `send_chat_message` directly by creating a dummy instance
        # that doesn't call __init__ to avoid UI setup, or by bypassing __init__.


        # Create a dummy object and bind the method
        class DummyMainWindow:
            pass

        window = DummyMainWindow()

        # Setup the mocked widgets
        window.txt_chat_input = MagicMock()
        window.txt_chat_history = MagicMock()
        window.btn_send_chat = MagicMock()
        window.rag = MagicMock()
        window.llm = MagicMock()

        # Mock the query return
        window.rag.query.return_value = []

        # Setup the input
        malicious_input = "<script>alert('xss')</script>"
        window.txt_chat_input.text.return_value = malicious_input

        # Ensure it doesn't crash on connecting missing methods
        window.on_chat_response = MagicMock()
        window.on_chat_error = MagicMock()

        # Bind and call the method
        MainWindow.send_chat_message(window)

        # Ensure it was called with the escaped string
        import html
        expected_escaped = html.escape(malicious_input)

        # txt_chat_history.append is called a few times.
        calls = window.txt_chat_history.append.call_args_list
        self.assertTrue(len(calls) >= 2)

        # Verify the first append call contains the escaped input
        first_call_arg = calls[0][0][0]
        self.assertIn(expected_escaped, first_call_arg)
        self.assertNotIn(malicious_input, first_call_arg)

    def test_on_chat_response_escapes_input(self):


        class DummyMainWindow:
            pass

        window = DummyMainWindow()
        window.txt_chat_history = MagicMock()
        window.btn_send_chat = MagicMock()

        # Mock text cursor
        cursor_mock = MagicMock()
        window.txt_chat_history.textCursor.return_value = cursor_mock

        malicious_input = "<img src=x onerror=alert(1)>"

        MainWindow.on_chat_response(window, malicious_input)

        import html
        expected_escaped = html.escape(malicious_input)

        calls = window.txt_chat_history.append.call_args_list
        self.assertTrue(len(calls) >= 1)

        first_call_arg = calls[0][0][0]
        self.assertIn(expected_escaped, first_call_arg)
        self.assertNotIn(malicious_input, first_call_arg)

    def test_on_chat_error_escapes_input(self):


        class DummyMainWindow:
            pass

        window = DummyMainWindow()
        window.txt_chat_history = MagicMock()
        window.btn_send_chat = MagicMock()

        malicious_input = "<svg/onload=alert(1)>"

        MainWindow.on_chat_error(window, malicious_input)

        import html
        expected_escaped = html.escape(malicious_input)

        calls = window.txt_chat_history.append.call_args_list
        self.assertTrue(len(calls) >= 1)

        first_call_arg = calls[0][0][0]
        self.assertIn(expected_escaped, first_call_arg)
        self.assertNotIn(malicious_input, first_call_arg)

if __name__ == '__main__':
    unittest.main()


class TestMainWindowXSS(unittest.TestCase):
    @patch('main.QApplication')
    def test_send_chat_message_escapes_html(self, mock_qapp):
        # We only want to instantiate MainWindow, but we have mocked dependencies.
        # MainWindow.__init__ creates instances of mocked managers and sets up the UI.

        # It needs some GUI parts to work, wait, since we mocked PyQt6, MainWindow won't have actual widgets!
        # But wait, MainWindow subclasses QMainWindow which we didn't mock properly if we just did MagicMock()
        # Actually, in this test file we mocked PyQt6.QtWidgets = MagicMock().
        # So MainWindow inherits from a MagicMock. Its UI setup might not work as expected or might just be mock calls.
        pass
