# Feature Demand Service

## Overview

The `feature_demand` service processes electricity demand data from Kafka, generates enriched features, and outputs the processed data to another Kafka topic. It supports both live and historical processing modes.

## Features

- **Time-based Feature Engineering**: Adds cyclical encodings for hour, day of the week, and month, along with holiday indicators and hour categorization.
- **Sliding Window Management**: Maintains a historical sliding window of data points for statistical computations.
- **Statistical Feature Computation**: Computes rolling statistics (mean, median) and lag features for demand data.
- **Inactivity Handling**: Automatically shuts down in historical mode if no messages are received for a configurable timeout period.

## File Structure

- `src/main.py`: Main script containing the feature engineering logic and Kafka integration.

## Requirements

- Python 3.12.9
- Kafka
- Required Python libraries:
  - `numpy`
  - `holidays`
  - `loguru`
  - `quixstreams`

## Configuration

The service uses a `config` module to load the following parameters:

- `kafka_broker_address`: Address of the Kafka broker.
- `kafka_input_topic`: Name of the Kafka topic to read raw demand data from.
- `kafka_output_topic`: Name of the Kafka topic to write enriched data to.
- `kafka_consumer_group`: Kafka consumer group name.
- `live_or_historical`: Mode of operation (`live` or `historical`).

## Usage

### Running the Service

1. Ensure the required dependencies are installed.
2. Configure the `config` module with the appropriate Kafka settings.
3. Run the service:

   ```bash
   python src/main.py
   ```

### Modes of Operation

- **Live Mode**: Processes data in real-time. (Currently not implemented in detail.)
- **Historical Mode**: Processes historical data from the beginning of the Kafka topic.

### Key Functions

- `add_time_data`: Adds time-based features to each data point.
- `update_window`: Maintains a sliding window of historical data points.
- `compute_rolling_values`: Computes statistical features from the sliding window.
- `check_inactivity`: Monitors inactivity and shuts down the service if no messages are received for a specified timeout.

## Example Workflow

1. **Input**: Raw demand data from the Kafka input topic.
2. **Processing**:
   - Add time-based features.
   - Maintain a sliding window of historical data.
   - Compute rolling statistics and lag features.
3. **Output**: Enriched data is sent to the Kafka output topic.

## Development Notes

- The service uses `loguru` for logging and `quixstreams` for Kafka integration.
- The `MAX_WINDOW_IN_STATE` constant defines the maximum number of hourly data points to retain in the sliding window (default: 168 hours or 1 week).
- The `IDLE_TIMEOUT` constant specifies the inactivity timeout in seconds (default: 20 seconds).

## Future Enhancements

- Implement detailed logic for live mode processing.
- Add support for additional statistical features or custom feature engineering.
- Improve configuration flexibility (e.g., via environment variables).