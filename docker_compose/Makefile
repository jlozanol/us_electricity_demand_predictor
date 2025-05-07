start-redpanda:
	docker compose -f redpanda.yml up -d

stop-redpanda:
	docker compose -f redpanda.yml down

# Historical pipeline management
build-hist-pipeline:
	@echo "Removing all Kafka topics that contain the word historical"
	docker compose -f redpanda.yml exec redpanda rpk topic delete -r ".*_hist.*"
	RUN_ID="" docker compose -f historical_pipeline.yml build

start-hist-pipeline: build-hist-pipeline
	$(eval RUN_ID := $(shell uuidgen))
	@echo "Starting backfill with RUN_ID: $(RUN_ID)"
	RUN_ID=$(RUN_ID) docker compose -f historical_pipeline.yml up -d

stop-hist-pipeline:
	docker compose -f historical_pipeline.yml down

clean-backfill-kafka-topics:
	@echo "Removing all Kafka topics that contain the word historical"
	docker compose -f redpanda.yml exec redpanda rpk topic delete -r ".*_hist.*"
