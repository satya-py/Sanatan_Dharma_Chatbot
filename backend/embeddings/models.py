"""
Embedding + reranking models.

Two backends are supported, chosen by the EMBEDDING_BACKEND setting:

  "onnx"  (default) -- fastembed / onnxruntime. No torch. ~150 MB RSS.
                       Produces vectors numerically identical (cosine > 0.999999)
                       to the sentence-transformers build of BAAI/bge-small-en-v1.5,
                       so the pre-built FAISS indices remain valid.

  "torch"           -- the original sentence-transformers path. ~620 MB RSS.
                       Only usable on an instance with >= 2 GB RAM.

The ONNX backend is what makes the service fit inside Render's 512 MB tier.
"""
from typing import List

from langchain_core.embeddings import Embeddings

from ..config import settings

EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
RERANKER_MODEL_NAME_ONNX = "Xenova/ms-marco-MiniLM-L-6-v2"
RERANKER_MODEL_NAME_TORCH = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_onnx_tuned = False


def _tune_onnxruntime():
    """
    Shrink onnxruntime's memory profile before any session is created.

    By default onnxruntime allocates a CPU memory arena on the first inference
    and never gives it back. Measured on this model pair that arena alone costs
    ~230 MB, which is what pushes the service past a 512 MB instance the moment
    the first question arrives -- an OOM kill that looks like a random 502
    rather than a startup failure.

    Disabling the arena and pinning to a single thread costs a few ms per call
    and holds total model memory at ~220 MB, flat across requests. Single
    threading is the right default anyway on a fractional-CPU instance.

    fastembed builds its sessions with ort.SessionOptions(), so overriding that
    class is what actually reaches them.
    """
    global _onnx_tuned
    if _onnx_tuned:
        return
    try:
        import onnxruntime as ort
    except ImportError:
        return

    base = ort.SessionOptions

    class LeanSessionOptions(base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.enable_cpu_mem_arena = False
            self.enable_mem_pattern = False
            self.intra_op_num_threads = 1
            self.inter_op_num_threads = 1

    ort.SessionOptions = LeanSessionOptions
    _onnx_tuned = True
    print("[Embeddings] onnxruntime tuned for low memory (arena off, 1 thread).")


class FastEmbedEmbeddings(Embeddings):
    """LangChain Embeddings adapter over fastembed's ONNX runtime."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name, threads=1)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [v.tolist() for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> List[float]:
        return next(iter(self._model.embed([text]))).tolist()


class EmbeddingManager:
    def __init__(self):
        self.backend = settings.EMBEDDING_BACKEND.lower()
        self.reranker = None

        if self.backend == "torch":
            self._init_torch()
        else:
            self._init_onnx()

    # -- backends ---------------------------------------------------------

    def _init_onnx(self):
        if settings.ONNX_LOW_MEMORY:
            _tune_onnxruntime()
        print("[Embeddings] Backend: onnx (fastembed). Loading BAAI/bge-small-en-v1.5...")
        self.device = "cpu"
        self.embeddings = FastEmbedEmbeddings(EMBEDDING_MODEL_NAME)

        if settings.ENABLE_RERANK:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            print(f"[Embeddings] Loading ONNX reranker {RERANKER_MODEL_NAME_ONNX}...")
            self.reranker = TextCrossEncoder(
                model_name=RERANKER_MODEL_NAME_ONNX, threads=1
            )
        else:
            print("[Embeddings] Reranking disabled (ENABLE_RERANK=false).")

    def _init_torch(self):
        import torch
        from langchain_huggingface import HuggingFaceEmbeddings
        from sentence_transformers import CrossEncoder

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Embeddings] Backend: torch. Initializing models on device: {self.device}")

        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            model_kwargs={"device": self.device},
            encode_kwargs={"normalize_embeddings": True, "batch_size": 64},
        )

        if settings.ENABLE_RERANK:
            self.reranker = CrossEncoder(RERANKER_MODEL_NAME_TORCH, device=self.device)
        else:
            print("[Embeddings] Reranking disabled (ENABLE_RERANK=false).")

    # -- public API -------------------------------------------------------

    def get_embeddings(self) -> Embeddings:
        return self.embeddings

    def _score(self, query: str, texts: List[str]):
        """Return one relevance score per text, whichever backend is active."""
        if self.backend == "torch":
            return self.reranker.predict([[query, t] for t in texts])
        # fastembed's TextCrossEncoder takes (query, documents) and yields scores
        return list(self.reranker.rerank(query, texts))

    def rerank(self, query: str, documents: list, top_k: int = 5) -> list:
        if not documents:
            return []

        # With reranking off, fall back to the retriever's own ordering.
        if self.reranker is None:
            return documents[:top_k]

        try:
            scores = self._score(query, [doc.page_content for doc in documents])
        except Exception as e:
            print(f"[Embeddings] Reranking failed ({e}); falling back to retriever order.")
            return documents[:top_k]

        scored_docs = sorted(
            zip(scores, documents), key=lambda x: x[0], reverse=True
        )

        results = []
        for score, doc in scored_docs[:top_k]:
            doc.metadata["rerank_score"] = float(score)
            results.append(doc)

        return results


# Singleton instance
embedding_manager = EmbeddingManager()
