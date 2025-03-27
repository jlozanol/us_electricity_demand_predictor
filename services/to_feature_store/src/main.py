from config import config, hopsworks_credentials
from loguru import logger
from quixstreams import Application
from sinks import HopsworksFeatureStoreSink


def main(
	kafka_broker_address: str,
	kafka_input_topic: str,
	kafka_consumer_group: str,
	output_sink: HopsworksFeatureStoreSink,
	live_or_historical: str,
) -> None:
	"""
	Function that ingests electricity demand data from the Kafka Topic
	and saves it to the Feature Store for further usage in the ML model
	for predicting electricity demand.

	This service acts as the final step in the data pipeline:
	1. Consumes enriched electricity demand data from Kafka
	2. Writes the data to Hopsworks Feature Store
	3. Supports both historical batch processing and live streaming modes

	The historical mode processes all available data from the beginning of the topic,
	while the live mode will be implemented to handle real-time data streaming.

	Args:
	    kafka_broker_address (str): The address of the Kafka broker (host:port).
	    kafka_input_topic (str): The name of the Kafka input topic containing enriched data.
	    kafka_consumer_group (str): The name of the Kafka consumer group for this service.
	    output_sink (HopsworksFeatureStoreSink): Configured sink for writing to Hopsworks.
	    live_or_historical (str): Processing mode - either 'live' or 'historical'.

	Returns:
	    None
	"""

	logger.info('Starting feature store ingestion service...')
	logger.info(f'Mode: {live_or_historical}')

	if live_or_historical == 'live':
		# Live processing mode
		# This will be implemented to handle real-time streaming data
		# For now, we're just logging and exiting
		logger.info('Live mode not yet implemented')
		pass  # For now, just pass
	elif live_or_historical == 'historical':
		# Historical processing mode - processes all available data from the beginning
		logger.info('Starting historical data processing')

		# Initialize the Quix Streams application with Kafka connection details
		app = Application(
			broker_address=kafka_broker_address,
			consumer_group=kafka_consumer_group,
			auto_offset_reset='earliest',  # Start from the beginning of the topic
		)

		# Define the input topic and deserialize JSON messages
		input_topic = app.topic(
			name=kafka_input_topic,
			value_deserializer='json',
		)

		# Create a streaming dataframe from the input topic
		sdf = app.dataframe(input_topic)

		# Write the data directly to the Hopsworks Feature Store
		# No transformations needed as data is already processed by upstream services
		sdf.sink(output_sink)

		# Start the streaming application
		logger.info(f'Starting to consume from topic: {kafka_input_topic}')
		app.run()
	else:
		# Handle invalid configuration
		raise ValueError(
			f"Invalid mode: {live_or_historical}. Must be 'live' or 'historical'"
		)


if __name__ == '__main__':
	# Create the Hopsworks Feature Store sink with credentials and configuration
	hopsworks_sink = HopsworksFeatureStoreSink(
		api_key=hopsworks_credentials.hopsworks_api_key,
		project_name=hopsworks_credentials.hopsworks_project_name,
		feature_group_name=config.feature_group_name,
		feature_group_version=config.feature_group_version,
		feature_group_primary_keys=config.feature_group_primary_keys,
		feature_group_event_time=config.feature_group_event_time,
	)

	# Run the main function with configuration from environment variables
	main(
		kafka_broker_address=config.kafka_broker_address,
		kafka_input_topic=config.kafka_input_topic,
		kafka_consumer_group=config.kafka_consumer_group,
		output_sink=hopsworks_sink,
		live_or_historical=config.live_or_historical,
	)
