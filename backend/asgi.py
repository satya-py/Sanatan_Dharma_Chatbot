"""
Working-directory-independent ASGI entry point.

backend/main.py uses package-relative imports, so it has to be imported as
`backend.main`, which only resolves when the repository root is on sys.path.
Point a host's "root directory" at backend/ -- an easy and reasonable-looking
mistake -- and the server dies at startup with
`ModuleNotFoundError: No module named 'backend'`.

This module puts the repository root on sys.path itself, so it works from
either location:

    uvicorn backend.asgi:app   # started from the repository root
    uvicorn asgi:app           # started from inside backend/

Both resolve to the same application object as `backend.main:app`.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.main import app  # noqa: E402

__all__ = ["app"]
