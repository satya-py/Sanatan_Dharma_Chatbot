import os
from langchain_community.vectorstores import FAISS
from ..config import settings
from ..embeddings.models import embedding_manager

class GitaRetriever:
    def __init__(self):
        self.db_path = settings.GITA_INDEX_PATH
        self.embeddings = embedding_manager.get_embeddings()
        self.vector_store = None
        self.retriever = None
        
        self.load_index()

    def load_index(self):
        if os.path.exists(self.db_path) and len(os.listdir(self.db_path)) > 0:
            print(f"[GitaRetriever] Loading existing Gita FAISS index from {self.db_path}")
            self.vector_store = FAISS.load_local(
                self.db_path,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
            # Default retriever searches k=4 documents
            self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})
        else:
            raise FileNotFoundError(
                f"Gita FAISS index not found at {self.db_path}. Please ensure it is present."
            )
            
    def retrieve(self, query: str, k: int = 4):
        if not self.vector_store:
            return []
        return self.vector_store.similarity_search(query, k=k)
        
    def get_retriever(self):
        return self.retriever

# Singleton instance
gita_retriever_instance = GitaRetriever()
