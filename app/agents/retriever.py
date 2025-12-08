"""
Retriever Agent
Fetches fresh articles from external sources, updates the vector store, and retrieves relevant articles.
"""

import logging
from typing import List, Dict, Optional
import os
import chromadb
from sentence_transformers import SentenceTransformer
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RetrieverAgent:
    """Fetch fresh articles, update vector store, and retrieve articles based on user preferences."""

    def __init__(
        self,
        collection_name: str = "aithena_articles",
        db_path: str = "./chroma_db",
        top_k: int = 5,
        embedding_model: str = "all-MiniLM-L6-v2",
        news_api_key: Optional[str] = None,
    ):
        """
        Initialize the Retriever Agent.
        
        Args:
            collection_name: Chroma collection name
            db_path: Path to Chroma database
            top_k: Number of top results to return
            embedding_model: Name of sentence-transformers embedding model
            news_api_key: Optional API key for NewsAPI.org (defaults to env var NEWS_API_KEY)
        """
        self.top_k = top_k
        self.collection_name = collection_name
        # Use provided key, fallback to .env, default to None
        self.news_api_key = news_api_key or os.getenv("NEWS_API_KEY")
        
        # Initialize embedding model for new articles
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Connect to Chroma (new API)
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)
        logger.info(f"Retriever connected to collection: {collection_name}")


    def fetch_fresh_articles(self, topics: List[str]) -> List[Dict]:
        """
        Fetch fresh articles from NewsAPI.org for the given topics.
        Falls back to mock data if API key is not available.
        
        Args:
            topics: List of topics to fetch articles for (e.g., ["politics", "finance", "technology"])
            
        Returns:
            List of fresh articles with id, title, text, date, topics, source, url
        """
        fresh_articles = []
        
        if self.news_api_key:
            # Fetch from NewsAPI.org
            for topic in topics:
                try:
                    url = "https://newsapi.org/v2/everything"
                    params = {
                        "q": topic,
                        "apiKey": self.news_api_key,
                        "pageSize": 5,
                        "sortBy": "publishedAt",
                    }
                    response = requests.get(url, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        for article in data.get("articles", []):
                            fresh_articles.append({
                                "id": f"{topic}_{len(fresh_articles)}",
                                "title": article.get("title", ""),
                                "text": article.get("description", "") or article.get("content", ""),
                                "date": article.get("publishedAt", datetime.now().isoformat()),
                                "topics": [topic],
                                "source": article.get("source", {}).get("name", "Unknown"),
                                "url": article.get("url", ""),
                            })
                except Exception as e:
                    logger.warning(f"Error fetching from NewsAPI for topic {topic}: {e}")
        else:
            # Fall back to mock articles (for testing without API key)
            logger.info("No NewsAPI key provided; using mock articles for demonstration")
            fresh_articles = self._get_mock_articles(topics)
        
        logger.info(f"Fetched {len(fresh_articles)} fresh articles from external source")
        return fresh_articles

    def _get_mock_articles(self, topics: List[str]) -> List[Dict]:
        """
        Generate mock articles for testing and demonstration.
        Replace this with real API calls when you have a NewsAPI.org key.
        
        Args:
            topics: List of topics
            
        Returns:
            List of mock articles
        """
        mock_data = {
            "politics": [
                {
                    "id": "politics_001",
                    "title": "Congress Debates New Tech Regulation Bill",
                    "text": "Senate committee advances comprehensive tech regulation addressing data privacy, algorithmic transparency, and AI governance. Industry experts divided on feasibility.",
                    "date": datetime.now().isoformat(),
                    "topics": ["politics"],
                    "source": "Political Times",
                    "url": "https://example.com/politics/001",
                },
                {
                    "id": "politics_002",
                    "title": "Election Year Brings Focus to Digital Rights",
                    "text": "As 2024 approaches, candidates increasingly highlight digital privacy and net neutrality in campaign platforms. Tech executives respond with policy papers.",
                    "date": datetime.now().isoformat(),
                    "topics": ["politics"],
                    "source": "Gov News",
                    "url": "https://example.com/politics/002",
                },
            ],
            "finance": [
                {
                    "id": "finance_001",
                    "title": "Tech Stocks Rally on AI Breakthroughs",
                    "text": "Major technology companies see stock gains following announcements of advanced AI models. Investors reassess tech sector valuations amid renewed optimism.",
                    "date": datetime.now().isoformat(),
                    "topics": ["finance"],
                    "source": "Finance Daily",
                    "url": "https://example.com/finance/001",
                },
                {
                    "id": "finance_002",
                    "title": "Central Banks Maintain Interest Rates Amid Inflation Concerns",
                    "text": "Federal Reserve and international central banks hold rates steady despite persistent inflation. Markets await next quarterly policy review.",
                    "date": datetime.now().isoformat(),
                    "topics": ["finance"],
                    "source": "Economic Times",
                    "url": "https://example.com/finance/002",
                },
            ],
            "technology": [
                {
                    "id": "technology_001",
                    "title": "OpenAI Releases GPT-5 with Enhanced Reasoning Capabilities",
                    "text": "Latest model demonstrates improved performance on complex reasoning tasks and multimodal understanding. Early adopters report significant productivity gains.",
                    "date": datetime.now().isoformat(),
                    "topics": ["technology"],
                    "source": "Tech Review",
                    "url": "https://example.com/tech/001",
                },
                {
                    "id": "technology_002",
                    "title": "Quantum Computing Achieves Practical Advantage in Drug Discovery",
                    "text": "IBM and pharma companies announce breakthrough in using quantum computers for molecular simulation. Implications for drug development timeline acceleration.",
                    "date": datetime.now().isoformat(),
                    "topics": ["technology"],
                    "source": "Science & Tech",
                    "url": "https://example.com/tech/002",
                },
            ],
        }
        
        articles = []
        for topic in topics:
            articles.extend(mock_data.get(topic, []))
        return articles

    def update_database_with_articles(self, articles: List[Dict]) -> int:
        """
        Add fresh articles to the vector store with embeddings.
        
        Args:
            articles: List of articles to add (each with id, title, text, metadata)
            
        Returns:
            Number of articles successfully added
        """
        if not articles:
            logger.info("No articles to add to database")
            return 0
        
        ids = []
        documents = []
        metadatas = []
        
        for article in articles:
            article_id = article.get("id", "")
            
            # Skip if article already exists in collection
            try:
                existing = self.collection.get(ids=[article_id])
                if existing and existing.get("ids") and len(existing["ids"]) > 0:
                    logger.debug(f"Article {article_id} already in database, skipping")
                    continue
            except Exception:
                pass  # Article doesn't exist, proceed
            
            # Combine title and text for embedding
            full_text = f"{article.get('title', '')} {article.get('text', '')}"
            
            ids.append(article_id)
            documents.append(full_text)
            metadatas.append({
                "title": article.get("title", ""),
                "date": article.get("date", ""),
                "source": article.get("source", ""),
                "url": article.get("url", ""),
                "topics": ",".join(article.get("topics", [])),
            })
        
        if ids:
            try:
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
                logger.info(f"✅ Added {len(ids)} fresh articles to vector store")
                return len(ids)
            except Exception as e:
                logger.error(f"Error adding articles to collection: {e}")
                return 0
        
        return 0

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
        Fetch fresh articles for each user preference, update the database, then retrieve results.
        
        This is the main method that orchestrates the RAG workflow:
        1. Fetch fresh articles from external source
        2. Update vector store with new articles
        3. Query for articles matching each preference
        
        Args:
            user_preferences: List of user interests (e.g., ["politics", "finance", "technology"])
            top_k: Override default top_k
            
        Returns:
            Dictionary mapping preference to list of retrieved articles
        """
        # Step 1: Fetch fresh articles from external sources
        fresh_articles = self.fetch_fresh_articles(user_preferences)
        
        # Step 2: Update the vector store with fresh articles
        self.update_database_with_articles(fresh_articles)
        
        # Step 3: Retrieve articles for each preference
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
