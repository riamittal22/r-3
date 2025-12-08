"""
Summarizer Agent
Uses Azure OpenAI to generate concise, RAG-grounded summaries.
"""

import logging
import os
from typing import List, Dict
import openai

logger = logging.getLogger(__name__)


class SummarizerAgent:
    """Generate AI-powered summaries using Azure OpenAI."""

    def __init__(self):
        """Initialize the Summarizer Agent with Azure OpenAI credentials."""
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        
        if not self.api_key or not self.endpoint:
            raise ValueError("Azure OpenAI credentials not configured in .env")
        
        openai.api_type = "azure"
        openai.api_key = self.api_key
        openai.api_base = self.endpoint
        openai.api_version = "2024-02-15-preview"
        
        logger.info(f"Summarizer initialized with Azure OpenAI deployment: {self.deployment}")

    def summarize(
        self,
        content: str,
        max_length: int = 150,
        style: str = "brief",
    ) -> str:
        """
        Generate a summary of the content using Azure OpenAI.
        
        Args:
            content: Text to summarize
            max_length: Maximum length of summary (approx words)
            style: "brief" (1-2 sent), "medium" (2-3 sent), "detailed" (3-5 sent)
            
        Returns:
            Summary text
        """
        style_map = {
            "brief": "1-2 sentences",
            "medium": "2-3 sentences",
            "detailed": "3-5 sentences",
        }
        instruction = style_map.get(style, "1-2 sentences")
        
        prompt = f"""Summarize the following content in {instruction}. Focus on key insights and relevance.

Content:
{content[:1000]}

Summary:"""
        
        try:
            response = openai.ChatCompletion.create(
                engine=self.deployment,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise summaries."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=200,
            )
            
            summary = response.choices[0].message["content"].strip()
            logger.debug(f"Generated summary: {summary[:100]}")
            return summary
        
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return content[:200] + "..."

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
