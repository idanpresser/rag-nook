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


def test_multimodal_segment_indexing():
    indexer = ChromaDBIndexer(in_memory=True)

    messages = [
        {
            "sender": "Idan P",
            "media_type": "image",
            "content": "[OCR Text extracted from receipt.jpg]: milk: 5$, eggs: 3$",
            "summary": "a yellow store receipt",
            "attachments": ["receipt.jpg"]
        },
        {
            "sender": "Idan P",
            "media_type": "text",
            "content": "[Parsed Contact Card EMobile.vcf]: Name: EMobile Clinic, Phones: 048533420",
            "attachments": ["EMobile.vcf"]
        }
    ]

    indexer.index_segment(
        segment_id="seg-1",
        document_text="Regular conversation log content.",
        start_time="2024-03-01T06:56:00Z",
        end_time="2024-03-01T06:57:00Z",
        messages=messages,
        tags=["receipt", "clinic"]
    )

    # 1. Verify semantic search finds image description and OCR text
    res_vlm = indexer.query("yellow receipt", limit=1)
    assert len(res_vlm["ids"][0]) == 1
    assert res_vlm["ids"][0][0] == "seg-1"
    assert "yellow store receipt" in res_vlm["documents"][0][0]

    res_ocr = indexer.query("milk eggs price", limit=1)
    assert len(res_ocr["ids"][0]) == 1
    assert res_ocr["ids"][0][0] == "seg-1"
    assert "milk: 5$" in res_ocr["documents"][0][0]

    # 2. Verify metadata filtering works for multimodal flags
    res_filter_contacts = indexer.query("Clinic", limit=1, where_filter={"has_contacts": 1})
    assert len(res_filter_contacts["ids"][0]) == 1
    assert "EMobile Clinic" in res_filter_contacts["documents"][0][0]

    res_filter_images = indexer.query("receipt", limit=1, where_filter={"has_images": 1})
    assert len(res_filter_images["ids"][0]) == 1
    assert "receipt.jpg" in res_filter_images["documents"][0][0]

