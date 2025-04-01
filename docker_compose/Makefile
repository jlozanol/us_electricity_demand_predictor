start-redpanda:
	docker compose -f redpanda.yml up -d

stop-redpanda:
	docker compose -f redpanda.yml down

# Technical indicators pipeline management
build-demand-hist-pipeline:
	@echo "Removing all Kafka topics that contain the word historical"
	docker compose -f redpanda.yml exec redpanda rpk topic delete -r ".*hist.*"
	RUN_ID="" docker compose -f electricity_demand_historical_pipeline.yml build

start-demand-hist-pipeline: build-demand-hist-pipeline
	$(eval RUN_ID := $(shell uuidgen))
	@echo "Starting backfill with RUN_ID: $(RUN_ID)"
	RUN_ID=$(RUN_ID) docker compose -f electricity_demand_historical_pipeline.yml up -d

stop-demand-hist-pipeline:
	docker compose -f electricity_demand_historical_pipeline.yml down

clean-backfill-kakfa-topics:
	@echo "Removing all Kafka topics that contain the word historical"
	docker compose -f redpanda.yml exec redpanda rpk topic delete -r ".*hist.*"
