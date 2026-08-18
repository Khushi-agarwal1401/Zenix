"""
Search Evaluation Runner for Zenix AI.
Compares BM25, Vector, and Hybrid search across different query types.
Outputs results to a JSON file for analysis.
"""

import sys
import os
import json
import time

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_engine import RAGEngine

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "search_eval_results_raw.json")


def run_evaluation():
    print("Initializing RAG Engine...")
    t0 = time.time()
    rag = RAGEngine()
    load_time = time.time() - t0
    print(f"Engine loaded in {load_time:.2f}s\n")

    queries = [
        {"query": "how to reset my account password", "intent": "procedural help", "tests": "synonym handling, FAQ matching"},
        {"query": "api rate limit exceeded error fix", "intent": "technical troubleshooting", "tests": "semantic understanding vs exact keywords"},
        {"query": "privacy policy data retention period", "intent": "compliance / legal lookup", "tests": "precision and document structure"},
        {"query": "cheap wireless headphones with noise cancellation", "intent": "comparison + budget constraint", "tests": "attribute extraction and ranking"},
        {"query": "laptop under 1000 dollars for programming", "intent": "filtered recommendation", "tests": "numeric constraints + intent matching"},
        {"query": "replacement charger for dell xps 13", "intent": "exact product compatibility", "tests": "keyword accuracy vs semantic fuzziness"},
        {"query": "how to deploy fastapi with docker", "intent": "tutorial", "tests": "multi-step content relevance"},
        {"query": "elasticsearch vs opensearch performance", "intent": "comparison", "tests": "balanced ranking of multiple documents"},
        {"query": "python memory leak in long running process", "intent": "debugging", "tests": "concept matching without exact phrases"},
        {"query": "search results not relevant", "intent": "vague problem statement", "tests": "robustness, query expansion, intent inference"},
    ]

    results_overview = []

    for q_idx, q_obj in enumerate(queries):
        query_text = q_obj["query"]
        print(f"--- Query {q_idx + 1}: '{query_text}' ---")

        # 1. BM25 Search
        bm25_results = []
        if rag.bm25:
            tokenized = rag._tokenize(query_text)
            scores = rag.bm25.get_scores(tokenized)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
            for idx in top_indices:
                if scores[idx] > 0:
                    doc = rag.bm25_documents[idx]
                    bm25_results.append({"content": doc["content"][:200] + "...", "score": round(float(scores[idx]), 4)})

        # 2. Vector Search
        vector_results = []
        query_emb = rag.model.encode([query_text]).tolist()
        v_res = rag.collection.query(query_embeddings=query_emb, n_results=3)
        if v_res["documents"]:
            for i in range(len(v_res["documents"][0])):
                content = v_res["documents"][0][i]
                dist = v_res["distances"][0][i]
                vector_results.append({"content": content[:200] + "...", "score": round(1.0 - float(dist), 4)})

        # 3. Hybrid Search
        hybrid_results = []
        t0 = time.time()
        h_res = rag.search(query_text, k=3)
        hybrid_latency = time.time() - t0
        for res in h_res:
            hybrid_results.append({"content": res["content"][:200] + "...", "score": round(res.get("cross_score", 0), 4)})

        q_result = {
            "query": query_text,
            "intent": q_obj["intent"],
            "tests": q_obj["tests"],
            "bm25": bm25_results,
            "vector": vector_results,
            "hybrid": hybrid_results,
            "hybrid_latency_ms": round(hybrid_latency * 1000, 1),
        }
        results_overview.append(q_result)

        print(f"  Intent: {q_obj['intent']}")
        print(f"  BM25:    {bm25_results[0]['content'][:60] if bm25_results else 'None'}...")
        print(f"  Vector:  {vector_results[0]['content'][:60] if vector_results else 'None'}...")
        print(f"  Hybrid:  {hybrid_results[0]['content'][:60] if hybrid_results else 'None'}...")
        print(f"  Latency: {hybrid_latency * 1000:.0f}ms\n")

    # Summary statistics
    all_latencies = [r["hybrid_latency_ms"] for r in results_overview]
    avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0

    summary = {
        "total_queries": len(queries),
        "engine_load_time_s": round(load_time, 2),
        "avg_hybrid_latency_ms": round(avg_latency, 1),
        "results": results_overview,
    }

    # Save
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("=" * 50)
    print(f"  SEARCH EVALUATION SUMMARY")
    print("=" * 50)
    print(f"  Queries evaluated: {len(queries)}")
    print(f"  Avg hybrid latency: {avg_latency:.1f}ms")
    print(f"  Full results: {OUTPUT_FILE}")
    print("=" * 50)


if __name__ == "__main__":
    run_evaluation()
