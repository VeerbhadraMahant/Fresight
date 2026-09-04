"""FreightSight - Freight Forecasting & Vessel Chartering Decision Support System.

SIH 2026 prototype. See backend/README.md for architecture.
"""

__version__ = "0.1.0"

# Load a local .env before anything reads os.environ (app.db freezes
# DATABASE_URL at import time). Real shell / container env vars always win
# (override=False). Looks for backend/.env first, then the repo-root .env.
# A missing python-dotenv or file is a silent no-op -- CI, Docker and Render set
# the environment directly. The test-suite opts out (see tests/conftest.py) so it
# stays hermetic regardless of a developer's local .env.
import os as _os

if not _os.getenv("FREIGHTSIGHT_SKIP_DOTENV"):
    try:  # pragma: no cover - trivial glue
        from pathlib import Path as _Path

        from dotenv import load_dotenv as _load_dotenv

        _here = _Path(__file__).resolve()
        for _candidate in (_here.parents[1] / ".env", _here.parents[2] / ".env"):
            if _candidate.is_file():
                _load_dotenv(_candidate, override=False)
    except Exception:  # dotenv not installed, unreadable file, etc.
        pass
