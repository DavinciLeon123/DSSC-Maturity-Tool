FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Place venv outside /app so docker-compose volume mount of /app doesn't hide it
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
# Use the container's system Python (3.13) — zen-engine has cp313 wheels
ENV UV_PYTHON_PREFERENCE=only-system

# Build context is the repo root.
# Copy lock file and project metadata first so this layer is cached separately.
COPY backend/uv.lock backend/pyproject.toml ./

# Install dependencies (without project itself)
RUN uv sync --locked --no-install-project --no-dev

# Copy backend source and install project
COPY backend/ /app/
# Override .python-version (pinned to 3.14 for local dev) to match container's Python
RUN echo "3.13" > /app/.python-version
RUN uv sync --locked --no-dev

# Bundle config files so the image is self-contained (no docker-compose volume needed)
COPY config /config

FROM python:3.13-slim
# Copy the venv, app source, and config — system Python 3.13 matches the builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app
COPY --from=builder /config /config
# WeasyPrint system libraries required for PDF generation at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
  && rm -rf /var/lib/apt/lists/*
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app

CMD ["sh", "-c", "alembic upgrade head && python scripts/create_admin.py && fastapi run app/main.py --host 0.0.0.0 --port 8000"]
