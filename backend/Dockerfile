FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Pycairo's Linux source build requires a C toolchain and Cairo headers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m pip install --upgrade pip \
    && python -m pip install --prefix=/install .

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SAFERETURN_PRINT_TEMPLATE_ASSET_ROOT=/app/print-assets

WORKDIR /app

# Keep the Cairo shared library, not the compiler or development headers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libcairo2 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY app ./app
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic
COPY print-assets ./print-assets

USER nobody

# Fail the build if the final non-root image cannot load its native dependencies.
RUN python -c "import cairo; import app.main; import app.core.template_preview_worker"
RUN python -c "import hashlib,json,pathlib; p=pathlib.Path('/app/print-assets'); m=json.loads((p/'manifest.json').read_text()); assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==h for n,h in m['files'].items())"
RUN python -m app.template_asset_check

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
