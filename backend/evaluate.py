"""
RAG Evaluation Pipeline for Zenix AI.
Evaluates retrieval quality with MRR, Recall@K, Precision@K, and F1 score.
Also tracks latency and produces a structured report.
"""

import json
import os
import sys
import time

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_engine import RAGEngine

DATASET_FILE = os.path.join(os.path.dirname(__file__), "data", "dataset_final.json")
REPORT_FILE = os.path.join(os.path.dirname(__file__), "data", "eval_report.json")


def calculate_metrics():
    print("Loading RAG Engine (this may take a moment)...")
    t0 = time.time()
    rag = RAGEngine()
    engine_load_time = time.time() - t0
    print(f"RAG Engine loaded in {engine_load_time:.2f}s")

    print(f"\nLoading dataset from {DATASET_FILE}...")
    if not os.path.exists(DATASET_FILE):
        print(f"Dataset not found at {DATASET_FILE}. Skipping dataset evaluation.")
        print("Running search latency benchmark instead...\n")
        _benchmark_search_latency(rag)
        return

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    positive_examples = [ex for ex in dataset if ex.get("label") == 1]

    if not positive_examples:
        print("No positive examples found. Running latency benchmark...\n")
        _benchmark_search_latency(rag)
        return

    print(f"Evaluating on {len(positive_examples)} positive examples...\n")

    k = 3
    total_mrr = 0.0
    total_recall = 0.0
    total_precision = 0.0
    total_latency = 0.0
    results = []

    for i, example in enumerate(positive_examples):
        query = example["query"]
        relevant_contexts = set(example["retrieved_context"])

        t0 = time.time()
        search_results = rag.search(query, k=k)
        latency = time.time() - t0
        total_latency += latency

        retrieved_contents = [r["content"] for r in search_results]

        # Calculate hits
        hits = []
        for rank, content in enumerate(retrieved_contents):
            if content in relevant_contexts:
                hits.append(rank + 1)

        # MRR
        mrr = 1.0 / hits[0] if hits else 0.0
        # Recall@K
        recall = len(hits) / len(relevant_contexts) if relevant_contexts else 0.0
        # Precision@K
        precision = len(hits) / k if k > 0 else 0.0
        # F1
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        total_mrr += mrr
        total_recall += recall
        total_precision += precision

        status = "HIT" if hits else "MISS"
        print(f"  [{status}] Query {i+1}: '{query[:60]}...'")
        print(f"         MRR={mrr:.2f}  Recall={recall:.2f}  P@{k}={precision:.2f}  F1={f1:.2f}  Latency={latency*1000:.0f}ms")

        results.append({
            "query": query,
            "intent": example.get("intent", "unknown"),
            "mrr": round(mrr, 4),
            "recall": round(recall, 4),
            "precision": round(precision, 4),
            "f1": round(f1, 4),
            "latency_ms": round(latency * 1000, 1),
            "hits": len(hits),
        })

    n = len(positive_examples)
    avg_mrr = total_mrr / n
    avg_recall = total_recall / n
    avg_precision = total_precision / n
    avg_f1 = 2 * avg_precision * avg_recall / (avg_precision + avg_recall) if (avg_precision + avg_recall) > 0 else 0.0
    avg_latency = total_latency / n
    hit_rate = sum(1 for r in results if r["hits"] > 0) / n

    report = {
        "dataset_size": n,
        "k": k,
        "engine_load_time_s": round(engine_load_time, 2),
        "metrics": {
            "mrr": round(avg_mrr, 4),
            "recall@k": round(avg_recall, 4),
            "precision@k": round(avg_precision, 4),
            "f1": round(avg_f1, 4),
            "hit_rate": round(hit_rate, 4),
            "avg_latency_ms": round(avg_latency * 1000, 1),
        },
        "per_query": results,
    }

    print("\n" + "=" * 55)
    print(f"  ZENIX RAG EVALUATION REPORT (N={n}, K={k})")
    print("=" * 55)
    print(f"  Mean Reciprocal Rank (MRR):      {avg_mrr:.4f}")
    print(f"  Recall@{k}:                       {avg_recall:.4f}")
    print(f"  Precision@{k}:                    {avg_precision:.4f}")
    print(f"  F1 Score:                        {avg_f1:.4f}")
    print(f"  Hit Rate:                        {hit_rate:.2%}")
    print(f"  Avg Search Latency:              {avg_latency*1000:.1f}ms")
    print(f"  Engine Load Time:                {engine_load_time:.2f}s")
    print("=" * 55)

    # Save report
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nFull report saved to: {REPORT_FILE}")


def _benchmark_search_latency(rag: RAGEngine):
    """Benchmark search latency with sample queries."""
    sample_queries = [
        "how to reset password",
        "API rate limit error",
        "deploy fastapi with docker",
        "python memory leak debugging",
        "best wireless headphones",
    ]

    total_latency = 0.0
    results = []

    print("Search Latency Benchmark")
    print("-" * 40)

    for query in sample_queries:
        t0 = time.time()
        results_list = rag.search(query, k=3)
        latency = time.time() - t0
        total_latency += latency

        top_content = results_list[0]["content"][:80] if results_list else "N/A"
        print(f"  '{query}'")
        print(f"    -> {latency*1000:.0f}ms | Top: {top_content}...")
        results.append({"query": query, "latency_ms": round(latency * 1000, 1), "results": len(results_list)})

    avg = total_latency / len(sample_queries)
    print(f"\n  Average latency: {avg*1000:.1f}ms over {len(sample_queries)} queries")


if __name__ == "__main__":
    calculate_metrics()
