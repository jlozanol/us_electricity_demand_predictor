from typing import Optional

from datetime import datetime

import comet_ml
import joblib
import pandas as pd
from config import config, services_credentials
from feature_reader import FeatureReader
from loguru import logger
from models.dummy_model import DummyModel
from models.xgboost_model import XGBoostModel
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def main(
	hopsworks_project_name: str,
	hopsworks_api_key: str,
	comet_ml_api_key: str,
	comet_ml_project_name: str,
	feature_view_name: str,
	feature_view_version: int,
	demand_feat_group_name: Optional[str],
	demand_feat_group_version: Optional[int],
	weather_feat_group_name: Optional[str],
	weather_feat_group_version: Optional[int],
	region_names: Optional[list],
	hyperparameter_tuning_search_trials: int,
	hyperparameter_tuning_n_splits: int,
	model_status: str,
	days_back: Optional[int] = None,
):
	"""
	Main function which does the following:

		1. Reads feature data from the Feature Store
		2. Splits the data into training and testing sets
		3. Trains a model on the training set
		4. Evaluates the model on the testing set
		5. Saves the model to the model registry

		Everything is instrumented with CometML.

    The model is saved to the model registry with the tag `model_tag`.

    Args:
		hopsworks_project_name (str): Hopsworks project name.
		hopsworks_api_key (str): Hopsworks API key.
		comet_ml_api_key (str): CometML API key.
		comet_ml_project_name (str): CometML project name.
		feature_view_name (str): Feature view name.
		feature_view_version (int): Feature view version.
		demand_feat_group_name (str): Demand feature group name.
		demand_feat_group_version (int): Demand feature group version.
		weather_feat_group_name (str): Weather feature group name.
		weather_feat_group_version (int): Weather feature group version.
		region_names (list): List of region names.
		region_timezones (dict): Dictionary of region timezones.
		hyperparameter_tuning_search_trials (int): Number of search trials for hyperparameter tuning.
		hyperparameter_tuning_n_splits (int): Number of splits for hyperparameter tuning.
		model_status (str): Model status.
		days_back (int): Number of days back to fetch data.
	"""

	logger.info('Starting the ML model training job...')

	# to log all parameters, metrics to our experiment tracking service
	# and model artifact to the model registry
	date_experiment = datetime.today().strftime('%y%m%d_%H%M')
	experiment = comet_ml.start(
		api_key=comet_ml_api_key,
		project_name=comet_ml_project_name,
	)

	# Set a custom experiment name
	experiment_name = f'{date_experiment}-XGBoost-{"no_tuning" if hyperparameter_tuning_search_trials == 0 else "tuned"}'
	experiment.set_name(experiment_name)

	experiment.log_parameters(
		{
			'feature_view_name': feature_view_name,
			'feature_view_version': feature_view_version,
			'regions_to_predict': region_names,
			'days_back': days_back,
			'hyperparameter_tuning_search_trials': hyperparameter_tuning_search_trials,
            'hyperparameter_tuning_n_splits': hyperparameter_tuning_n_splits,
            'model_status': model_status,
		}
	)

	# 1. Read feature data from the Feature Store and finish formatting the data to make it ready for the ML model
	feature_reader = FeatureReader(
		hopsworks_project_name=hopsworks_project_name,
		hopsworks_api_key=hopsworks_api_key,
		feature_view_name=feature_view_name,
		feature_view_version=feature_view_version,
		demand_feat_group_name=demand_feat_group_name,
		demand_feat_group_version=demand_feat_group_version,
		weather_feat_group_name=weather_feat_group_name,
		weather_feat_group_version=weather_feat_group_version,
	)

	training_data = feature_reader.get_training_data(days_back=days_back)

	# Drop rows with any NaN values in the raw DataFrame
	training_data.dropna(inplace=True)
	
	# Convert the min and max timestamp_ms values to datetime format
	min_timestamp = pd.to_datetime(training_data['timestamp_ms'], unit='ms').min()
	max_timestamp = pd.to_datetime(training_data['timestamp_ms'], unit='ms').max()

	logger.info(f'Training data acquired from {min_timestamp} to {max_timestamp}\n\n')
	experiment.log_parameters(
			{
				'min_timestamp': min_timestamp,
				'max_timestamp': max_timestamp,
			}
		)

	## THIS IS OPTIONAL ---
	# # Save the training data as a Pandas DataFrame and export it as a CSV
	# df = pd.DataFrame(training_data)
	# output_path = './training_data.csv'
	# df.to_csv(output_path, index=False)
	# logger.info(f'Training data saved to {output_path}')

	## FINISHING THE OPTIONAL PART ---

	# Extract forecast data into a separate DataFrame
	df_forecast = training_data[['timestamp_ms', 'region', 'demand', 'forecast']].copy()

	# Drop the forecast column from the main analysis DataFrame
	df = training_data.drop('forecast', axis=1)

	# Working on the ML model for each region availeble in the dataset
	for region in region_names:
		# Filter the DataFrame for the current region
		df_region = df[df['region'] == region].copy()
		logger.info(f'Complete dataset for {region} has {len(df_region)} rows')

		# 2. Split the data into training and testing sets
		train_df, test_df = train_test_split(df_region, test_size=0.2)

		# 3. Split into features and target
		X_train = train_df.drop(columns=['region', 'target'])
		y_train = train_df['target'].astype(int)
		X_test = test_df.drop(columns=['region', 'target'])
		y_test = test_df['target'].astype(int)

		experiment.log_parameters(
			{
				f'{region}_X_train': X_train.shape,
				f'{region}_y_train': y_train.shape,
				f'{region}_X_test': X_test.shape,
				f'{region}_y_test': y_test.shape,
			}
		)

		# 4. Evaluate quick baseline model
		logger.info('Evaluating the dummy model...')
		feature = 'demand'
		y_test_pred = DummyModel(from_feature=feature).predict(X_test)
		mae_dummy_model = mean_absolute_error(y_test, y_test_pred)
		# mse_dummy_model = mean_squared_error(y_test, y_test_pred)
		# r2_dummy_model = r2_score(y_test, y_test_pred)
		experiment.log_metric(f'{region}_mae_dummy_model', mae_dummy_model)
		# logger.info(f'MSE of dummy model based on {feature}: {mse_dummy_model}')
		# logger.info(f'R2 of dummy model based on {feature}: {r2_dummy_model}')
		# logger.info(f'RMSE of dummy model based on {feature}: {mse_dummy_model ** 0.5}')

		# To check overfitting we log the model error on the training set
		y_train_pred = DummyModel(from_feature=feature).predict(X_train)
		mae_dummy_model_train = mean_absolute_error(y_train, y_train_pred)
		# mse_dummy_model_train = mean_squared_error(y_train, y_train_pred)
		# r2_dummy_model_train = r2_score(y_train, y_train_pred)
		# logger.info(f'MSE of dummy model based on {feature} on training set: {mse_dummy_model_train}')
		# logger.info(f'R2 of dummy model based on {feature} on training set: {r2_dummy_model_train}')
		# logger.info(f'RMSE of dummy model based on {feature} on training set: {mse_dummy_model_train ** 0.5}')

		# 5. Fit an ML model on the training set.
		model = XGBoostModel()
		model.fit(
			X_train,
			y_train,
			n_search_trials=hyperparameter_tuning_search_trials,
			n_splits=hyperparameter_tuning_n_splits,
    	)

		# 6. Evaluate the model on the testing set
		y_test_pred = model.predict(X_test)
		mae_xgboost_model = mean_absolute_error(y_test, y_test_pred)
		
		experiment.log_metric(f'{region}_mae', mae_xgboost_model)

		# To check overfitting we log the model error on the training set
		y_train_pred = model.predict(X_train)
		mae_xgboost_model_train = mean_absolute_error(y_train, y_train_pred)
		

		logger.info(f'MAE of dummy model based on feature {feature}: {mae_dummy_model}')
		logger.info(f'MAE of XGBoost model: {mae_xgboost_model}\n\n')

		logger.info(f'MAE of dummy model based on {feature} on training set: {mae_dummy_model_train}')
		logger.info(f'MAE of XGBoost model on training set: {mae_xgboost_model_train}\n\n')

		# 7. Save the model artifact to the experiment and upload it to the model registry
		# Save the model to local filepath
		model_name = f"{region}_xgboost_model_{'no_tuning' if hyperparameter_tuning_search_trials == 0 else 'tuned'}"
		model_filepath = f'{model_name}.joblib'
		joblib.dump(model.get_model_object(), model_filepath)

		# Log the model to Comet
		experiment.log_model(
			name=f'{model_name}',
			file_or_folder=model_filepath,
		)
		if mae_xgboost_model < mae_dummy_model:
			# This means the model is better than the dummy model
			# so we register it
			logger.info(f'Registering model {model_name} with status {model_status}')
			experiment.register_model(
				model_name=model_name,
				status=model_status,
				public=True,
			)

	logger.info('Training job done!')


