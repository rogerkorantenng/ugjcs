.PHONY: check fmt test
fmt:
	uv run ruff format src tests
	uv run ruff check --fix src tests

check:
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run mypy
	uv run lint-imports
	uv run pytest --cov --cov-report=term-missing

test:
	uv run pytest -q
