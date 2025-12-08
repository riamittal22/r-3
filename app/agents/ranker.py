"""
Ranker Agent
Personalizes and ranks summaries per user preferences.
"""

import logging
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)


class RankerAgent:
    """Rank and personalize articles based on user preferences."""

    def __init__(self):
        """Initialize the Ranker Agent."""
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        logger.info("Ranker initialized")

    def rank_by_preference(
        self,
        articles: List[Dict],
        user_preferences: List[str],
    ) -> List[Dict]:
        """
        Rank articles by relevance to user preferences.
        
        Args:
            articles: List of articles with 'summary', 'metadata' fields
            user_preferences: List of user interests (e.g., ["politics", "finance", "technology"])
            
        Returns:
            Articles ranked by preference relevance (highest score first)
        """
        if not articles or not user_preferences:
            return articles
        
        try:
            # Create preference vector
            pref_text = " ".join(user_preferences)
            
            # Collect all texts for vectorization
            all_texts = [pref_text] + [
                (article.get("summary") or article.get("content", ""))[:500]
                for article in articles
            ]
            
            # Vectorize
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Compute similarity between preferences and each article
            pref_vector = tfidf_matrix[0]
            article_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(pref_vector, article_vectors)[0]
            
            # Add scores to articles
            for idx, article in enumerate(articles):
                article["preference_score"] = float(similarities[idx])
            
            # Sort by preference score
            ranked = sorted(articles, key=lambda a: a.get("preference_score", 0), reverse=True)
            
            logger.info(f"Ranked {len(ranked)} articles by preference: {user_preferences}")
            return ranked
        
        except Exception as e:
            logger.warning(f"Error ranking articles: {e}, returning original order")
            return articles

    def distribute_by_preference(
        self,
        articles: List[Dict],
        user_preferences: List[str],
    ) -> Dict[str, List[Dict]]:
        """
        Distribute and rank articles across user preferences.
        
        Args:
            articles: List of articles
            user_preferences: List of user interests
            
        Returns:
            Dictionary mapping preference to ranked articles
        """
        distribution = {pref: [] for pref in user_preferences}
        
        # For each article, assign to the preference it matches best
        for article in articles:
            content = (article.get("summary") or article.get("content", "")).lower()
            
            best_pref = None
            best_score = 0
            
            for pref in user_preferences:
                # Simple keyword matching + retrieval score
                keyword_score = 1.0 if pref.lower() in content else 0.0
                retrieval_score = article.get("score", 0.5)
                combined_score = 0.3 * keyword_score + 0.7 * retrieval_score
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_pref = pref
            
            if best_pref:
                article["assigned_preference"] = best_pref
                article["assignment_score"] = best_score
                distribution[best_pref].append(article)
        
        # Rank within each preference
        for pref in distribution:
            distribution[pref] = sorted(
                distribution[pref],
                key=lambda a: a.get("assignment_score", 0),
                reverse=True,
            )
        
        logger.info(f"Distributed {len(articles)} articles across {len(user_preferences)} preferences")
        return distribution
