from datetime import datetime, timezone
import numpy as np
import holidays
from loguru import logger
from quixstreams import Application
from typing import Any, Optional, List, Tuple
from config import config


def custom_ts_extractor(
    value: Any,
    headers: Optional[List[Tuple[str, bytes]]],
    timestamp: float,
    timestamp_type, #: TimestampType,
) -> int:
    """
    Specifying a custom timestamp extractor to use the timestamp from the message payload 
    instead of Kafka timestamp.
    """
    return value["timestamp_ms"]


def main(
	kafka_broker_address: str,
	kafka_input_topic: str,
	kafka_output_topic: str,
	kafka_consumer_group: str,
	region_names: list[str],
	live_or_historical: str,
) -> None:
	"""
	Function ingests electricity demand data from the Kafka Topic
	Generates features to be sent to the Feature Store for further usage in
	the ML model for predicting electricity demand.

	Args:
		kafka_broker_address (str): The address of the Kafka broker.
		kafka_input_topic (str): The name of the Kafka input topic.
		kafka_output_topic (str): The name of the Kafka output topic.
		kafka_consumer_group (str): The name of the Kafka consumer group.
		region_names (list[str]): List of region names to fetch data for.
		live_or_historical (str): Whether to fetch live or historical data.

	Returns:
		None
	"""
	logger.info('Starting feature creation services...')

	# Initialise the Quix Streams application
	app = Application(
		broker_address=kafka_broker_address,
		consumer_group=kafka_consumer_group,
		auto_offset_reset='earliest',
	)

	# Define the input and output topics
	input_topic = app.topic(
		name=kafka_input_topic,
		value_deserializer='json',
		timestamp_extractor=custom_ts_extractor,
	)
	
	output_topic = app.topic(
		name=kafka_output_topic,
		value_serializer='json',
	)

	# Creating the Steaming DataFrame

	sdf = app.dataframe(topic=input_topic)
	
	sdf = sdf.update(add_time_data)

	# push these message to the output topic
	sdf = sdf.to_topic(output_topic)

	app.run()

def add_time_data(value) -> None:
	"""
	Create new time features on for the Streaming DataFrame. This takes the value of `timestamp_ms`
	to create different time features.

	Note that this function doesn't return anything and only mutates the incoming value

	Args:
		value (dict): The incoming value from the Streaming DataFrame.

	Returns:
		None
	"""
	# Converting the timestamp_ms to datetime object in UTC
	timestamp_ms = value["timestamp_ms"]
	timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
	
	# Get US holidays
	us_holidays = holidays.US()
	
	# Check if the date is a holiday
	value['is_holiday'] = int(timestamp.date() in us_holidays)
	
	# Extracting the date components of the timestamp
	hour = timestamp.hour
	day_of_week = timestamp.weekday()
	month = timestamp.month

	# Encoding the hour of the day cyclically (sin/cos functions)
	value['hour_sin'] = float(np.sin(2 * np.pi * hour / 24))
	value['hour_cos'] = float(np.cos(2 * np.pi * hour / 24))

	# Encoding the day of the week cyclically (sin/cos functions)
	value['day_of_week_sin'] = float(np.sin(2 * np.pi * day_of_week / 7))
	value['day_of_week_cos'] = float(np.cos(2 * np.pi * day_of_week / 7))

	# Encoding the month of the year cyclically (sin/cos functions)
	value['month_sin'] = float(np.sin(2 * np.pi * month / 12))
	value['month_cos'] = float(np.cos(2 * np.pi * month / 12))

	logger.debug(value)


if __name__ == '__main__':
	main(
		kafka_broker_address=config.kafka_broker_address,
		kafka_input_topic=config.kafka_input_topic,
		kafka_output_topic=config.kafka_output_topic,
		kafka_consumer_group=config.kafka_consumer_group,
		region_names=config.region_names,
		live_or_historical=config.live_or_historical,
	)
