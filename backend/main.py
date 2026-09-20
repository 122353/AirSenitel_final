"""Vercel Services entry point; /api is stripped by the platform router."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.api.operational import app  # noqa: E402,F401
