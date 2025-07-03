# US Electricity ML Training Platform

A modular, end-to-end machine learning platform for forecasting electricity demand across US regions. The system ingests, processes, and stores both electricity demand and weather data, engineers features, and provides real-time and historical predictions via a Streamlit dashboard. The architecture is composed of loosely coupled microservices communicating via Kafka and feature stores.

---

## Architecture Overview

```
+-------------------+      +-------------------+      +-------------------+      +-------------------+      +-------------------+
| Ingest Demand     | ---> | Feature Demand    | ---> | To Feature Store  | ---> | Model Inference   | ---> | Streamlit         |
| Service           |      | Service           |      | Demand Service    |      | Client            |      | Dashboard         |
+-------------------+      +-------------------+      +-------------------+      +-------------------+      +-------------------+
        |                        |                        |                        |                        |
        v                        v                        v                        v                        v
+-------------------+      +-------------------+      +-------------------+      +-------------------+      +-------------------+
| Ingest Weather    | ---> | Feature Weather   | ---> | To Feature Store  | ---> | Model Inference   | ---> | Streamlit         |
| Service           |      | Service           |      | Weather Service   |      | Client            |      | Dashboard         |
+-------------------+      +-------------------+      +-------------------+      +-------------------+      +-------------------+
```

- **Kafka** is used for inter-service communication.
- **Feature Store** (e.g., Hopsworks, Redis, DynamoDB) is used for storing engineered features.
- **Model Registry** is used for storing and retrieving ML model artifacts.

---

## Microservices

### 1. Ingest Demand Service
- Fetches hourly electricity demand data from the EIA API for multiple US regions.
- Publishes raw demand data to a Kafka topic.
- Supports both live and historical ingestion (historical mode implemented).

### 2. Ingest Weather Service
- Fetches weather data (temperature, humidity, wind speed, precipitation) from a weather API.
- Publishes raw weather data to a Kafka topic.
- Supports both live and historical ingestion (historical mode implemented).

### 3. Feature Demand Service
- Consumes raw demand data from Kafka.
- Engineers time-based and statistical features (rolling means, lags, cyclical encodings, holiday indicators).
- Publishes enriched demand features to a Kafka topic.

### 4. Feature Weather Service
- Consumes raw weather data from Kafka.
- Engineers weather features (cyclical encodings, normalization, etc.).
- Publishes enriched weather features to a Kafka topic.

### 5. To Feature Store Demand/Weather Services
- Consumes enriched features from Kafka.
- Writes features to the configured feature store backend (e.g., Hopsworks, Redis, DynamoDB).
- Supports configurable retention and graceful shutdown.

### 6. Inference Client (Streamlit Dashboard)
- Loads latest model artifacts from the model registry.
- Fetches and synchronizes demand and weather features.
- Provides real-time and historical demand predictions.
- Interactive dashboard for visualization and analysis.

---

## Getting Started

### Prerequisites

- Python 3.12.9 (or 3.8+ for Streamlit client)
- Docker (for Kafka/Redpanda)
- EIA API key (for demand ingestion)
- Weather API key (for weather ingestion)
- Kafka broker
- Feature store backend (e.g., Hopsworks, Redis, DynamoDB)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd us_electricity
   ```

2. **Set up Python environment**
   ```bash
   pyenv install 3.12.9
   pyenv local 3.12.9
   ```

3. **Install dependencies**
   ```bash
   uv pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Create a `.env` file in each service directory as described in their respective READMEs.

---

## Running the Platform

Each microservice can be run independently. See each service's README for details. Example for historical demand ingestion:

```bash
cd services/ingest_demand
make run-dev
```

To launch the Streamlit dashboard:

```bash
cd services/inference_client
streamlit run src/main.py
```

---

## Data Flow

1. **Ingestion**: Demand and weather data are fetched from external APIs and published to Kafka.
2. **Feature Engineering**: Feature services consume raw data, engineer features, and publish to Kafka.
3. **Feature Store**: Enriched features are written to the feature store for downstream ML use.
4. **Inference**: The dashboard fetches features and model artifacts, performs predictions, and visualizes results.

---

## Configuration

Each service uses a `.env` file for configuration. Common variables include:

```env
KAFKA_BROKER_ADDRESS=your_kafka_broker
KAFKA_INPUT_TOPIC=your_input_topic
KAFKA_OUTPUT_TOPIC=your_output_topic
KAFKA_CONSUMER_GROUP=your_consumer_group
FEATURE_GROUP_NAME=your_feature_group
FEATURE_GROUP_VERSION=your_feature_group_version
FEATURE_GROUP_PRIMARY_KEYS=your_primary_key
FEATURE_GROUP_EVENT_TIME=timestamp_ms
LIVE_OR_HISTORICAL=historical|live
EIA_API_KEY=your_eia_api_key
WEATHER_API_KEY=your_weather_api_key
```

---

## Development Notes

- All services use `loguru` for logging and `quixstreams` for Kafka integration.
- Feature engineering is modular and can be extended for new features or regions.
- The platform is designed for easy extension and integration with new data sources, feature stores, or ML models.

---

## Future Enhancements

- Seamless integration of live and historical pipelines.
- Support for additional regions, data types, and feature stores.
- Advanced error handling, monitoring, and alerting.
- Automated model retraining and deployment.

---

## Contributing

Contributions are welcome! Please fork the repository, create a feature branch, and submit a pull request. For issues or feature requests, open an issue on GitHub.

---
