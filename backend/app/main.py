"""FreightSight API -- Freight Forecasting & Vessel Chartering Decision Support.

SIH 2026 prototype backend.

Local:  uvicorn app.main:app --reload
Prod:   uvicorn app.main:app --host 0.0.0.0 --port 8000

Environment variables (all optional):
  FREIGHTSIGHT_CORS_ORIGINS   comma-separated allowed origins (default: "*")
  FREIGHTSIGHT_LOG_LEVEL      DEBUG | INFO | WARNING | ERROR   (default: INFO)
  FREIGHTSIGHT_SKIP_LIVE_PROBE  "1" to skip the public Baltic Dry Index probe
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .market_store import STORE
from .routers import analysis, geo, reference, system

logging.basicConfig(
    level=os.getenv("FREIGHTSIGHT_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("freightsight")

_CORS_ORIGINS = os.getenv("FREIGHTSIGHT_CORS_ORIGINS", "*")
_ALLOW = ["*"] if _CORS_ORIGINS.strip() == "*" else [o.strip() for o in _CORS_ORIGINS.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("building market dataset (public-source probe + synthetic engine)...")
    STORE.build()
    log.info("ready - %d series, mode=%s", STORE.data.freight.shape[1], STORE.provenance.mode)
    yield


app = FastAPI(
    title="FreightSight API",
    version=__version__,
    description=(
        "Predictive freight-rate forecasting, vessel-type optimisation against "
        "port constraints, market-entry timing, and idle/risk management for bulk "
        "cargo procurement to India's East Coast ports."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOW,
    allow_credentials=_ALLOW != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reference.router)
app.include_router(analysis.router)
app.include_router(geo.router)
app.include_router(system.router)


@app.get("/api/health", tags=["meta"])
def health():
    data_ready = STORE.data is not None
    return {
        "status": "ok" if data_ready else "starting",
        "version": __version__,
        "dataset_mode": STORE.provenance.mode if data_ready else None,
        "series": STORE.data.freight.shape[1] if data_ready else 0,
    }


@app.get("/", tags=["meta"])
def root():
    return {"name": "FreightSight API", "version": __version__, "docs": "/docs", "health": "/api/health"}
