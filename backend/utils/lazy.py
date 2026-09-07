"""
Deferred construction of expensive singletons.

The retrievers and embedding models used to be built at import time. uvicorn
only binds its listening socket after the application module has been imported
and the lifespan startup handler has returned, so every second spent
downloading ONNX weights and mapping a 60 MB FAISS index was a second the port
stayed closed. On a small instance that overran the platform's port scan and
the deploy was killed with "no open ports detected" before the app ever ran.

Wrapping them in LazyObject keeps `import backend.main` fast, so the port opens
immediately and the heavy work happens in a background warm-up thread.
"""
import threading


class LazyObject:
    """
    A proxy that builds the real object on first attribute access.

    Attribute access is forwarded, so call sites keep using
    `gita_retriever_instance.retrieve(...)` unchanged. Construction is guarded
    by a lock: the warm-up thread and an early request can race, and the
    factories load hundreds of megabytes, so running one twice would blow the
    memory budget.
    """

    def __init__(self, factory, name=None):
        object.__setattr__(self, "_lazy_factory", factory)
        object.__setattr__(self, "_lazy_name", name or getattr(factory, "__name__", "object"))
        object.__setattr__(self, "_lazy_obj", None)
        object.__setattr__(self, "_lazy_error", None)
        object.__setattr__(self, "_lazy_lock", threading.Lock())

    # -- introspection that must NOT trigger construction -----------------

    @property
    def lazy_initialized(self) -> bool:
        return object.__getattribute__(self, "_lazy_obj") is not None

    @property
    def lazy_error(self):
        return object.__getattribute__(self, "_lazy_error")

    def lazy_resolve(self):
        """Build the object now (used by the warm-up thread)."""
        obj = object.__getattribute__(self, "_lazy_obj")
        if obj is not None:
            return obj

        lock = object.__getattribute__(self, "_lazy_lock")
        with lock:
            # Re-check: another thread may have built it while we waited.
            obj = object.__getattribute__(self, "_lazy_obj")
            if obj is not None:
                return obj

            factory = object.__getattribute__(self, "_lazy_factory")
            name = object.__getattribute__(self, "_lazy_name")
            print(f"[Lazy] Initializing {name}...", flush=True)
            try:
                obj = factory()
            except Exception as e:
                object.__setattr__(self, "_lazy_error", str(e))
                print(f"[Lazy] Failed to initialize {name}: {e}", flush=True)
                raise
            object.__setattr__(self, "_lazy_obj", obj)
            print(f"[Lazy] {name} ready.", flush=True)
            return obj

    # -- proxying ---------------------------------------------------------

    def __getattr__(self, item):
        # Only called for attributes not found normally, so the lazy_* members
        # above never reach here.
        return getattr(self.lazy_resolve(), item)

    def __setattr__(self, key, value):
        setattr(self.lazy_resolve(), key, value)

    def __repr__(self):
        name = object.__getattribute__(self, "_lazy_name")
        state = "initialized" if self.lazy_initialized else "not initialized"
        return f"<LazyObject {name} ({state})>"
