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
