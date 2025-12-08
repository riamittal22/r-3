"""
Summarizer Agent
Uses local Hugging Face models to generate concise, RAG-grounded summaries.
No API keys or cloud credentials required - runs completely offline.
"""

import logging
from typing import List, Dict
from transformers import pipeline

logger = logging.getLogger(__name__)


class SummarizerAgent:
    """Generate summaries using a local Hugging Face model (facebook/bart-large-cnn)."""

    def __init__(self):
        """Initialize the Summarizer Agent with a local model."""
        try:
            logger.info("Loading local summarization model: facebook/bart-large-cnn")
            self.summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=-1,  # Use CPU; change to 0 for GPU if available
            )
            logger.info("✅ Summarizer initialized with local model (no API keys needed)")
        except Exception as e:
            logger.error(f"Error loading summarization model: {e}")
            raise

    def summarize(
        self,
        content: str,
        max_length: int = 150,
        style: str = "brief",
    ) -> str:
        """
        Generate a summary of the content using local model.
        
        Args:
            content: Text to summarize
            max_length: Maximum length of summary (approx words)
            style: "brief", "medium", or "detailed" (currently uses same model for all)
            
        Returns:
            Summary text
        """
        if not content or len(content.strip()) < 50:
            return content[:100]
        
        try:
            # BART works best with 50-1024 token inputs
            # Truncate to ~500 chars to ensure good quality
            text_to_summarize = content[:500]
            
            # Map style to summary length
            length_map = {
                "brief": (20, 60),      # min, max tokens
                "medium": (60, 100),
                "detailed": (100, 150),
            }
            min_len, max_len = length_map.get(style, (20, 60))
            
            # Generate summary
            summary = self.summarizer(text_to_summarize, max_length=max_len, min_length=min_len, do_sample=False)
            result = summary[0]["summary_text"].strip()
            
            logger.debug(f"Generated summary ({style}): {result[:80]}")
            return result
        
        except Exception as e:
            logger.warning(f"Error generating summary: {e}, returning excerpt")
            return content[:120] + "..."

    def summarize_batch(
        self,
        articles: List[Dict],
        style: str = "brief",
    ) -> List[Dict]:
        """
        Summarize multiple articles.
        
        Args:
            articles: List of article dicts with 'content' field
            style: Summary style
            
        Returns:
            Articles with added 'summary' field
        """
        for idx, article in enumerate(articles):
            content = article.get("content", "")
            if content:
                article["summary"] = self.summarize(content, style=style)
            
            if (idx + 1) % 5 == 0:
                logger.info(f"Summarized {idx + 1}/{len(articles)} articles")
        
        logger.info(f"✅ Summarized {len(articles)} articles")
        return articles
