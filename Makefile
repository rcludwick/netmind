.PHONY: install run test

install:
	uv sync

run:
	uv run uvicorn netmind.app:app --host 0.0.0.0 --port 8000 --reload

test:
	uv run pytest
