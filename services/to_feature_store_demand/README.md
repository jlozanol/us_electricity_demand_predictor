# US Electricity Demand Feature Store

A Python service for ingesting, processing, and storing enriched U.S. electricity demand data in a feature store. This system is designed for real-time machine learning pipelines, using Kafka for data ingestion and supporting extensible feature store backends.

---

## 🚀 Features

- Real-time ingestion via Kafka
- Feature engineering and enrichment of electricity demand data
- Writes to a feature store (Hopsworks)
- Signal-based graceful shutdown for reliability
- Modular and configurable via environment variables

---

## 📦 Prerequisites

- Python 3.12.9
- Kafka broker instance
- Feature store backend (e.g., Hopsworks, Redis, or DynamoDB)
- `make`, `uv`, and optionally Docker

---

## 🛠️ Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd <project-directory>

# Set Python version
pyenv install 3.12.9
pyenv local 3.12.9

# Install dependencies with uv
uv pip install -r requirements.txt
```

---

## ⚙️ Configuration

Create a `.env` file in the root directory with the following keys:

```env
KAFKA_BROKER_ADDRESS=your_kafka_broker
KAFKA_INPUT_TOPIC=your_input_topic_name
KAFKA_CONSUMER_GROUP=your_kafka_consumer_group
FEATURE_GROUP_NAME=hopsworks_feature_group
FEATURE_GROUP_VERSION=hopsworks_feature_group_version
FEATURE_GROUP_PRIMARY_KEYS=your_primary_key
FEATURE_GROUP_EVENT_TIME=timestamp_ms
FEATURE_STORE_BACKEND=hopsworks|redis|dynamodb
LIVE_OR_HISTORICAL=live|historical
```

---

## ▶️ Running the Service

### Development Mode

```bash
make run-dev
```

### Docker Mode

```bash
make run
```

---

## 📄 Data Format

Each record must follow the format:

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
- `region`: Regional code (e.g., CAL, MIDA)
- `timestamp_ms`: Unix timestamp in milliseconds
- `features`: Dictionary of engineered features

---

## 🧩 Architecture

### `main.py`
- Sets up and runs the Kafka stream processing pipeline.
- Handles signal-based shutdown.

### `sinks.py`
- Defines sink classes for different feature store backends.
- Implements `write_to_store()` method based on the backend.

### `config.py`
- Loads configuration from environment variables using Pydantic.

---

## 📚 Dependencies

- [`loguru`](https://github.com/Delgan/loguru) – Structured logging
- [`quixstreams`](https://github.com/quixio/quix-streams) – Kafka streaming
- [`pydantic`](https://docs.pydantic.dev) – Configuration and validation
- [`hopsworks`](https://github.com/logicalclocks/hopsworks) feature store client

---

## 🧪 Development Notes

- Use `make run-dev` to test changes locally.
- Extend the `Sink` class in `sinks.py` to support new feature store targets.
- Add unit tests (suggested improvement) to validate sink behavior and stream transformations.

---

## 🔮 Future Enhancements

- Add retry and error logging for feature store writes
- Implement monitoring and alerting for failed ingestions
- Extend support for other messaging platforms (e.g., Pulsar)

---

## 🧼 Graceful Shutdown

The service listens for termination signals (`SIGINT`, `SIGTERM`) and ensures a clean shutdown of Kafka consumers and resource deallocation.

---

## License

MIT License

---

## Contact

For issues or collaboration, contact: `jlozanol@protonmail.com`