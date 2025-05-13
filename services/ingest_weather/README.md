# US Electricity Weather Data Ingestor

A service for ingesting weather data relevant to electricity demand forecasting. The service fetches weather data from a weather API, processes it, and publishes the data to a Kafka topic. It supports both live and historical data collection.

## Features

- Real-time weather data ingestion
- Historical weather data batch processing
- Support for multiple weather attributes:
  - Temperature
  - Humidity
  - Wind speed
  - Precipitation
- Configurable multi-region data collection
- Kafka integration using Redpanda
- Automatic retries for failed API requests
- Graceful shutdown handling with signal interception

## Prerequisites

- Python 3.12.9
- Docker (for Redpanda)
- Weather API key (obtain from your preferred weather API provider)

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
KAFKA_TOPIC=your_topic_name
REGION_NAMES=CAL,MIDA,NE  # Comma-separated list of regions
LAST_N_DAYS=7
LIVE_OR_HISTORICAL=live|historical
```

### Available Regions

The service supports the following regions (or cities, depending on the API):

- CAL: California
- MIDA: Mid-Atlantic
- NE: New England
- NY: New York
- TEX: Texas
- Additional regions can be configured as needed.

## Running the Service

### Development Mode

```bash
# For live data collection
make run-live-dev

# For historical data collection
make run-hist-dev
```

### Docker Mode

```bash
# For live data collection
make run-live

# For historical data collection
make run-hist
```

## Data Format

The service processes and publishes data in the following format:

```json
{
  "timestamp_ms": 1234567890000,
  "region": "REGION_CODE",
  "temperature": 25.0,
  "humidity": 60.0,
  "wind_speed": 5.0,
  "precipitation": 0.0
}
```

Where:

- `timestamp_ms`: Unix timestamp in milliseconds
- `region`: Regional identifier (e.g., CAL, MIDA)
- `temperature`: Temperature in degrees Celsius
- `humidity`: Humidity percentage
- `wind_speed`: Wind speed in meters per second
- `precipitation`: Precipitation in millimeters

## Key Functions

- **Data Ingestion**: Fetches weather data from the API for specified regions and time periods.
- **Error Handling**: Implements retries for failed API requests and logs errors for debugging.
- **Kafka Integration**: Publishes processed data to a Kafka topic for downstream processing.
- **Graceful Shutdown**: Handles termination signals (`SIGINT`, `SIGTERM`) to ensure clean shutdown of the service.

## Dependencies

- `loguru`: For logging
- `quixstreams`: For Kafka integration
- `pydantic`: For configuration management
- `requests`: For API calls

## Development Notes

- The service uses `loguru` for detailed logging, including retries and API errors.
- The `LAST_N_DAYS` configuration determines the range of historical data to fetch in `historical` mode.
- The `LIVE_OR_HISTORICAL` configuration toggles between live and historical data collection.

## Future Enhancements

- Add support for additional weather attributes or regions.
- Implement advanced error handling for Kafka publishing.
- Add monitoring and alerting for data ingestion failures.