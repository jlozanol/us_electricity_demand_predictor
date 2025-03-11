run-live-dev:
	cp live.env .env
	clear && uv run python src/main.py

run-hist-dev:
	cp hist.env .env
	clear && uv run python src/main.py

build:
	docker build -f Dockerfile -t ingest-demand .

run-live: build
	docker run -it \
	--network redpanda_network \
	-e KAFKA_BROKER_ADDRESS=redpanda:9092 \
	--entrypoint /bin/sh \
	ingest-demand \
	-c "cp live.env .env && python src/main.py"

run-hist: build
	docker run -it \
	--network redpanda_network \
	-e KAFKA_BROKER_ADDRESS=redpanda:9092 \
	--entrypoint /bin/sh \
	ingest-demand \
	-c "cp hist.env .env && python src/main.py"

lint:
	ruff check --fix

format:
	ruff format .