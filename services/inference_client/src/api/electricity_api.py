# import sys
# import os

# # Add the src directory to sys.path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from typing import Tuple

import pandas as pd
import requests
from config import config, services_credentials


class ElectricityAPI:
	"""
	Class to fetch electricity data from the EIA API.
	"""

	def __init__(self, region_name):
		self.region_name = region_name
		self.config = config
		self.api_key = services_credentials.eia_api_key
		self.base_url = 'https://api.eia.gov/v2/electricity/rto/region-data/data/'

	def get_raw_data(self, current_time: datetime) -> pd.DataFrame:
		"""
		Connecting to the EIA API for the particular region and return the raw data for the ML prediction service
		"""

		start_date, end_date = self._time_to_string(current_time)
		params = self._get_params(self.region_name, start_date, end_date)
		pre_data = self._fetch_eia_data(params)

		return self._convert_to_raw_data(pre_data)

	def _get_params(
		self,
		region_name: str,
		start_date: str,
		end_date: str,
	) -> dict:
		"""
		Get parameters for demand data API call

		Args:
			region_name (str): Region identifier
			api_key (str): API key for EIA API

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
			'start': start_date,
			'end': end_date,
			'api_key': self.api_key,
		}

	def _time_to_string(self, current_time: datetime) -> Tuple[str, str]:
		"""
		Current time to the format required by the EIA API.

		Parameters:
			None

		Returns:
			start_date (str): Start date in the format required by the EIA API.
			end_date (str): End date in the format required by the EIA API.
		"""

		end_date = current_time + timedelta(hours=24)
		start_date = current_time - timedelta(hours=self.config.hours_back)

		end_date = end_date.strftime('%Y-%m-%d')
		start_date = start_date.strftime('%Y-%m-%d')

		# Append 'T00' to dates to match API's datetime format (YYYY-MM-DDT00)
		end_date = end_date + 'T00'
		start_date = start_date + 'T00'

		return [start_date, end_date]

	def _fetch_eia_data(self, params: dict) -> list:
		"""
		Generic function to fetch data from EIA API

		Args:
			url (str): EIA API endpoint URL
			params (dict): Query parameters for the API call

		Returns:
			list: Raw data from API response
		"""
		response = requests.get(self.base_url, params=params)
		response.raise_for_status()
		return response.json()['response']['data']

	def _convert_datestring_to_ms(
		self,
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

	def _convert_to_raw_data(self, pre_data: list) -> list:
		"""
		Transform EIA API response into a list of dictionaries with the following keys:
		- timestamp: Unix timestamp in milliseconds (from YYYY-MM-DDT00)
		- region: Regional identifier
		- electricity_demand: Actual demand in megawatthours (MWh)

		Args:
			list_of_dicts (list): List of dictionaries containing the individual electricity demand data.

		Returns:
			list: List of dictionaries containing the transfo raw electricity demand data.

		"""
		# Group raw data by type (D, DF, TI, NG)
		# Initialize empty lists for all possible data types
		data_by_type = {'D': [], 'DF': [], 'TI': [], 'NG': []}
		for entry in pre_data:
			data_by_type[entry['type']].append(entry)

		list_of_dicts = [
			{
				'timestamp_ms': self._convert_datestring_to_ms(entry['period']),
				'region': entry['respondent'],
				'electricity_demand': int(entry['value']),
				'electricity_demand_type': entry['type'],
			}
			for entry in pre_data  # Changed from list_of_dicts to pre_data
		]

		"""
		list_of_dicts has the format of:
		(Pdb) list_of_dicts[0]
		{'timestamp_ms': 1746316800000, 'region': 'CAL', 'electricity_demand': 26845, 'electricity_demand_type': 'D'}
		(Pdb) list_of_dicts[1]
		{'timestamp_ms': 1746316800000, 'region': 'CAL', 'electricity_demand': 22570, 'electricity_demand_type': 'DF'}
		(Pdb) list_of_dicts[2]
		{'timestamp_ms': 1746316800000, 'region': 'CAL', 'electricity_demand': 28046, 'electricity_demand_type': 'NG'}
		(Pdb) list_of_dicts[3]
		{'timestamp_ms': 1746316800000, 'region': 'CAL', 'electricity_demand': 53, 'electricity_demand_type': 'TI'}
		This needs to be converted into a dataframe where the electricity_demand_type are the columns:
			- timestamp_ms
			- region
			- demand (replacing D)
			- demand_forecast (replacing DF)
			- total_interchange (replacing TI)
			- net_generation (replacing NG)
		"""
		# Create DataFrame and pivot in one step
		df = (
			pd.DataFrame(list_of_dicts)
			.pivot(
				index=['timestamp_ms', 'region'],
				columns='electricity_demand_type',
				values='electricity_demand',
			)
			.reset_index()
		)

		# Remove column name from the columns index
		df.columns.name = None

		# Rename and reorder columns in one step
		df = df.rename(
			columns={
				'D': 'demand',
				'DF': 'demand_forecast',
				'TI': 'total_interchange',
				'NG': 'net_generation',
			}
		)[
			[
				'timestamp_ms',
				'region',
				'demand',
				'demand_forecast',
				'total_interchange',
				'net_generation',
			]
		]

		# Find the latest row where demand is not NaN
		last_valid_demand_index = df['demand'].last_valid_index()
		# Check if demand_forecast is not NaN for the same row
		if pd.notna(df.loc[last_valid_demand_index, 'demand_forecast']):
			# If it is not NaN, keep this row
			last_valid_demand_index += 1
			# drop all the other rows from the df after last_valid_demand_index
			df = df.iloc[: last_valid_demand_index + 1]
		else:
			df = df.dropna(subset=['demand'])

		return df


# if __name__ == '__main__':
# 	region = 'CAL'
# 	electricity_api = ElectricityAPI(region)
# 	current_time = datetime.now()
# 	raw_data = electricity_api.get_raw_data(current_time)
# 	print(raw_data)
