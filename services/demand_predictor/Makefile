run-dev:
	clear && uv run --active python src/main.py

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