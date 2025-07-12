# US Electricity Weather Feature Store

A streaming microservice for transforming enriched weather data and storing it in **Hopsworks** Feature Store for downstream machine learning applications. It ingests data from a Kafka topic, performs time-based feature engineering, and writes region-specific data into Hopsworks.

## Features

- ✅ Real-time ingestion of enriched weather data via Kafka
- ✅ Time-based and cyclic feature transformations (e.g., hour, day of week, month)
- ✅ Seamless integration with Hopsworks Feature Store
- ✅ Environment-based configuration using `.env` and `pydantic`
- ✅ Graceful shutdown handling (`SIGINT`, `SIGTERM`)


Each message is parsed, enriched with cyclic and temporal features, and written into a Hopsworks feature group with support for historical or live data labeling.

## Prerequisites

- Python 3.12.9
- Access to [Hopsworks](https://www.hopsworks.ai/)
- Kafka (broker and topic configured)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-org/weather-feature-store.git
   cd weather-feature-store
   ```

2. Set up Python environment (recommended: `pyenv` + `uv`):

   ```bash
   pyenv install 3.12.9
   pyenv local 3.12.9
   uv pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the root directory with the following keys:

```env
KAFKA_BROKER_ADDRESS=your_kafka_broker
KAFKA_INPUT_TOPIC=your_input_topic
KAFKA_CONSUMER_GROUP=your_consumer_group

FEATURE_GROUP_NAME=weather_features
FEATURE_GROUP_VERSION=1
FEATURE_GROUP_PRIMARY_KEYS=region
FEATURE_GROUP_EVENT_TIME=timestamp_ms

LIVE_OR_HISTORICAL=live
```

You must also be authenticated to your Hopsworks instance (e.g., via API key or CLI login).

## Running the Service

### Development Mode

```bash
make run-dev
```

### Docker Mode

```bash
make run
```

## Data Format

Expected input format (Kafka message):

```json
{
  "region": "CAL",
  "timestamp_ms": 1720483200000,
  "temperature": 27.5,
  "humidity": 55.0,
  "wind_speed": 4.1,
  "precipitation": 0.0
}
```

After transformation, the following features are derived and stored:

```json
{
  "region": "CAL",
  "timestamp_ms": 1720483200000,
  "temperature": 27.5,
  "humidity": 55.0,
  "wind_speed": 4.1,
  "precipitation": 0.0,
  "hour_sin": 0.5,
  "hour_cos": -0.5,
  "day_of_week_sin": 0.866,
  "day_of_week_cos": 0.5,
  "month_sin": 0.707,
  "month_cos": 0.707
}
```

## Code Structure

- `main.py`: Service entry point and Kafka stream setup
- `sinks.py`: Handles transformation and writing to Hopsworks
- `config.py`: Defines and loads environment variables using `pydantic`

## Dependencies

- `hopsworks`: Python SDK for writing to Hopsworks
- `loguru`: Structured logging
- `quixstreams`: Kafka client for real-time ingestion
- `pydantic`: Environment variable management and validation

## Graceful Shutdown

The service handles `SIGINT` and `SIGTERM` signals to cleanly stop Kafka consumers and ensure data is flushed to Hopsworks before shutdown.

## Notes

- Only **Hopsworks** is supported as the feature store — other systems are not configured or supported in this implementation.
- The `LIVE_OR_HISTORICAL` flag tags features to indicate whether they are part of a real-time or backfill pipeline.

## Future Enhancements

- Support additional weather attributes (e.g., solar radiation, snow depth)
- Expand region coverage and multi-topic handling
- Add metrics and monitoring for ingestion performance and feature freshness
- Enhance error handling and retry logic for Hopsworks failures

---

## License

MIT License

---

## Contact

For issues or collaboration, contact: `jlozanol@protonmail.com`