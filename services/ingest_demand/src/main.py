import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple

import requests
from config import config
from loguru import logger
from quixstreams import Application


def kafka_producer(
	kafka_broker_address: str,
	kafka_topic: str,
	region_names: list[str],  # Changed to list of strings
	last_n_days: int,
	live_or_historical: str,
) -> None:
	"""
	Function to fetch electricity demand data from the EIA API and save it to a Kafka topic.

	Args:
		kafka_broker_address (str): The address of the Kafka broker.
		kafka_topic (str): The name of the Kafka topic.
		region_names (list[str]): List of region names to fetch data for.
		last_n_days (int): The number of days to fetch data for.
		live_or_historical (str): Whether to fetch live or historical data.

	Returns:
		None
	"""
	logger.info('Start the ingestion of the electricity demand service')

	# Initialize the Quix Streams application.
	# This class handles all the low-level details to connect to Kafka.
	app = Application(
		broker_address=kafka_broker_address,
	)

	# Define the topic where we will push the trades to
	topic = app.topic(
		name=kafka_topic,
		value_serializer='json',
	)

	# Push the data to the Kafka Topic
	match live_or_historical:
		case 'live':
			with app.get_producer() as producer:
				# Initialize dictionary to store the most recent reading for each region
				latest_readings = {region: None for region in region_names}

				while True:
					for region_name in region_names:
						logger.info(f'Fetching data for region: {region_name}')
						# Fetch and merge new data from EIA API
						merged_data = connect_api(
							start_day=None, end_day=None, region_name=region_name
						)
						# Get the most recent reading
						current_reading = merged_data[0]

						# Push to Kafka if this is the first reading or if we have new data
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
							logger.info(
								f'New merged demand data pushed to Kafka for {region_name}: {current_reading}'
							)
							latest_readings[region_name] = current_reading
						else:
							logger.info(
								f'No new data available for {region_name}, waiting...'
							)

					logger.info('Waiting 10 minutes before next data check...')
					time.sleep(600)

		case 'historical':
			total_records_all_regions = 0
			region_records = {}
			first_period = None
			last_period = None

			with app.get_producer() as producer:
				for region_name in region_names:
					logger.info(f'Processing historical data for region: {region_name}')
					
					start_day, end_day = get_shifted_time_range(last_n_days, shift_hours=192)
					current_start = start_day
					has_more_data = True
					batch_count = 1
					region_total = 0

					while has_more_data:
						logger.info(
							f'Fetching batch {batch_count} for merged data '
							f'in region {region_name}'
						)
						logger.info(f'Time range: {current_start} to {end_day}')
						
						# Fetch data from API
						merged_data = connect_api(
							start_day=current_start,
							end_day=end_day,
							region_name=region_name
						)
						
						# Update first and last periods
						if first_period is None:
							first_period = merged_data[0]['human_read_period']
						last_period = merged_data[-1]['human_read_period']

						total_elements = len(merged_data)

						if total_elements == 1250:
							# Find the last T23 entry from the end of the batch
							cutoff_index = None
							for i in range(len(merged_data) - 1, -1, -1):
								if merged_data[i]['human_read_period'].endswith('T23'):
									cutoff_index = i + 1  # Include the T23 entry
									break

							if cutoff_index:
								# Keep data up to and including the T23 entry
								merged_data = merged_data[:cutoff_index]
								# Get the date of the T23 entry and set next start to T00 of next day
								last_entry = merged_data[-1]['human_read_period']
								dt = datetime.strptime(last_entry, '%Y-%m-%dT%H')
								current_start = (dt + timedelta(days=1)).strftime(
									'%Y-%m-%dT00'
								)
								has_more_data = True
								logger.info(
									f'Batch {batch_count} complete. Ending at {last_entry}'
								)
								logger.info(
									f'Next batch will start from: {current_start}'
								)
								batch_count += 1
							else:
								# If no T23 found (shouldn't happen with sorted data)
								last_entry = merged_data[-1]['human_read_period']
								dt = datetime.strptime(last_entry, '%Y-%m-%dT%H')
								current_start = (dt + timedelta(hours=1)).strftime(
									'%Y-%m-%dT%H'
								)
								has_more_data = True
								logger.info(
									f'No T23 found in batch. Using next hour as start: {current_start}'
								)
						else:
							has_more_data = False
							logger.info(f'Final batch with {total_elements} records')

						# Push data to Kafka
						batch_records = len(merged_data)
						region_total += batch_records

						for index, data in enumerate(merged_data, 1):
							message = topic.serialize(
								key=data['region'],
								value=data,
							)
							producer.produce(
								topic=topic.name, value=message.value, key=message.key
							)
							logger.info(
								f'Pushed merged data {index}/{batch_records} '
								f'to Kafka for region {region_name}'
							)
							logger.info(data)

						if not has_more_data:
							logger.info(
								f'Finished pushing historical merged data to Kafka for region {region_name}'
							)
							logger.info(
								f'Total batches processed: {batch_count}'
							)

					# Store region total and update grand total
					region_records[region_name] = region_total
					total_records_all_regions += region_total
					
					# Log region summary
					logger.info(f'Region {region_name} complete. Total records sent: {region_total}')

				# Log final summary for all regions
				logger.info('\n=== Final Processing Summary ===')
				logger.info(f'Time Range: {first_period} to {last_period}')
				logger.info('Records per region:')
				for region, count in region_records.items():
					logger.info(f'  Region {region}: {count:,} records')
				logger.info(f'Grand Total: {total_records_all_regions:,} records')
				logger.info('==============================\n')
		case _:
			raise ValueError(
				"Error: live_or_historical must be either 'live' or 'historical'"
			)


