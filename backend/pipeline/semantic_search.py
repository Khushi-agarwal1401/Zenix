"""
Semantic Search Module for Zenix AI.
Uses sentence-transformers for vector-based knowledge retrieval.
Falls back to keyword matching if sentence-transformers is not available.
"""

import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. Using keyword-based search.")


class SemanticSearchEngine:
    """
    Vector-based semantic search engine.
    Uses sentence-transformers for embedding generation and cosine similarity.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.documents: List[Dict[str, Any]] = []
        self.embeddings = None
        self._cache_dir = os.path.join(os.path.dirname(__file__), "..", "data", "semantic_cache")
        os.makedirs(self._cache_dir, exist_ok=True)

        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                logger.info(f"Loaded semantic search model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self.model = None

    def add_documents(self, documents: List[Dict[str, Any]], text_key: str = "content"):
        """
        Add documents to the search index.

        Args:
            documents: List of dicts with at least a 'content' or specified text_key field
            text_key: Key to use for extracting text from documents
        """
        self.documents = documents

        if self.model and documents:
            texts = [doc.get(text_key, "") for doc in documents]
            try:
                self.embeddings = self.model.encode(texts, show_progress_bar=False)
                logger.info(f"Indexed {len(documents)} documents")
            except Exception as e:
                logger.error(f"Failed to generate embeddings: {e}")
                self.embeddings = None

    def search(self, query: str, top_k: int = 5, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Search documents using semantic similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)

        Returns:
            List of matching documents with scores
        """
        if not self.documents:
            return []

        # Try semantic search first
        if self.model and self.embeddings is not None:
            return self._semantic_search(query, top_k, threshold)

        # Fallback to keyword search
        return self._keyword_search(query, top_k)

    def _semantic_search(self, query: str, top_k: int, threshold: float) -> List[Dict[str, Any]]:
        """Perform semantic search using embeddings."""
        try:
            query_embedding = self.model.encode([query])

            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(query_embedding, self.embeddings)[0]

            # Get top-k results
            scored_indices = list(enumerate(similarities))
            scored_indices.sort(key=lambda x: x[1], reverse=True)

            results = []
            for idx, score in scored_indices[:top_k]:
                if score >= threshold:
                    doc = self.documents[idx].copy()
                    doc["semantic_score"] = float(score)
                    doc["search_method"] = "semantic"
                    results.append(doc)

            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Fallback keyword-based search."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []
        for doc in self.documents:
            content = doc.get("content", "").lower()
            title = doc.get("title", "").lower()
            tags = [t.lower() for t in doc.get("tags", [])]

            score = 0

            # Exact query match in content
            if query_lower in content:
                score += 10

            # Word overlap with content
            content_words = set(content.split())
            word_overlap = len(query_words.intersection(content_words))
            score += word_overlap

            # Title match
            for word in query_words:
                if word in title:
                    score += 5

            # Tag match
            for tag in tags:
                if query_lower in tag or tag in query_lower:
                    score += 8
                for word in query_words:
                    if word in tag:
                        score += 2

            if score > 0:
                doc_copy = doc.copy()
                doc_copy["keyword_score"] = score
                doc_copy["search_method"] = "keyword"
                results.append(doc_copy)

        # Sort by score
        results.sort(key=lambda x: x.get("keyword_score", 0), reverse=True)
        return results[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return {
            "total_documents": len(self.documents),
            "model_loaded": self.model is not None,
            "model_name": self.model_name,
            "embeddings_generated": self.embeddings is not None,
            "search_method": "semantic" if self.model else "keyword",
        }


class HybridSearchEngine:
    """
    Hybrid search combining semantic and keyword search.
    Uses Reciprocal Rank Fusion (RRF) to combine results.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.semantic_engine = SemanticSearchEngine(model_name)
        self.keyword_weight = 0.3
        self.semantic_weight = 0.7

    def add_documents(self, documents: List[Dict[str, Any]], text_key: str = "content"):
        """Add documents to both search engines."""
        self.semantic_engine.add_documents(documents, text_key)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword results.

        Uses Reciprocal Rank Fusion:
        score(d) = Σ 1/(k + rank_i(d)) for each search method
        """
        # Get results from both methods
        semantic_results = self.semantic_engine.search(query, top_k=top_k * 2)
        keyword_results = self.semantic_engine._keyword_search(query, top_k=top_k * 2)

        # Combine using RRF
        k = 60  # RRF constant
        doc_scores = {}

        # Score semantic results
        for rank, doc in enumerate(semantic_results):
            doc_id = self._doc_id(doc)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + self.semantic_weight / (k + rank + 1)
            if doc_id not in [d.get("_id") for d in doc_scores.values()]:
                doc_scores[doc_id] = {"doc": doc, "score": doc_scores[doc_id]}

        # Score keyword results
        for rank, doc in enumerate(keyword_results):
            doc_id = self._doc_id(doc)
            if doc_id in doc_scores:
                doc_scores[doc_id]["score"] += self.keyword_weight / (k + rank + 1)
            else:
                doc_scores[doc_id] = {"doc": doc, "score": self.keyword_weight / (k + rank + 1)}

        # Sort by combined score
        sorted_results = sorted(doc_scores.values(), key=lambda x: x["score"], reverse=True)

        # Return top-k
        results = []
        for item in sorted_results[:top_k]:
            doc = item["doc"].copy()
            doc["hybrid_score"] = item["score"]
            doc["search_method"] = "hybrid"
            results.append(doc)

        return results

    def _doc_id(self, doc: Dict[str, Any]) -> str:
        """Generate a unique ID for a document."""
        content = doc.get("content", "")[:100]
        return hashlib.md5(content.encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """Get hybrid search statistics."""
        stats = self.semantic_engine.get_stats()
        stats["search_type"] = "hybrid"
        stats["semantic_weight"] = self.semantic_weight
        stats["keyword_weight"] = self.keyword_weight
        return stats


# Singleton instance
_hybrid_search = None


def get_semantic_search() -> HybridSearchEngine:
    """Get or create the hybrid search engine singleton."""
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = HybridSearchEngine()
    return _hybrid_search


def search_knowledge(query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Convenience function for semantic search.

    Args:
        query: Search query
        documents: List of documents to search
        top_k: Number of results

    Returns:
        List of matching documents with scores
    """
    engine = get_semantic_search()
    if not engine.semantic_engine.documents:
        engine.add_documents(documents)
    return engine.search(query, top_k)
