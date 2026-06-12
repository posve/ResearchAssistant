import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

class RAGManager:
    def __init__(self, db_path="library_vector_db"):
        self.db_path = db_path
        
        # Initialize ChromaDB client (persistent storage)
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # We will use the default MiniLM-L6-v2 embedding function built into Chroma
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create our document collection
        self.collection = self.client.get_or_create_collection(
            name="pdf_library",
            embedding_function=self.embedding_fn
        )
        
        # Set up a smart chunker that tries to split by paragraphs first, then sentences
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

    def is_indexed(self, filepath):
        """Check if a file's chunks are already in the vector DB."""
        results = self.collection.get(where={"filepath": filepath}, limit=1)
        return len(results['ids']) > 0

    def add_document(self, filepath, filename, full_text):
        """Chunks the document text and embeds it into ChromaDB."""
        if self.is_indexed(filepath):
            return  # Skip already indexed
            
        chunks = self.text_splitter.split_text(full_text)
        
        if not chunks:
            return

        ids = []
        metadatas = []
        documents = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filepath}_chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({"filepath": filepath, "filename": filename})
            
        # Add to ChromaDB (this generates embeddings automatically)
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, user_question, n_results=3):
        """Retrieve the most relevant chunks for a given question."""
        results = self.collection.query(
            query_texts=[user_question],
            n_results=n_results
        )
        
        # Return a list of dicts with context and source
        retrieved_contexts = []
        if results['documents'] and len(results['documents']) > 0:
            for idx, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][idx]
                retrieved_contexts.append({
                    "text": doc,
                    "filename": meta.get("filename", "Unknown")
                })
                
        return retrieved_contexts