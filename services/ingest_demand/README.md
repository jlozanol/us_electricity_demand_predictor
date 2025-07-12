# ⚡ US Electricity Demand Ingestion Microservice

A Python-based data ingestion service for collecting and publishing hourly electricity demand metrics from the **U.S. Energy Information Administration (EIA)** API. Supports **historical** (and in the future, **live**) data retrieval for multiple U.S. regions and streams the results to a **Kafka** topic via **Redpanda**.

---

## 🚀 Features

- ⏱ Historical electricity demand ingestion (live mode planned)
- 🌍 Multi-region support (configurable)
- 📦 Supports multiple metrics:
  - **D**: Actual Demand  
  - **DF**: Day-Ahead Forecast  
  - **TI**: Total Interchange  
  - **NG**: Net Generation  
- 🔁 Automatic retries on API failure
- 📤 Kafka (Redpanda) integration
- 📦 Environment-based configuration with Pydantic
- 🧹 Graceful shutdown via signal interception

---

## 🧰 Prerequisites

- Python 3.12.9
- [Docker](https://www.docker.com/) (for Redpanda)
- EIA API Key ([Get yours here](https://www.eia.gov/opendata/))

---

## ⚙️ Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/us-electricity-demand-predictor.git
   cd us-electricity-demand-predictor
   ```

2. **Set up Python environment**

   ```bash
   pyenv install 3.12.9
   pyenv local 3.12.9
   ```

3. **Install dependencies**

   Using [uv](https://github.com/astral-sh/uv):

   ```bash
   uv pip install -r requirements.txt
   ```

---

## 🔧 Configuration

Create a `.env` file at the root directory with the following environment variables:

```env
EIA_API_KEY=your_api_key
KAFKA_BROKER_ADDRESS=localhost:9092
KAFKA_TOPIC=electricity-demand
REGION_NAMES=CAL,MIDA,NE             # Comma-separated list
LAST_N_DAYS=7                        # Number of past days to fetch (historical mode)
LIVE_OR_HISTORICAL=historical       # Only 'historical' is currently supported
```

### ✅ Supported Regions

| Code  | Region       |
|-------|--------------|
| CAL   | California   |
| CAR   | Carolinas    |
| CENT  | Central      |
| FLA   | Florida      |
| MIDW  | Midwest      |
| NW    | Northwest    |
| NY    | New York     |
| SW    | Southwest    |

---

## ▶️ Running the Service

### 🧪 Development Mode

```bash
make run-dev
```

### 🐳 Docker Mode

```bash
make run
```

> 🔄 Both modes currently support **historical** data collection only.

---

## 📊 Output Format

Each Kafka message is a JSON object:

```json
{
  "timestamp_ms": 1723456800000,
  "human_read_period": "2025-07-10T15",
  "region": "CAL",
  "demand": 1000.0,
  "forecast": 1050.0,
  "ti": -250.0,
  "ng": 750.0
}
```

### Field Descriptions

- `timestamp_ms`: Unix timestamp (milliseconds)
- `human_read_period`: Timestamp in "YYYY-MM-DDTHH" format
- `region`: Region code (e.g., CAL, MIDA)
- `demand`: Actual demand in MWh
- `forecast`: Forecasted demand in MWh
- `ti`: Total interchange in MWh
- `ng`: Net generation in MWh

---

## 🧩 Key Components

- **`main.py`**  
  Coordinates the ingestion loop, shutdown signals, and Kafka publishing.

- **`config.py`**  
  Loads and validates configuration using `pydantic`.

- **Data Retrieval**  
  Queries EIA API for specified metrics per region and parses results.

- **Kafka Producer**  
  Uses `quixstreams` to stream processed JSON data to the configured topic.

---

## 📦 Dependencies

- [`loguru`](https://github.com/Delgan/loguru) – Logging
- [`pydantic`](https://docs.pydantic.dev/) – Config management
- [`quixstreams`](https://quix.io/docs/streaming/quixstreams.html) – Kafka integration
- [`requests`](https://docs.python-requests.org/) – HTTP API calls

---

## 📝 Development Notes

- `LAST_N_DAYS` controls the historical fetch range (default: 7).
- Graceful shutdown via `SIGINT` and `SIGTERM`.
- Kafka topic and broker are `.env` configurable.
- "Live" data mode is **planned but not yet implemented**.

---

## 🛠 Future Improvements

- [ ] Full implementation of **live** data mode  
- [ ] Support more EIA metrics  
- [ ] Robust Kafka failure handling  
- [ ] Monitoring and alerting (e.g., Prometheus, Grafana)

---

## License

MIT License

---

## Contact

For issues or collaboration, contact: `jlozanol@protonmail.com`