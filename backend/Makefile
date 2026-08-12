.PHONY: check fmt test integration
fmt:
	uv run ruff format src tests
	uv run ruff check --fix src tests

# The coverage gate covers domain and application only. Infrastructure adapters are
# verified by the integration suite, which needs Docker and is deselected here; measuring
# them in a run that excludes their tests would only reward mock-based tests that assert
# nothing. `make integration` reports adapter coverage separately.
check:
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run mypy
	uv run lint-imports
	uv run pytest --cov=src/ugjcs/domain --cov=src/ugjcs/application \
		--cov-report=term-missing --cov-fail-under=85

integration:
	uv run pytest -m integration -v --cov=src/ugjcs/infrastructure \
		--cov-report=term-missing --cov-fail-under=0

test:
	uv run pytest -q
