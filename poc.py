import sys
import os
import re
import requests
import html
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFileDialog, QListWidget, QTextEdit, QLabel, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class PDFProcessorThread(QThread):
    progress_update = pyqtSignal(str)
    metadata_found = pyqtSignal(str, dict)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
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
        self.progress_update.emit(f"Processing: {os.path.basename(pdf_path)}")
        try:
            # Extract text from the first few pages
            text = ""
            doc = fitz.open(pdf_path)
            # Read up to the first 3 pages
            for page_num in range(min(3, len(doc))):
                page = doc.load_page(page_num)
                text += page.get_text("text")
            doc.close()

            # Find DOI
            # Common regex for DOIs (simplified but effective for most modern DOIs)
            doi_pattern = re.compile(r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b', re.IGNORECASE)
            match = doi_pattern.search(text)

            if match:
                doi = match.group(1)
                self.progress_update.emit(f"Found DOI: {doi} in {os.path.basename(pdf_path)}")
                metadata = self.fetch_crossref_metadata(doi)
                if metadata:
                    self.metadata_found.emit(pdf_path, metadata)
                else:
                    self.progress_update.emit(f"Failed to fetch metadata for DOI: {doi}")
            else:
                self.progress_update.emit(f"No DOI found in: {os.path.basename(pdf_path)}")
        except Exception as e:
            self.progress_update.emit(f"Error processing {os.path.basename(pdf_path)}: {str(e)}")

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
        self.setWindowTitle("Next-Gen Research Assistant (PoC)")
        self.resize(800, 600)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Controls
        controls_layout = QHBoxLayout()
        self.btn_select_folder = QPushButton("Select PDF Folder")
        self.btn_select_folder.clicked.connect(self.select_folder)
        self.lbl_status = QLabel("Ready")
        
        controls_layout.addWidget(self.btn_select_folder)
        controls_layout.addWidget(self.lbl_status, stretch=1)
        main_layout.addLayout(controls_layout)

        # Splitter for files and details
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, stretch=1)

        # Left side: File list
        self.list_files = QListWidget()
        self.list_files.itemClicked.connect(self.display_metadata)
        splitter.addWidget(self.list_files)

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

        right_layout.addWidget(QLabel("Metadata:"))
        right_layout.addWidget(self.txt_metadata, stretch=2)
        right_layout.addWidget(QLabel("Logs:"))
        right_layout.addWidget(self.txt_logs, stretch=1)
        
        splitter.addWidget(right_widget)

        self.processor_thread = None
        self.metadata_store = {}

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Directory with PDFs")
        if folder_path:
            self.lbl_status.setText(f"Selected: {folder_path}")
            self.start_processing(folder_path)

    def start_processing(self, folder_path):
        self.list_files.clear()
        self.txt_logs.clear()
        self.txt_metadata.clear()
        self.metadata_store.clear()

        if self.processor_thread and self.processor_thread.isRunning():
            self.processor_thread.stop()
            self.processor_thread.wait()

        self.processor_thread = PDFProcessorThread(folder_path)
        self.processor_thread.progress_update.connect(self.log_message)
        self.processor_thread.metadata_found.connect(self.add_file_metadata)
        self.processor_thread.start()

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
            self.txt_metadata.setHtml(display_text)
        else:
            self.txt_metadata.setPlainText("Metadata not found.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())