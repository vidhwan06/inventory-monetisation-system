# ──────────────────────────────────────────────────────────────────
# Root-level launcher shim.
#
# This file allows you to run the backend from the project root:
#
#   python -m uvicorn main:app --reload
#
# It adds the backend/ folder to sys.path so all imports resolve
# exactly as if you had cd'd into backend/ first.
# ──────────────────────────────────────────────────────────────────

import sys
import os

# Ensure backend/ is on the path so "from agents.X import …" works
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Re-export the FastAPI app so uvicorn can find it as "main:app"
from backend.main import app  # noqa: E402  (import not at top is intentional)

__all__ = ["app"]
