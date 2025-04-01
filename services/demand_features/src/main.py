from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple
import signal
import sys
import time

import holidays
import numpy as np
from config import config
from loguru import logger
from quixstreams import Application, State

# Maximum number of hourly data points to keep in state (1 week of hourly data)
MAX_WINDOW_IN_STATE = 168
# Timeout in seconds to wait for new messages before shutting down in historical mode
IDLE_TIMEOUT = 10

# Add a global variable to track message processing
last_message_time = 0


def custom_ts_extractor(
	value: Any,
	headers: Optional[List[Tuple[str, bytes]]],
	timestamp: float,
	timestamp_type,
) -> int:
	"""Extract timestamp from message payload instead of using Kafka timestamp."""
	return value['timestamp_ms']


def update_window(data: dict, state: State) -> dict:
	"""
	Maintain a sliding window of historical data points in state.

	Args:
		data: Current data point
		state: State object for storing persistent data

	Returns:
		The current data point (not the entire window)
	"""
	# Get existing data from state or initialize empty list
	all_data = state.get('all_data', [])

	# Handle the new data point
	if not all_data:
		# First data point
		all_data = [data]
	elif same_window(data, all_data[-1]):
		# Replace last data point if same time window
		all_data[-1] = data
	else:
		# Add new data point
		all_data.append(data)

	# Remove oldest data point if window size exceeded
	if len(all_data) > MAX_WINDOW_IN_STATE:
		all_data.pop(0)

	# Debug logging
	# logger.debug(f'Number of candles in state for {data["region"]}: {len(all_data)}')
	# logger.debug(f'Data: {all_data}')

	# Update state
	state.set('all_data', all_data)
	return data  # Return the current data point, not the entire window


def same_window(data_1: dict, data_2: dict) -> bool:
	"""Check if two data points belong to the same time window."""
	return (
		data_1['timestamp_ms'] == data_2['timestamp_ms']
		and data_1['region'] == data_2['region']
	)


def compute_rolling_values(data: dict, state: State) -> dict:
	"""
	Compute statistical features from historical data.

	Args:
		data: Current data point
		state: State containing historical data

	Returns:
		Data point enriched with statistical features
	"""
	all_data = state.get('all_data', [])

	# Extract demand values from historical data
	demand = np.array([d['demand'] for d in all_data if d['demand'] is not None])
	values = {}

	# Get current demand value to use as fallback
	current_demand = data.get('demand')

	if len(demand) > 0:
		# Basic statistics
		values['full_mean'] = float(np.mean(demand))
		values['full_median'] = float(np.median(demand))

		# Last 3 hours statistics
		last_3_demand = demand[-3:] if len(demand) >= 3 else demand
		values['mean_3'] = float(np.mean(last_3_demand))
		values['median_3'] = float(np.median(last_3_demand))

		# Last 24 hours statistics
		last_24_demand = demand[-24:] if len(demand) >= 24 else demand
		values['mean_24'] = float(np.mean(last_24_demand))
		values['median_24'] = float(np.median(last_24_demand))

		# Lag features - use current demand as fallback instead of None
		values['lag_1h'] = float(demand[-2]) if len(demand) >= 2 else current_demand
		values['lag_24h'] = float(demand[-25]) if len(demand) >= 25 else current_demand
		values['lag_168h'] = (
			float(demand[-169]) if len(demand) >= 169 else current_demand
		)
	else:
		# Default values when no historical data is available
		# Use current demand for all lag features
		for key in [
			'full_mean',
			'mean_3',
			'mean_24',
			'full_median',
			'median_3',
			'median_24',
			'lag_1h',
			'lag_24h',
			'lag_168h',
		]:
			values[key] = current_demand

	# Combine with current data point
	return {**data, **values}


