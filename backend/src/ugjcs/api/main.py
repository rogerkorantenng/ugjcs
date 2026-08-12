"""Uvicorn entrypoint: `uv run uvicorn ugjcs.api.main:app`."""

from ugjcs.api.app import create_app

app = create_app()
