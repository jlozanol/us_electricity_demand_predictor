run-dev:
	clear && uv run --active python src/main.py

build:
	docker build -f Dockerfile -t ingest-weather .

run: build
	docker run -it \
	--network redpanda_network \
	-e KAFKA_BROKER_ADDRESS=redpanda:9092 \
	--entrypoint /bin/sh \
	ingest-weather \
	-c "python src/main.py"

lint:
	ruff check --fix

format:
	ruff format .