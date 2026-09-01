"""Shared HTTP helper: cached, timed-out, best-effort GET."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("freightsight.datasources")

CACHE_DIR = Path(os.getenv("FREIGHTSIGHT_CACHE_DIR", ".cache"))
DEFAULT_TTL_H = float(os.getenv("FREIGHTSIGHT_CACHE_TTL_HOURS", "6"))
_UA = "Mozilla/5.0 (FreightSight/0.1; +https://sih-2026)"


def _cache_path(key: str) -> Path:
    return CACHE_DIR / (hashlib.sha1(key.encode()).hexdigest() + ".json")


def _read_cache(key: str, ttl_h: float) -> Any | None:
    p = _cache_path(key)
    try:
        if not p.exists():
            return None
        blob = json.loads(p.read_text())
        if time.time() - blob["fetched_at"] > ttl_h * 3600:
            return None
        return blob["payload"]
    except Exception:
        return None


def _write_cache(key: str, payload: Any) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(key).write_text(json.dumps({"fetched_at": time.time(), "payload": payload}))
    except Exception as exc:
        log.debug("cache write failed: %s", exc)


def get_json(url: str, *, ttl_h: float = DEFAULT_TTL_H, timeout: float = 8.0,
             params: dict | None = None, retries: int = 2) -> Any | None:
    """GET -> parsed JSON, or None on any failure. Cached on disk; retried with backoff."""
    key = url + (json.dumps(params, sort_keys=True) if params else "")
    hit = _read_cache(key, ttl_h)
    if hit is not None:
        return hit
    last = ""
    for attempt in range(retries + 1):
        try:
            r = httpx.get(url, params=params, headers={"User-Agent": _UA},
                          timeout=timeout, follow_redirects=True)
            if r.status_code == 429:
                last = "429"
                time.sleep(1.5 * (attempt + 1))
                continue
            r.raise_for_status()
            data = r.json()
            _write_cache(key, data)
            return data
        except Exception as exc:
            last = str(exc)
            time.sleep(0.6 * (attempt + 1))
    log.warning("fetch failed %s: %s", url.split("?")[0], last)
    return None
