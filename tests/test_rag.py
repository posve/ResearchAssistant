import pytest
from unittest.mock import patch
import chromadb
from rag import RAGManager

@pytest.fixture
def ephemeral_chroma_client():
    """Returns an in-memory ephemeral client for testing."""
    return chromadb.EphemeralClient()

@pytest.fixture
def rag_manager(ephemeral_chroma_client):
    """Fixture that provides a RAGManager backed by an ephemeral ChromaDB client."""
    with patch('chromadb.PersistentClient', return_value=ephemeral_chroma_client):
        # We also need to patch out the persistence behavior, but EphemeralClient works similarly
        # so simply returning it from the PersistentClient constructor mock is enough.
        manager = RAGManager(db_path="test_db")
        yield manager

def test_add_document_happy_path(rag_manager):
    """Test adding a normal document successfully."""
    text = "This is the first sentence. This is the second sentence. " * 50  # Make it long enough to maybe chunk, though 1000 limit is high.

    rag_manager.add_document("test/path.pdf", "path.pdf", text)

    # Assert it was added
    assert rag_manager.is_indexed("test/path.pdf")

    # Assert collection size
    results = rag_manager.collection.get(where={"filepath": "test/path.pdf"})
    assert len(results["ids"]) > 0
    assert results["metadatas"][0]["filename"] == "path.pdf"

def test_add_document_empty(rag_manager):
    """Test adding an empty document."""
    rag_manager.add_document("test/empty.pdf", "empty.pdf", "")

    # Assert it was NOT added
    assert not rag_manager.is_indexed("test/empty.pdf")

    # Assert nothing with this filepath is in the collection
    results = rag_manager.collection.get(where={"filepath": "test/empty.pdf"})
    assert len(results["ids"]) == 0

def test_add_document_already_indexed(rag_manager):
    """Test adding a document that is already indexed is skipped."""
    text = "Some text to index."

    # Add first time
    rag_manager.add_document("test/dup.pdf", "dup.pdf", text)

    # Get initial size
    initial_results = rag_manager.collection.get(where={"filepath": "test/dup.pdf"})
    initial_count = len(initial_results["ids"])
    assert initial_count > 0

    # Add second time
    rag_manager.add_document("test/dup.pdf", "dup.pdf", text + " EXTRA TEXT THAT SHOULD BE IGNORED")

    # Assert size hasn't changed and text wasn't updated
    final_results = rag_manager.collection.get(where={"filepath": "test/dup.pdf"})
    assert len(final_results["ids"]) == initial_count
    assert "EXTRA TEXT" not in final_results["documents"][0]

def test_add_document_minimal_text(rag_manager):
    """Test adding a very small document."""
    text = "Word"

    rag_manager.add_document("test/min.pdf", "min.pdf", text)

    assert rag_manager.is_indexed("test/min.pdf")
    results = rag_manager.collection.get(where={"filepath": "test/min.pdf"})
    assert len(results["ids"]) == 1
    assert results["documents"][0] == "Word"

def test_add_document_long_unbreakable_text(rag_manager):
    """Test adding a document with one very long word without spaces."""
    # RAGManager chunk size is 1000
    text = "A" * 2500

    rag_manager.add_document("test/long.pdf", "long.pdf", text)

    assert rag_manager.is_indexed("test/long.pdf")
    results = rag_manager.collection.get(where={"filepath": "test/long.pdf"})

    # It should have been split into chunks of ~1000 chars (with overlap)
    assert len(results["ids"]) > 1
    # Check that lengths are around the chunk size (1000) or less
    for doc in results["documents"]:
        assert len(doc) <= 1000

def test_add_document_exact_chunk_size(rag_manager):
    """Test adding a document that is exactly the chunk size."""
    # RAGManager chunk size is 1000
    text = "B" * 1000

    rag_manager.add_document("test/exact.pdf", "exact.pdf", text)

    assert rag_manager.is_indexed("test/exact.pdf")
    results = rag_manager.collection.get(where={"filepath": "test/exact.pdf"})

    assert len(results["ids"]) == 1
    assert len(results["documents"][0]) == 1000
    assert results["documents"][0] == text
