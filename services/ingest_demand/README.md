# US Electricity Demand Predictor

A service for ingesting hourly electricity demand data from different regions in the United States using the EIA (Energy Information Administration) API. The service supports both live and historical data collection and publishes the data to a Kafka topic.

## Features

- Real-time electricity demand data ingestion
- Historical data batch processing
- Support for both actual demand and day-ahead forecast data
- Configurable regional data collection
- Kafka integration using Redpanda

## Prerequisites

- Python 3.12.9
- Docker (for Redpanda)
- EIA API key

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
EIA_API_KEY=your_api_key
KAFKA_BROKER_ADDRESS=your_kafka_broker
KAFKA_TOPIC=your_topic_name
REGION_NAME=your_region
LAST_N_DAYS=number_of_days
LIVE_OR_HISTORICAL=live|historical
```

## Data Format

The service processes and publishes data in the following format:

```json
{
  "timestamp": 1234567890000,
  "region": "REGION_CODE",
  "electricity_demand": 1000.0,
  "electricity_demand_type": "D|DF",
  "human_readable_period": "YYYY-MM-DDTHH"
}
```

Where:

- `timestamp`: Unix timestamp in milliseconds
- `region`: Regional identifier
- `electricity_demand`: Actual demand in megawatthours (MWh)
- `electricity_demand_type`: "D" for actual demand, "DF" for day-ahead forecast
- `human_readable_period`: Human-readable timestamp

## Dependencies

- loguru: For logging
- quixstreams: For Kafka integration
- pydantic: For configuration management
- requests: For API calls
