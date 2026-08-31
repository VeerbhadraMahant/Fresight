"""FreightSight API -- Freight Forecasting & Vessel Chartering Decision Support.

SIH 2026 prototype backend.  Run with:  uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .market_store import STORE
from .routers import analysis, reference

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("freightsight")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("building market dataset (public-source probe + synthetic engine)...")
    STORE.build()
    log.info("ready.")
    yield


app = FastAPI(
    title="FreightSight API",
    version="0.1.0",
    description=(
        "Predictive freight-rate forecasting, vessel-type optimisation against "
        "port constraints, market-entry timing, and idle/risk management for bulk "
        "cargo procurement to India's East Coast ports."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reference.router)
app.include_router(analysis.router)


@app.get("/api/health", tags=["meta"])
def health():
    data_ready = STORE.data is not None
    return {
        "status": "ok" if data_ready else "starting",
        "dataset_mode": STORE.provenance.mode if data_ready else None,
        "series": STORE.data.freight.shape[1] if data_ready else 0,
    }


@app.get("/", tags=["meta"])
def root():
    return {"name": "FreightSight API", "docs": "/docs", "health": "/api/health"}
