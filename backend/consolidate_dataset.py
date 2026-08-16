import json
import os
from datetime import datetime

LOGS_FILE = "data/training_logs.jsonl"
FEEDBACK_FILE = "data/feedback.jsonl"
OUTPUT_FILE = "data/dataset_final.json"

def load_jsonl(filepath):
    data = []
    if not os.path.exists(filepath):
        print(f"Warning: File not found: {filepath}")
        return data
        
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return data

def consolidate():
    print("Loading logs...")
    logs = load_jsonl(LOGS_FILE)
    feedbacks = load_jsonl(FEEDBACK_FILE)
    
    print(f"Loaded {len(logs)} interaction logs.")
    print(f"Loaded {len(feedbacks)} feedback entries.")
    
    # Index logs by request_id
    logs_by_id = {log.get('request_id'): log for log in logs if log.get('request_id')}
    
    training_examples = []
    
    for fb in feedbacks:
        req_id = fb.get('request_id')
        if not req_id or req_id not in logs_by_id:
            continue
            
        interaction = logs_by_id[req_id]
        
        # Structure for Learning-to-Rank (or Classification)
        example = {
            "query": interaction.get('query'),
            "retrieved_context": interaction.get('retrieved_context'),
            "label": 1 if fb.get('feedback') == 'up' else 0,
            "timestamp": fb.get('timestamp'),
            "metadata": {
                "persona": interaction.get('persona'),
                "request_id": req_id
            }
        }
        
        training_examples.append(example)
        
    print(f"Generated {len(training_examples)} training examples.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(training_examples, f, indent=2)
        
    print(f"Dataset saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    consolidate()
