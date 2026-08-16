import json
import os
import sys

# Add current directory to path so we can import rag_engine
sys.path.append(os.getcwd())
from backend.rag_engine import RAGEngine

DATASET_FILE = "data/dataset_final.json"

def calculate_metrics():
    print("Loading RAG Engine (this may take a moment)...")
    rag = RAGEngine()
    
    print(f"Loading dataset from {DATASET_FILE}...")
    if not os.path.exists(DATASET_FILE):
        print("Dataset not found.")
        return

    with open(DATASET_FILE, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # Filter for positive examples (label=1)
    positive_examples = [ex for ex in dataset if ex.get('label') == 1]
    
    if not positive_examples:
        print("No positive examples found in dataset to evaluate against.")
        return

    print(f"Evaluating on {len(positive_examples)} positive examples...")
    
    total_mrr = 0.0
    total_precision_at_k = 0.0
    k = 3
    
    for i, example in enumerate(positive_examples):
        query = example['query']
        # The context that the user previously saw and liked
        relevant_contexts = set(example['retrieved_context'])
        
        # Run search
        results = rag.search(query, k=k)
        retrieved_contents = [r['content'] for r in results]
        
        # Check matches
        hits = []
        for rank, content in enumerate(retrieved_contents):
            # We use exact string match here as we are comparing against the same corpus
            if content in relevant_contexts:
                hits.append(rank + 1) # 1-based rank
        
        # MRR Calculation
        if hits:
            # First hit determines MRR
            mrr = 1.0 / hits[0]
            precision = 1.0 # At least one relevant doc retrieved
        else:
            mrr = 0.0
            precision = 0.0
            
        total_mrr += mrr
        total_precision_at_k += precision
        
        print(f"Query {i+1}: '{query}' -> MRR: {mrr:.2f}, Hit: {bool(hits)}")

    avg_mrr = total_mrr / len(positive_examples)
    avg_precision = total_precision_at_k / len(positive_examples)
    
    print("\n" + "="*30)
    print(f"OFFLINE EVALUATION REPORT (N={len(positive_examples)})")
    print("="*30)
    print(f"Mean Reciprocal Rank (MRR): {avg_mrr:.4f}")
    print(f"Precision@{k}:             {avg_precision:.4f}")
    print("="*30)

if __name__ == "__main__":
    calculate_metrics()
