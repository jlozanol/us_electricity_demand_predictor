# US Electricity Demand Feature Store

A service for transforming enriched electricity demand data and storing it in a feature store for downstream machine learning applications. The service reads data from a Kafka topic, processes it, and writes it to a feature store.

## Features

- Integration with Kafka for real-time data ingestion
- Enriched demand data into feature store-ready format
- Graceful shutdown handling with signal interception

## Prerequisites

- Python 3.12.9
- Kafka
- hopsworks feature store

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
    "full_mean": 1000.0,
    "mean_3": 950.0,
    "mean_24": 1020.0,
    "lag_1h": 980.0,
    "lag_24h": 1010.0,
    "lag_168h": 990.0,
    "hour_category_num": 2,
    "is_holiday": 0
  }
}
```

Where:

- `region`: Regional identifier (e.g., CAL, MIDA)
- `timestamp_ms`: Unix timestamp in milliseconds
- `features`: Dictionary of computed features for the given timestamp and region

## Key Functions

- **Kafka Integration**: Reads enriched demand data from a Kafka topic.
- **Feature Store Integration**: Writes transformed data to the configured feature store backend.
- **Graceful Shutdown**: Handles termination signals (`SIGINT`, `SIGTERM`) to ensure clean shutdown of the service.

## Dependencies

- `loguru`: For logging
- `quixstreams`: For Kafka integration
- `pydantic`: For configuration management
- Feature store-specific libraries (e.g., `redis`, `boto3` for DynamoDB)

## Development Notes

- The service uses `loguru` for detailed logging, including feature transformation and storage errors.
- The `FEATURE_STORE_BACKEND` configuration determines the feature store system to use.
- The service is designed to be extendable for additional feature store backends.

## Future Enhancements

- Add support for additional feature store backends.
- Implement advanced error handling for feature store writes.
- Add monitoring and alerting for feature ingestion failures.