from typing import Optional

import pandas as pd


class DummyModel:
	"""
	A dummy model that predicts the last known electricity demand and assumes
	it will be the same 1 hour into the future.
	We use this model to compare the performance of our ML model with a simple heuristic.
	"""

	def __init__(
		self,
		from_feature: Optional[str] = 'demand',
	):
		"""
		Initialize the dummy model. We store the name of the feature we will use as the prediction.

		Args:
			from_feature: The feature to use as the prediction.
		"""
		self.from_feature = from_feature

	def predict(self, data: pd.DataFrame) -> pd.DataFrame:
		"""
		Predict the next electricity demand value, based on the feature used for prediction.

		Args:
			data (pd.DataFrame): Input data.

		Returns:
			pd.DataFrame: A DataFrame with the predicted demand values.

		Raises:
			ValueError: If the feature is not found in the input data.
		"""
		try:
			return data[self.from_feature]
		except Exception as e:
			raise Exception(f'Feature {self.from_feature} not found in data') from e
