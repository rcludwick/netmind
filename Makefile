.PHONY: install run test

install:
	uv sync

run:
	(sleep 1 && open http://localhost:8002) &
	uv run uvicorn netmind.app:app --host 0.0.0.0 --port 8002 --reload

test:
	uv run pytest
