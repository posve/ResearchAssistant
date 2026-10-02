import time
import os
import sys
import shutil
import fitz
import sqlite3
import requests
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

from db import DatabaseManager
from rag import RAGManager

def benchmark_pdf_extraction(num_pages=50):
    print("--- 1. PyMuPDF Parsing Benchmark ---")
    doc = fitz.open()
    sample_text = (
        "10.1000/182 Quantum computing and research methodology in modern physics. "
        "Abstract: The fast brown fox jumps over the lazy dog. " * 50
    )
    for _ in range(num_pages):
        page = doc.new_page()
        page.insert_text((50, 50), sample_text)

    pdf_filename = "temp_benchmark.pdf"
    doc.save(pdf_filename)
    doc.close()

    start_time = time.perf_counter()
    read_doc = fitz.open(pdf_filename)
    full_text = ""
    for page in read_doc:
        full_text += page.get_text("text") + "\n"
    read_doc.close()
    elapsed = time.perf_counter() - start_time

    if os.path.exists(pdf_filename):
        os.remove(pdf_filename)

    pages_per_sec = num_pages / elapsed
    print(f"Parsed {num_pages} pages in {elapsed:.4f}s ({pages_per_sec:.2f} pages/sec)")
    return elapsed, pages_per_sec

def benchmark_crossref_api():
    print("\n--- 2. Crossref API Metadata Fetching Benchmark ---")
    doi = "10.1038/s41586-020-2649-2" # Nature paper DOI
    url = f"https://api.crossref.org/works/{doi}"

    latencies = []
    for i in range(3):
        start = time.perf_counter()
        try:
            resp = requests.get(url, timeout=5)
            elapsed = time.perf_counter() - start
            if resp.status_code == 200:
                latencies.append(elapsed)
                print(f"Request {i+1}: {elapsed*1000:.2f} ms")
        except Exception as e:
            print(f"Request {i+1} failed: {e}")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    print(f"Average Crossref HTTP GET latency: {avg_latency*1000:.2f} ms")
    return avg_latency

def benchmark_sqlite_fts(num_docs=100):
    print("\n--- 3. SQLite FTS5 Indexing & Search Benchmark ---")
    db_file = "temp_bench.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    db = DatabaseManager(db_file)

    # Measure per-doc commit insert (current implementation)
    start_time = time.perf_counter()
    for i in range(num_docs):
        metadata = {"title": f"Paper {i}", "author": "Alice & Bob", "year": "2024", "doi": f"10.1000/{i}"}
        text = f"Quantum error correction document sample {i} with additional context words."
        db.add_document(f"/path/doc_{i}.pdf", f"doc_{i}.pdf", metadata, text)
    per_doc_commit_time = time.perf_counter() - start_time

    # Measure batch commit insert
    db.close()
    if os.path.exists(db_file):
        os.remove(db_file)

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE documents (id INTEGER PRIMARY KEY AUTOINCREMENT, filepath TEXT UNIQUE, filename TEXT, title TEXT, authors TEXT, year TEXT, doi TEXT)''')
    cursor.execute('''CREATE VIRTUAL TABLE document_texts USING fts5(doc_id UNINDEXED, full_text)''')
    conn.commit()

    start_time = time.perf_counter()
    for i in range(num_docs):
        cursor.execute("INSERT INTO documents (filepath, filename, title, authors, year, doi) VALUES (?, ?, ?, ?, ?, ?)",
                       (f"/path/doc_{i}.pdf", f"doc_{i}.pdf", f"Paper {i}", "Alice & Bob", "2024", f"10.1000/{i}"))
        doc_id = cursor.lastrowid
        cursor.execute("INSERT INTO document_texts (doc_id, full_text) VALUES (?, ?)",
                       (doc_id, f"Quantum error correction document sample {i} with additional context words."))
    conn.commit()
    batch_commit_time = time.perf_counter() - start_time
    conn.close()

    # Measure Search Latency
    db = DatabaseManager(db_file)
    search_start = time.perf_counter()
    results = db.search("quantum error")
    search_time = time.perf_counter() - search_start
    db.close()

    if os.path.exists(db_file):
        os.remove(db_file)

    print(f"Individual Commits ({num_docs} docs): {per_doc_commit_time:.4f}s ({num_docs/per_doc_commit_time:.2f} docs/sec)")
    print(f"Batched Transaction ({num_docs} docs): {batch_commit_time:.4f}s ({num_docs/batch_commit_time:.2f} docs/sec)")
    print(f"FTS Search Query ('quantum error'): {search_time*1000:.2f} ms (Found {len(results)} items)")
    return per_doc_commit_time, batch_commit_time, search_time

def benchmark_chromadb(num_docs=10):
    print("\n--- 4. ChromaDB Chunking & Embedding Benchmark ---")
    vec_db_path = "temp_vec_db"
    if os.path.exists(vec_db_path):
        shutil.rmtree(vec_db_path)

    rag = RAGManager(vec_db_path)
    sample_text = ("This is a research document regarding artificial intelligence and quantum computing. " * 50)

    start_time = time.perf_counter()
    for i in range(num_docs):
        rag.add_document(f"/path/doc_{i}.pdf", f"doc_{i}.pdf", sample_text)
    elapsed = time.perf_counter() - start_time

    print(f"Indexed {num_docs} documents in ChromaDB sequentially: {elapsed:.4f}s ({num_docs/elapsed:.2f} docs/sec)")

    if os.path.exists(vec_db_path):
        shutil.rmtree(vec_db_path)
    return elapsed

if __name__ == "__main__":
    benchmark_pdf_extraction()
    benchmark_crossref_api()
    benchmark_sqlite_fts()
    benchmark_chromadb()
