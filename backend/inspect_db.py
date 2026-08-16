import chromadb
from chromadb.utils import embedding_functions

def inspect_db():
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path="./chroma_db")
    
    try:
        collection = client.get_collection(name="zenix_knowledge")
        count = collection.count()
        print(f"Total Documents in Vector DB: {count}")
        
        if count > 0:
            print("\n--- Sample Document ---")
            # Fetch 1 item
            result = collection.peek(limit=1)
            
            # Chroma returns dict of lists
            print(f"ID: {result['ids'][0]}")
            print(f"Content (First 100 chars): {result['documents'][0][:100]}...")
            print(f"Metadata: {result['metadatas'][0]}")
            
            # Check embeddings
            if result['embeddings']:
                emb_len = len(result['embeddings'][0])
                print(f"Embedding Vector Length: {emb_len} (Dimensions)")
                print("Vector Storage: CONFIRMED")
            else:
                 print("Vector Storage: NOT VISIBLE (might be excluded in peek)")
                 
            # Explicit get to check embedding existence if peek missed it
            full_res = collection.get(ids=[result['ids'][0]], include=["embeddings", "metadatas", "documents"])
            if full_res['embeddings']:
                 print(f"Explicit Check - Embedding Length: {len(full_res['embeddings'][0])}")
                 
            print("\nANN Search is enabled by default in ChromaDB (HNSW).")
            
        else:
            print("Database is empty.")
            
    except Exception as e:
        print(f"Error inspecting DB: {e}")

if __name__ == "__main__":
    inspect_db()
