"""Repository-root Vercel service with an explicit public API mount.

Current Vercel Services routing preserves the public ``/api`` path. Mounting
the evidence application keeps its internal ``/v2`` routes unchanged and
matches local Vite development, where the proxy strips ``/api``.
"""
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from src.api.operational import app as evidence_app
from src.services import case_store_v2, devices_v2


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Run explicit, additive schema bootstrap only when deployment requests it."""
    if os.environ.get("AIRSENTINEL_INIT_SCHEMA") == "1":
        case_store_v2.initialize_store()
        devices_v2.initialize_devices()
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.mount('/api', evidence_app)
