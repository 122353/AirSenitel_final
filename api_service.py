"""Repository-root Vercel service with an explicit public API mount.

Current Vercel Services routing preserves the public ``/api`` path. Mounting
the evidence application keeps its internal ``/v2`` routes unchanged and
matches local Vite development, where the proxy strips ``/api``.
"""
from fastapi import FastAPI

from src.api.operational import app as evidence_app

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/api', evidence_app)
