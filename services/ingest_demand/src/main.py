
import time

from pathlib import Path
from typing import Any, List

from config import config
from loguru import logger
from quixstreams import Application
from utils.data_handler import get_data, time_to_string, process_batch
from utils.logger import setup_logger
from quixstreams.models import TopicConfig



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
		# config=TopicConfig(
        #     num_partitions=2,
        #     replication_factor=1,
        # )
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

				if (latest_readings[region_name] is None or 
					current_reading != latest_readings[region_name]):
					message = topic.serialize(
						key=current_reading['region'], 
						value=current_reading
					)
					producer.produce(
						topic=topic.name,
						value=message.value,
						key=message.key
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
	demand_types = ['D', 'DF']
	type_labels = {'D': 'actual', 'DF': 'forecast'}

	with app.get_producer() as producer:
		for region_name in region_names:
			logger.info(f'Processing historical data for region: {region_name}')
			for demand_type in demand_types:
				start_day, original_end_day = time_to_string(last_n_days)
				end_day = original_end_day
				has_more_data = True
				batch_count = 1
				total_records = 0

				while has_more_data:
					logger.info(
						f'Fetching batch {batch_count} for {type_labels[demand_type]} '
						f'data in region {region_name}'
					)
					logger.info(f'Time range: {start_day} to {end_day}')

					feature_data = get_data(
						start_day=start_day,
						end_day=end_day,
						region_name=region_name,
						demand_type=demand_type,
					)

					has_more_data, end_day, feature_data = process_batch(
						feature_data, batch_count, type_labels[demand_type]
					)

					push_to_kafka(producer, topic, feature_data, type_labels[demand_type])

					total_records += len(feature_data)

					if not has_more_data:
						logger.info(
							f'Finished pushing historical {type_labels[demand_type]} '
							f'demand data to Kafka for region {region_name}'
						)
						logger.info(
							f'Total batches processed: {batch_count}, '
							f'Final record count: {total_records}'
						)
					batch_count += 1


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
		region_names=config.region_names,  # Updated parameter name
		last_n_days=config.last_n_days,
		live_or_historical=config.live_or_historical,
		kafka_topic=config.kafka_topic,
	)


if __name__ == '__main__':
	main()
