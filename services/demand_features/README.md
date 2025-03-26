# Electricity Demand Features Service

A service for processing electricity demand data and generating time-based features for machine learning models. This service consumes data from a Kafka topic, adds time-related features, and publishes the enriched data to another Kafka topic.

## Features

- Consumes electricity demand data from Kafka
- Adds time-based features:
  - Cyclical encoding of hour of day (sin/cos)
  - Cyclical encoding of day of week (sin/cos)
  - Cyclical encoding of month (sin/cos)
  - Holiday indicator for US holidays
- Publishes enriched data to a feature store via Kafka

## Prerequisites

- Python 3.12.9
- Docker (for Redpanda)
- Kafka broker (Redpanda recommended)

## Installation

1. Clone the repository
2. Set up Python environment:

   ```bash
   pyenv install 3.12.9
   pyenv local 3.12.9
   ```

3. Install dependencies using uv:
   ```bash
   uv pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file with the following variables:

```env
KAFKA_BROKER_ADDRESS=your_kafka_broker
KAFKA_INPUT_TOPIC=input_topic_name
KAFKA_OUTPUT_TOPIC=output_topic_name
KAFKA_CONSUMER_GROUP=consumer_group_name
REGION_NAMES=CAL,MIDA,NE  # Comma-separated list of regions
LIVE_OR_HISTORICAL=live|historical
```

### Available Regions

The service supports the following regions:

- CAL: California
- CAR: Carolinas
- CENT: Central
- FLA: Florida
- MIDA: Mid-Atlantic
- MIDW: Midwest
- NE: New England
- NW: Northwest
- NY: New York
- SE: Southeast
- SW: Southwest
- TEN: Tennessee
- TEX: Texas

## Running the Service

### Development Mode

```bash
# For live data processing
make run-live-dev

# For historical data processing
make run-hist-dev
```

### Docker Mode

```bash
# For live data processing
make run-live

# For historical data processing
make run-hist
```

## Data Format

### Input Data Format

The service expects input data in the following format:

```json
{
  "timestamp_ms": 1234567890000,
  "human_read_period": "YYYY-MM-DDTHH",
  "region": "REGION_CODE",
  "demand": 1000.0,
  "forecast": 1050.0,
  "ti": -250.0,
  "ng": 750.0
}
```

### Output Data Format

The service enriches the input data with the following features:

```json
{
  "timestamp_ms": 1234567890000,
  "human_read_period": "YYYY-MM-DDTHH",
  "region": "REGION_CODE",
  "demand": 1000.0,
  "forecast": 1050.0,
  "ti": -250.0,
  "ng": 750.0,
  "is_holiday": 0,
  "hour_sin": 0.0,
  "hour_cos": 1.0,
  "day_of_week_sin": 0.7818,
  "day_of_week_cos": 0.6234,
  "month_sin": 0.5,
  "month_cos": 0.866
}
```

## Dependencies

- holidays: For US holiday detection
- loguru: For logging
- numpy: For mathematical operations
- quixstreams: For Kafka integration
- pydantic: For configuration management

## Development

```bash
# Run linting
make lint

# Run formatting
make format
```
