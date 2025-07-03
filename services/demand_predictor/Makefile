MODE=True
run-dev:
	clear && DEBUG_MODE=$(MODE) uv run --active python src/main.py

build:
	docker build -f Dockerfile -t demand-predictor .

run: build
	docker run -it \
	--entrypoint /bin/sh \
	demand-predictor \
	-c "python src/main.py"

lint:
	ruff check --fix

format:
	ruff format .

reset-venv:
	uv clean
	rm -rf .venv
	rm uv.lock
	uv sync