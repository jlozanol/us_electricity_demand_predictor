from typing import Tuple

import joblib
import pandas as pd
from comet_ml.api import API
from config import config, services_credentials
from loguru import logger
from models.xgboost_model import XGBoostModel
from packaging import version
from pydantic import BaseModel

Model = XGBoostModel


class PredictionOutput(BaseModel):
	"""
	Pydantic model for prediction output.
	"""

	predictions: list[float]

	def to_dict(self) -> dict:
		"""
		Convert PredictionOutput to dictionary.

		Returns:
			dict: Dictionary representation of the prediction output.
		"""
		return self.model_dump()


class PricePredictor:
	"""
	Class for fetching and using a price prediction model for a given region.
	"""

	def __init__(self, region_name: str) -> None:
		"""
		Initialise the PricePredictor.

		Args:
			region_name (str): Name of the region.

		Returns:
			None
		"""
		self.comet_credentials = services_credentials
		self.comet_api = API(api_key=services_credentials.comet_api_key)
		self.region_name = region_name
		self.model_status = config.model_status

		self.model_name, self.model_version = self._get_model_name_and_version(
			self.region_name
		)

		# Load the model from the model registry
		self.model, experiment_key = self._get_model_from_model_registry(
			model_name=self.model_name,
			model_version=self.model_version,
			comet_api=self.comet_api,
		)

		self.experiment_name = self._get_experiment_name(
			comet_api=self.comet_api,
			experiment_key=experiment_key,
		)

		logger.info(
			f'Model {self.model_name} version {self.model_version} from experiment {self.experiment_name} has been downloaded successfully.'
		)

	def predict(self, df: pd.DataFrame) -> PredictionOutput:
		"""
		Predict electricity demand values for all rows in the input DataFrame.

		Args:
			df (pd.DataFrame): Input DataFrame containing features for prediction.

		Returns:
			PredictionOutput: A Pydantic model containing a list of predictions.
		"""
		self.df = df
		# Efficiently predict and convert to list
		predictions = self.model.predict(self.df).tolist()
		return PredictionOutput(predictions=predictions)

	def model_information(self) -> dict:
		"""
		Shows the information about the model (model name, version and experiment).

		Returns:
			dict: Model information including region, model name, version, and experiment name.
		"""
		return {
			'region': self.region_name,
			'model_name': self.model_name,
			'model_version': self.model_version,
			'experiment_name': self.experiment_name,
		}

	def _get_model_name_and_version(self, region_name: str) -> Tuple[str, str]:
		"""
		Get the model name and version from the Comet ML registry, prioritizing:
		1. Models with the requested status
		2. Tuned models over non-tuned models
		3. Highest version number

		Args:
			region_name (str): Name of the region.

		Returns:
			tuple: (model_name, model_version)
		"""
		registry_names = self.comet_api.get_registry_model_names(
			workspace=self.comet_credentials.comet_workspace
		)

		# Get all models matching the region name
		model_names = [
			model for model in registry_names if region_name.lower() in model.lower()
		]
		if not model_names:
			raise ValueError(f'No models found for region {region_name}')

		# Find all models with matching status and their versions
		models_with_status = []
		for name in model_names:
			model_details = self.comet_api.get_registry_model_details(
				workspace=self.comet_credentials.comet_workspace, registry_name=name
			)

			matching_versions = [
				version_info['version']
				for version_info in model_details['versions']
				if version_info['status'] == self.model_status
			]

			if matching_versions:
				# Sort versions by semantic version
				sorted_versions = sorted(
					matching_versions, key=version.parse, reverse=True
				)
				models_with_status.append(
					{
						'name': name,
						'versions': sorted_versions,
						'is_tuned': 'tuned' in name.lower(),
					}
				)

		if not models_with_status:
			raise ValueError(
				f'No models found for region {region_name} with status {self.model_status}'
			)

		# Sort by tuned status (True first) and then by version count
		models_with_status.sort(key=lambda x: (not x['is_tuned'], -len(x['versions'])))
		# Return the best model (tuned if available, with highest version)
		return models_with_status[0]['name'], models_with_status[0]['versions'][0]

	def _get_model_from_model_registry(
		self,
		model_name: str,
		model_version: str,
		comet_api: API,
	) -> Tuple[Model, str]:
		"""
		Loads the model from the model registry, and returns the model and the
		corresponding experiment run key that generated that model artifact.

		Args:
			model_name (str): The name of the model to load from the model registry.
			model_version (str): The version of the model to load from the model registry.
			comet_api (API): The Comet API object to interact with the model registry.

		Returns:
			tuple: (model object loaded from the model registry, experiment run key)
		"""
		# Download the model artifact from the model registry
		model = comet_api.get_model(
			workspace=self.comet_credentials.comet_workspace,
			model_name=model_name,
		)

		# Download the model artifact for this `model_version`
		model.download(version=model_version, output_folder='./model_artifacts')

		# Find the experiment associated with this model
		experiment_key = model.get_details(version=model_version)['experimentKey']

		# Load the model from the file to memory
		model_file = f'./model_artifacts/{model_name}.joblib'
		model = joblib.load(model_file)

		return model, experiment_key

	def _get_experiment_name(
		self,
		comet_api: API,
		experiment_key: str,
	) -> str:
		"""
		Retrieve the experiment name for the given experiment key.

		Args:
			comet_api (API): The Comet API object.
			experiment_key (str): The experiment key.

		Returns:
			str: The experiment name.
		"""
		experiment_metadata = comet_api.get_experiment_by_key(
			experiment_key=experiment_key
		)
		experiment_name = experiment_metadata.get_name()
		return experiment_name
