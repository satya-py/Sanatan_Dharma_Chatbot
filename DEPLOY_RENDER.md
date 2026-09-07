# Deploying the backend to Render

## Why the original build failed

Four independent blockers, in the order Render hits them:

1. **The build ran out of room.** `requirements.txt` pinned `torch`, which on PyPI
   drags in ~900 MB of CUDA wheels that are useless on a CPU host.
2. **Missing dependencies.** `pandas` and `python-dotenv` were imported but never
   declared.
3. **The service crashed on import.** Both retrievers raised `FileNotFoundError`
   at module scope, and the FAISS indices were in `.gitignore`, so the repo Render
   clones did not contain them.
4. **It did not fit in memory.** Measured peak was **1202 MB** against a 512 MB cap.

## What changed

### Memory: 1202 MB -> ~415 MB

| Component | Before | After |
|---|---|---|
| `torch` import | 368 MB | removed |
| Embedding model | 252 MB | 121 MB (ONNX) |
| Reranker | 7 MB | off by default (96 MB when on) |
| FAISS indices | 100 MB | 100 MB |
| BM25 corpus | 335 MB | off by default |
| `pandas` | 55 MB | removed (stdlib `csv`) |
| **Peak under traffic** | **1202 MB** | **~415 MB** |

- **Embeddings now run on ONNX** (`fastembed`) instead of `torch` +
  `sentence-transformers`. Same `BAAI/bge-small-en-v1.5` model; vectors match the
  torch build to **cosine > 0.999999**, so the pre-built FAISS indices stay valid.
- **onnxruntime's CPU memory arena is disabled** and inference pinned to one
  thread. The arena alone cost ~230 MB on first inference — an OOM that shows up
  as a random 502 rather than a startup failure.
- **BM25 hybrid retrieval is off** (`ENABLE_BM25=false`); it costs ~335 MB for
  this corpus.
- **Reranking is off** (`ENABLE_RERANK=false`). With it on, peak reaches ~511 MB
  against a 512 MB cap.
- **`pandas` replaced with the stdlib `csv` module** for the Gita CSV. Output is
  byte-identical; verified across all 701 rows.

### Correctness fixes

- **Contradictory validator prompts.** The generator is *required* to produce
  "Practical Application" and "Conclusion" sections, and the validator then failed
  the answer for containing exactly that content. The citation validator
  separately demanded verbatim translations. Together these refused **4 of 5**
  questions and burned the retry budget. Both prompts now check what actually
  matters: fabricated verses, wrong citations, contradictions. Measured after the
  fix: **5 of 6 answered**, max latency 244s -> 58s.
- **Language misdetection.** `langdetect` classified "Hare Krishna!" as Albanian
  and translated the whole reply into Albanian. Detection is now script-based for
  Indic languages, with English as the fallback for short Latin text. All 12
  supported languages verified.
- **Empty query rewrites.** The rewrite node sometimes returned `""` and then
  searched on it, guaranteeing the next validation round also failed.
- **Refusals were validated.** "I could not find a teaching" was itself failed for
  being ungrounded, looping until the retry budget ran out.
- **`UnicodeEncodeError` on non-UTF-8 consoles** turned working answers into 500s.
- **CORS was invalid.** `allow_credentials=True` with `allow_origins=["*"]` is
  rejected by browsers. Credentials are now only enabled with an explicit origin list.
- **Missing API keys crashed the process at import.** Clients are built lazily and
  `/api/health` reports which keys are absent.
- `check_same_thread` is no longer passed to non-SQLite drivers.
- File logging is opt-in; logs go to stdout, which is what Render collects.

## Deploy

1. Push this branch to `main`.
2. In Render: **New -> Web Service**, connect the repo. `render.yaml` is detected
   automatically (Blueprint).
3. Set the four secrets under **Environment** — they are marked `sync: false` so
   they are never committed:
   `GROQ_API_KEY`, `GOOGLE_API_KEY`, `TAVILY_API_KEY`, `ASSEMBLYAI_API_KEY`
4. Deploy, then check `https://<service>.onrender.com/api/health`. It reports the
   active config, whether each index loaded, and any missing keys.

To create the service without a Blueprint, use:

- Build: `pip install -r backend/requirements.txt`
- Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --workers 1`
- Health check path: `/api/health`

Keep `--workers 1`. Each worker loads its own copy of the models.

## Connecting the Vercel frontend

Set `CORS_ORIGINS` on Render to your Vercel URL (comma-separated, no trailing
slash), then redeploy:

```
CORS_ORIGINS=https://your-app.vercel.app
```

Leaving it as `*` works but disables credentialed requests.

## Known constraints

- **Groq free tier: 200,000 tokens/day, 8,000 tokens/minute.** The Self-RAG graph
  spends roughly 10k-25k tokens per question (intent, generation, two validators,
  retries, translation), so the free tier supports only about **10-20 questions per
  day** before returning 429s. This is the binding limit on the project, not RAM.
- **Free instances sleep after 15 minutes idle.** The next request pays a ~60-90s
  cold start while the models load.
- **SQLite lives on ephemeral disk** — chat history is wiped on every deploy and
  restart. Attach a Render Postgres instance and set `DATABASE_URL` to persist it.
- Reranking and BM25 are disabled for memory. On a 2 GB instance set
  `ENABLE_RERANK=true` and `ENABLE_BM25=true` to restore full retrieval quality.
