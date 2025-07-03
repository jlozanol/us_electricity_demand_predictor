# import sys
# import os

# # Add the src directory to sys.path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
from config import config


class WeatherAPI:
	"""
	Class to fetch weather data from the Open-Meteo API.
	"""

	def __init__(self, region_name):
		self.region_name = region_name
		self.config = config
		self.base_url = 'https://api.open-meteo.com/v1/forecast'

	def get_raw_data(self, current_time: datetime) -> pd.DataFrame:
		end_date = current_time + timedelta(hours=24)
		start_date = current_time - timedelta(hours=self.config.hours_back)

		params = {
			'hourly': [
				'temperature_2m',
				'apparent_temperature',
				'dew_point_2m',
				'shortwave_radiation',
				'direct_radiation',
				'diffuse_radiation',
				'relative_humidity_2m',
				'precipitation',
				'snowfall',
				'surface_pressure',
				'wind_speed_10m',
			],
			'timezone': 'UTC',
			'start_date': start_date.strftime('%Y-%m-%d'),
			'end_date': end_date.strftime('%Y-%m-%d'),
		}

		region_weather = []
		location = config.eia_locations[self.region_name]

		for city, lat, lon in location:
			params.update({'latitude': lat, 'longitude': lon})

			response = requests.get(self.base_url, params=params)
			if response.status_code == 200:
				data = response.json()
				timestamps_ms = list(
					map(
						lambda x: int(
							pd.to_datetime(
								x, format='%Y-%m-%dT%H:%M', utc=True
							).timestamp()
							* 1000
						),
						data['hourly']['time'],
					)
				)
				timestamps_str = data['hourly']['time']
				temp = data['hourly']['temperature_2m']
				wind = data['hourly']['wind_speed_10m']
				humidity = data['hourly']['relative_humidity_2m']
				radiation = data['hourly'].get(
					'shortwave_radiation', [np.nan] * len(temp)
				)
				apparent_temp = data['hourly']['apparent_temperature']
				dew_point = data['hourly']['dew_point_2m']
				direct_rad = data['hourly'].get(
					'direct_radiation', [np.nan] * len(temp)
				)
				diffuse_rad = data['hourly'].get(
					'diffuse_radiation', [np.nan] * len(temp)
				)
				precip = data['hourly']['precipitation']
				snowfall = data['hourly']['snowfall']
				pressure = data['hourly']['surface_pressure']

				df = pd.DataFrame(
					{
						'timestamp_ms': timestamps_ms,
						'human_read_period': timestamps_str,
						'city': city,
						'temperature': temp,
						'apparent_temperature': apparent_temp,
						'dew_point': dew_point,
						'wind_speed': wind,
						'humidity': humidity,
						'solar_radiation': radiation,
						'direct_radiation': direct_rad,
						'diffuse_radiation': diffuse_rad,
						'precipitation': precip,
						'snowfall': snowfall,
						'surface_pressure': pressure,
					}
				)
				# Append the DataFrame to the list
				region_weather.append(df)

		# Combine all city DataFrames into one
		if region_weather:
			# Concatenate all DataFrames
			all_data = pd.concat(region_weather)

			# Group by timestamp and calculate averages
			aggregated_data = (
				all_data.groupby(['timestamp_ms', 'human_read_period'])
				.agg(
					{
						'temperature': 'mean',
						'apparent_temperature': 'mean',
						'dew_point': 'mean',
						'wind_speed': 'mean',
						'humidity': 'mean',
						'solar_radiation': 'mean',
						'direct_radiation': 'mean',
						'diffuse_radiation': 'mean',
						'precipitation': 'mean',
						'snowfall': 'mean',
						'surface_pressure': 'mean',
					}
				)
				.reset_index()
			)

			# Reorder columns to match original format
			region_weather = aggregated_data

		return region_weather


# if __name__ == '__main__':
# 	region = 'CAL'
# 	weather_api = WeatherAPI(region)
# 	current_time = datetime.now(timezone.utc)
# 	print(current_time)
# 	raw_data = weather_api.get_raw_data(current_time)
# 	print(raw_data)
