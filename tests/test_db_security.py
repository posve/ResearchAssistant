import pytest
from db import DatabaseManager

@pytest.fixture
def db_manager():
    # Use an in-memory database for testing
    db = DatabaseManager(":memory:")
    yield db
    db.close()

def test_fts5_sql_injection_prevention(db_manager):
    # Add a dummy document
    doc_id = db_manager.add_document("doc1.pdf", "doc1.pdf", {"title": "Test Doc"}, "machine learning is fun")
    assert doc_id is not None

    # Test a query that would normally cause an fts5 syntax error
    # e.g., sqlite3.OperationalError: fts5: syntax error near """
    malicious_query = 'machine " OR 1=1 --'

    # This should not raise an exception
    try:
        results = db_manager.search(malicious_query)
    except Exception as e:
        pytest.fail(f"Search raised an exception with malicious query: {e}")

    # No exception was raised, the query executed safely.
    # We should get 0 results for this query because it searches for literally those terms including the quotes and OR
    assert len(results) == 0

def test_fts5_normal_search(db_manager):
    db_manager.add_document("doc1.pdf", "doc1.pdf", {"title": "Test Doc"}, "machine learning is fun")

    # Ensure normal search still works
    results = db_manager.search("machine learning")
    assert len(results) == 1
    assert results[0]['filename'] == "doc1.pdf"
