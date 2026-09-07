import json
import os

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from ..config import settings
from ..embeddings.models import embedding_manager

# Try-except fallbacks for LangChain imports to support different library versions
try:
    from langchain_classic.retrievers import EnsembleRetriever
except ImportError:
    try:
        from langchain.retrievers import EnsembleRetriever
    except ImportError:
        # Fallback implementation if not found
        class EnsembleRetriever:
            def __init__(self, retrievers, weights):
                self.retrievers = retrievers
                self.weights = weights

            def invoke(self, query):
                # Simple merge as fallback
                docs = []
                for r in self.retrievers:
                    docs.extend(r.invoke(query))
                return list({d.page_content: d for d in docs}.values())

try:
    from langchain_classic.retrievers import MultiQueryRetriever
except ImportError:
    try:
        from langchain.retrievers.multi_query import MultiQueryRetriever
    except ImportError:
        MultiQueryRetriever = None


class ScriptureRetriever:
    def __init__(self):
        self.db_path = settings.SCRIPTURE_INDEX_PATH

        self.vector_store = None
        self.vector_retriever = None
        self.bm25_retriever = None
        self.ensemble_retriever = None
        self.load_error = None

        self.load_vector_store()
        if settings.ENABLE_BM25:
            self.load_bm25_retriever()
        else:
            print(
                "[ScriptureRetriever] BM25 hybrid retrieval disabled (ENABLE_BM25=false) "
                "to stay within the memory budget. Using vector search only."
            )
        self.setup_ensemble_retriever()

    @property
    def available(self) -> bool:
        return self.vector_store is not None

    def load_vector_store(self):
        if os.path.isdir(self.db_path) and os.listdir(self.db_path):
            print(
                f"[ScriptureRetriever] Loading existing scripture FAISS index from {self.db_path}"
            )
            try:
                self.vector_store = FAISS.load_local(
                    self.db_path,
                    embeddings=embedding_manager.get_embeddings(),
                    allow_dangerous_deserialization=True,
                )
                # Default vector search retrieves k=8 documents
                self.vector_retriever = self.vector_store.as_retriever(
                    search_kwargs={"k": 8}
                )
                print("[ScriptureRetriever] Scripture index ready.")
            except Exception as e:
                self.load_error = f"Failed to load scripture FAISS index: {e}"
                print(f"[ScriptureRetriever] ERROR: {self.load_error}")
        else:
            # Do not raise: scripture questions fall back to web search instead.
            self.load_error = f"Scripture FAISS index not found at {self.db_path}"
            print(
                f"[ScriptureRetriever] WARNING: {self.load_error}. "
                "Scripture retrieval disabled."
            )

    def load_bm25_retriever(self):
        from langchain_community.retrievers import BM25Retriever
        from .cache_manager import get_scripture_chunks

        print(
            "[ScriptureRetriever] Initializing BM25 corpus from cached chunks and Mahabharata JSON..."
        )
        # 1. Load PDF chunks from cache
        pdf_chunks = get_scripture_chunks()

        # 2. Load Mahabharata chunks from JSON
        mahabharata_chunks = []
        if os.path.exists(settings.MAHABHARATA_JSON_PATH):
            with open(settings.MAHABHARATA_JSON_PATH, "r", encoding="utf-8") as f:
                mahabharata_chunks = json.load(f)
            print(
                f"[ScriptureRetriever] Loaded {len(mahabharata_chunks)} Mahabharata chunks."
            )
        else:
            print(
                f"[ScriptureRetriever] Warning: Mahabharata progress JSON not found at "
                f"{settings.MAHABHARATA_JSON_PATH}"
            )

        if not pdf_chunks and not mahabharata_chunks:
            print("[ScriptureRetriever] No BM25 corpus available; skipping BM25.")
            return

        # Build LangChain Document objects
        bm25_docs = [
            Document(
                page_content=c["text"],
                metadata={"source": c["source"], "reference": c["reference"]},
            )
            for c in pdf_chunks
        ] + [
            Document(
                page_content=c["text"],
                metadata={
                    "source": c["source"],
                    "reference": c["reference"],
                    "book_num": c.get("book_num"),
                },
            )
            for c in mahabharata_chunks
        ]

        self.bm25_retriever = BM25Retriever.from_documents(bm25_docs)
        self.bm25_retriever.k = 8
        print(
            f"[ScriptureRetriever] BM25 corpus initialized with {len(bm25_docs)} documents."
        )

    def setup_ensemble_retriever(self):
        if self.bm25_retriever and self.vector_retriever:
            print(
                "[ScriptureRetriever] Initializing Ensemble Retriever (weights: 0.4 BM25, 0.6 FAISS)..."
            )
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.bm25_retriever, self.vector_retriever],
                weights=[0.4, 0.6],
            )
        elif self.vector_retriever:
            # Vector-only mode.
            self.ensemble_retriever = self.vector_retriever

    def retrieve(self, query: str, llm=None, use_multiquery: bool = True, top_k: int = 5):
        """
        Retrieves matching documents using the ensemble (BM25 + FAISS Vector) retriever,
        optionally performs query expansion using LLM, and reranks results using Cross-Encoder.
        """
        if not self.ensemble_retriever:
            return []

        # Determine whether to use MultiQueryRetriever
        retriever_to_use = self.ensemble_retriever
        if use_multiquery and settings.ENABLE_MULTIQUERY and MultiQueryRetriever and llm:
            # Dynamically instantiate MultiQueryRetriever with local LLM context
            retriever_to_use = MultiQueryRetriever.from_llm(
                retriever=self.ensemble_retriever, llm=llm
            )

        # Retrieve raw documents
        try:
            raw_docs = retriever_to_use.invoke(query)
        except Exception as e:
            print(f"[ScriptureRetriever] Retrieval error: {e}. Falling back to vector search.")
            try:
                raw_docs = self.vector_retriever.invoke(query)
            except Exception as inner:
                print(f"[ScriptureRetriever] Vector fallback also failed: {inner}")
                return []

        # Re-rank retrieved documents using CrossEncoder
        return embedding_manager.rerank(query, raw_docs, top_k=top_k)


# Singleton instance
scripture_retriever_instance = ScriptureRetriever()
