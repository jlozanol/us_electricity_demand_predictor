# US Electricity Weather Data Ingestor

This service `demand_predictor` ingests historical weather data relevant to electricity demand forecasting. It fetches weather data via Open-Meteo API and publishes structured data to a Kafka topic using Quix Streams. The project is designed to be modular, fault-tolerant, and configurable by region and time range.

## Features

- Historical weather data ingestion
- Support for multiple weather attributes:
  - Temperature
  - Humidity
  - Wind speed
  - Precipitation
- Configurable region-based data collection
- Kafka integration via Redpanda (through Quix Streams)
- Automatic retry logic with exponential backoff for failed API calls
- Graceful shutdown using signal interception (`SIGINT`, `SIGTERM`)
- Logging with `loguru`

## Prerequisites

- Python 3.12.9
- Docker (for Redpanda broker)
- Open-Meteo API (no key required)

## Installation

1. Clone the repository and set up the Python environment:

   ```bash
   pyenv install 3.12.9
   pyenv local 3.12.9
   ```

2. Install dependencies using `uv`:

   ```bash
   uv pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file with the following variables:

```env
KAFKA_BROKER_ADDRESS=your_kafka_broker
KAFKA_TOPIC=your_topic_name
LAST_N_DAYS=7
LIVE_OR_HISTORICAL=historical
```

> Note: Currently only `historical` mode is implemented.

### Regions Supported

The service supports region names mapped to geographical coordinates, configured in `config.py`:

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
make run-dev
```

### Docker Mode

```bash
make run
```

## Output Data Format

Each published message conforms to the following structure:

```json
{
  "timestamp_ms": 1627857600000,
  "region": "CAL",
  "temperature": 27.3,
  "humidity": 55.4,
  "wind_speed": 3.1,
  "precipitation": 0.0
}
```

- `timestamp_ms`: Unix timestamp in milliseconds
- `region`: Regional code
- `temperature`: °C
- `humidity`: Percentage
- `wind_speed`: m/s
- `precipitation`: mm

## Key Modules

- `main.py`: Entry point for fetching and publishing weather data
- `config.py`: Region configuration and runtime environment variables

## Dependencies

- `loguru`: Structured logging
- `quixstreams`: Kafka publishing via Quix SDK
- `pydantic`: Environment variable management
- `requests`: HTTP communication with weather API

## Development Notes

- Retries are implemented using simple retry loops with wait intervals.
- The Kafka producer uses Quix Streams with Avro serialization disabled for simplicity.
- The service uses UTC timestamps across all data points.

## Future Enhancements

- Implement `live` ingestion mode
- Add CLI interface for custom time range inputs
- Add Prometheus metrics for ingestion performance
- Improve resilience on producer exceptions

---

## License

MIT License

---

## Contact

For issues or collaboration, contact: `jlozanol@protonmail.com`