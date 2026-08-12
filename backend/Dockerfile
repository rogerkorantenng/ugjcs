# syntax=docker/dockerfile:1

# ---- builder ---------------------------------------------------------------
# Installs dependencies with uv from the committed lockfile. `--locked` makes a
# lockfile that has drifted from pyproject.toml fail the build loudly instead of
# uv silently re-resolving something the lockfile never pinned.
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
RUN uv sync --locked --no-dev

# ---- runtime ----------------------------------------------------------------
# Slim, no build toolchain, no uv binary — only the .venv the builder stage
# produced is copied across. Runs as a non-root user.
FROM python:3.13-slim AS runtime
RUN addgroup --system app && adduser --system --ingroup app --home /app app
WORKDIR /app

COPY --from=builder --chown=app:app /app /app
COPY --chown=app:app entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENV PATH="/app/.venv/bin:${PATH}" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
