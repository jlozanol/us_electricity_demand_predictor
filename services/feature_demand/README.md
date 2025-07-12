# Feature Demand Service

## Overview

The service `feature_demand` processes electricity demand data streamed via Kafka. It performs real-time or batch (historical) feature engineering to enrich the data for downstream modeling or analytics.

> ✅ Currently, only **historical mode** is implemented.

---

## Features

- ⏱️ **Time-based Feature Engineering**
  - Cyclical encoding of hour, day of week, and month.
  - Holiday and weekend flags.
  - Hour-of-day categorization (e.g., morning, peak hours).

- 📊 **Sliding Window & Statistical Features**
  - Maintains a rolling window of historical demand data.
  - Computes rolling mean, median, and lag features.

- ⚠️ **Inactivity Handling (Historical Mode)**
  - Automatically stops if no messages are received for a configurable idle timeout.

- ⚙️ **Kafka Integration**
  - Streams data from an input topic, enriches it, and publishes to an output topic.

---

## Project Structure

```plaintext
src/
├── config.py       # Configuration loader (env-based)
└── main.py         # Main logic: Kafka consumption, feature engineering, streaming
```

---

## Installation & Requirements

- Python 3.12.9
- Kafka cluster or broker
- Required Python libraries:

```bash
pip install numpy holidays loguru quixstreams
```

You can also create a `requirements.txt` with:

```txt
numpy
holidays
loguru
quixstreams
```

---

## Configuration

The service reads Kafka and pipeline settings from environment variables. Create a `.env` file in the root directory with the following:

```env
KAFKA_BROKER_ADDRESS=your_kafka_broker_ip
KAFKA_INPUT_TOPIC=raw_demand_topic
KAFKA_OUTPUT_TOPIC=processed_demand_topic
KAFKA_CONSUMER_GROUP=feature_demand_consumer
LIVE_OR_HISTORICAL=historical  # Only 'historical' supported at the moment
```

---

## Running the Service

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the feature demand processor:

```bash
python src/main.py
```

---

## Core Functions

| Function | Description |
|----------|-------------|
| `add_time_data(df)` | Adds time-based features (hour, weekday, holiday, cyclical encodings). |
| `update_window(key, df, window_data)` | Maintains and updates a sliding window of recent demand values for each key. |
| `compute_rolling_values(df, window_data)` | Computes rolling statistics (mean, median, lag) for each data point. |
| `check_inactivity(last_msg_time)` | Shuts down the service if no new messages are received within a timeout window. |

---

## Example Workflow

1. **Input**: Raw hourly demand data (timestamp + value) from Kafka input topic.
2. **Processing**:
   - Adds timestamp-derived features.
   - Tracks demand history per region.
   - Computes statistical summaries (rolling mean, lag).
3. **Output**: Enriched demand data written to the Kafka output topic.

---

## Development Notes

- Uses `loguru` for structured logging.
- Uses `quixstreams` for Kafka message streaming.
- Constants:
  - `MAX_WINDOW_IN_STATE = 168` → max hours of demand history (7 days).
  - `IDLE_TIMEOUT = 20` → service timeout if no data received (in seconds).
- Region ID is derived from the `tag` field of each input message.

---

## Future Enhancements

- ⚡ Add full support for **live** mode streaming.
- 🧠 Expand statistical features (e.g., standard deviation, trend detection).
- 🛠️ Add CLI interface or REST hooks for better monitoring and control.
- 🔧 Make configuration more flexible (e.g., config file or argument parsing).

---

## License

MIT License

---

## Contact

For issues or collaboration, contact: `jlozanol@protonmail.com`
