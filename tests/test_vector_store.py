import pytest
import os
from core.vector_store import ChromaDBIndexer

def test_vector_store_operations():
    # Initialize indexer with ephemeral/in-memory configuration
    indexer = ChromaDBIndexer(in_memory=True)
    
    # Sample documents to index
    docs = [
        "מצעים פחים ברכה לאלון שמיכת כרית",
        "https://github.com/rohankishore/Youtility photo editor and developer tools",
        "Lungotevere dei Fiorentini, Roma travel plans and hotel bookings"
    ]
    
    ids = ["doc-1", "doc-2", "doc-3"]
    
    metadatas = [
        {"sender": "Idan P", "type": "text", "has_links": False},
        {"sender": "Idan P", "type": "link", "has_links": True},
        {"sender": "System", "type": "text", "has_links": False}
    ]
    
    # 1. Test indexing documents
    indexer.add_documents(docs, ids, metadatas)
    
    # 2. Test semantic query
    results = indexer.query("photo editor github tools", limit=1)
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "doc-2"
    assert "Youtility" in results["documents"][0][0]
    
    # 3. Test query with metadata filter (Idan P only)
    results_filter = indexer.query("Roma travel plans", limit=5, where_filter={"sender": "System"})
    assert len(results_filter["ids"][0]) == 1
    assert results_filter["ids"][0][0] == "doc-3"
    assert "Fiorentini" in results_filter["documents"][0][0]
