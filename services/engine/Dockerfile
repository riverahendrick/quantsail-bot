# ── Engine Dockerfile ──────────────────────────────────────
# Multi-stage build for the Quantsail trading engine.
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
COPY quantsail_engine/ quantsail_engine/
COPY scripts/ scripts/

# Health check: verify the engine module imports cleanly
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD uv run python -c "from quantsail_engine.core.trading_loop import TradingLoop; print('ok')" || exit 1

# Default entrypoint
ENTRYPOINT ["uv", "run", "python", "-m", "quantsail_engine.main"]
