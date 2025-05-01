import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from config import config
from loguru import logger
from quixstreams import Application

# EIA Regions with significant locations and coordinates.
eia_locations = {
	'CAL': [
		('Los Angeles', 34.05, -118.25),
		('San Francisco', 37.77, -122.42),
		('Sacramento', 38.58, -121.49),
		('San Diego', 32.72, -117.16),
		('Fresno', 36.74, -119.78),
	],
	'CAR': [
		('Charlotte', 35.23, -80.84),
		('Columbia', 34.00, -81.03),
		('Raleigh', 35.78, -78.64),
		('Charleston', 32.78, -79.93),
		('Greensboro', 36.07, -79.79),
	],
	'CENT': [
		('Little Rock', 34.74, -92.33),
		('Baton Rouge', 30.45, -91.15),
		('Des Moines', 41.60, -93.61),
		('St. Louis', 38.63, -90.20),
		('Omaha', 41.26, -95.94),
	],
	'FLA': [
		('Miami', 25.76, -80.19),
		('Orlando', 28.54, -81.38),
		('Tallahassee', 30.44, -84.28),
		('Tampa', 27.95, -82.46),
		('Jacksonville', 30.33, -81.65),
	],
	'MIDW': [
		('Chicago', 41.88, -87.63),
		('Indianapolis', 39.77, -86.16),
		('Minneapolis', 44.98, -93.27),
		('Kansas City', 39.10, -94.58),
		('Columbus', 39.96, -83.00),
		('Milwaukee', 43.04, -87.91),
		('Detroit', 42.33, -83.05),
	],
	'NW': [
		('Seattle', 47.61, -122.33),
		('Portland', 45.52, -122.68),
		('Boise', 43.62, -116.20),
		('Spokane', 47.66, -117.43),
		('Missoula', 46.87, -113.99),
	],
	'NY': [
		('New York City', 40.71, -74.01),
		('Albany', 42.65, -73.75),
		('Buffalo', 42.89, -78.87),
		('Rochester', 43.16, -77.61),
		('Syracuse', 43.04, -76.14),
	],
	'SW': [
		('Las Vegas', 36.17, -115.14),
		('Phoenix', 33.45, -112.07),
		('Denver', 39.74, -104.99),
		('Salt Lake City', 40.76, -111.89),
		('Albuquerque', 35.08, -106.65),
	],
}


def get_shifted_time_range(
	last_n_days: int, shift_hours: int = 192
) -> tuple[datetime, datetime]:
	"""
	Calculate start and end dates with a specified hour shift:
	- end_time: current time minus shift_hours
	- start_time: end_time minus last_n_days

	Args:
		last_n_days (int): Number of days to look back from the end_time
		shift_hours (int, optional): Number of hours to shift back from current time. Defaults to 192 (8 days).

	Returns:
		tuple[datetime, datetime]: (start_date, end_date) as datetime objects
	"""
	current_time = datetime.now(timezone.utc)
	end_time = current_time - timedelta(hours=shift_hours)
	start_time = end_time - timedelta(days=last_n_days)

	return start_time, end_time


def fetch_weather_data(start_date, end_date):
	"""Fetches weather data from Open-Meteo API for all locations and aggregates per EIA region."""

	# Change to historical weather API endpoint
	base_url = 'https://archive-api.open-meteo.com/v1/archive'
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

	weather_data_list = []  # Collect all weather data entries

	for region, locations in eia_locations.items():
		region_weather = []

		for city, lat, lon in locations:
			params.update({'latitude': lat, 'longitude': lon})

			response = requests.get(base_url, params=params)
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

				region_weather.append(df)

		# Process each timestamp on the fly with running averages
		if region_weather:
			all_timestamps = sorted(
				set(ts for df in region_weather for ts in df['timestamp_ms'])
			)
			end_date_t00 = datetime.combine(
				end_date.date(), datetime.min.time()
			).replace(tzinfo=timezone.utc)
			end_date_t00_ms = int(end_date_t00.timestamp() * 1000)
			filtered_timestamps = [ts for ts in all_timestamps if ts <= end_date_t00_ms]

			for timestamp in filtered_timestamps:
				timestamp_data = {}

				for df in region_weather:
					row = df[df['timestamp_ms'] == timestamp]
					if not row.empty:
						for col in df.columns:
							if col != 'timestamp_ms':
								if col not in timestamp_data:
									timestamp_data[col] = []
								value = row[col].iloc[0]
								timestamp_data[col].append(value)

				avg_data = {'region': region, 'timestamp_ms': timestamp}
				for col, values in timestamp_data.items():
					if col == 'human_read_period':
						avg_data[col] = values[0]
					elif col != 'timestamp_ms':
						avg_data[col] = float(np.mean(values))

				weather_data_list.append(avg_data)

				logger.info(f'Current processed data: {avg_data}')

	return weather_data_list


def kafka_producer(
	kafka_broker_address: str,
	kafka_topic: str,
	last_n_days: int,
	live_or_historical: str,
) -> None:
	"""
	Function to fetch weather data and send it to a Kafka topic.

	Args:
		kafka_broker_address (str): The address of the Kafka broker.
		kafka_topic (str): The name of the Kafka topic.
		live_or_historical (str): Whether to fetch live or historical data.
		last_n_days (int): The number of days to fetch data for.

	Returns:
		None
	"""
	logger.info('Starting the ingestion of weather data service')

	# Initialize the Quix Streams application
	app = Application(
		broker_address=kafka_broker_address,
	)

	# Define the topic where we will push the weather data
	topic = app.topic(
		name=kafka_topic,
		value_serializer='json',
	)

	# Push the data to the Kafka Topic
	match live_or_historical:
		case 'live':
			pass

		case 'historical':
			# Historical processing logic
			with app.get_producer() as producer:
				# Get date range for historical data
				last_n_days = config.last_n_days
				start_date, end_date = get_shifted_time_range(last_n_days)

				logger.info(
					f'Fetching historical weather data from {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'
				)

				# Fetch weather data
				weather_data_list = fetch_weather_data(start_date, end_date)

				# Initialize counters for total records and per-region records
				total_records = 0
				region_records = {region: 0 for region in eia_locations.keys()}

				# Push each entry to Kafka
				for weather_data in weather_data_list:
					message = topic.serialize(
						key=weather_data['region'], value=weather_data
					)
					producer.produce(
						topic=topic.name, value=message.value, key=message.key
					)
					total_records += 1  # Increment grand total counter
					region_records[weather_data['region']] += (
						1  # Increment per-region counter
					)
					logger.info(
						f'Historical weather data pushed to Kafka: {weather_data}'
					)

				# Log total records sent per region
				logger.info('\n=== Final Processing Summary ===')
				for region, count in region_records.items():
					logger.info(f'Region {region}: {count:,} records')
				logger.info(f'Grand Total: {total_records:,} records')
				logger.info('Finished pushing historical weather data to Kafka')

		case _:
			raise ValueError(
				"Error: live_or_historical must be either 'live' or 'historical'"
			)


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

	# Call the kafka_producer function with configuration
	kafka_producer(
		kafka_broker_address=config.kafka_broker_address,
		kafka_topic=config.kafka_topic,
		live_or_historical=config.live_or_historical,
		last_n_days=config.last_n_days,
	)


if __name__ == '__main__':
	main()
