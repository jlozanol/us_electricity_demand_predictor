from datetime import datetime, timedelta
from typing import Optional

import hopsworks
import pandas as pd
from hsfs.feature_group import FeatureGroup
from hsfs.feature_store import FeatureStore
from hsfs.feature_view import FeatureView
from loguru import logger


class FeatureReader:
	"""
	Reads features from our 2 features groups and prepares data for ML training/inference.
	
	This class handles all interactions with the Hopsworks Feature Store, including:
	- Connecting to the feature store
	- Creating or retrieving feature views
	- Joining electricity demand and weather feature groups
	- Preprocessing the data for model training and inference
	
	The two main feature groups are:
	- Electricity demand: Contains historical demand data by region
	- Weather: Contains weather conditions by region
	
	The class creates a feature view that joins these groups and provides
	methods to retrieve and preprocess the data for ML workflows.
	"""

	def __init__(
		self,
		hopsworks_project_name: str,
		hopsworks_api_key: str,
		feature_view_name: str,
		feature_view_version: int,
		demand_feat_group_name: Optional[str] = None,
		demand_feat_group_version: Optional[int] = None,
		weather_feat_group_name: Optional[str] = None,
		weather_feat_group_version: Optional[int] = None,
	):
		"""
		Initialize the FeatureReader with connection to Hopsworks Feature Store.
		
		This constructor either retrieves an existing feature view or creates a new one
		by joining the demand and weather feature groups.
		
		Args:
			hopsworks_project_name: Name of the Hopsworks project
			hopsworks_api_key: API key for Hopsworks authentication
			feature_view_name: Name of the feature view to use or create
			feature_view_version: Version of the feature view
			demand_feat_group_name: Name of the demand feature group (required for creation)
			demand_feat_group_version: Version of the demand feature group (required for creation)
			weather_feat_group_name: Name of the weather feature group (required for creation)
			weather_feat_group_version: Version of the weather feature group (required for creation)
		"""
		# Connect to the Hopsworks Feature Store
		self.feature_view_name = feature_view_name
		self._feature_store = self._get_feature_store(
			hopsworks_project_name,
			hopsworks_api_key,
		)

		# Check if the feature view already exists
		available_feature_views = self._list_existing_feature_views(
			self.feature_view_name
		)
		
		if len(available_feature_views) > 0:
			# Use existing feature view if available
			logger.info(
				f'Getting feature view {feature_view_name}-{feature_view_version}'
			)
			self._feature_view = self._get_feature_view(
				feature_view_name,
				feature_view_version,
			)
		else:
			# Create a new feature view if none exists
			logger.info(
				f'Attempt to create the feature view {feature_view_name}-{feature_view_version}'
			)
			self._feature_view = self._create_feature_view(
				feature_view_name,
				feature_view_version,
				demand_feat_group_name,
				demand_feat_group_version,
				weather_feat_group_name,
				weather_feat_group_version,
			)

	def _get_feature_group(self, name: str, version: int) -> FeatureGroup:
		"""
		Retrieve a feature group from the feature store by name and version.
		
		Args:
			name: Name of the feature group
			version: Version of the feature group
			
		Returns:
			FeatureGroup: The requested feature group object
		"""
		return self._feature_store.get_feature_group(
			name=name,
			version=version,
		)

	def _create_feature_view(
		self,
		feature_view_name: str,
		feature_view_version: int,
		demand_feat_group_name: str,
		demand_feat_group_version: int,
		weather_feat_group_name: str,
		weather_feat_group_version: int,
	) -> FeatureView:
		"""
		Creates a feature view by joining the demand and weather feature groups.
		
		This method performs a left join between the demand and weather feature groups
		on the 'region' column, prefixing weather features with 'weather_' to avoid
		column name conflicts.
		
		Args:
			feature_view_name: Name for the new feature view
			feature_view_version: Version for the new feature view
			demand_feat_group_name: Name of the demand feature group
			demand_feat_group_version: Version of the demand feature group
			weather_feat_group_name: Name of the weather feature group
			weather_feat_group_version: Version of the weather feature group
			
		Returns:
			FeatureView: The newly created feature view object
		"""
		# Retrieve the two feature groups we need to join
		demand_fg = self._get_feature_group(
			demand_feat_group_name,
			demand_feat_group_version,
		)
		weather_fg = self._get_feature_group(
			weather_feat_group_name,
			weather_feat_group_version,
		)

		# Create a query that joins the two feature groups on the 'region' column
		# Using a left join to ensure we keep all demand records even if weather data is missing
		query = demand_fg.select_all().join(
			weather_fg.select_all(),
			on=['region'],
			join_type='left',
			prefix='weather_',  # Prefix to avoid column name conflicts
		)

		# Create the feature view using the join query
		feature_view = self._feature_store.create_feature_view(
			name=feature_view_name,
			version=feature_view_version,
			query=query,
		)
		logger.info(f'Feature view {feature_view_name}-{feature_view_version} created')

		return feature_view

	def _get_feature_view(
		self, feature_view_name: str, feature_view_version: int
	) -> FeatureView:
		"""
		Retrieve an existing feature view from the feature store.
		
		Args:
			feature_view_name: Name of the feature view
			feature_view_version: Version of the feature view
			
		Returns:
			FeatureView: The requested feature view object
		"""
		return self._feature_store.get_feature_view(
			name=feature_view_name,
			version=feature_view_version,
		)

	def _get_feature_store(self, project_name: str, api_key: str) -> FeatureStore:
		"""
		Connect to the Hopsworks Feature Store using project credentials.
		
		Args:
			project_name: Name of the Hopsworks project
			api_key: API key for Hopsworks authentication
			
		Returns:
			FeatureStore: The connected feature store object
		"""
		logger.info('Getting feature store')
		project = hopsworks.login(project=project_name, api_key_value=api_key)
		fs = project.get_feature_store()
		return fs

	def _list_existing_feature_views(self, feature_view_name):
		"""
		List all feature views with the given name in the connected Hopsworks project.
		
		This method logs information about each found feature view and returns the list
		of feature views for further processing.
		
		Args:
			feature_view_name: Name of the feature views to search for
			
		Returns:
			list: List of feature view objects with the specified name
		"""
		logger.info('Listing all feature views in the feature store...')
		feature_views = self._feature_store.get_feature_views(name=feature_view_name)
		for fv in feature_views:
			logger.info(f'Feature View: {fv.name}, Version: {fv.version}')
		return feature_views

	def get_training_data(self, days_back: int):
		"""
		Retrieve and preprocess training data from the feature view.
		
		This method fetches data from the feature view for the specified time period
		and preprocesses it into the format required for model training.
		
		Args:
			days_back: Number of days of historical data to retrieve
			
		Returns:
			pd.DataFrame: Preprocessed DataFrame ready for model training
		"""
		# Retrieve raw features from the Feature Store for the specified time period
		logger.info(f'Getting training data going back {days_back} days')
		raw_features = self._feature_view.get_batch_data(
			start_time=datetime.now() - timedelta(days=days_back),
			end_time=datetime.now(),
		)

		# Preprocess the raw features into the format needed for training
		features = self._raw_features_into_features(raw_features)

		return features

	def _raw_features_into_features(
		self,
		data: pd.DataFrame,
	) -> pd.DataFrame:
		"""
		Preprocess raw feature data into a format suitable for ML training.
		
		This method:
		1. Removes unnecessary columns
		2. Sorts data by region and timestamp
		3. Creates the target variable by shifting the demand column
		   (predicting the next hour's demand)
		
		Args:
			data: Raw DataFrame from the feature view
			
		Returns:
			pd.DataFrame: Processed DataFrame with features and target variable
		"""
		# Remove columns that aren't needed for training
		df = data.drop(
			[
				'human_read_period',     # Human-readable timestamp (redundant)
				'hour_category',         # Categorical hour (redundant with timestamp)
				'weather_region',        # Duplicate of region column
				'weather_timestamp_ms',  # Weather timestamp (redundant)
				'weather_human_read_period',  # Human-readable weather timestamp
				'ti',                    # Feature is not available for all timeframes when querying in real time
                'ng',                    # Feature is not available for all timeframes when querying in real time
			],
			axis=1,
		)

		# Sort by region and timestamp to ensure proper time series ordering
		df = df.sort_values(by=['region', 'timestamp_ms']).reset_index(drop=True)

		# Create the target variable by shifting demand values forward by 1 hour
		# This sets up our prediction task: predict the next hour's demand
		# The groupby ensures we don't create targets that cross region boundaries
		df['target'] = df.groupby('region')['demand'].shift(-1)

		return df
