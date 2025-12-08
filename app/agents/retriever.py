"""
Retriever Agent
Queries the Chroma vector store using user preferences and returns top-K relevant articles.
"""

import logging
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class RetrieverAgent:
    """Retrieve articles from the vector store based on user preferences."""

    def __init__(
        self,
        collection_name: str = "aithena_articles",
        db_path: str = "./chroma_db",
        top_k: int = 5,
    ):
        """
        Initialize the Retriever Agent.
        
        Args:
            collection_name: Chroma collection name
            db_path: Path to Chroma database
            top_k: Number of top results to return
        """
        self.top_k = top_k
        self.collection_name = collection_name
        
        # Connect to Chroma
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=db_path,
            anonymized_telemetry=False,
        )
        self.client = chromadb.Client(settings)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        logger.info(f"Retriever connected to collection: {collection_name}")

    def retrieve(
        self,
        query: str,
        user_preferences: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """
        Retrieve articles matching a query, optionally filtered by user preferences.
        
        Args:
            query: Search query (often constructed from user preferences)
            user_preferences: List of user interests (e.g., ["politics", "finance", "technology"])
            top_k: Override default top_k
            
        Returns:
            List of retrieved articles with scores
        """
        if top_k is None:
            top_k = self.top_k
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
            )
            
            retrieved = []
            if results and results.get("ids"):
                for idx, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][idx] if results.get("distances") else 0.0
                    score = 1.0 - distance  # Convert distance to similarity score
                    
                    metadata = results["metadatas"][0][idx] if results.get("metadatas") else {}
                    document = results["documents"][0][idx] if results.get("documents") else ""
                    
                    retrieved.append({
                        "id": doc_id,
                        "content": document,
                        "score": score,
                        "metadata": metadata,
                    })
            
            logger.info(f"Retrieved {len(retrieved)} articles for query: {query[:50]}")
            return retrieved
        
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return []

    def retrieve_by_preference(
        self,
        user_preferences: List[str],
        top_k: Optional[int] = None,
    ) -> Dict[str, List[Dict]]:
        """
        Retrieve articles for each user preference.
        
        Args:
            user_preferences: List of user interests (e.g., ["politics", "finance", "technology"])
            top_k: Override default top_k
            
        Returns:
            Dictionary mapping preference to list of retrieved articles
        """
        results = {}
        
        for pref in user_preferences:
            # Build preference-aware query
            query = f"news about {pref} for professionals"
            articles = self.retrieve(query, top_k=top_k)
            results[pref] = articles
        
        logger.info(f"Retrieved articles for {len(user_preferences)} preferences")
        return results

    def get_collection_stats(self) -> Dict:
        """Get stats about the vector store."""
        return {
            "collection_name": self.collection_name,
            "total_documents": self.collection.count(),
        }
