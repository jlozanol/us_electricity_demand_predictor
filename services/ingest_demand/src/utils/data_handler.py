from datetime import datetime, timedelta, timezone

from demand_api.api import connect_api
from loguru import logger


def get_data(
	start_day: str | None = None,
	end_day: str | None = None,
	region_name: str = None,
	demand_type: str = None,
	last_n_days: int | None = None,
) -> list:
	"""
	Gets electricity demand data from the EIA API. Can handle both live and historical data requests.

	Args:
		start_day (str, optional): Start date in YYYY-MM-DDT00 format. If None, calculated from last_n_days.
		end_day (str, optional): End date in YYYY-MM-DDT00 format. If None, calculated from last_n_days.
		region_name (str): The name of the region to fetch data for.
		demand_type (str): The type of demand data to fetch ('D' for actual demand, 'DF' for day-ahead forecast).
		last_n_days (int, optional): The number of days to fetch data for. Used if start_day/end_day not provided.

	Returns:
		list: A list of dictionaries containing the electricity demand data.
	"""
	# If dates not provided, calculate them from last_n_days
	if start_day is None or end_day is None:
		if last_n_days is None:
			raise ValueError('Either start_day/end_day or last_n_days must be provided')
		start_day, end_day = time_to_string(last_n_days)

	# Get EIA API data for the specified date range
	data = connect_api(start_day, end_day, region_name, demand_type)
	feature_data = convert_to_feature(data)

	return feature_data


def process_batch(
	feature_data: list, batch_count: int, data_type: str
) -> tuple[bool, str, list]:
	"""Process a batch of data and determine if more data needs to be fetched"""
	total_elements = len(feature_data)
	has_more_data = total_elements == 5000
	end_day = None

	if has_more_data:
		cutoff_index = None
		for i, data in enumerate(reversed(feature_data)):
			if data['human_read_period'].endswith('T01'):
				cutoff_index = len(feature_data) - i
				break

		if cutoff_index is not None:
			feature_data = feature_data[:cutoff_index]
			last_entry = feature_data[-1]['human_read_period']
			end_day = last_entry.replace('T01', 'T00')
		else:
			last_timestamp = feature_data[-1]['human_read_period']
			end_day = datetime.strptime(last_timestamp, '%Y-%m-%dT%H')
			end_day = (end_day - timedelta(hours=1)).strftime('%Y-%m-%dT%H')

		logger.info(f'Batch {batch_count} complete. Maximum records reached (5000)')
		logger.info(f'Starting batch {batch_count + 1} with end_day: {end_day}')
	else:
		logger.info(f'Final batch with {total_elements} records')

	return has_more_data, end_day, feature_data

def collect_demand_data(
	start_day: str,
	end_day: str,
	region_name: str,
	demand_type: str,
	data_label: str,
) -> dict:
	"""
	Collect demand data (actual or forecast) for a given region and time range.
	
	Args:
		start_day: Start date for data collection
		end_day: End date for data collection
		region_name: Name of the region
		demand_type: Type of demand data ('D' for actual, 'DF' for forecast)
		data_label: Label for logging ('actual' or 'forecast')
		
	Returns:
		Dictionary mapping timestamps to demand data
	"""
	has_more_data = True
	batch_count = 1
	collected_data = {}
	current_end_day = end_day

	while has_more_data:
		logger.info(
			f'Fetching batch {batch_count} for {data_label} demand '
			f'data in region {region_name}'
		)
		logger.info(f'Time range: {start_day} to {current_end_day}')

		feature_data = get_data(
			start_day=start_day,
			end_day=current_end_day,
			region_name=region_name,
			demand_type=demand_type,
		)

		has_more_data, current_end_day, feature_data = process_batch(
			feature_data, batch_count, data_label
		)

		for data in feature_data:
			ts = data['timestamp_ms']
			collected_data[ts] = {
				'timestamp_ms': ts,
				'human_read_period': data['human_read_period'],
				'region': data['region'],
				'demand_actual': data['demand'] if demand_type == 'D' else None,
				'demand_forecast': data['demand'] if demand_type == 'DF' else None,
			}

		batch_count += 1

	return collected_data


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
			'demand': int(entry['value']),
			'demand_type': entry['type'],
		}
		for entry in list_of_dicts
	]

	return list_of_dicts
