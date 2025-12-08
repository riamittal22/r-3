"""
Generate a daily HTML digest of articles from the RAG (Chroma) database.

This script will:
 - Read all documents from the configured Chroma collection
 - Group chunked documents into articles
 - Filter articles published in the last 24 hours
 - Summarize articles (falls back to excerpts if summarizer not available)
 - Rank and distribute articles by user preferences
 - Create and save an HTML digest using the EmailAgent

Usage: run from the project root:
    python scripts/generate_daily_html.py

"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import os
import argparse

from app.agents.ranker import RankerAgent
from app.agents.emailer import EmailAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_iso_date(s: str):
    if not s:
        return None
    try:
        # datetime.fromisoformat handles many ISO forms
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        try:
            # fallback: parse common datetime formats
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None


def aggregate_chunks(results: Dict) -> List[Dict]:
    """Group chunk documents returned from Chroma into per-article dicts."""
    articles = {}

    ids = results.get("ids") or []
    metadatas = results.get("metadatas") or []
    documents = results.get("documents") or []

    for idx, chunk_id in enumerate(ids):
        meta = metadatas[idx] if idx < len(metadatas) else {}
        doc = documents[idx] if idx < len(documents) else ""

        # Prefer explicit article_id in metadata, else derive from chunk id
        article_id = meta.get("article_id") or str(chunk_id).split("_chunk_")[0]

        if article_id not in articles:
            articles[article_id] = {
                "id": article_id,
                "title": meta.get("title") or meta.get("article_id") or article_id,
                "source": meta.get("source") or meta.get("source_name") or "Unknown",
                "chunks": [],
                "dates": [],
            }

        # Keep chunk ordering if provided
        try:
            chunk_index = int(meta.get("chunk_index", 0))
        except Exception:
            chunk_index = 0

        articles[article_id]["chunks"].append((chunk_index, doc))

        # Collect any date metadata
        date_field = meta.get("date") or meta.get("publishedAt") or meta.get("datetime")
        dt = parse_iso_date(date_field) if date_field else None
        if dt:
            articles[article_id]["dates"].append(dt)

    # Finalize articles: sort chunks and join
    final = []
    for aid, info in articles.items():
        chunks = sorted(info["chunks"], key=lambda x: x[0])
        content = "\n\n".join([c for _, c in chunks]) if chunks else ""
        # choose newest date if available
        date = max(info["dates"]) if info["dates"] else None

        final.append({
            "id": aid,
            "title": info.get("title", aid),
            "content": content,
            "source": info.get("source", "Unknown"),
            "date": date,
        })

    return final


def filter_last_24h(articles: List[Dict]) -> List[Dict]:
    cutoff = datetime.now(datetime.utcnow().astimezone().tzinfo) - timedelta(days=1)
    recent = []
    for a in articles:
        if a.get("date"):
            if a["date"] >= cutoff:
                recent.append(a)
        else:
            # If no date metadata, conservatively include (so nothing is missed)
            recent.append(a)
    return recent


def main(args):
    # Try to use the RetrieverAgent / Chroma DB. If chromadb or agent isn't available,
    # fall back to reading the local JSONL file (`aithena_articles.jsonl`).
    results = {"ids": [], "metadatas": [], "documents": []}
    retriever = None
    try:
        # Import RetrieverAgent lazily to avoid import-time chromadb dependency error
        from app.agents.retriever import RetrieverAgent
        retriever = RetrieverAgent(db_path=args.db_path)
        try:
            results = retriever.collection.get(include=["ids", "metadatas", "documents"], limit=None)
        except Exception as e:
            logger.warning(f"Could not read collection directly: {e}; attempting fallback get()")
            try:
                results = retriever.collection.get()
            except Exception as e2:
                logger.error(f"Failed to read Chroma collection: {e2}")
                results = {"ids": [], "metadatas": [], "documents": []}
    except Exception as e:
        logger.warning(f"RetrieverAgent unavailable (chromadb missing or init failed): {e}")
        # Fallback: read from JSONL
        jsonl_path = args.jsonl or "aithena_articles.jsonl"
        try:
            import json
            loaded = []
            if os.path.exists(jsonl_path):
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line or not line.strip():
                            continue
                        # strip BOM and whitespace
                        raw = line.lstrip('\ufeff').strip()
                        try:
                            loaded.append(json.loads(raw))
                        except Exception:
                            # try skipping surrounding characters and continue
                            try:
                                loaded.append(json.loads(raw.strip('\n\r')))
                            except Exception:
                                logger.debug(f"Skipping malformed JSONL line: {raw[:80]}")

            # Convert loaded articles into a pseudo-Chroma results structure
            ids = []
            metadatas = []
            documents = []
            for art in loaded:
                aid = str(art.get("id") or art.get("title") or len(ids))
                # store whole article as a single document
                ids.append(aid)
                documents.append((art.get("title", "") + "\n\n" + (art.get("content") or art.get("text") or "")))
                metadatas.append({
                    "title": art.get("title", ""),
                    "date": art.get("date") or art.get("publishedAt") or art.get("created_at"),
                    "source": art.get("source", "Unknown"),
                })

            results = {"ids": ids, "metadatas": metadatas, "documents": documents}
            logger.info(f"Loaded {len(ids)} articles from {jsonl_path} as fallback")
        except Exception as e2:
            logger.error(f"Failed to load fallback JSONL: {e2}")
            results = {"ids": [], "metadatas": [], "documents": []}

    aggregated = aggregate_chunks(results)
    logger.info(f"Aggregated {len(aggregated)} unique articles from vector store")

    recent = filter_last_24h(aggregated)
    logger.info(f"Found {len(recent)} articles in the last 24 hours")

    # Fallback: if none found, fetch fresh articles from RetrieverAgent
    if not recent:
        logger.info("No recent articles found in DB; fetching fresh mock/external articles")
        fresh = retriever.fetch_fresh_articles(args.preferences)
        # Convert to normalized structure
        recent = []
        for art in fresh:
            dt = parse_iso_date(art.get("date") or art.get("publishedAt") or "")
            recent.append({
                "id": art.get("id"),
                "title": art.get("title"),
                "content": art.get("text") or art.get("content") or "",
                "source": art.get("source", "Unknown"),
                "date": dt,
            })

    if not recent:
        logger.warning("No articles available to create digest; exiting")
        return

    # Summarize articles (use SummarizerAgent if available)
    summaries = []
    try:
        # Import the summarizer lazily to avoid import-time failures when transformers isn't installed
        try:
            from app.agents.summarizer import SummarizerAgent
        except Exception as ie:
            raise RuntimeError(f"Summarizer import failed: {ie}")

        summarizer = SummarizerAgent()
        # map structure: SummarizerAgent expects 'content' key
        for art in recent:
            summaries.append({
                "id": art.get("id"),
                "title": art.get("title"),
                "content": art.get("content", ""),
                "summary": summarizer.summarize(art.get("content", ""), style=args.summary_style),
                "metadata": {"title": art.get("title"), "source": art.get("source"), "date": art.get("date")},
            })
    except Exception as e:
        logger.warning(f"Summarizer not available or failed: {e}; falling back to excerpts")
        for art in recent:
            summaries.append({
                "id": art.get("id"),
                "title": art.get("title"),
                "content": art.get("content", ""),
                "summary": (art.get("content") or "")[:300],
                "metadata": {"title": art.get("title"), "source": art.get("source"), "date": art.get("date")},
            })

    # Rank & distribute articles by preference
    ranker = RankerAgent()
    # ranker.distribute_by_preference expects a list of article dicts
    distribution = ranker.distribute_by_preference(summaries, args.preferences)

    # Convert distribution to the shape expected by EmailAgent (articles with 'summary' and 'metadata')
    formatted = {}
    for pref, items in distribution.items():
        formatted[pref] = []
        for it in items:
            formatted[pref].append({
                "metadata": {"title": it.get("title"), "source": it.get("metadata", {}).get("source", it.get("source", "Unknown"))},
                "summary": it.get("summary"),
                "content": it.get("content", ""),
            })

    emailer = EmailAgent()
    html = emailer.create_html_digest(formatted, user_name=args.user_name)

    output_file = args.output or f"daily_news_{datetime.now().strftime('%Y%m%d')}.html"
    if emailer.save_digest(html, output_file):
        logger.info(f"Daily digest saved to {output_file}")
    else:
        logger.error("Failed to save daily digest")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate daily HTML digest from RAG DB")
    parser.add_argument("--db-path", default="./chroma_db", help="Path to Chroma DB folder")
    parser.add_argument("--preferences", nargs="+", default=["politics", "finance", "technology"], help="User preferences/topics")
    parser.add_argument("--output", default=None, help="Output HTML file path")
    parser.add_argument("--user-name", default="Reader", help="User name for personalization")
    parser.add_argument("--summary-style", default="brief", choices=["brief", "medium", "detailed"], help="Summary style")
    parser.add_argument("--jsonl", default="aithena_articles.jsonl", help="Fallback JSONL file to read articles from if Chroma isn't available")

    args = parser.parse_args()
    main(args)
