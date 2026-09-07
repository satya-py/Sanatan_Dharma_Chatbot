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
        self.load_error = None

        self.load_index()

    @property
    def available(self) -> bool:
        return self.vector_store is not None

    def load_index(self):
        if os.path.isdir(self.db_path) and os.listdir(self.db_path):
            print(f"[GitaRetriever] Loading existing Gita FAISS index from {self.db_path}")
            try:
                self.vector_store = FAISS.load_local(
                    self.db_path,
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True,
                )
                # Default retriever searches k=4 documents
                self.retriever = self.vector_store.as_retriever(search_kwargs={"k": 4})
                print("[GitaRetriever] Gita index ready.")
            except Exception as e:
                self.load_error = f"Failed to load Gita FAISS index: {e}"
                print(f"[GitaRetriever] ERROR: {self.load_error}")
        else:
            # Do not raise: a missing index must not take the whole service down.
            # Gita questions will fall back to web search / general LLM answers.
            self.load_error = f"Gita FAISS index not found at {self.db_path}"
            print(f"[GitaRetriever] WARNING: {self.load_error}. Gita retrieval disabled.")

    def retrieve(self, query: str, k: int = 4):
        if not self.vector_store:
            return []
        try:
            return self.vector_store.similarity_search(query, k=k)
        except Exception as e:
            print(f"[GitaRetriever] Search error: {e}")
            return []

    def get_retriever(self):
        return self.retriever


# Singleton instance
gita_retriever_instance = GitaRetriever()