def fetch_eia_data(url: str, params: dict) -> list:
	"""
	Generic function to fetch data from EIA API

	Args:
		url (str): EIA API endpoint URL
		params (dict): Query parameters for the API call

	Returns:
		list: Raw data from API response
	"""
	response = requests.get(url, params=params)
	response.raise_for_status()
	return response.json()['response']['data']


def get_demand_params(region_name: str, start_day: str, end_day: str) -> dict:
	"""
	Get parameters for demand data API call

	Args:
		region_name (str): Region identifier
		start_day (str): Start date in YYYY-MM-DDT00 format
		end_day (str): End date in YYYY-MM-DDT00 format

	Returns:
		dict: Parameters for API call
	"""
	return {
		'frequency': 'hourly',
		'data[0]': 'value',
		'facets[respondent][0]': region_name,
		'sort[0][column]': 'period',
		'sort[0][direction]': 'asc',
		'offset': 0,
		'length': 5000,
		'start': start_day,
		'end': end_day,
		'api_key': config.eia_api_key,
	}


def merge_demand_data(data_types: dict[str, list]) -> list:
	"""
	Merge different types of demand data into a single list

	Args:
		data_types (dict): Dictionary containing lists of different data types
			Keys should be: 'D', 'DF', 'TI', 'NG'

	Returns:
		list: Merged and sorted list of demand data
	"""
	merged_data = {}

	# Define data type mapping for cleaner code
	type_mapping = {
		'D': 'demand',
		'DF': 'forecast',
		'TI': 'total interchange',
		'NG': 'net generation',
	}

	# Process each entry once
	for data_type, entries in data_types.items():
		field_name = type_mapping[data_type]

		for entry in entries:
			key = (entry['timestamp_ms'], entry['region'])

			if key not in merged_data:
				# Initialize new entry with all fields as None
				merged_data[key] = {
					'timestamp_ms': entry['timestamp_ms'],
					'human_read_period': entry['human_read_period'],
					'region': entry['region'],
					'demand': None,
					'forecast': None,
					'total interchange': None,
					'net generation': None,
				}

			# Update the specific field
			merged_data[key][field_name] = entry['electricity_demand']

	# Convert to list and sort
	merged_list = list(merged_data.values())
	merged_list.sort(key=lambda x: x['timestamp_ms'])

	return merged_list


def connect_api(start_day: str, end_day: str, region_name: str) -> list:
	"""
	Fetch raw electricity demand data from the EIA API for the specified date.

	Args:
		start_day (str): Start date in YYYY-MM-DDT00 format
		end_day (str): End date in YYYY-MM-DDT00 format
		region_name (str): Region identifier

	Returns:
		list: Merged and sorted list of demand data
	"""
	# API URL and parameters
	url = 'https://api.eia.gov/v2/electricity/rto/region-data/data/'
	params = get_demand_params(region_name, start_day, end_day)

	# Fetch and process data
	raw_data = fetch_eia_data(url, params)

	# Group data by type
	data_by_type = {'D': [], 'DF': [], 'TI': [], 'NG': []}
	for entry in raw_data:
		data_by_type[entry['type']].append(entry)

	# Convert each type to features
	processed_data = {
		data_type: convert_to_feature(entries)
		for data_type, entries in data_by_type.items()
	}

	# Merge all data types
	return merge_demand_data(processed_data)


