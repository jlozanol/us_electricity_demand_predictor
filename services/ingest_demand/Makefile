run-live:
	cp live.dev.env .env
	clear && uv run python src/main.py

run-hist:
	cp hist.dev.env .env
	clear && uv run python src/main.py

lint:
	ruff check --fix

format:
	ruff format .