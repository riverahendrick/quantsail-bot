# ── API Dockerfile ─────────────────────────────────────────
# Multi-stage build for the Quantsail FastAPI service.
# Uses uv for fast dependency resolution.

FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (without dev deps for production)
RUN uv sync --frozen --no-dev

# Copy source code
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini ./

EXPOSE 8000

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/public/v1/heartbeat || exit 1

# Run with uvicorn
ENTRYPOINT ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
