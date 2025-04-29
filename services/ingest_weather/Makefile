run-live-dev:
	cp live.env .env
	clear && uv run --active python src/main.py

run-hist-dev:
	clear && uv run --active python src/main.py

build:
	docker build -f Dockerfile -t ingest-weather .

lint:
	ruff check --fix

format:
	ruff format .