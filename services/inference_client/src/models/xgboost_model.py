import pandas as pd
from xgboost import XGBRegressor


class XGBoostModel:
	"""
	Encapsulates the training logic with or without hyperparameter tuning using an
	XGBRegressor.
	"""

	def __init__(self):
		self.model = XGBRegressor(
			objective='reg:absoluteerror',
			eval_metric=['mae'],
		)

	def get_model_object(self):
		"""
		Returns the model object.
		"""
		return self.model

	def predict(self, X: pd.DataFrame) -> pd.Series:
		return self.model.predict(X)
