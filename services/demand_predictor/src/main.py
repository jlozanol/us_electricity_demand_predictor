from typing import Optional

from datetime import datetime
import os

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
    days_back: int,
    debug_mode: bool,
):
    """
    Main function for the electricity demand prediction model training pipeline.
    
    This function orchestrates the complete ML workflow:

        1. Reads feature data from the Hopsworks Feature Store
        2. Splits the data into training and testing sets
        3. Trains an XGBoost model on the training set
        4. Evaluates the model against a baseline dummy model
        5. Saves the trained model to the CometML model registry

    All metrics, parameters, and artifacts are tracked with CometML for experiment tracking.
    The model is saved to the model registry with appropriate status tags.

    Args:
        hopsworks_project_name (str): Name of the Hopsworks project containing feature store.
        hopsworks_api_key (str): API key for authenticating with Hopsworks.
        comet_ml_api_key (str): API key for authenticating with CometML.
        comet_ml_project_name (str): Name of the CometML project for experiment tracking.
        feature_view_name (str): Name of the feature view in Hopsworks.
        feature_view_version (int): Version of the feature view to use.
        demand_feat_group_name (str, optional): Name of the demand feature group.
        demand_feat_group_version (int, optional): Version of the demand feature group.
        weather_feat_group_name (str, optional): Name of the weather feature group.
        weather_feat_group_version (int, optional): Version of the weather feature group.
        region_names (list, optional): List of region names to train models for.
        hyperparameter_tuning_search_trials (int): Number of trials for hyperparameter tuning (0 = no tuning).
        hyperparameter_tuning_n_splits (int): Number of cross-validation splits for hyperparameter tuning.
        model_status (str): Status to assign to the model in registry ('Development', 'Staging', 'Production').
        days_back (int): Number of days of historical data to use for training.
        debug_mode (bool): If True, saves intermediate data to files for debugging.
    """

    logger.info('Starting the ML model training job...\n\n')
    if debug_mode:
        logger.info('Debug mode is enabled. DataFrames will be saved locally...\n\n')

    # Initialize CometML experiment for tracking metrics, parameters, and artifacts
    date_experiment = datetime.today().strftime('%y%m%d_%H%M')
    experiment = comet_ml.start(
        api_key=comet_ml_api_key,
        project_name=comet_ml_project_name,
    )

    # Set a descriptive experiment name with timestamp and tuning information
    experiment_name = f'{date_experiment}-XGBoost-{"no_tuning" if hyperparameter_tuning_search_trials == 0 else "tuned"}'
    experiment.set_name(experiment_name)

    # Log key configuration parameters to CometML
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

    # Step 1: Initialize feature reader and fetch training data from Feature Store
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

    # Fetch training data for the specified time period
    training_data = feature_reader.get_training_data(days_back=days_back)

    # Clean the data by removing rows with missing values
    training_data.dropna(inplace=True)
    
    # Log the time range of the training data
    dataset_min_timestamp = pd.to_datetime(training_data['timestamp_ms'], unit='ms').min()
    dataset_max_timestamp = pd.to_datetime(training_data['timestamp_ms'], unit='ms').max()

    logger.info(f'Training data acquired from {dataset_min_timestamp} to {dataset_max_timestamp}\n\n')
    experiment.log_parameters(
            {
                'dataset_min_timestamp': dataset_min_timestamp,
                'dataset_max_timestamp': dataset_max_timestamp,
            }
        )

    # Save training data to CSV if in debug mode
    if debug_mode:
        os.makedirs('files', exist_ok=True)
        logger.info('Debug mode is enabled. Saving the training data as a CSV file...')
        df = pd.DataFrame(training_data)
        output_path = 'files/training_data.csv'
        df.to_csv(output_path, index=False)
        logger.info(f'Training data saved to {output_path}')

    # Train separate models for each region in the dataset
    for region in region_names:
        logger.info(f'Training model for region: {region}')
        
        # Filter data for the current region
        df_region = training_data[training_data['region'] == region].copy()
        
        # Extract forecast data for debugging if enabled
        if debug_mode:
            df_forecast = df_region[['timestamp_ms', 'demand', 'forecast']].copy()
            
        # Remove the forecast column as it's not a valid feature for training
        # (would create data leakage since it's directly related to our target)
        df_region = df_region.drop('forecast', axis=1)

        logger.info(f'Complete dataset for {region} has {len(df_region)} rows')

        # Step 2: Split data into training and testing sets (80/20 split)
        train_df, test_df = train_test_split(df_region, test_size=0.2)

        # Step 3: Separate features (X) from target variable (y)
        X_train = train_df.drop(columns=['region', 'target'])
        y_train = train_df['target'].astype(int)
        X_test = test_df.drop(columns=['region', 'target'])
        y_test = test_df['target'].astype(int)

        training_min_timestamp = pd.to_datetime(X_train['timestamp_ms'], unit='ms').min()
        training_max_timestamp = pd.to_datetime(X_train['timestamp_ms'], unit='ms').max()

        # Log dataset dimensions to CometML
        experiment.log_parameters(
            {
                'training_min_timestamp': training_min_timestamp,
                'training_max_timestamp': training_max_timestamp,
                f'{region}_X_train': X_train.shape,
                f'{region}_y_train': y_train.shape,
                f'{region}_X_test': X_test.shape,
                f'{region}_y_test': y_test.shape,
            }
        )

        # Step 4: Evaluate baseline dummy model for comparison
        logger.info('Evaluating the dummy model as baseline...')
        feature = 'demand'  # Use current demand as baseline prediction for future demand
        dummy_model = DummyModel(from_feature=feature)
        
        # Test set evaluation
        y_test_pred = dummy_model.predict(X_test)
        mae_dummy_model = mean_absolute_error(y_test, y_test_pred)
        experiment.log_metric(f'{region}_mae_dummy_model', mae_dummy_model)
        
        # Training set evaluation (to check for potential overfitting)
        y_train_pred = dummy_model.predict(X_train)
        mae_dummy_model_train = mean_absolute_error(y_train, y_train_pred)

        # Step 5: Train XGBoost model with optional hyperparameter tuning
        logger.info(f'Training XGBoost model for {region}...')
        model = XGBoostModel()
        model.fit(
            X_train,
            y_train,
            n_search_trials=hyperparameter_tuning_search_trials,
            n_splits=hyperparameter_tuning_n_splits,
        )

        # Step 6: Evaluate XGBoost model performance
        # Test set evaluation
        y_test_pred = model.predict(X_test)
        mae_xgboost_model = mean_absolute_error(y_test, y_test_pred)
        experiment.log_metric(f'{region}_mae', mae_xgboost_model)
        
        # Training set evaluation (to check for potential overfitting)
        y_train_pred = model.predict(X_train)
        mae_xgboost_model_train = mean_absolute_error(y_train, y_train_pred)

        # Save debug predictions if enabled
        if debug_mode:
            # Create dataframe with predictions for visualization
            df_predict = pd.DataFrame({
                'timestamp_ms': X_test['timestamp_ms'] + 3600000,  # Add 1 hour (3600000 ms) to represent prediction time
                'y_test_pred': y_test_pred,
            })

            # Merge with actual values for comparison
            df_debug = df_forecast.merge(df_predict, on='timestamp_ms', how='inner')

            # Add one more prediction point at the end (for future forecasting)
            df_debug.loc[len(df_debug)] = [
                df_debug['timestamp_ms'].iloc[-1] + 3600000,
                None,	# demand (unknown for future)
                None,	# forecast (unknown for future)
                y_test_pred[-1]	# prediction for future point
            ]

            # Save predictions to CSV for analysis
            output_path = f"files/{region}_debug_predictions_{'no_tuning' if hyperparameter_tuning_search_trials == 0 else 'tuned'}.csv"
            df_debug.to_csv(output_path, index=False)
            logger.info(f'Debug predictions saved to {output_path}')
        
        # Log performance metrics
        logger.info(f'MAE of dummy model based on feature {feature}: {mae_dummy_model}')
        logger.info(f'MAE of XGBoost model: {mae_xgboost_model}\n\n')

        logger.info(f'MAE of dummy model based on {feature} on training set: {mae_dummy_model_train}')
        logger.info(f'MAE of XGBoost model on training set: {mae_xgboost_model_train}\n\n')

        # Step 7: Save and register the model if it outperforms the baseline
        # Create model name with region and tuning information
        model_name = f"{region}_xgboost_model_{'no_tuning' if hyperparameter_tuning_search_trials == 0 else 'tuned'}"
        model_filepath = f'files/{model_name}.joblib'
        
        # Save model to disk
        joblib.dump(model.get_model_object(), model_filepath)

        # Log model to CometML
        experiment.log_model(
            name=f'{model_name}',
            file_or_folder=model_filepath,
        )
        
        # Register models that outperform the baseline dummy model
        if mae_xgboost_model < mae_dummy_model:
            # Register other models with status 'Production'
            logger.info(f'Registering model {model_name} with status {model_status}')
            experiment.register_model(
                model_name=model_name,
                status=model_status,
            )
        else:
            logger.info(f'Model {model_name} did not outperform baseline, not registering')

    logger.info('Training job completed successfully!')


def train_test_split(
    data: pd.DataFrame,
    test_size: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split time series data into training and testing sets based on chronological order.
    
    This function performs a temporal split rather than a random split, which is
    appropriate for time series forecasting problems. The first (1-test_size)% of
    data points are used for training, and the remaining test_size% are used for testing.
    
    Args:
        data (pd.DataFrame): DataFrame containing time series data, assumed to be sorted by time.
        test_size (float, default=0.2): Proportion of data to use for testing (0.0 to 1.0).
        
    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: A tuple containing:
            - train_df: DataFrame with training data
            - test_df: DataFrame with testing data
    """
    train_size = int(len(data) * (1 - test_size))

    train_df = data.iloc[:train_size]
    test_df = data.iloc[train_size:]

    return train_df, test_df


if __name__ == '__main__':
    # Entry point: Run the main function with configuration from environment variables
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
        debug_mode=config.debug_mode,
    )
