from datetime import datetime, timedelta, timezone

import requests
from config import config
from loguru import logger
from quixstreams import Application
import time
from typing import Tuple
import sys

# Configure loguru to write to both console and file
# Create logs directory if it doesn't exist
from pathlib import Path
Path("logs").mkdir(exist_ok=True)

# Generate filename with timestamp
log_filename = f"logs/demand_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure logger to write to both console and file
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.add(log_filename, 
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="100 MB",  # Create new file when current one reaches 100MB
    retention="30 days"  # Keep logs for 30 days
)

logger.info(f"Starting new logging session. Logs will be saved to: {log_filename}")

def kafka_producer(
		kafka_broker_address: str,
		kafka_topic: str,
		region_name: str,
		last_n_days: int,
		live_or_historical: str,
)-> None:
	"""
	Function to fetch electricity demand data from the EIA API and save it to a Kafka topic.
	
	Args:
		kafka_broker_address (str): The address of the Kafka broker.
		kafka_topic (str): The name of the Kafka topic.
		kafka_consumer_group (str): The name of the Kafka consumer group.
		region_name (str): The name of the region to fetch data for.
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
		consumer_group=config.kafka_consumer_group,
		auto_offset_reset='earliest',
    )

	topic = app.topic(
		name=kafka_topic,
		value_serializer='json',
	)

	# Push the data to the Kafka Topic
	match live_or_historical:
		case "live":
			demand_type='D'
			with app.get_producer() as producer:
				# Initialize variable to store the most recent reading
				latest_reading = None
				while True:
					# Fetch new data from EIA API
					data = get_live_data(last_n_days, region_name, demand_type)
					# Get the most recent reading (first element)
					current_reading = data[0]

					# Push to Kafka if this is the first reading or if we have new data
					if latest_reading is None or current_reading != latest_reading:
						# Serialize the message for Kafka
						message = topic.serialize(
							key=current_reading['region'],
							value=current_reading
						)
						# Send the message to Kafka topic
						producer.produce(
							topic=topic.name,
							value=message.value,
							key=message.key
						)
						logger.info(f'New demand data pushed to Kafka: {current_reading}')
						logger.info(f'App will wait for new data, waiting time: 10 minutes')
						# Update our reference for comparison
						latest_reading = current_reading
					else:
						logger.info('No new data available, waiting...')

					time.sleep(600)  # Wait 10 minutes (600 seconds)
		
		case "historical":
			demand_types = ['D', 'DF']
			type_labels = {'D': 'actual', 'DF': 'forecast'}
			
			with app.get_producer() as producer:
				for demand_type in demand_types:
					# Initial time range
					start_day, original_end_day = time_to_string(last_n_days)
					end_day = original_end_day
					has_more_data = True
					batch_count = 1

					while has_more_data:
						logger.info(f'Fetching batch {batch_count} for {type_labels[demand_type]} data')
						logger.info(f'Time range: {start_day} to {end_day}')
						
						feature_data = get_hist_data(start_day, end_day, region_name, demand_type)
						total_elements = len(feature_data)
						
						# Check batch size and adjust feature_data if needed
						if total_elements == 5000:
							# Find the first T01 entry from the end
							cutoff_index = None
							for i, data in enumerate(reversed(feature_data)):
								if data['human_readable_period'].endswith('T01'):
									cutoff_index = len(feature_data) - i
									break
							
							if cutoff_index is not None:
								# Keep data up to (and including) the T01 entry
								feature_data = feature_data[:cutoff_index]
								# Set next batch to start from T00 of the same day
								last_entry = feature_data[-1]['human_readable_period']  # This is the T01 entry
								end_day = last_entry.replace('T01', 'T00')
							else:
								# If no T01 found, use the last entry
								last_timestamp = feature_data[-1]['human_readable_period']
								end_day = datetime.strptime(last_timestamp, "%Y-%m-%dT%H")
								end_day = (end_day - timedelta(hours=1)).strftime("%Y-%m-%dT%H")

							logger.info(f'Batch {batch_count} complete. Maximum records reached (5000)')
							logger.info(f'Starting batch {batch_count + 1} with end_day: {end_day}')
							batch_count += 1
						else:
							has_more_data = False
							logger.info(f'Final batch with {total_elements} records')

						# Now push the adjusted data to Kafka
						for index, data in enumerate(feature_data, 1):
							message = topic.serialize(
								key=data['region'],
								value=data,
							)
							producer.produce(
								topic=topic.name,
								value=message.value,
								key=message.key
							)
							logger.info(
								f'Pushed {type_labels[demand_type]} demand data '
								f'{index}/{len(feature_data)} to Kafka: {data}'
							)

						if not has_more_data:
							logger.info(f'Finished pushing historical {type_labels[demand_type]} demand data to Kafka')
							logger.info(f'Total batches processed: {batch_count}, Final record count: {total_elements}')

		case _:
			raise ValueError("Error: live_or_historical must be either 'live' or 'historical'")
		
def get_hist_data(
		start_day: str,
		end_day: str,
		region_name: str,
		demand_type: str,
)->list:
	"""
	Gets the latest electricity demand data from the EIA API.

	Args:
		last_n_days (int): The number of days to fetch data for.
		region_name (str): The name of the region to fetch data for.

	Returns:
		list: A list of dictionaries containing the electricity demand data.
	"""

	# Get EIA API data for the specified date range
	# start_day, end_day: dates in YYYY-MM-DDT00 format
	# D_data: actual demand, DF_data: day-ahead forecast
	data = connect_api(start_day, end_day, region_name, demand_type)
	feature_data = convert_to_feature(data)

	return feature_data

def get_live_data(
		last_n_days: int,
		region_name: str,
		demand_type: str,
)->list:
	"""
	Gets the latest electricity demand data from the EIA API.

	Args:
		last_n_days (int): The number of days to fetch data for.
		region_name (str): The name of the region to fetch data for.

	Returns:
		list: A list of dictionaries containing the electricity demand data.
	"""

	# Get EIA API data for the specified date range
	# start_day, end_day: dates in YYYY-MM-DDT00 format
	# D_data: actual demand, DF_data: day-ahead forecast
	start_day, end_day = time_to_string(last_n_days)
	data = connect_api(start_day, end_day, region_name, demand_type)
	feature_data = convert_to_feature(data)

	return feature_data

def connect_api(
		start_day: str,
		end_day: str,
		region_name: str,
		demand_type: str,
) -> list:
	"""
	Fetch raw electricity demand data from the EIA API for the specified date.

	Parameters:
		start_day (str): Start date in the format 'YYYY-MM-DDT00'.
		end_day (str): End date in the format 'YYYY-MM-DDT00'.
		region_name (str): The name of the region to fetch data for.
		demand_type (str): The type of demand data to fetch ('D' for actual demand, 'DF' for day-ahead forecast).

	Returns:
		list: A list of dictionaries containing the raw electricity demand data for the specified hour.
	"""

	# API URL and parameters
	url = 'https://api.eia.gov/v2/electricity/rto/region-data/data/'
	region_name = config.region_name
	params = {
		'frequency': 'hourly',
		'data[0]': 'value',
		'facets[respondent][0]': region_name,
		'facets[type][0]': demand_type,
		'sort[0][column]': 'period',
		'sort[0][direction]': 'desc',
		'offset': 0,
		'length': 5000,
		'start': start_day,
		'end': end_day,
		'api_key': config.eia_api_key,
	}
	# Make GET request
	response = requests.get(url, params=params)
	response.raise_for_status()  # Raise HTTPError for bad responses

	# Parse JSON response
	data = response.json()
	data = data['response']['data']

	# breakpoint()

	return data


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
)-> int:
	"""
	Converts a date string in the format 'YYYY-MM-DDT00' to a timestamp in milliseconds.

	Parameters:
		date_str (str): The date string to convert.

	Returns:
		timestamp_ms (int): The timestamp in milliseconds.
	"""
	dt = datetime.strptime(date_str, "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)
	timestamp_ms = int(dt.timestamp() * 1000)

	return timestamp_ms

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
			"timestamp": convert_datestring_to_ms(entry['period']),
			"region": entry['respondent'],
			"electricity_demand": entry['value'],
			"electricity_demand_type": entry['type'],
			"human_readable_period": entry['period'],
		}
		for entry in list_of_dicts
	]

	return list_of_dicts


if __name__ == '__main__':
	kafka_producer(
		kafka_broker_address=config.kafka_broker_address,
		region_name=config.region_name,
		last_n_days=config.last_n_days,
		live_or_historical=config.live_or_historical,
		kafka_topic=config.kafka_topic,
	)