def add_time_data(value: dict) -> None:
	"""
	Add time-based features to data point.

	Creates cyclical encodings for hour, day of week, and month,
	plus holiday indicator and hour categorization.
	"""
	# Convert timestamp to datetime
	timestamp = datetime.fromtimestamp(value['timestamp_ms'] / 1000, tz=timezone.utc)

	# Add holiday indicator
	is_holiday = timestamp.date() in holidays.US()

	# Extract time components
	hour = timestamp.hour
	day_of_week = timestamp.weekday()
	month = timestamp.month

	# Add hour categorization
	is_weekend = day_of_week >= 5  # 5=Saturday, 6=Sunday

	if is_weekend:
		# Weekend logic - only evening peak or off peak
		if 18 <= hour <= 22:
			value['hour_category'] = 'evening_peak'
		else:
			value['hour_category'] = 'off_peak'
	else:
		# Weekday logic - all three categories
		if 9 <= hour <= 17:
			value['hour_category'] = 'office_hours'
		elif 18 <= hour <= 22:
			value['hour_category'] = 'evening_peak'
		else:
			value['hour_category'] = 'off_peak'

	# Add numerical hour category
	category_mapping = {'off_peak': 0, 'office_hours': 1, 'evening_peak': 2}
	value['hour_category_num'] = category_mapping[value['hour_category']]

	value['is_holiday'] = int(is_holiday)

	# Add cyclical encodings (sin/cos transformations)
	value['hour_sin'] = float(np.sin(2 * np.pi * hour / 24))
	value['hour_cos'] = float(np.cos(2 * np.pi * hour / 24))
	value['day_of_week_sin'] = float(np.sin(2 * np.pi * day_of_week / 7))
	value['day_of_week_cos'] = float(np.cos(2 * np.pi * day_of_week / 7))
	value['month_sin'] = float(np.sin(2 * np.pi * month / 12))
	value['month_cos'] = float(np.cos(2 * np.pi * month / 12))


def update_last_message_time(value):
	"""Update the timestamp of the last processed message."""
	global last_message_time
	last_message_time = time.time()
	return value


def check_inactivity(app):
	"""Check if no messages have been received for IDLE_TIMEOUT seconds and shut down if in historical mode."""
	global last_message_time
	
	while True:
		time.sleep(5)  # Check every 5 seconds
		if last_message_time > 0 and time.time() - last_message_time > IDLE_TIMEOUT:
			logger.info(f"No messages received for {IDLE_TIMEOUT} seconds. Shutting down...")
			app.stop()
			break


def signal_handler(sig, frame):
	"""Handle termination signals gracefully."""
	logger.info("Received termination signal. Shutting down...")
	sys.exit(0)


def main(
	kafka_broker_address: str,
	kafka_input_topic: str,
	kafka_output_topic: str,
	kafka_consumer_group: str,
	live_or_historical: str,
) -> None:
	"""
	Process electricity demand data from Kafka, generate features, and output to another topic.

	Workflow:
	1. Read raw demand data from input topic
	2. Add time-based features
	3. Maintain sliding window of historical data
	4. Compute statistical features
	5. Output enriched data to output topic
	"""
	logger.info('Starting feature creation services...')
	logger.info(f'Mode: {live_or_historical}')

	# Register signal handlers
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)

	if live_or_historical == 'live':
		# Live processing mode
		pass  # For now, just pass
	elif live_or_historical == 'historical':
		# Historical processing mode - use existing code
		# Initialize Quix Streams application
		app = Application(
			broker_address=kafka_broker_address,
			consumer_group=kafka_consumer_group,
			auto_offset_reset='earliest',
		)

		# Define input/output topics
		input_topic = app.topic(
			name=kafka_input_topic,
			value_deserializer='json',
			timestamp_extractor=custom_ts_extractor,
		)
		output_topic = app.topic(
			name=kafka_output_topic,
			value_serializer='json',
		)

		# Create processing pipeline
		sdf = app.dataframe(topic=input_topic)
		sdf = sdf.update(update_last_message_time)  # Track message processing time
		sdf = sdf.update(add_time_data)
		sdf = sdf.apply(update_window, stateful=True)
		sdf = sdf.apply(compute_rolling_values, stateful=True)
		sdf = sdf.update(lambda value: logger.debug(f'Final message: {value}'))
		sdf = sdf.to_topic(output_topic)

		# Start inactivity checker in a separate thread if in historical mode
		import threading
		inactivity_thread = threading.Thread(target=check_inactivity, args=(app,), daemon=True)
		inactivity_thread.start()

		# Run the application
		app.run()
	else:
		raise ValueError(
			f"Invalid mode: {live_or_historical}. Must be 'live' or 'historical'"
		)


if __name__ == '__main__':
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	main(
		kafka_broker_address=config.kafka_broker_address,
		kafka_input_topic=config.kafka_input_topic,
		kafka_output_topic=config.kafka_output_topic,
		kafka_consumer_group=config.kafka_consumer_group,
		live_or_historical=config.live_or_historical,
	)
