import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path="library.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Main documents table for metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                title TEXT,
                authors TEXT,
                year TEXT,
                doi TEXT
            )
        ''')

        # FTS5 virtual table for full-text search
        # Note: We use doc_id to link back to the documents table
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS document_texts 
            USING fts5(doc_id UNINDEXED, full_text)
        ''')
        
        self.conn.commit()

    def is_indexed(self, filepath):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE filepath = ?", (filepath,))
        return cursor.fetchone() is not None

    def add_document(self, filepath, filename, metadata, full_text):
        cursor = self.conn.cursor()
        
        try:
            # Insert metadata
            cursor.execute('''
                INSERT INTO documents (filepath, filename, title, authors, year, doi)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                filepath, 
                filename, 
                metadata.get('title'), 
                metadata.get('author'), 
                metadata.get('year'), 
                metadata.get('doi')
            ))
            
            doc_id = cursor.lastrowid
            
            # Insert full text into FTS table
            cursor.execute('''
                INSERT INTO document_texts (doc_id, full_text)
                VALUES (?, ?)
            ''', (doc_id, full_text))
            
            self.conn.commit()
            return doc_id
        except sqlite3.IntegrityError:
            # Document already exists, rollback and return None
            self.conn.rollback()
            return None

    def _sanitize_fts_query(self, query):
        if not query:
            return ""
        # Split by whitespace, escape double quotes, wrap each term in double quotes
        return " ".join('"{}"'.format(word.replace('"', '""')) for word in query.split())

    def search(self, query):
        cursor = self.conn.cursor()
        sanitized_query = self._sanitize_fts_query(query)

        # Using snippet to get context around the matched text
        cursor.execute('''
            SELECT 
                d.id, d.filepath, d.filename, d.title, d.authors, d.year, d.doi,
                snippet(document_texts, 1, '<b>', '</b>', '...', 64) as context
            FROM document_texts fts
            JOIN documents d ON fts.doc_id = d.id
            WHERE document_texts MATCH ?
            ORDER BY rank
        ''', (sanitized_query,))
        
        return [dict(row) for row in cursor.fetchall()]

    def get_all_documents(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents")
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()