def time_to_string(
	last_n_days: int,
) -> tuple[str, str]:
	"""
	Convert the last_n_days to the format required by the EIA API.

	Parameters:
		last_n_days (int): Number of days to fetch data for.

	Returns:
		start_date (str): Start date in the format required by the EIA API.
		end_date (str): End date in the format required by the EIA API.
	"""
	# Add one day to the current date to ensure we capture a full day's worth of data
	current_date = datetime.now() + timedelta(days=1)
	current_date = current_date.strftime('%Y-%m-%d')

	# Define the 'start_date' value considering the last_n_days value
	start_date = datetime.now() - timedelta(days=last_n_days)
	start_date = start_date.strftime('%Y-%m-%d')

	# Append 'T00' to dates to match API's datetime format (YYYY-MM-DDT00)
	current_date = current_date + 'T00'
	start_date = start_date + 'T00'

	return start_date, current_date


def convert_datestring_to_ms(
	date_str: str,
) -> int:
	"""
	Converts a date string in the format 'YYYY-MM-DDT00' to a timestamp in milliseconds.

	Parameters:
		date_str (str): The date string to convert.

	Returns:
		timestamp_ms (int): The timestamp in milliseconds.
	"""
	dt = datetime.strptime(date_str, '%Y-%m-%dT%H').replace(tzinfo=timezone.utc)
	timestamp_ms = int(dt.timestamp() * 1000)

	return timestamp_ms


def get_data(
	last_n_days: int,
	region_name: str,
) -> Tuple[list, list]:
	"""
	Gets the latest electricity demand data from the EIA API.

	Args:
		last_n_days (int): The number of days to fetch data for.
		region_name (str): The name of the region to fetch data for.

	Returns:
		Tuple[list, list]: A tuple containing two lists:
			1. A list of dictionaries containing the electricity demand data.
			2. A list of dictionaries containing the electricity day-ahead forecast data.
	"""

	# Get EIA API data for the specified date range
	# start_day, end_day: dates in YYYY-MM-DDT00 format
	# D_data: actual demand, DF_data: day-ahead forecast
	start_day, end_day = time_to_string(last_n_days)
	data = connect_api(start_day, end_day, region_name)

	return data


def convert_to_feature(list_of_dicts: list) -> list:
	"""
	Transform EIA API response into Kafka message format:
	- timestamp: Unix timestamp in milliseconds (from YYYY-MM-DDT00)
	- region: Regional identifier
	- electricity_demand: Actual demand in megawatthours (MWh)

	Args:
		list_of_dicts (list): List of dictionaries containing the raw electricity demand data.

	Returns:
		list: List of dictionaries containing the transformed electricity demand data.

	"""
	list_of_dicts = [
		{
			'timestamp_ms': convert_datestring_to_ms(entry['period']),
			'human_read_period': entry['period'],
			'region': entry['respondent'],
			'electricity_demand': int(entry['value']),
			'electricity_demand_type': entry['type'],
		}
		for entry in list_of_dicts
	]

	return list_of_dicts


def get_shifted_time_range(last_n_days: int, shift_hours: int = 192) -> tuple[str, str]:
	"""
	Calculate start and end dates with a specified hour shift:
	- end_time: current time minus shift_hours
	- start_time: end_time minus last_n_days

	Args:
		last_n_days (int): Number of days to look back from the end_time
		shift_hours (int, optional): Number of hours to shift back from current time. Defaults to 192 (8 days).

	Returns:
		tuple[str, str]: (start_date, end_date) in YYYY-MM-DDTHH format
	"""
	current_time = datetime.now()
	end_time = current_time - timedelta(hours=shift_hours)
	start_time = end_time - timedelta(days=last_n_days)

	start_day = start_time.strftime('%Y-%m-%dT%H')
	end_day = end_time.strftime('%Y-%m-%dT%H')

	return start_day, end_day


def setup_logger() -> str:
	"""
	Configure loguru logger with both console and file handlers.
	Console output includes colors, while file output is plain text.
	Logs are rotated at 100MB and kept for 30 days.

	Returns:
		str: Path to the created log file
	"""
	# Generate filename with timestamp
	log_filename = f'logs/demand_ingest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

	# Configure logger to write to both console and file
	logger.remove()  # Remove default handler
	logger.add(
		sys.stderr,
		format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
	)
	logger.add(
		log_filename,
		format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
		rotation='100 MB',  # Create new file when current one reaches 100MB
		retention='30 days',  # Keep logs for 30 days
	)

	logger.info(f'Starting new logging session. Logs will be saved to: {log_filename}')
	return log_filename


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
