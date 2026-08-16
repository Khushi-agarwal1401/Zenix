import chromadb
import uuid
from typing import List, Dict
from rank_bm25 import BM25Okapi
import re

class RAGEngine:
    def __init__(self, persist_directory="./chroma_db"):
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Lazy-loaded heavy models
        self._model = None
        self._cross_encoder = None
        
        # Create or get the ChromaDB collection
        self.collection = self.client.get_or_create_collection(name="zenix_knowledge")
        
        # Initialize BM25
        self.bm25 = None
        self.bm25_documents = []
        self._build_bm25_index()

    @property
    def model(self):
        if self._model is None:
            print("Loading SentenceTransformer ('BAAI/bge-m3')...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer('BAAI/bge-m3')
        return self._model

    @property
    def cross_encoder(self):
        if self._cross_encoder is None:
            print("Loading CrossEncoder ('cross-encoder/ms-marco-MiniLM-L-6-v2')...")
            from sentence_transformers import CrossEncoder
            self._cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        return self._cross_encoder

    def _tokenize(self, text: str) -> List[str]:
        # Simple whitespace tokenizer with lowercasing
        return re.findall(r'\w+', text.lower())

    def _build_bm25_index(self):
        """
        Fetches all documents from Chroma and builds in-memory BM25 index.
        """
        try:
            result = self.collection.get()
            if result['documents']:
                self.bm25_documents = []
                tokenized_corpus = []
                
                for idx, doc in enumerate(result['documents']):
                    self.bm25_documents.append({
                        "content": doc,
                        "metadata": result['metadatas'][idx] if result['metadatas'] else {},
                        "id": result['ids'][idx]
                    })
                    tokenized_corpus.append(self._tokenize(doc))
                
                self.bm25 = BM25Okapi(tokenized_corpus)
                print(f"BM25 Index built with {len(self.bm25_documents)} documents.")
            else:
                print("ChromaDB is empty. BM25 index not built.")
        except Exception as e:
             print(f"Error building BM25 index: {e}")

    def ingest_documents(self, documents: List[Dict[str, str]]):
        """
        Ingests a list of documents.
        Each doc should have 'content' and 'metadata'.
        """
        ids = [str(uuid.uuid4()) for _ in documents]
        contents = [doc['content'] for doc in documents]
        metadatas = [doc['metadata'] for doc in documents]
        
        # Generate embeddings
        embeddings = self.model.encode(contents).tolist()
        
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )
        
        # Rebuild BM25 index after ingestion
        self._build_bm25_index()

    def search(self, query: str, k: int = 3, alpha: float = 0.5) -> List[Dict]:
        """
        Hybrid Semantic Search with Re-Ranking.
        1. Retrieval: Get top N candidates using Hybrid Search (Vector + BM25).
        2. Re-Ranking: Score candidates using Cross-Encoder.
        """
        
        # Fetch more candidates for re-ranking (e.g. 3x k)
        candidate_k = k * 4
        
        # 1. Vector Search
        query_embedding = self.model.encode([query]).tolist()
        vector_results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=candidate_k
        )
        
        # Format Vector Results
        v_docs = []
        if vector_results['documents']:
             for i in range(len(vector_results['documents'][0])):
                v_docs.append({
                    "content": vector_results['documents'][0][i],
                    "metadata": vector_results['metadatas'][0][i],
                    "score": 1.0 - vector_results['distances'][0][i]
                })
        
        # 2. BM25 Search
        bm25_docs = []
        if self.bm25:
             tokenized_query = self._tokenize(query)
             scores = self.bm25.get_scores(tokenized_query)
             top_n_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:candidate_k]
             
             for idx in top_n_indices:
                 if scores[idx] > 0:
                     doc_info = self.bm25_documents[idx]
                     bm25_docs.append({
                         "content": doc_info['content'],
                         "metadata": doc_info['metadata'],
                         "score": scores[idx] 
                     })

        # 3. Merge candidates (Union)
        seen_content = set()
        candidates = []
        
        max_len = max(len(v_docs), len(bm25_docs)) if (v_docs or bm25_docs) else 0
        for i in range(max_len):
            if i < len(v_docs):
                item = v_docs[i]
                if item['content'] not in seen_content:
                    candidates.append(item)
                    seen_content.add(item['content'])
            
            if i < len(bm25_docs):
                item = bm25_docs[i]
                if item['content'] not in seen_content:
                    candidates.append(item)
                    seen_content.add(item['content'])
        
        print(f"Retrieval stage found {len(candidates)} candidates.")

        # 4. Re-Ranking with Cross-Encoder
        if not candidates:
            return []

        pairs = [[query, doc['content']] for doc in candidates]
        cross_scores = self.cross_encoder.predict(pairs)
        
        for idx in range(len(candidates)):
            candidates[idx]['cross_score'] = float(cross_scores[idx])
            
        candidates.sort(key=lambda x: x['cross_score'], reverse=True)
        
        return candidates[:k]
