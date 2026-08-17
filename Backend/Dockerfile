# =============================================================================
# Backend Dockerfile
#
# Two production targets are provided:
#   - api    : FastAPI runtime dependencies only
#   - worker : FastAPI/common dependencies + ML stack + CPU-only PyTorch
#
# The API and Celery worker intentionally use separate Python environments so
# the API image does not carry the heavy training stack.
# =============================================================================

# ---- API builder ------------------------------------------------------------
FROM python:3.11-slim AS api-builder

WORKDIR /build

COPY requirements/base.txt requirements/api.txt ./requirements/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements/api.txt

# ---- Worker builder ---------------------------------------------------------
FROM python:3.11-slim AS worker-builder

WORKDIR /build

# Build tools are required only while creating the worker environment. In
# particular, Prophet/Stan needs a compiler toolchain when CmdStan is built.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/ml.txt requirements/worker.txt ./requirements/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements/worker.txt && \
    pip install --no-cache-dir \
      --index-url https://download.pytorch.org/whl/cpu \
      torch==2.2.2

# Build CmdStan once in the image instead of downloading/compiling it when the
# first Prophet job runs. Keep the failure visible so a broken ML image cannot
# reach production pretending to be ready.
RUN python -c "import cmdstanpy; cmdstanpy.install_cmdstan()"

# ---- Common runtime base ----------------------------------------------------
FROM python:3.11-slim AS runtime-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN useradd --create-home --uid 1000 appuser && \
    mkdir -p /app/fastapi_app/media/uploads /app/model_artifacts /app/data/processed && \
    chown -R appuser:appuser /app

# ---- API runtime ------------------------------------------------------------
FROM runtime-base AS api

COPY --from=api-builder /opt/venv /opt/venv
COPY --chown=appuser:appuser . .

RUN mkdir -p fastapi_app/media/uploads model_artifacts data/processed && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"

CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---- Celery worker runtime --------------------------------------------------
FROM runtime-base AS worker

# xgboost/torch require OpenMP at runtime. No compiler/dev packages are copied
# into the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=worker-builder /opt/venv /opt/venv
COPY --from=worker-builder /root/.cmdstan /home/appuser/.cmdstan
COPY --chown=appuser:appuser . .

ENV CMDSTAN=/home/appuser/.cmdstan

RUN mkdir -p fastapi_app/media/uploads model_artifacts data/processed && \
    chown -R appuser:appuser /app /home/appuser/.cmdstan

USER appuser

CMD ["celery", "-A", "fastapi_app.celery_app.celery_app", "worker", "--loglevel=info"]

# Keep the default `docker build Backend` target useful for developers.
FROM api AS default
