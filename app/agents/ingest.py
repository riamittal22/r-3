"""
RAG Database Ingest Module
Loads aithena_articles.jsonl into Chroma vector store with embeddings.
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class RAGIngestor:
    """Ingest articles from JSONL into a Chroma vector store for retrieval."""

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "aithena_articles",
        db_path: str = "./chroma_db",
    ):
        """
        Initialize the RAG ingestor.
        
        Args:
            embedding_model: HuggingFace sentence-transformers model name
            collection_name: Chroma collection name
            db_path: Path to store Chroma persistence
        """
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        self.db_path = db_path
        
        # Load embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Initialize Chroma client
        os.makedirs(db_path, exist_ok=True)
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=db_path,
            anonymized_telemetry=False,
        )
        self.client = chromadb.Client(settings)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Chroma collection initialized: {collection_name}")

    def load_jsonl(self, jsonl_path: str) -> List[Dict]:
        """Load articles from JSONL file."""
        articles = []
        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        articles.append(json.loads(line))
        except Exception as e:
            logger.error(f"Error loading JSONL: {e}")
            return []
        
        logger.info(f"Loaded {len(articles)} articles from {jsonl_path}")
        return articles

    def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """
        Chunk text into overlapping segments for embedding.
        
        Args:
            text: Text to chunk
            chunk_size: Approximate chunk size in chars
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        chunks = []
        if len(text) <= chunk_size:
            return [text]
        
        step = chunk_size - overlap
        for i in range(0, len(text), step):
            chunk = text[i : i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks

    def ingest(self, jsonl_path: str, skip_existing: bool = True) -> int:
        """
        Ingest articles from JSONL into the vector store.
        
        Args:
            jsonl_path: Path to JSONL file
            skip_existing: If True, skip articles already in the collection
            
        Returns:
            Number of articles ingested
        """
        articles = self.load_jsonl(jsonl_path)
        if not articles:
            logger.warning(f"No articles to ingest from {jsonl_path}")
            return 0
        
        ingested_count = 0
        
        for idx, article in enumerate(articles):
            try:
                article_id = str(article.get("id", idx))
                
                # Skip if already exists
                if skip_existing:
                    try:
                        existing = self.collection.get(ids=[article_id])
                        if existing["ids"]:
                            logger.debug(f"Article {article_id} already exists, skipping")
                            continue
                    except Exception:
                        pass
                
                # Extract text content
                title = article.get("title", "")
                content = article.get("content", "") or article.get("text", "")
                source = article.get("source", "")
                
                # Create chunks
                chunks = self.chunk_text(content, chunk_size=512, overlap=50)
                
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_id = f"{article_id}_chunk_{chunk_idx}"
                    
                    # Create embedding
                    embedding = self.embedding_model.encode(chunk).tolist()
                    
                    # Add to collection
                    self.collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding],
                        metadatas=[{
                            "article_id": article_id,
                            "title": title,
                            "source": source,
                            "chunk_index": chunk_idx,
                            "total_chunks": len(chunks),
                        }],
                        documents=[chunk],
                    )
                
                ingested_count += 1
                if (idx + 1) % 100 == 0:
                    logger.info(f"Ingested {idx + 1} articles...")
                
            except Exception as e:
                logger.warning(f"Error ingesting article {idx}: {e}")
                continue
        
        logger.info(f"✅ Ingested {ingested_count} articles into Chroma")
        return ingested_count

    def get_collection_stats(self) -> Dict:
        """Get statistics about the current collection."""
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "total_documents": count,
            "embedding_model": self.embedding_model_name,
        }
