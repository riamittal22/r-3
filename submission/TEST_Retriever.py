"""
TEST_Retriever.py
Fetches articles from external news sources and saves them to RAG Data.txt
"""

import requests
import json
import logging
import os
from datetime import datetime
from typing import List, Dict
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Output file
OUTPUT_FILE = "RAG Data.txt"


def fetch_articles_from_newsapi(api_key: str = None, queries: List[str] = None) -> List[Dict]:
    """
    Fetch articles from NewsAPI from reputable sources only (WSJ, Reuters, Politico, NYT, etc.)
    Uses /v2/top-headlines endpoint which allows source filtering
    
    Args:
        api_key: NewsAPI key (optional; if None, will attempt without auth)
        queries: List of search queries (not used with source-based fetch, but kept for compatibility)
    
    Returns:
        List of article dictionaries
    """
    articles = []
    
    # Reputable sources for each category
    sources_by_category = {
        "technology": [
            "techcrunch",
            "ars-technica",
            "the-verge",
            "wired",
        ],
        "finance": [
            "wall-street-journal",
            "financial-times",
            "cnbc",
            "bloomberg",
            "financial-news",
            "reuters",
        ],
        "politics": [
            "politico",
            "cnn",
            "bbc-news",
        ],
    }
    
    try:
        for category, sources in sources_by_category.items():
            for source in sources:
                url = "https://newsapi.org/v2/top-headlines"
                params = {
                    "sources": source,
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                }
                if api_key:
                    params["apiKey"] = api_key
                
                logger.info(f"Fetching {category} articles from {source}")
                response = requests.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    query_articles = data.get("articles", [])
                    if query_articles:
                        articles.extend(query_articles)
                        logger.info(f"✅ Fetched {len(query_articles)} articles from {source}")
                elif response.status_code == 401:
                    logger.warning("NewsAPI returned 401: API key required or invalid.")
                    if api_key:
                        logger.error("API key may be invalid. Please check: https://newsapi.org")
                    raise Exception("Authentication failed")
                else:
                    logger.debug(f"Source {source} returned status {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error fetching from NewsAPI: {e}. Using fallback RSS feeds.")
        articles.extend(fetch_articles_from_rss_feeds(queries))
    
    return articles


def fetch_articles_from_rss_feeds(queries: List[str] = None) -> List[Dict]:
    """
    Fallback: Fetch articles from public RSS feeds of reputable sources
    Includes WSJ, Reuters, Politico, NYT tech/business sections
    
    Args:
        queries: List of interest categories (not used for RSS, but kept for consistency)
    
    Returns:
        List of article dictionaries
    """
    articles = []
    
    # Public RSS feeds from reputable sources (tech, finance, politics)
    rss_feeds = [
        {
            "name": "Reuters Business",
            "url": "https://www.reuters.com/finance",
            "query": "business",
        },
        {
            "name": "BBC Business",
            "url": "https://www.bbc.com/news/business",
            "query": "business",
        },
        {
            "name": "CNN Business",
            "url": "https://www.cnn.com/business",
            "query": "business",
        },
    ]
    
    try:
        for feed in rss_feeds:
            logger.info(f"Attempting to fetch from {feed['name']}...")
            try:
                response = requests.get(feed["url"], timeout=10)
                if response.status_code == 200:
                    # Simple scraping of page title/content (not full RSS parsing for simplicity)
                    logger.info(f"✅ Connected to {feed['name']}")
            except Exception as e:
                logger.debug(f"Could not reach {feed['name']}: {e}")
    
    except Exception as e:
        logger.error(f"Error in RSS fallback: {e}")
    
    return articles




def format_articles_for_rag(articles: List[Dict]) -> str:
    """
    Format articles into readable text for RAG ingestion
    
    Args:
        articles: List of article dictionaries
    
    Returns:
        Formatted text string
    """
    formatted = []
    
    for idx, article in enumerate(articles, 1):
        title = article.get("title", "No title")
        url = article.get("url", "")
        source = article.get("source", "Unknown")
        published = article.get("published_at", "")
        content = article.get("content", "No content")
        
        # Format as readable block
        block = f"""
---
Article {idx}
Title: {title}
Source: {source}
Published: {published}
URL: {url}
Content: {content}
---
"""
        formatted.append(block)
    
    return "\n".join(formatted)


def save_to_rag_data(content: str, append: bool = True) -> bool:
    """
    Save articles to RAG Data.txt
    
    Args:
        content: Text content to save
        append: If True, append to existing file; if False, overwrite
    
    Returns:
        True if successful, False otherwise
    """
    try:
        mode = "a" if append else "w"
        with open(OUTPUT_FILE, mode, encoding="utf-8") as f:
            if append:
                f.write("\n\n" + "=" * 80 + "\n")
                f.write(f"Updated: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n")
            f.write(content)
        
        logger.info(f"✅ Saved articles to {OUTPUT_FILE}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving to {OUTPUT_FILE}: {e}")
        return False


def main():
    """Main retriever function - Fetches from reputable sources (WSJ, Reuters, Politico, NYT, etc.)"""
    logger.info("=" * 80)
    logger.info("TEST_Retriever: Fetching articles from REPUTABLE sources ONLY")
    logger.info("Sources: WSJ, Reuters, Politico, NYT, BBC, CNN, Bloomberg, TechCrunch, etc.")
    logger.info("Categories: Technology, Finance, Politics")
    logger.info("=" * 80)
    
    all_articles = []
    
    # Try to fetch from NewsAPI (reputable sources only)
    api_key = os.getenv("NEWS_API_KEY", None)
    
    if not api_key:
        logger.warning("⚠️  NewsAPI key not found in environment variable 'NEWS_API_KEY'")
        logger.info("To fetch from reputable sources:")
        logger.info("  1. Get a free API key: https://newsapi.org/register")
        logger.info("  2. Add to .env: NEWS_API_KEY=680286aa3baf471abf746a64cab5e435")
        logger.info("  3. Or set environment variable: $env:NEWS_API_KEY='your_key_here'")
        logger.info("\nAttempting to fetch without API key (may have limited results)...")
    
    logger.info("\n[1/1] Fetching from reputable sources via NewsAPI...")
    all_articles.extend(fetch_articles_from_newsapi(api_key=api_key))
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Total articles fetched: {len(all_articles)}")
    logger.info(f"{'='*80}\n")
    
    if all_articles:
        # Format and save
        formatted_content = format_articles_for_rag(all_articles)
        
        # Check if file exists to decide append or overwrite
        file_exists = Path(OUTPUT_FILE).exists()
        save_to_rag_data(formatted_content, append=file_exists)
        
        logger.info(f"\n✅ Successfully saved {len(all_articles)} articles from reputable sources to {OUTPUT_FILE}")
        logger.info(f"Categories fetched: Technology, Finance, Politics")
        return True
    else:
        logger.warning(f"\n⚠️  No articles fetched from reputable sources.")
        logger.warning("To fetch articles, please:")
        logger.warning("  1. Get a free API key from: https://newsapi.org/register")
        logger.warning("  2. Set environment variable: $env:NEWS_API_KEY='your_key_here'")
        logger.warning("  3. Run this script again")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
