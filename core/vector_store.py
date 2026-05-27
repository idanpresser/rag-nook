import chromadb
from typing import List, Optional, Dict, Any
from config import config

class ChromaDBIndexer:
    """A modular indexer wrapper for ChromaDB.

    Supports ephemeral testing instances, persistent local databases, document embedding, and hybrid queries.
    """

    def __init__(self, in_memory: bool = False):
        """Initializes the ChromaDB client and sets up the collection.

        Args:
            in_memory: If True, boots up an in-memory client for testing. Otherwise, uses persistent local storage.
        """
        if in_memory:
            self.client = chromadb.EphemeralClient()
        else:
            self.client = chromadb.PersistentClient(path=str(config.vector_db_dir))
            
        # Get or create the main chat collection
        self.collection = self.client.get_or_create_collection(name="whatsapp_chat")

    def add_documents(
        self,
        documents: List[str],
        ids: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """Adds text documents, unique identifiers, and structured metadata to the collection.

        Args:
            documents: A list of clean text chunk strings.
            ids: A list of unique ID strings matching each document chunk.
            metadatas: A list of dictionaries containing keys like sender, date, has_links.
        """
        if not documents:
            return
            
        self.collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )

    def query(
        self,
        query_text: str,
        limit: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Performs a semantic query on the vector collection with optional metadata filters.

        Args:
            query_text: The user's query search string.
            limit: The maximum number of results to return.
            where_filter: A ChromaDB metadata filter dictionary (e.g., {"sender": "Idan P"}).

        Returns:
            A dictionary containing lists of matching ids, documents, metadatas, and distances.
        """
        return self.collection.query(
            query_texts=[query_text],
            n_results=limit,
            where=where_filter
        )

    def index_segment(
        self,
        segment_id: str,
        document_text: str,
        start_time: str,
        end_time: str,
        messages: List[Dict[str, Any]],
        tags: List[str]
    ) -> None:
        """Serializes and indexes a conversation segment, compiling VLM/OCR text and contact info

        directly into the searchable document content and indexing filterable metadata fields.
        """
        has_images = False
        has_contacts = False
        image_summaries = []
        ocr_texts = []
        contact_names = []

        for msg in messages:
            m_type = msg.get("media_type", "text")
            attachments = msg.get("attachments", []) or []
            
            if m_type == "image" or any(att.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic')) for att in attachments):
                has_images = True
                if msg.get("summary"):
                    image_summaries.append(msg["summary"])
                content = msg.get("content", "")
                if "[OCR Text extracted" in content:
                    ocr_texts.append(content)
                    
            elif m_type == "document" or any(att.lower().endswith(".vcf") for att in attachments):
                for att in attachments:
                    if att.lower().endswith(".vcf"):
                        has_contacts = True
                        content = msg.get("content", "")
                        if "Name:" in content:
                            contact_names.append(content)

        metadata = {
            "segment_id": segment_id,
            "start_time": start_time,
            "end_time": end_time,
            "has_links": int(any(msg.get("media_type") == "link" for msg in messages)),
            "has_images": int(has_images),
            "has_contacts": int(has_contacts),
            "tags": ", ".join(tags)
        }

        # Build fully enriched document string to embed OCR & VLM
        full_doc = document_text
        if image_summaries:
            full_doc += "\n[Image Summaries]: " + " | ".join(image_summaries)
        if ocr_texts:
            full_doc += "\n[Image OCR Texts]: " + " | ".join(ocr_texts)
        if contact_names:
            full_doc += "\n[Contact Cards]: " + " | ".join(contact_names)

        self.collection.upsert(
            documents=[full_doc],
            ids=[segment_id],
            metadatas=[metadata]
        )

