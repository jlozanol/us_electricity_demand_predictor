import time
from pathlib import Path
from typing import Any, List

from config import config
from loguru import logger
from quixstreams import Application
from utils.data_handler import get_data, collect_demand_data, time_to_string
from utils.logger import setup_logger


def init_kafka_app(broker_address: str, topic_name: str) -> tuple[Application, Any]:
	"""
	Initialize Kafka application and topic.

	Args:
	    broker_address (str): Kafka broker address
	    topic_name (str): Name of the Kafka topic

	Returns:
	    tuple: (Application instance, Topic instance)
	"""
	app = Application(
		broker_address=broker_address,
		auto_offset_reset='earliest',
	)

	topic = app.topic(
		name=topic_name,
		value_serializer='json',
	)

	return app, topic


def kafka_producer(
	kafka_broker_address: str,
	kafka_topic: str,
	region_names: List[str],
	last_n_days: int,
	live_or_historical: str,
) -> None:
	"""
	Function to fetch electricity demand data from the EIA API and save it to a Kafka topic.

	Args:
	    kafka_broker_address (str): The address of the Kafka broker.
	    kafka_topic (str): The name of the Kafka topic.
	    region_names (List[str]): List of region names to fetch data for.
	    last_n_days (int): The number of days to fetch data for.
	    live_or_historical (str): Whether to fetch live or historical data.
	"""
	logger.info('Start the ingestion of the electricity demand service')

	app, topic = init_kafka_app(kafka_broker_address, kafka_topic)

	match live_or_historical:
		case 'live':
			handle_live_data(app, topic, region_names, last_n_days)
		case 'historical':
			handle_historical_data(app, topic, region_names, last_n_days)
		case _:
			raise ValueError(
				"Error: live_or_historical must be either 'live' or 'historical'"
			)


def handle_live_data(
	app: Application, topic: Any, region_names: List[str], last_n_days: int
) -> None:
	"""Handle live data ingestion"""
	demand_type = 'D'
	with app.get_producer() as producer:
		latest_readings = {region: None for region in region_names}

		while True:
			for region_name in region_names:
				data = get_data(
					region_name=region_name,
					demand_type=demand_type,
					last_n_days=last_n_days,
				)
				current_reading = data[0]

				if (
					latest_readings[region_name] is None
					or current_reading != latest_readings[region_name]
				):
					message = topic.serialize(
						key=current_reading['region'], value=current_reading
					)
					producer.produce(
						topic=topic.name, value=message.value, key=message.key
					)
					logger.info(f'New demand data pushed to Kafka: {current_reading}')
					latest_readings[region_name] = current_reading
				else:
					logger.info(f'No new data available for {region_name}, waiting...')

			logger.info('App will wait for new data, waiting time: 10 minutes')
			time.sleep(600)


def handle_historical_data(
	app: Application, topic: Any, region_names: List[str], last_n_days: int
) -> None:
	"""Handle historical data ingestion"""
	with app.get_producer() as producer:
		for region_name in region_names:
			logger.info(f'Processing historical data for region: {region_name}')
			
			# Get initial time range
			start_day, end_day = time_to_string(last_n_days)
			
			# Collect actual demand data
			actual_data = collect_demand_data(
				start_day, end_day, region_name, 'D', 'actual'
			)
			
			# Collect forecast demand data
			forecast_data = collect_demand_data(
				start_day, end_day, region_name, 'DF', 'forecast'
			)
			
			# Merge actual and forecast data
			merged_data = actual_data.copy()
			for ts, data in forecast_data.items():
				if ts in merged_data:
					merged_data[ts]['demand_forecast'] = data['demand_forecast']
				else:
					merged_data[ts] = data

			# Sort and push to Kafka
			sorted_data = [merged_data[ts] for ts in sorted(merged_data.keys())]
			push_to_kafka(producer, topic, sorted_data, 'merged')

			logger.info(
				f'Finished pushing merged historical demand data '
				f'to Kafka for region {region_name}'
			)
			logger.info(f'Final record count: {len(sorted_data)}')


def push_to_kafka(
	producer: Any, topic: Any, feature_data: list, data_type: str
) -> None:
	"""Push data to Kafka topic"""
	for index, data in enumerate(feature_data, 1):
		message = topic.serialize(
			key=data['region'],
			value=data,
		)
		producer.produce(topic=topic.name, value=message.value, key=message.key)
		logger.info(
			f'Pushed {data_type} demand data '
			f'{index}/{len(feature_data)} to Kafka: {data}'
		)


def main():
	"""Main entry point of the application"""
	# Create logs directory if it doesn't exist
	Path('logs').mkdir(exist_ok=True)
	setup_logger()

	kafka_producer(
		kafka_broker_address=config.kafka_broker_address,
		region_names=config.region_names,
		last_n_days=config.last_n_days,
		live_or_historical=config.live_or_historical,
		kafka_topic=config.kafka_topic,
	)


if __name__ == '__main__':
	main()
