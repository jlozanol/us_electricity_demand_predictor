# US Electricity Weather Feature Store

A service for transforming enriched weather data and storing it in a feature store for downstream machine learning applications. The service reads data from a Kafka topic, processes it, and writes it to a feature store.

## Features

- Integration with Kafka for real-time weather data ingestion
- Transformation of enriched weather data into feature store-ready format
- Configurable feature retention policies
- Graceful shutdown handling with signal interception

## Prerequisites

- Python 3.12.9
- Kafka
- Feature store backend (e.g., Redis, DynamoDB, or other supported systems)

## Installation

1. Clone the repository.
2. Set up the Python environment:

   ```bash
   pyenv install 3.12.9
   pyenv local 3.12.9
   ```

3. Install dependencies using `uv`:

   ```bash
   uv pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file with the following variables:

```env
KAFKA_BROKER_ADDRESS=your_kafka_broker
KAFKA_INPUT_TOPIC=your_input_topic_name
KAFKA_CONSUMER_GROUP=your_kafka_consumer_group
FEATURE_GROUP_NAME=hopsworks_feature_group
FEATURE_GROUP_VERSION=hopsworks_feature_group_version
FEATURE_GROUP_PRIMARY_KEYS=your_primary_key
FEATURE_GROUP_EVENT_TIME=timestamp_ms
LIVE_OR_HISTORICAL=historical_or_live
```

## Running the Service

### Development Mode

```bash
# Run the service in development mode
make run-dev
```

### Docker Mode

```bash
# Run the service in Docker
make run
```

## Data Format

The service processes and stores data in the following format:

```json
{
  "region": "REGION_CODE",
  "timestamp_ms": 1234567890000,
  "features": {
    "temperature": 25.0,
    "humidity": 60.0,
    "wind_speed": 5.0,
    "precipitation": 0.0,
    "hour_sin": 0.5,
    "hour_cos": -0.5,
    "day_of_week_sin": 0.866,
    "day_of_week_cos": 0.5,
    "month_sin": 0.707,
    "month_cos": 0.707
  }
}
```

Where:

- `region`: Regional identifier (e.g., CAL, MIDA)
- `timestamp_ms`: Unix timestamp in milliseconds
- `features`: Dictionary of computed weather features for the given timestamp and region

## Key Functions

- **Kafka Integration**: Reads enriched weather data from a Kafka topic.
- **Feature Transformation**: Converts enriched data into a format suitable for the feature store.
- **Feature Store Integration**: Writes transformed data to the configured feature store backend.
- **Graceful Shutdown**: Handles termination signals (`SIGINT`, `SIGTERM`) to ensure clean shutdown of the service.

## Dependencies

- `loguru`: For logging
- `quixstreams`: For Kafka integration
- `pydantic`: For configuration management
- `hopsworks`: Feature store

## Development Notes

- The service uses `loguru` for detailed logging, including feature transformation and storage errors.
- The `FEATURE_STORE_BACKEND` configuration determines the feature store system to use.
- The service is designed to be extendable for additional feature store backends.

## Future Enhancements

- Add support for additional weather attributes or regions.
- Implement advanced error handling for feature store writes.
- Add monitoring and alerting for feature ingestion failures.