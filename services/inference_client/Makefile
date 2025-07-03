run-dev:
	clear && uv run --active python src/main.py

build:
	docker build -f Dockerfile -t inference-client .

run: build
	docker rm -f inference-app
	docker run --name inference-app \
	-it --entrypoint /bin/sh \
	-p 8501:8501 \
	inference-client \
	-c "streamlit run src/main.py --server.address=0.0.0.0"

lint:
	ruff check --fix

format:
	ruff format .

reset-venv:
	uv clean
	rm -rf .venv
	rm uv.lock
	uv sync