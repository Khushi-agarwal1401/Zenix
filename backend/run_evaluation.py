import sys
import os
import json

# Add current directory to path so we can import rag_engine assuming we run from project root
sys.path.append(os.getcwd())
from backend.rag_engine import RAGEngine

def run_evaluation():
    print("Initialize RAG Engine...")
    rag = RAGEngine()
    
    queries = [
        {
            "query": "how to reset my account password",
            "intent": "procedural help",
            "tests": "synonym handling, FAQ matching"
        },
        {
            "query": "api rate limit exceeded error fix",
            "intent": "technical troubleshooting",
            "tests": "semantic understanding vs exact keywords"
        },
        {
            "query": "privacy policy data retention period",
            "intent": "compliance / legal lookup",
            "tests": "precision and document structure"
        },
        {
            "query": "cheap wireless headphones with noise cancellation",
            "intent": "comparison + budget constraint",
            "tests": "attribute extraction and ranking"
        },
        {
            "query": "laptop under 1000 dollars for programming",
            "intent": "filtered recommendation",
            "tests": "numeric constraints + intent matching"
        },
        {
            "query": "replacement charger for dell xps 13",
            "intent": "exact product compatibility",
            "tests": "keyword accuracy vs semantic fuzziness"
        },
        {
            "query": "how to deploy fastapi with docker",
            "intent": "tutorial",
            "tests": "multi-step content relevance"
        },
        {
            "query": "elasticsearch vs opensearch performance",
            "intent": "comparison",
            "tests": "balanced ranking of multiple documents"
        },
        {
            "query": "python memory leak in long running process",
            "intent": "debugging",
            "tests": "concept matching without exact phrases"
        },
        {
            "query": "search results not relevant",
            "intent": "vague problem statement",
            "tests": "robustness, query expansion, intent inference"
        }
    ]

    results_overview = []

    for q_idx, q_obj in enumerate(queries):
        query_text = q_obj['query']
        print(f"\n--- Query {q_idx+1}: '{query_text}' ---")
        
        # 1. Keyword Search (BM25)
        bm25_results = []
        if rag.bm25:
            tokenized = rag._tokenize(query_text)
            scores = rag.bm25.get_scores(tokenized)
            # Get top 3
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
            for idx in top_indices:
                if scores[idx] > 0:
                    doc = rag.bm25_documents[idx]
                    bm25_results.append({
                        "content": doc['content'][:200] + "...", # Truncate for display
                        "score": scores[idx]
                    })
        
        # 2. Semantic Search (Vector)
        vector_results = []
        query_emb = rag.model.encode([query_text]).tolist()
        v_res = rag.collection.query(query_embeddings=query_emb, n_results=3)
        if v_res['documents']:
            for i in range(len(v_res['documents'][0])):
                content = v_res['documents'][0][i]
                dist = v_res['distances'][0][i]
                vector_results.append({
                    "content": content[:200] + "...",
                    "score": 1.0 - dist
                })

        # 3. Hybrid Search (RAGEngine.search)
        hybrid_results = []
        h_res = rag.search(query_text, k=3)
        for res in h_res:
            hybrid_results.append({
                "content": res['content'][:200] + "...",
                "score": res.get('cross_score', 0)
            })

        # Structure for output
        q_result = {
            "query": query_text,
            "intent": q_obj['intent'],
            "bm25": bm25_results,
            "vector": vector_results,
            "hybrid": hybrid_results
        }
        results_overview.append(q_result)

        print(f"  [Intent]: {q_obj['intent']}")
        print(f"  [BM25 Top]: {bm25_results[0]['content'] if bm25_results else 'None'}")
        print(f"  [Vector Top]: {vector_results[0]['content'] if vector_results else 'None'}")
        print(f"  [Hybrid Top]: {hybrid_results[0]['content'] if hybrid_results else 'None'}")

    # Dump full details to a file for closer manual inspection
    with open("search_eval_results_raw.json", "w") as f:
        json.dump(results_overview, f, indent=2)
    print("\nFull results saved to 'search_eval_results_raw.json'.")

if __name__ == "__main__":
    run_evaluation()
