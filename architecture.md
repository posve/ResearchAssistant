# Next-Gen Research Assistant Architecture

## 1. Vision & Overview
The goal is to create a cross-platform, privacy-focused standalone desktop application that combines the powerful file indexing and fast search capabilities of DEVONthink with the reference management features of Zotero. 

This application targets researchers, historians, and academics who need to manage thousands of PDFs, quickly extract metadata, insert citations smoothly into word processors, and securely interact with their own data using AI—without sending their intellectual property to the cloud or relying on complex, external setups.

## 2. Core Pillars

### 2.1 File Management & Indexing (The "DEVONthink" Pillar)
- **Zero-Movement Policy:** PDFs and documents remain exactly where the user has organized them on their file system. The application does not force a proprietary folder structure or duplicate files into an internal database.
- **Fast Indexing:** The app monitors selected directories. Upon adding new files, it rapidly extracts text (via standard extraction and localized OCR when necessary) and indexes it.
- **Data Storage:** 
  - A local SQLite database is used for fast metadata and full-text search indexing.
  - A local Vector Database (e.g., FAISS or ChromaDB) is used to store document embeddings to power the RAG (Retrieval-Augmented Generation) chat feature.

### 2.2 Reference Management & Citations (The "Zotero" Pillar)
- **Metadata Extraction:** The app extracts basic metadata and DOIs directly from the PDF text. It fetches complete bibliographic details via the Crossref API (or similar services) to ensure high accuracy without manual entry.
- **The "Floating Bar" Citation Engine:** Instead of relying on brittle and sluggish Word-specific plugins, the application features a system-wide, fast-trigger floating search bar (similar to macOS Spotlight or PowerToys Run). 
  - The user presses a global shortcut.
  - Types part of the author name or title.
  - Selects the desired source.
  - The app instantly copies the correctly formatted citation (or citation key) to the clipboard, ready to be pasted into Word, Google Docs, Obsidian, etc.

### 2.3 Privacy-First AI Chat (The RAG Pillar)
- **Fully Local Processing:** The user can "chat with their documents." The AI answers questions and summarizes texts while citing specific PDFs from the user's library.
- **Bundled LLM:** The user does not need to install Ollama, Docker, or external tools. The application bundles an inference engine (like `llama.cpp` via Python bindings) and automatically downloads a lightweight, highly-quantized open-source model (e.g., Llama-3-8B-Instruct or Mistral) on initial setup. 
- **Retrieval-Augmented Generation (RAG):** When the user asks a question, the local vector database retrieves the most relevant chunks of text from the user's PDFs, feeds them to the local LLM, and generates an accurate, cited response without needing an internet connection.

## 3. Technology Stack

- **User Interface:** Native desktop UI built with Python and **PyQt6 / PySide6**. This ensures true cross-platform compatibility across Windows, macOS, and Linux while looking natively integrated.
- **Core Logic & Backend:** Python 3.
- **PDF Processing:** `PyMuPDF` (for fast text extraction) and `pytesseract` (for OCR if required).
- **AI / LLM Engine:** `llama-cpp-python` (for running local inference without external servers).
- **Vector Storage:** `ChromaDB` or `FAISS` (running entirely locally).
- **Traditional Database:** SQLite (for metadata, DOIs, user settings, and application state).
- **Packaging:** PyInstaller or Briefcase, creating a single click-to-run installer for Windows (.exe), Mac (.dmg), and Linux (.AppImage).

## 4. Development Roadmap

### Phase 1: Proof of Concept (Current)
- Native PyQt UI.
- Select a local folder of PDFs without moving them.
- Extract text and find DOIs.
- Fetch and display accurate bibliographic metadata from the Crossref API.

### Phase 2: Core Indexing & Storage
- Implement SQLite for saving retrieved metadata.
- Implement full-text search across the local library.

### Phase 3: The AI RAG Engine
- Integrate local embedding models.
- Integrate `llama.cpp` for local, offline chat queries against the specific PDF library.

### Phase 4: The Floating Citation Bar
- Implement a global system hotkey.
- Create the quick-search overlay UI.
- Implement formatting engines (APA, MLA, Chicago) to copy citations to the clipboard.