def train_test_split(
	data: pd.DataFrame,
	test_size: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
	"""
	Split the given `data` into 2 dataframes based on the `timestamp_ms` column
	such that
	> the first dataframe contains the first `train_size` rows
	> the second dataframe contains the remaining rows
	"""
	train_size = int(len(data) * (1 - test_size))

	train_df = data.iloc[:train_size]
	test_df = data.iloc[train_size:]

	return train_df, test_df


if __name__ == '__main__':
	main(
		hopsworks_project_name=services_credentials.hopsworks_project_name,
		hopsworks_api_key=services_credentials.hopsworks_api_key,
		comet_ml_api_key=services_credentials.comet_api_key,
		comet_ml_project_name=services_credentials.comet_project_name,
		feature_view_name=config.feature_view_name,
		feature_view_version=config.feature_view_version,
		demand_feat_group_name=config.demand_feat_group_name,
		demand_feat_group_version=config.demand_feat_group_version,
		weather_feat_group_name=config.weather_feat_group_name,
		weather_feat_group_version=config.weather_feat_group_version,
		region_names=config.region_names,
		hyperparameter_tuning_search_trials=config.hyperparameter_tuning_search_trials,
        hyperparameter_tuning_n_splits=config.hyperparameter_tuning_n_splits,
        model_status=config.model_status,
		days_back=config.days_back,
	)
