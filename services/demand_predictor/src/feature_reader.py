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
	Reads features from our 2 features groups
	- electricity demand
	- weather from region
	and preprocess it so that it has the format (features, target) we need for
	training and for inference.
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
		# connect to the Hopsworks Feature Store
		self.feature_view_name = feature_view_name
		self._feature_store = self._get_feature_store(
			hopsworks_project_name,
			hopsworks_api_key,
		)

		available_feature_views = self._list_existing_feature_views(
			self.feature_view_name
		)
		if len(available_feature_views) > 0:
			logger.info(
				f'Getting feature view {feature_view_name}-{feature_view_version}'
			)
			self._feature_view = self._get_feature_view(
				feature_view_name,
				feature_view_version,
			)
		else:
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
		Returns a feature group object given its name and version.
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
		Creates a feature view by joining the demand_feature and weather_feature
		feature groups.

		Args:
			feature_view_name: The name of the feature view to create.
			feature_view_version: The version of the feature view to create.
			demand_feat_group_name: The name of the demand feature group.
			demand_feat_group_version: The version of the demand feature group.
			weather_feat_group_name: The name of the weather feature group.
			weather_feat_group_version: The version of the weather feature group.

		Returns:
			The feature view object.
		"""

		# we get the 2 features groups we need to join
		demand_fg = self._get_feature_group(
			demand_feat_group_name,
			demand_feat_group_version,
		)
		weather_fg = self._get_feature_group(
			weather_feat_group_name,
			weather_feat_group_version,
		)

		# Attempt to create the feature view in one query
		query = demand_fg.select_all().join(
			weather_fg.select_all(),
			on=['region'],
			join_type='left',
			prefix='weather_',
		)

		# attempt to create the feature view
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
		Returns a feature view object given its name and version.
		"""
		return self._feature_store.get_feature_view(
			name=feature_view_name,
			version=feature_view_version,
		)

	def _get_feature_store(self, project_name: str, api_key: str) -> FeatureStore:
		"""
		Returns a feature store object.
		"""
		logger.info('Getting feature store')
		project = hopsworks.login(project=project_name, api_key_value=api_key)
		fs = project.get_feature_store()
		return fs

	def _list_existing_feature_views(self, feature_view_name):
		"""
		List all feature views available in the connected Hopsworks project.
		"""
		logger.info('Listing all feature views in the feature store...')
		feature_views = self._feature_store.get_feature_views(name=feature_view_name)
		for fv in feature_views:
			logger.info(f'Feature View: {fv.name}, Version: {fv.version}')
		return feature_views

	def get_training_data(self, days_back: int):
		"""
		Use the self._feature_view to get the training data going back `days_back` days.
		"""
		# get features from the Feature Store
		logger.info(f'Getting training data going back {days_back} days')
		raw_features = self._feature_view.get_batch_data(
			start_time=datetime.now() - timedelta(days=days_back),
			end_time=datetime.now(),
		)

		features = self._raw_features_into_features(raw_features)

		return features

	def _raw_features_into_features(
		self,
		data: pd.DataFrame,
	) -> pd.DataFrame:
		"""
		Preprocess the raw features into a clear dataframe for feature processing.
		"""
		df = data.drop(
			[
				'human_read_period',
				'hour_category',
				'weather_region',
				'weather_timestamp_ms',
				'weather_human_read_period',
			],
			axis=1,
		)

		# Sort by timestamp_ms first, then by region
		df = df.sort_values(by=['region', 'timestamp_ms']).reset_index(drop=True)

		# Create the 'target' column by shifting 'demand' by -1 within each region
		df['target'] = df.groupby('region')['demand'].shift(-1)

		return df
