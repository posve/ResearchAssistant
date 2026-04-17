import sys
import os
import re
import requests
import html
import fitz  # PyMuPDF
# Suppress the non-fatal C-level warning messages from MuPDF about malformed PDFs
fitz.TOOLS.mupdf_display_errors(False)

from db import DatabaseManager
from rag import RAGManager
from llm import LLMManager

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFileDialog, QListWidget, QTextEdit, QLabel, QSplitter,
    QLineEdit, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class LLMLoadThread(QThread):
    progress_update = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, llm_manager):
        super().__init__()
        self.llm = llm_manager
        
    def run(self):
        def callback(msg):
            self.progress_update.emit(msg)
        self.llm.load_model(progress_callback=callback)
        self.finished.emit()

class LLMChatThread(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, llm_manager, question, contexts):
        super().__init__()
        self.llm = llm_manager
        self.question = question
        self.contexts = contexts

    def run(self):
        try:
            answer = self.llm.ask(self.question, self.contexts)
            self.response_ready.emit(answer)
        except Exception as e:
            self.error_occurred.emit(str(e))

class PDFProcessorThread(QThread):
    progress_update = pyqtSignal(str)
    metadata_found = pyqtSignal(str, dict)

    def __init__(self, folder_path, db_manager, rag_manager):
        super().__init__()
        self.folder_path = folder_path
        self.db = db_manager
        self.rag = rag_manager
        self.running = True

    def run(self):
        self.progress_update.emit(f"Scanning folder: {self.folder_path}...")
        for root, _, files in os.walk(self.folder_path):
            if not self.running:
                break
            for file in files:
                if not self.running:
                    break
                if file.lower().endswith(".pdf"):
                    pdf_path = os.path.join(root, file)
                    self.process_pdf(pdf_path)
        self.progress_update.emit("Scanning complete.")

    def process_pdf(self, pdf_path):
        filename = os.path.basename(pdf_path)
        
        if self.db.is_indexed(pdf_path):
            self.progress_update.emit(f"Skipping already indexed file: {filename}")
            # Even if skipped, we want to show it in the UI list
            self.metadata_found.emit(pdf_path, {})
            return

        self.progress_update.emit(f"Processing: {filename}")
        try:
            full_text = ""
            first_pages_text = ""
            doc = fitz.open(pdf_path)
            
            # Read all pages for indexing, but only first 3 for DOI search
            for page_num in range(len(doc)):
                page_text = doc.load_page(page_num).get_text("text")
                full_text += page_text + "\n"
                if page_num < 3:
                    first_pages_text += page_text
            
            doc.close()

            metadata = {}
            # Find DOI in the first 3 pages
            doi_pattern = re.compile(r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b', re.IGNORECASE)
            match = doi_pattern.search(first_pages_text)

            if match:
                doi = match.group(1)
                self.progress_update.emit(f"Found DOI: {doi} in {filename}")
                crossref_data = self.fetch_crossref_metadata(doi)
                if crossref_data:
                    metadata = crossref_data
                else:
                    self.progress_update.emit(f"Failed to fetch metadata for DOI: {doi}")
            else:
                self.progress_update.emit(f"No DOI found in: {filename}")
            
            # Save to Traditional Database for metadata search
            self.db.add_document(pdf_path, filename, metadata, full_text)
            
            # Save to Vector Database for AI Chat
            self.rag.add_document(pdf_path, filename, full_text)
            
            self.metadata_found.emit(pdf_path, metadata)

        except Exception as e:
            self.progress_update.emit(f"Error processing {filename}: {str(e)}")

    def fetch_crossref_metadata(self, doi):
        try:
            url = f"https://api.crossref.org/works/{doi}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                message = data.get("message", {})
                
                title = message.get("title", ["Unknown Title"])[0]
                
                authors = message.get("author", [])
                author_names = []
                for author in authors:
                    family = author.get("family", "")
                    given = author.get("given", "")
                    if family and given:
                        author_names.append(f"{given} {family}")
                    elif family:
                        author_names.append(family)
                
                author_str = ", ".join(author_names) if author_names else "Unknown Author"
                
                # Try to get year from created or published-print
                year = "Unknown Year"
                if "published-print" in message:
                    year = message["published-print"]["date-parts"][0][0]
                elif "created" in message:
                    year = message["created"]["date-parts"][0][0]

                return {
                    "title": title,
                    "author": author_str,
                    "year": str(year),
                    "doi": doi
                }
            return None
        except Exception as e:
            return None

    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Next-Gen Research Assistant")
        self.resize(900, 700)

        # Managers
        self.db = DatabaseManager()
        self.rag = RAGManager()
        self.llm = LLMManager()
        
        # Threads
        self.processor_thread = None
        self.llm_load_thread = None
        self.llm_chat_thread = None
        self.metadata_store = {}

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # --- TAB 1: Library & Search ---
        self.tab_library = QWidget()
        self.setup_library_tab()
        self.tabs.addTab(self.tab_library, "Library & Search")
        
        # --- TAB 2: AI Chat (RAG) ---
        self.tab_chat = QWidget()
        self.setup_chat_tab()
        self.tabs.addTab(self.tab_chat, "Chat with Documents")
        
        self.load_existing_documents()
        self.init_llm()

    def init_llm(self):
        self.txt_chat_history.append("<i>Initializing Local AI Model... Please wait.</i>")
        self.llm_load_thread = LLMLoadThread(self.llm)
        self.llm_load_thread.progress_update.connect(lambda msg: self.txt_chat_history.append(f"<i>{html.escape(msg)}</i>"))
        self.llm_load_thread.finished.connect(lambda: self.txt_chat_history.append("<b>AI is ready! Ask a question.</b><br><hr>"))
        self.llm_load_thread.start()

    def setup_library_tab(self):
        layout = QVBoxLayout(self.tab_library)

        # Controls
        controls_layout = QHBoxLayout()
        self.btn_select_folder = QPushButton("Select PDF Folder")
        self.btn_select_folder.clicked.connect(self.select_folder)
        self.lbl_status = QLabel("Ready")
        
        controls_layout.addWidget(self.btn_select_folder)
        controls_layout.addWidget(self.lbl_status, stretch=1)
        layout.addLayout(controls_layout)

        # Search Bar layout
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search within PDFs (Full-Text Search)...")
        self.txt_search.returnPressed.connect(self.perform_search)
        
        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self.perform_search)
        
        search_layout.addWidget(self.txt_search)
        search_layout.addWidget(self.btn_search)
        layout.addLayout(search_layout)

        # Splitter for files and details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter, stretch=1)

        # Left side: File list and search results
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        
        self.list_files = QListWidget()
        self.list_files.itemClicked.connect(self.display_metadata)
        
        left_layout.addWidget(QLabel("Indexed Files / Search Results:"))
        left_layout.addWidget(self.list_files)
        
        splitter.addWidget(left_widget)

        # Right side: Metadata display and logs
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)

        self.txt_metadata = QTextEdit()
        self.txt_metadata.setReadOnly(True)
        self.txt_metadata.setPlaceholderText("Select a PDF to view its extracted metadata.")
        
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setPlaceholderText("Scanning logs will appear here...")

        right_layout.addWidget(QLabel("Metadata / Content Snippet:"))
        right_layout.addWidget(self.txt_metadata, stretch=2)
        right_layout.addWidget(QLabel("Logs:"))
        right_layout.addWidget(self.txt_logs, stretch=1)
        
        splitter.addWidget(right_widget)

    def setup_chat_tab(self):
        layout = QVBoxLayout(self.tab_chat)
        
        # Chat History
        self.txt_chat_history = QTextEdit()
        self.txt_chat_history.setReadOnly(True)
        layout.addWidget(QLabel("Conversation:"))
        layout.addWidget(self.txt_chat_history, stretch=1)
        
        # Input Area
        input_layout = QHBoxLayout()
        self.txt_chat_input = QLineEdit()
        self.txt_chat_input.setPlaceholderText("Ask a question about your indexed PDFs...")
        self.txt_chat_input.returnPressed.connect(self.send_chat_message)
        
        self.btn_send_chat = QPushButton("Send")
        self.btn_send_chat.clicked.connect(self.send_chat_message)
        
        input_layout.addWidget(self.txt_chat_input)
        input_layout.addWidget(self.btn_send_chat)
        layout.addLayout(input_layout)

    def load_existing_documents(self):
        docs = self.db.get_all_documents()
        for doc in docs:
            self.metadata_store[doc['filename']] = {
                "path": doc['filepath'],
                "metadata": {
                    "title": doc['title'],
                    "author": doc['authors'],
                    "year": doc['year'],
                    "doi": doc['doi']
                }
            }
            self.list_files.addItem(doc['filename'])
        if docs:
            self.lbl_status.setText(f"Loaded {len(docs)} documents from database.")

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Directory with PDFs")
        if folder_path:
            self.lbl_status.setText(f"Selected: {folder_path}")
            self.start_processing(folder_path)

    def start_processing(self, folder_path):
        self.txt_logs.clear()

        if self.processor_thread and self.processor_thread.isRunning():
            self.processor_thread.stop()
            self.processor_thread.wait()

        self.processor_thread = PDFProcessorThread(folder_path, self.db, self.rag)
        self.processor_thread.progress_update.connect(self.log_message)
        self.processor_thread.metadata_found.connect(self.add_file_metadata)
        self.processor_thread.start()

    def send_chat_message(self):
        question = self.txt_chat_input.text().strip()
        if not question:
            return
            
        self.txt_chat_input.clear()
        self.txt_chat_history.append(f"<b>You:</b> {html.escape(question)}<br>")
        self.btn_send_chat.setEnabled(False)
        self.txt_chat_history.append("<i>Searching documents and thinking...</i>")
        
        # 1. Retrieve Contexts from Vector DB
        contexts = self.rag.query(question, n_results=3)
        
        # 2. Pass to LLM in a thread
        self.llm_chat_thread = LLMChatThread(self.llm, question, contexts)
        self.llm_chat_thread.response_ready.connect(self.on_chat_response)
        self.llm_chat_thread.error_occurred.connect(self.on_chat_error)
        self.llm_chat_thread.start()

    def on_chat_response(self, answer):
        # Remove the 'thinking' message
        cursor = self.txt_chat_history.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.select(cursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
        
        self.txt_chat_history.append(f"<b>Assistant:</b> {html.escape(answer)}<br><br><hr>")
        self.btn_send_chat.setEnabled(True)

    def on_chat_error(self, error_msg):
        self.txt_chat_history.append(f"<b style='color:red;'>Error:</b> {html.escape(error_msg)}<br><br><hr>")
        self.btn_send_chat.setEnabled(True)

    def perform_search(self):
        query = self.txt_search.text().strip()
        if not query:
            # If search is empty, reload all existing documents
            self.list_files.clear()
            self.metadata_store.clear()
            self.load_existing_documents()
            return
            
        results = self.db.search(query)
        self.list_files.clear()
        self.metadata_store.clear()
        
        self.lbl_status.setText(f"Found {len(results)} matches for '{query}'.")
        
        for res in results:
            self.metadata_store[res['filename']] = {
                "path": res['filepath'],
                "metadata": {
                    "title": res['title'],
                    "author": res['authors'],
                    "year": res['year'],
                    "doi": res['doi']
                },
                "snippet": res.get('context', '')
            }
            self.list_files.addItem(res['filename'])

    def log_message(self, message):
        self.txt_logs.append(message)
        # scroll to bottom
        scrollbar = self.txt_logs.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_file_metadata(self, filepath, metadata):
        filename = os.path.basename(filepath)
        self.metadata_store[filename] = {
            "path": filepath,
            "metadata": metadata
        }
        self.list_files.addItem(filename)

    def display_metadata(self, item):
        filename = item.text()
        data = self.metadata_store.get(filename)
        if data:
            meta = data["metadata"]
            title = html.escape(str(meta.get('title', 'Unknown Title')))
            author = html.escape(str(meta.get('author', 'Unknown Author')))
            year = html.escape(str(meta.get('year', 'Unknown Year')))
            doi = html.escape(str(meta.get('doi', 'Unknown DOI')))
            path = html.escape(str(data.get('path', 'Unknown Path')))

            display_text = f"""<b>Title:</b> {title}
<br><br>
<b>Author(s):</b> {author}
<br><br>
<b>Year:</b> {year}
<br><br>
<b>DOI:</b> {doi}
<br><br>
<i><b>File:</b> {path}</i>
"""
            if "snippet" in data and data["snippet"]:
                snippet = data['snippet']
                # snippet contains <b> tags from SQLite FTS5 snippet() function
                # We want to preserve those while escaping other HTML
                escaped_snippet = html.escape(snippet).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
                display_text += f"<br><br><b>Search Match:</b><br><i>...{escaped_snippet}...</i>"
                
            self.txt_metadata.setHtml(display_text)
        else:
            self.txt_metadata.setPlainText("Metadata not found.")
            
    def closeEvent(self, event):
        if self.processor_thread and self.processor_thread.isRunning():
            self.processor_thread.stop()
            self.processor_thread.wait()
        self.db.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())