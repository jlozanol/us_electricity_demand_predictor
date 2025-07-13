from typing import Tuple

import holidays
import numpy as np
import pandas as pd
from api.electricity_api import ElectricityAPI
from api.weather_api import WeatherAPI


class FeatureCreator:
	def __init__(self, region_name, current_time):
		self.region_name = region_name
		self.current_time = current_time

	def create_features(
		self,
	) -> Tuple[pd.DataFrame, pd.DataFrame]:
		"""
		Create features for electricity demand prediction by merging weather and demand data.
		Args:
			None
		Returns:
			Tuple[pd.DataFrame, pd.DataFrame]: A tuple containing two DataFrames:
				1. features_data: DataFrame with demand and weather features.
				2. demand_forecast: DataFrame with demand forecast.
		"""
		weather_data = self._get_weather_data()
		weather_data.drop(columns=['human_read_period'], inplace=True)
		weather_data = weather_data.sort_values(by='timestamp_ms').reset_index(
			drop=True
		)

		# Add 'weather_' prefix to all columns except 'timestamp_ms'
		weather_cols = [col for col in weather_data.columns if col != 'timestamp_ms']
		weather_data = weather_data.rename(
			columns={col: f'weather_{col}' for col in weather_cols}
		)

		demand_data = self._get_demand_data()
		demand_data = demand_data.sort_values(by='timestamp_ms').reset_index(drop=True)

		demand_forecast = demand_data[['timestamp_ms', 'demand_forecast']].copy()
		demand_data = demand_data[['timestamp_ms', 'demand']]
		demand_data = demand_data.dropna(subset=['demand'])

		demand_data = self._temporal_features(demand_data)
		demand_data = self._rolling_features(demand_data)

		features_data = pd.merge(
			demand_data, weather_data, on=['timestamp_ms'], how='left'
		)

		return features_data, demand_forecast

	def _get_demand_data(
		self,
	) -> Tuple[pd.DataFrame, pd.DataFrame]:
		"""
		Get electricity demand data for the specified region and time.
		Args:
			None
		Returns:
			Tuple[pd.DataFrame, pd.DataFrame]: A tuple containing two DataFrames:
				1. demand_data: DataFrame with electricity demand data.
				2. demand_forecast: DataFrame with demand forecast.
		"""
		electricity_api = ElectricityAPI(self.region_name)

		return electricity_api.get_raw_data(self.current_time)

	def _get_weather_data(
		self,
	) -> pd.DataFrame:
		"""
		Get weather data for the specified region and time.
		Args:
			None
		Returns:
			pd.DataFrame: DataFrame with weather data.
		"""
		# Initialize the WeatherAPI with the region name
		weather_api = WeatherAPI(self.region_name)

		return weather_api.get_raw_data(self.current_time)

	def _temporal_features(self, data: pd.DataFrame) -> pd.DataFrame:
		"""
		Compute temporal features from historical data using DataFrame input/output.

		Args:
			data: DataFrame containing demand data

		Returns:
			DataFrame enriched with time features
		"""
		result_df = data.copy()
		time_data = pd.to_datetime(result_df['timestamp_ms'], unit='ms', utc=True)

		# Extract time components
		hour = time_data.dt.hour
		day_of_week = time_data.dt.weekday
		month = time_data.dt.month

		# Add hour categorization
		is_weekend = day_of_week >= 5  # 5=Saturday, 6=Sunday

		# Initialize with default category (0 = off peak)
		result_df['hour_category_num'] = 0

		# Add holiday indicator
		us_holidays = holidays.US()
		is_holiday = time_data.dt.date.apply(lambda x: x in us_holidays)

		# Convert boolean Series to integer Series (1 for holiday, 0 for non-holiday)
		result_df['is_holiday'] = is_holiday.astype(int)

		# Set category 2 (evening peak) for all days where time is 18-22
		evening_peak_mask = (18 <= hour) & (hour <= 22)
		result_df.loc[evening_peak_mask, 'hour_category_num'] = 2

		# Set category 1 (office hours) only for weekdays where time is 9-17
		office_hours_mask = (~is_weekend) & (9 <= hour) & (hour <= 17)
		result_df.loc[office_hours_mask, 'hour_category_num'] = 1

		# Add cyclical encodings (sin/cos transformations)
		result_df['hour_sin'] = np.sin(2 * np.pi * hour / 24)
		result_df['hour_cos'] = np.cos(2 * np.pi * hour / 24)
		result_df['day_of_week_sin'] = np.sin(2 * np.pi * day_of_week / 7)
		result_df['day_of_week_cos'] = np.cos(2 * np.pi * day_of_week / 7)
		result_df['month_sin'] = np.sin(2 * np.pi * month / 12)
		result_df['month_cos'] = np.cos(2 * np.pi * month / 12)

		return result_df

	def _rolling_features(self, data: pd.DataFrame) -> pd.DataFrame:
		"""
		Compute statistical features from historical data using DataFrame input/output.

		Args:
			data: DataFrame containing demand data

		Returns:
			DataFrame enriched with statistical features
		"""
		# Create a copy to avoid modifying the original
		result_df = data.copy()

		if not data.empty and 'demand' in data.columns:
			# Rolling window calculations
			# 3-hour window
			result_df['mean_3'] = result_df['demand'].rolling(window=3).mean()
			result_df['median_3'] = result_df['demand'].rolling(window=3).median()

			# 24-hour window
			result_df['mean_24'] = result_df['demand'].rolling(window=24).mean()
			result_df['median_24'] = result_df['demand'].rolling(window=24).median()

			# 168-hour window
			result_df['mean_168'] = result_df['demand'].rolling(window=168).mean()
			result_df['median_168'] = result_df['demand'].rolling(window=168).median()

			# Lag features
			result_df['lag_1h'] = result_df['demand'].shift(1)
			result_df['lag_24h'] = result_df['demand'].shift(24)
			result_df['lag_168h'] = result_df['demand'].shift(168)

		else:
			# Default values when no data is available
			default_value = 0.0
			for key in [
				'mean_3',
				'median_3',
				'mean_24',
				'median_24',
				'mean_168',
				'median_168',
				'lag_1h',
				'lag_24h',
				'lag_168h',
			]:
				result_df[key] = default_value

		return result_df
