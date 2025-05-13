# US Electricity Demand Predictor

A service for ingesting hourly electricity demand data from different regions in the United States using the EIA (Energy Information Administration) API. The service supports both live and historical data collection and publishes the data to a Kafka topic.

## Features

- Real-time electricity demand data ingestion
- Historical data batch processing
- Support for multiple data types:
  - Actual demand (D)
  - Day-ahead forecast (DF)
  - Total interchange (TI)
  - Net generation (NG)
- Configurable multi-region data collection
- Kafka integration using Redpanda
- Automatic retries for failed API requests
- Graceful shutdown handling with signal interception

## Prerequisites

- Python 3.12.9
- Docker (for Redpanda)
- EIA API key (obtain from [EIA website](https://www.eia.gov/opendata/))

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
EIA_API_KEY=your_api_key
KAFKA_BROKER_ADDRESS=your_kafka_broker
KAFKA_TOPIC=your_topic_name
REGION_NAMES=CAL,MIDA,NE  # Comma-separated list of regions
LAST_N_DAYS=7
LIVE_OR_HISTORICAL=live|historical
```

### Available Regions

The service supports the following regions:

- CAL: California
- CAR: Carolinas
- CENT: Central
- FLA: Florida
- MIDW: Midwest
- NW: Northwest
- NY: New York
- SW: Southwest

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
  "human_read_period": "YYYY-MM-DDTHH",
  "region": "REGION_CODE",
  "demand": 1000.0,
  "forecast": 1050.0,
  "ti": -250.0,
  "ng": 750.0
}
```

Where:

- `timestamp_ms`: Unix timestamp in milliseconds
- `human_read_period`: Human-readable timestamp (YYYY-MM-DDTHH)
- `region`: Regional identifier (e.g., CAL, MIDA)
- `demand`: Actual electricity demand in megawatthours (MWh)
- `forecast`: Day-ahead forecast in megawatthours (MWh)
- `ti`: Total interchange in megawatthours (MWh)
- `ng`: Net generation in megawatthours (MWh)

## Key Functions

- **Data Ingestion**: Fetches electricity demand data from the EIA API for specified regions and time periods.
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

- Add support for additional data types or regions.
- Implement advanced error handling for Kafka publishing.
- Add monitoring and alerting for data ingestion failures.