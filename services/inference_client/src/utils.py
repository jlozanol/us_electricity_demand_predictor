from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import mutual_info_regression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import pandas as pd
import streamlit as st
from typing import Tuple, Optional

def format_feature_df(
	selected_region: str,
	prediction_dfs: pd.DataFrame,
	prediction_plot: bool
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
	"""
	Format the feature DataFrame for further feature calculations or plotting.

	Args:
		selected_region (str): The region name selected.
		prediction_dfs (pd.DataFrame): DataFrame containing prediction and features data.
		prediction_plot (bool): Flag to indicate if the prediction plot is needed.

	Returns:
		Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
			- If prediction_plot is True: (pred_df, None)
			- Else: (features_df, target_df)
	"""
	region_timezones = {
		'CAL': 'America/Los_Angeles',
		'CAR': 'America/New_York',
		'CENT': 'America/Chicago',
		'FLA': 'America/New_York',
		'MIDW': 'America/Chicago',
		'NW': 'America/Los_Angeles',
		'NY': 'America/New_York',
		'SW': 'America/Phoenix'
	}

	region_key = f'{selected_region.lower()}_prediction_df'
	if region_key not in prediction_dfs:
		st.error(f'No prediction data found for region: {selected_region}')
		st.write('Available regions:', list(prediction_dfs.keys()))
		return None, None

	pred_df = prediction_dfs[region_key]

	# Convert timestamps in UNIX format to local time
	local_tz = region_timezones[selected_region]
	pred_df['timestamp'] = pd.to_datetime(
		pred_df['timestamp_ms'],    # UNIX timestamp in milliseconds
		unit='ms',                  # unit = milliseconds
		utc=True                    # interpret as UTC initially
	).dt.tz_convert(local_tz)       # convert to the region's timezone

	if prediction_plot:
		return pred_df, None
	else:
		# Drop columns to form feature matrix
		target_df = pred_df['prediction'].copy()
		features_df = pred_df.drop(columns=['prediction'])
		return features_df, target_df
	

def calculate_feature_importance(selected_region: str, prediction_dfs: dict[str, pd.DataFrame]) -> pd.DataFrame | None:
	"""
	Calculate feature importance using mutual information regression.

	Args:
		selected_region (str): The region name selected.
		prediction_dfs (dict): Dictionary of DataFrames with predictions and features.

	Returns:
		pd.DataFrame or None: DataFrame with 'feature' and 'importance' columns sorted descending.
	"""

	features_df, target_df = format_feature_df(selected_region, prediction_dfs, prediction_plot=False)
	# Drop columns that are not needed for feature importance
	features_df = features_df.drop(columns=['timestamp_ms','timestamp','demand_forecast', 'demand'])

	X = features_df.iloc[:-1]
	y = target_df.iloc[:-1]

	# Get feature names
	feature_cols = X.columns.tolist()

	# Scale features
	scaler = StandardScaler()
	X_scaled = scaler.fit_transform(X)

	# Compute mutual information scores
	mi_scores = mutual_info_regression(X_scaled, y)

	# Return as DataFrame
	importance_df = pd.DataFrame({
		"feature": feature_cols,
		"importance": mi_scores
	}).sort_values("importance", ascending=False)

	return importance_df

def extract_time_features(features_df: pd.DataFrame, timestamp_col: str = 'timestamp') -> pd.DataFrame:
    """
    Extracts time-based features from a datetime column in the DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame with a datetime column.
        timestamp_col (str): Name of the datetime column to extract features from.

    Returns:
        pd.DataFrame: DataFrame with added time-based features.
    """

    features_df['hour'] = features_df[timestamp_col].dt.hour
    features_df['day_of_week'] = features_df[timestamp_col].dt.dayofweek
    features_df['month'] = features_df[timestamp_col].dt.month
    features_df['is_weekend'] = features_df['day_of_week'].isin([5, 6]).astype(int)
    features_df['part_of_day'] = pd.cut(
        features_df['hour'], 
        bins=[0, 6, 12, 18, 24], 
        labels=['Night', 'Morning', 'Afternoon', 'Evening'],
        right=False
    )

    return features_df

def calculate_model_accuracy(pred_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute accuracy metrics for model prediction and EIA forecast.

    Returns a DataFrame with MAE, RMSE, MAPE, and R2 for both.
    """
    df = pred_df.dropna(subset=['demand', 'prediction', 'demand_forecast'])

    actual = df['demand']
    model_pred = df['prediction']
    forecast = df['demand_forecast']

    def mape(y_true, y_pred):
        return (abs((y_true - y_pred) / y_true).replace([float('inf')], 0).mean()) * 100

    metrics = {
        'MAE': [
            mean_absolute_error(actual, model_pred),
            mean_absolute_error(actual, forecast),
        ],
        'RMSE': [
            mean_squared_error(actual, model_pred),
            mean_squared_error(actual, forecast),
        ],
        'MAPE': [
            mape(actual, model_pred),
            mape(actual, forecast),
        ],
        'R²': [
            r2_score(actual, model_pred),
            r2_score(actual, forecast),
        ]
    }

    return pd.DataFrame(metrics, index=['Model', 'EIA Forecast']).T.reset_index().rename(columns={'index': 'Metric'})
