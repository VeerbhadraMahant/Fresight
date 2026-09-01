# FreightSight API — production image
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code + committed real-data snapshot
COPY app ./app

# non-root
RUN useradd --create-home --uid 10001 appuser
USER appuser

# PORT is honoured (Render / Railway / Fly / Cloud Run inject it); defaults to 8000
ENV PORT=8000 \
    FREIGHTSIGHT_SKIP_LIVE_PROBE=1 \
    FREIGHTSIGHT_LOG_LEVEL=INFO

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\",\"8000\")}/api/health').status==200 else 1)"

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
