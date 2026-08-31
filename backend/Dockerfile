# FreightSight API — production image
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# non-root
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# fully offline by default in a container; flip the env to re-enable the probe
ENV FREIGHTSIGHT_SKIP_LIVE_PROBE=1 \
    FREIGHTSIGHT_LOG_LEVEL=INFO

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
