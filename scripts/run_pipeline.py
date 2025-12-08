"""
Pipeline Runner
End-to-end execution of Retriever → Summarizer → Ranker → Email Agent workflow.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

from app.agents.ingest import RAGIngestor
from app.agents.retriever import RetrieverAgent
from app.agents.summarizer import SummarizerAgent
from app.agents.ranker import RankerAgent
from app.agents.emailer import EmailAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RAGPipeline:
    """Execute the full RAG + multi-agent pipeline."""

    def __init__(self, db_path: str = "./chroma_db"):
        """
        Initialize the pipeline with all agents.
        
        Args:
            db_path: Path to Chroma database
        """
        load_dotenv()
        
        self.db_path = db_path
        self.ingestor = None  # Lazy-loaded
        self.retriever = RetrieverAgent(db_path=db_path)
        self.summarizer = SummarizerAgent()
        self.ranker = RankerAgent()
        self.emailer = EmailAgent()
        
        logger.info("✅ RAG Pipeline initialized")

    def ingest_articles(self, jsonl_path: str) -> int:
        """
        Ingest articles from JSONL into vector store.
        
        Args:
            jsonl_path: Path to JSONL file
            
        Returns:
            Number of articles ingested
        """
        if self.ingestor is None:
            self.ingestor = RAGIngestor(db_path=self.db_path)
        
        count = self.ingestor.ingest(jsonl_path)
        return count

    def run(
        self,
        user_preferences: List[str],
        top_k: int = 5,
        save_html: bool = True,
        send_email: bool = False,
        user_name: str = "User",
    ) -> Dict:
        """
        Execute the full pipeline for a user.
        
        Args:
            user_preferences: List of user interests (e.g., ["politics", "finance", "technology"])
            top_k: Number of articles to retrieve per preference
            save_html: Whether to save HTML digest
            send_email: Whether to send email
            user_name: User's name for personalization
            
        Returns:
            Dictionary with pipeline results
        """
        results = {
            "user_preferences": user_preferences,
            "retrieved_articles": 0,
            "summarized_articles": 0,
            "ranked_articles": 0,
            "html_saved": False,
            "email_sent": False,
        }
        
        try:
            # Step 1: Retrieve articles for each preference
            logger.info(f"Step 1/4: Retrieving articles for preferences: {user_preferences}")
            articles_by_preference = self.retriever.retrieve_by_preference(
                user_preferences=user_preferences,
                top_k=top_k,
            )
            
            # Flatten articles for summarization
            all_articles = []
            for pref, articles in articles_by_preference.items():
                for article in articles:
                    article["preference_origin"] = pref
                    all_articles.append(article)
            
            results["retrieved_articles"] = len(all_articles)
            logger.info(f"✅ Retrieved {len(all_articles)} articles")
            
            # Step 2: Summarize articles
            logger.info("Step 2/4: Summarizing articles")
            summarized_articles = self.summarizer.summarize_batch(all_articles, style="brief")
            results["summarized_articles"] = len(summarized_articles)
            logger.info(f"✅ Summarized {len(summarized_articles)} articles")
            
            # Step 3: Rank by preference
            logger.info("Step 3/4: Ranking articles by preference")
            ranked_distribution = self.ranker.distribute_by_preference(
                articles=summarized_articles,
                user_preferences=user_preferences,
            )
            results["ranked_articles"] = sum(len(articles) for articles in ranked_distribution.values())
            logger.info(f"✅ Ranked {results['ranked_articles']} articles across preferences")
            
            # Step 4: Create and deliver digest
            logger.info("Step 4/4: Creating digest")
            html_content = self.emailer.create_html_digest(
                articles_by_preference=ranked_distribution,
                user_name=user_name,
            )
            
            # Save HTML
            if save_html:
                output_file = f"digest_{user_name.replace(' ', '_')}.html"
                if self.emailer.save_digest(html_content, output_file):
                    results["html_saved"] = True
            
            # Send email
            if send_email:
                results["email_sent"] = self.emailer.send_email(html_content)
            
            logger.info("✅ Pipeline execution completed successfully")
            return results
        
        except Exception as e:
            logger.error(f"❌ Pipeline error: {e}", exc_info=True)
            return results


if __name__ == "__main__":
    import sys
    
    # Example usage
    pipeline = RAGPipeline()
    
    # Ingest articles (if not already done)
    jsonl_path = "aithena_articles.jsonl"
    if Path(jsonl_path).exists():
        logger.info(f"Ingesting articles from {jsonl_path}")
        count = pipeline.ingest_articles(jsonl_path)
    
    # Run pipeline
    user_preferences = ["politics", "finance", "technology"]
    results = pipeline.run(
        user_preferences=user_preferences,
        top_k=5,
        save_html=True,
        send_email=False,
        user_name="User",
    )
    
    logger.info(f"Pipeline results: {results}")
