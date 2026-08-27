import torch
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder

class EmbeddingManager:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Embeddings] Initializing models on device: {self.device}")
        
        # Initialize LangChain Embeddings wrapper
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={"device": self.device},
            encode_kwargs={"normalize_embeddings": True, "batch_size": 64}
        )
        
        # Initialize CrossEncoder for re-ranking
        self.reranker = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2", 
            device=self.device
        )
        
    def get_embeddings(self) -> HuggingFaceEmbeddings:
        return self.embeddings
        
    def rerank(self, query: str, documents: list, top_k: int = 5) -> list:
        if not documents:
            return []
        
        # Pair query with each document content
        pairs = [[query, doc.page_content] for doc in documents]
        scores = self.reranker.predict(pairs)
        
        # Sort documents based on scores
        scored_docs = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
        
        # Attach the relevance score to metadata if needed, and return top_k
        results = []
        for score, doc in scored_docs[:top_k]:
            doc.metadata["rerank_score"] = float(score)
            results.append(doc)
            
        return results

# Singleton instance
embedding_manager = EmbeddingManager()
