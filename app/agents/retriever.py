# retriever.py

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

import requests
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# -------------------------------------------------------------------
# Setup
# -------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("RetrieverAgent")

# Your NewsAPI key (from the user message)
# NOTE: For production, prefer putting this in a .env file instead.
DEFAULT_NEWS_API_KEY = "680286aa3baf471abf746a64cab5e435"


# -------------------------------------------------------------------
# Retriever Agent
# -------------------------------------------------------------------

class RetrieverAgent:
    """
    Handles:
      - Fetching fresh articles from NewsAPI
      - Storing them in a Chroma vector DB
      - Retrieving relevant articles for a query
    """

    def __init__(
        self,
        collection_name: str = "aithena_articles",
        db_path: str = "./chroma_db",
        top_k: int = 5,
        embedding_model: str = "all-MiniLM-L6-v2",
        news_api_key: Optional[str] = None,
    ):
        """
        :param collection_name: Name of the ChromaDB collection
        :param db_path: Path for persistent Chroma storage
        :param top_k: Default number of results to retrieve
        :param embedding_model: SentenceTransformers model name
        :param news_api_key: Optional override for the NewsAPI key
        """
        self.collection_name = collection_name
        self.db_path = db_path
        self.top_k = top_k

        # Embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.model = SentenceTransformer(embedding_model)

        # Chroma persistent client
        logger.info(f"Initializing ChromaDB at: {db_path}")
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # NewsAPI key resolution:
        # passed in arg > env vars > default hard-coded key
        self.news_api_key = (
            news_api_key
            or os.getenv("NEWS_API_KEY")
            or os.getenv("NEWSAPI_KEY")
            or DEFAULT_NEWS_API_KEY
        )

        if not self.news_api_key:
            logger.warning(
                "No NewsAPI key found. Set NEWS_API_KEY in .env or pass news_api_key explicitly."
            )
        else:
            logger.info("NewsAPI key loaded successfully.")

    # -------------------------------------------------------------------
    # Embedding helpers
    # -------------------------------------------------------------------

    def _embed_text(self, texts: List[str]):
        """Compute embeddings for a list of texts."""
        return self.model.encode(texts, convert_to_numpy=True).tolist()

    # -------------------------------------------------------------------
    # NewsAPI fetching
    # -------------------------------------------------------------------

    def fetch_fresh_articles(self, topics: List[str]) -> List[Dict]:
        """
        Fetch fresh news articles from NewsAPI for given topics.

        Uses the /v2/top-headlines endpoint for US headlines and
        filters with `q=topic` for each topic.

        Returns list of dicts:
          {
            "id": str,
            "title": str,
            "text": str,
            "date": str (ISO),
            "topics": List[str],
            "source": str,
            "url": str,
          }
        """
        if not self.news_api_key:
            logger.error("Cannot fetch articles: NewsAPI key is not set.")
            return []

        base_url = "https://newsapi.org/v2/top-headlines"
        all_articles: List[Dict] = []

        logger.info(f"Fetching fresh articles for topics: {topics}")

        for topic in topics:
            params = {
                "country": "us",
                "q": topic,         # topic filter (optional but useful)
                "pageSize": 20,     # max 20 per topic
                "apiKey": self.news_api_key,
            }

            try:
                response = requests.get(base_url, params=params, timeout=10)
                if response.status_code != 200:
                    logger.warning(
                        f"NewsAPI error for topic '{topic}': "
                        f"{response.status_code} {response.text}"
                    )
                    continue

                data = response.json()
                articles = data.get("articles", [])

                logger.info(f"Fetched {len(articles)} articles for topic '{topic}'")

                for idx, article in enumerate(articles):
                    title = article.get("title") or ""
                    desc = article.get("description") or ""
                    content = article.get("content") or ""
                    text = (desc + "\n\n" + content).strip() or desc or content

                    if not title and not text:
                        # Skip empty articles
                        continue

                    pub_date = article.get("publishedAt") or datetime.utcnow().isoformat()
                    source_name = (
                        article.get("source", {}).get("name") or "NewsAPI"
                    )

                    article_id = f"newsapi_{topic}_{idx}_{int(datetime.utcnow().timestamp())}"

                    all_articles.append(
                        {
                            "id": article_id,
                            "title": title,
                            "text": text,
                            "date": pub_date,
                            "topics": [topic],
                            "source": source_name,
                            "url": article.get("url") or "",
                        }
                    )

            except Exception as e:
                logger.exception(f"Error fetching from NewsAPI for topic '{topic}': {e}")

        logger.info(f"Total fresh articles fetched: {len(all_articles)}")
        return all_articles

    # -------------------------------------------------------------------
    # Vector store operations
    # -------------------------------------------------------------------

    def upsert_articles(self, articles: List[Dict]) -> None:
        """
        Insert or update a batch of articles into ChromaDB.

        Each article dict must have keys:
          - id
          - title
          - text
          - date
          - topics
          - source
          - url
        """
        if not articles:
            logger.info("No articles to upsert.")
            return

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict] = []

        for art in articles:
            ids.append(art["id"])
            # Document used for semantic search
            doc_text = f"{art.get('title', '')}\n\n{art.get('text', '')}"
            documents.append(doc_text)

            metadatas.append(
                {
                    "title": art.get("title", ""),
                    "date": art.get("date", ""),
                    # Chroma metadata must be primitive types (str/int/float/bool).
                    # Store topics as a comma-separated string.
                    "topics": ",".join(art.get("topics", [])) if art.get("topics") else "",
                    "source": art.get("source", ""),
                    "url": art.get("url", ""),
                }
            )

        logger.info(f"Computing embeddings for {len(documents)} documents...")
        embeddings = self._embed_text(documents)

        logger.info(f"Upserting {len(ids)} articles into collection '{self.collection_name}'")
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        """
        Retrieve the top_k most relevant articles for the given query.

        Returns list of dicts with:
          {
            "id": str,
            "score": float,
            "title": str,
            "text": str,
            "date": str,
            "topics": List[str],
            "source": str,
            "url": str,
          }
        """
        if not query:
            return []

        if top_k is None:
            top_k = self.top_k

        logger.info(f"Retrieving top {top_k} articles for query: {query!r}")
        query_emb = self._embed_text([query])[0]

        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
        )

        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]  # cosine distance (lower is better)

        retrieved: List[Dict] = []
        for i, doc_id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            score = 1.0 - dists[i] if i < len(dists) else None  # convert distance to similarity

            retrieved.append(
                {
                    "id": doc_id,
                    "score": score,
                    "title": meta.get("title", ""),
                    "text": docs[i] if i < len(docs) else "",
                    "date": meta.get("date", ""),
                    "topics": meta.get("topics", []),
                    "source": meta.get("source", ""),
                    "url": meta.get("url", ""),
                }
            )

        return retrieved

    # -------------------------------------------------------------------
    # Convenience method: one-shot refresh
    # -------------------------------------------------------------------

    def fetch_and_index(self, topics: List[str]) -> List[Dict]:
        """
        Convenience method:
          1. Fetch fresh articles for given topics.
          2. Upsert them into the vector store.
          3. Return the list of fetched articles.
        """
        fresh = self.fetch_fresh_articles(topics)
        self.upsert_articles(fresh)
        return fresh

    def retrieve_by_preference(self, user_preferences: List[str], top_k: Optional[int] = None) -> Dict[str, List[Dict]]:
        """
        Compatibility wrapper used by the pipeline.

        For each preference:
          - fetch fresh articles
          - upsert them into the vector store
          - run a semantic query to retrieve top-k results

        Returns a mapping from preference to list of retrieved article dicts.
        """
        # Step 1: fetch and index fresh articles
        fresh = self.fetch_fresh_articles(user_preferences)
        if fresh:
            try:
                self.upsert_articles(fresh)
            except Exception:
                logger.exception("Error upserting fresh articles into Chroma")

        # Step 2: retrieve per preference
        results: Dict[str, List[Dict]] = {}
        for pref in user_preferences:
            query = f"news about {pref} for professionals"
            try:
                articles = self.retrieve(query, top_k=top_k)
            except Exception:
                logger.exception(f"Error retrieving articles for preference: {pref}")
                articles = []
            results[pref] = articles

        logger.info(f"Retrieved articles for {len(user_preferences)} preferences")
        return results


# -------------------------------------------------------------------
# Quick manual test
# -------------------------------------------------------------------

if __name__ == "__main__":
    # Example usage / smoke test
    agent = RetrieverAgent()

    topics = ["technology", "politics", "business"]
    new_articles = agent.fetch_and_index(topics)

    print(f"Fetched and indexed {len(new_articles)} new articles.")

    results = agent.retrieve("federal interest rates and inflation", top_k=3)
    print("\nSample retrieval results:")
    for r in results:
        print(f"- [{r['score']:.4f}] {r['title']} ({r['source']})")
        print(f"  {r['url']}")
