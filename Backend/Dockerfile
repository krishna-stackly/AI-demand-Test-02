# =============================================================================
# Backend Dockerfile — FastAPI + Celery worker share this image.
# Build once, run with a different CMD for the API vs the worker (see
# docker-compose.yml).
# =============================================================================

# ---- Stage 1: builder ------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Build-time system deps:
# - build-essential, gcc, g++: compiling mysqlclient, xgboost, scipy, prophet's cmdstanpy backend
# - default-libmysqlclient-dev, pkg-config: required by mysqlclient's setup.py
# - curl: used by cmdstanpy to fetch/build the cmdstan toolchain for prophet
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Build wheels into an isolated venv so the final stage can copy just this
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Prophet's cmdstanpy backend needs a compiled cmdstan toolchain. Doing this
# in the build stage (not at first request) avoids a slow, surprising delay
# the first time a forecast job runs in production.
RUN python -c "import cmdstanpy; cmdstanpy.install_cmdstan()" || true

# ---- Stage 2: runtime -------------------------------------------------------
FROM python:3.11-slim AS runtime

# Runtime-only system deps:
# - libmariadb3: shared lib mysqlclient needs at runtime (no dev headers needed here)
# - libgomp1: required by xgboost/torch at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.cmdstan /home/appuser/.cmdstan
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CMDSTAN=/home/appuser/.cmdstan

WORKDIR /app

COPY --chown=appuser:appuser . .

# Runtime data directories — these are volume-mounted in docker-compose so
# uploads/models/data survive container restarts and aren't baked into the image.
RUN mkdir -p fastapi_app/media/uploads model_artifacts data/processed \
    && chown -R appuser:appuser /app /home/appuser/.cmdstan

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: run the API. The celery-worker service in docker-compose overrides
# this command to run a celery worker from the same image instead.
CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
