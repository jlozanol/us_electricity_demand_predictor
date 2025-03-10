from datetime import datetime, timedelta, timezone

import requests
from config import config
from loguru import logger
from quixstreams import Application

def kafka_producer(
		kafka_broker_address: str,
		kafka_topic: str,
		region_name: str,
		last_n_days: int,
)-> None:
	"""
	Function to fetch electricity demand data from the EIA API and save it to a Kafka topic.
	
	Args:
		kafka_broker_address (str): The address of the Kafka broker.
		kafka_topic (str): The name of the Kafka topic.
		region_name (str): The name of the region to fetch data for.
		last_n_days (int): The number of days to fetch data for.

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
	topic = app.topic(name=kafka_topic, value_serializer='json')

	# Get EIA API data for the specified date range
	# start_day, end_day: dates in YYYY-MM-DDT00 format
	# D_data: actual demand, DF_data: day-ahead forecast
	start_day, end_day = time_format_to_string(last_n_days)
	D_data, DF_data = connect_api(start_day, end_day, region_name)

	# Transform EIA API response into Kafka message format:
	# - timestamp: Unix timestamp in milliseconds (from YYYY-MM-DDT00)
	# - region: Regional Transmission Organization (RTO) identifier
	# - electricity_demand: Actual demand in megawatthours (MWh)

	feature_D_data = [
		{
			"timestamp": convert_date_string_to_ms(entry['period']),
			"region": entry['respondent'],
			"electricity_demand": entry['value'],
		}
		for entry in D_data
	]

	feature_DF_data = [
		{
			"timestamp": convert_date_string_to_ms(entry['period']),
			"region": entry['respondent'],
			"electricity_demand": entry['value'],
		}
		for entry in DF_data
	]

	# Push the data to the Kafka Topic
	with app.get_producer() as producer:
		# Inspect the feature_D_data list and while it has rows in the list, keep pushing the data to the
		# kafka topic
		breakpoint()
		while feature_D_data:
			for data in feature_D_data:
				# serialize the trade as bytes
				message = topic.serialize(
					key=data.region,
					value=data,
                )
				
				# push the serialized message to the topic
				producer.produce(topic=topic.name, value=message.value, key=message.key)
				
				logger.info(f'Pushed trade to Kafka: {data}')

def connect_api(
		start_day: str,
		end_day: str,
		region_name: str,
) -> tuple[list, list]:
	"""
	Fetch raw electricity demand data from the EIA API for the specified date.

	Parameters:
		start_day (str): Start date in the format 'YYYY-MM-DDT00'.
		end_day (str): End date in the format 'YYYY-MM-DDT00'.
		region_name (str): The name of the region to fetch data for.

	Returns:
		Tuple[list, list]: A tuple containing two lists:
			1. A list of dictionaries containing the raw electricity demand data for the specified hour.
			2. A list of dictionaries containing the raw electricity day-ahead forecast data for the specified hour.
	"""

	# API URL and parameters
	url = 'https://api.eia.gov/v2/electricity/rto/region-data/data/'
	region_name = config.region_name
	params = {
		'frequency': 'hourly',
		'data[0]': 'value',
		'facets[respondent][0]': region_name,
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

	# Divide the data obtained in data to 2 different tables, one with data['response']['data'][]['type'] == 'D'
	# and the other table with  data['response']['data'][]['type'] == 'DF'
	D_data = [entry for entry in data if entry['type'] == 'D']
	DF_data = [entry for entry in data if entry['type'] == 'DF']

	return D_data, DF_data


def time_format_to_string(
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

def convert_date_string_to_ms(
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



if __name__ == '__main__':
	kafka_producer(
		kafka_broker_address=config.kafka_broker_address,
		kafka_topic=config.kafka_topic_name,
		region_name=config.region_name,
		last_n_days=config.last_n_days,
	)

	

	# latest_feature_D_data = feature_D_data[0]
	
	# logger.info(feature_D_data)

	# breakpoint()
	# print('Breakpoint')
	
