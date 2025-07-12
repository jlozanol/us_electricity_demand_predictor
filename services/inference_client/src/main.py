from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st
from config import config
from feature_creator import FeatureCreator
from loguru import logger
from model_fetcher import PricePredictor
from plots import (
    plot_eia_regions_map,
	plot_region_predictions,
	plot_feature_importance,
	plot_hourly_demand_temprature,
    plot_weekday_weekend_comparison,
)
from utils import calculate_feature_importance, format_feature_df, calculate_model_accuracy

# Define paths for storing models
MODELS_DIR = Path('model_artifacts')
PREDICTORS_FILE = MODELS_DIR / 'predictors.pkl'
FEATURE_CREATORS_FILE = MODELS_DIR / 'feature_creators.pkl'


def cleanup_saved_models() -> None:
	"""
	Delete any existing saved models.

	Returns:
		None. Removes model files if they exist.
	"""
	try:
		if PREDICTORS_FILE.exists():
			PREDICTORS_FILE.unlink()
		if FEATURE_CREATORS_FILE.exists():
			FEATURE_CREATORS_FILE.unlink()
		if PREDICTORS_FILE.exists() or FEATURE_CREATORS_FILE.exists():
			logger.info('Cleaned up existing saved models')
	except Exception as e:
		st.warning(f'Could not clean up saved models: {e}')


def init_predictor(region: str) -> Tuple[str, 'PricePredictor']:
	"""
	Initialise predictor for a region.

	Args:
		region (str): Region name.

	Returns:
		Tuple[str, 'PricePredictor']:
			(predictor variable name, PricePredictor instance)
	"""
	return f'{region.lower()}_predictor', PricePredictor(region)


def init_feature_creator(region: str) -> Tuple[str, 'FeatureCreator']:
	"""
	Initialise feature creator for a region.

	Args:
		region (str): Region name.

	Returns:
		Tuple[str, 'FeatureCreator']:
			(predictor variable name, FeatureCreator instance)
	"""
	return f'{region.lower()}_feature_creator', FeatureCreator(
		region, datetime.now(timezone.utc)
	)


@st.cache_resource
def load_or_initialise_models() -> Tuple[
	Dict[str, 'PricePredictor'], Dict[str, 'FeatureCreator']
]:
	"""
	Initialise fresh models for all regions (no loading from disk).

	Returns:
		tuple: (predictors dict, feature_creators dict)
	"""
	# Create models directory if it doesn't exist
	MODELS_DIR.mkdir(exist_ok=True)

	st.info('Initialising prediction models... This may take a few minutes.')

	predictors = {}
	feature_creators = {}
	region_names = config.region_names

	# Progress bar for initialisation
	progress_bar = st.progress(0)
	status_text = st.empty()

	# Initialise predictors and feature creators in parallel
	with ThreadPoolExecutor(max_workers=min(8, len(region_names))) as init_executor:
		status_text.text('Initialising predictors and feature creators...')
		predictor_futures = {
			region: init_executor.submit(init_predictor, region)
			for region in region_names
		}
		feature_creator_futures = {
			region: init_executor.submit(init_feature_creator, region)
			for region in region_names
		}

		total_tasks = len(region_names) * 2
		completed_tasks = 0

		# Collect predictors
		for region, future in predictor_futures.items():
			var_name, predictor = future.result()
			predictors[var_name] = predictor
			completed_tasks += 1
			progress_bar.progress(completed_tasks / total_tasks)

		# Collect feature creators
		for region, future in feature_creator_futures.items():
			var_name, feature_creator = future.result()
			feature_creators[var_name] = feature_creator
			completed_tasks += 1
			progress_bar.progress(completed_tasks / total_tasks)

	st.success('Prediction models initialised successfully!')

	# Clear progress indicators
	progress_bar.empty()
	status_text.empty()

	return predictors, feature_creators


def process_single_region(
	region_name: str,
	predictors: Dict[str, 'PricePredictor'],
	feature_creators: Dict[str, 'FeatureCreator'],
) -> pd.DataFrame | None:
	"""
	Process a single region and return complete DataFrame.

	Args:
		region_name (str): Name of the region.
		predictors (dict): Dict of predictors.
		feature_creators (dict): Dict of feature creators.

	Returns:
		pd.DataFrame or None: DataFrame with predictions and features, or None on error.
	"""
	try:
		st.write(f'🔄 Processing region: {region_name}')

		feature_creator = feature_creators[f'{region_name.lower()}_feature_creator']
		predictor = predictors[f'{region_name.lower()}_predictor']

		# Create features
		st.write(f'📊 Creating features for {region_name}...')
		region_features, region_forecast = feature_creator.create_features()

		# Validate features
		if region_features is None or region_features.empty:
			st.error(f'Empty features for {region_name}')
			return None

		if region_forecast is None or region_forecast.empty:
			st.error(f'Empty forecast for {region_name}')
			return None

		st.write(f'✅ Features created for {region_name}:')

		# Make predictions
		st.write(f'🤖 Making predictions for {region_name}...')
		prediction_result = predictor.predict(region_features)

		# Handle PredictionOutput object - check if it's None first
		if prediction_result is None:
			st.error(f'Empty predictions for {region_name}')
			return None

		# Extract predictions from PredictionOutput object
		try:
			if hasattr(prediction_result, 'predictions'):
				predictions = prediction_result.predictions
			elif hasattr(prediction_result, 'model_dump'):
				pred_dict = prediction_result.model_dump()
				predictions = pred_dict.get('predictions')
				if predictions is None:
					st.error(
						f"No 'predictions' key in PredictionOutput for {region_name}"
					)
					st.write(f'Available keys: {list(pred_dict.keys())}')
					return None
			elif hasattr(prediction_result, 'dict'):
				pred_dict = prediction_result.dict()
				predictions = pred_dict.get('predictions')
				if predictions is None:
					st.error(
						f"No 'predictions' key in PredictionOutput for {region_name}"
					)
					st.write(f'Available keys: {list(pred_dict.keys())}')
					return None
			elif (
				isinstance(prediction_result, dict)
				and 'predictions' in prediction_result
			):
				predictions = prediction_result['predictions']
			else:
				st.warning(
					f'Using fallback method to extract predictions for {region_name}'
				)
				predictions = prediction_result
		except Exception as e:
			st.error(
				f'Error extracting predictions from PredictionOutput for {region_name}: {e}'
			)
			return None

		# Validate predictions
		if predictions is None:
			st.error(f'Predictions is None for {region_name}')
			return None

		if isinstance(predictions, (list, np.ndarray)):
			predictions = pd.Series(predictions)
		elif not isinstance(predictions, pd.Series):
			st.error(f'Invalid predictions type for {region_name}: {type(predictions)}')
			return None

		# Start with timestamp and predictions
		pred_df = pd.DataFrame(
			{
				'timestamp_ms': (region_features['timestamp_ms'] + 3600000).astype(int),
				'prediction': predictions.values,
			}
		)

		# Merge with forecast data
		if 'timestamp_ms' in region_forecast.columns:
			pred_df = pred_df.merge(region_forecast, on='timestamp_ms', how='left')
		else:
			st.warning(f'   - No timestamp_ms in forecast for {region_name}')

		# Merge with demand data
		if 'timestamp_ms' in region_features.columns:
			# Merge all columns from region_features
			feature_data = region_features.copy()
			pred_df = pred_df.merge(feature_data, on='timestamp_ms', how='left')
		else:
			st.warning(
				f'   - Missing timestamp_ms in features for {region_name}'
			)

		# Identify the last row
		last_row = pred_df.tail(1)

		# Drop NaNs from all rows except the last one
		pred_df = pred_df.iloc[:-1].dropna()

		# Append the last row back
		pred_df = pd.concat([pred_df, last_row], ignore_index=True)

		st.write(f'✅ Predictions created for {region_name}:')

		return pred_df

	except Exception as e:
		st.error(f'Error processing region {region_name}: {e}')
		import traceback

		st.text(traceback.format_exc())
		return None


def create_features_and_predictions(
	predictors: Dict[str, 'PricePredictor'],
	feature_creators: Dict[str, 'FeatureCreator'],
	region_names: list,
) -> Tuple[
	Dict[str, pd.DataFrame],
	Dict[str, pd.DataFrame],
	Dict[str, pd.DataFrame],
	Dict[str, pd.DataFrame],
]:
	"""
	Create features and predictions for all regions in parallel.

	Args:
		predictors (Dict): Dict of predictors.
		feature_creators (Dict): Dict of feature creators.
		region_names (list): List of region names.

	Returns:
		Tuple[Dict[str, pd.DataFrame], Dict[str, pd.DataFrame], Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
			(features dict, forecasts dict, predictions dict, prediction_dfs dict)
	"""
	prediction_dfs = {}
	progress_bar = st.progress(0)
	total = len(region_names)
	completed = 0

	def process_and_update(region: str) -> Tuple[str, pd.DataFrame | None]:
		pred_df = process_single_region(region, predictors, feature_creators)
		return region, pred_df

	with ThreadPoolExecutor(max_workers=8) as executor:
		futures = {
			executor.submit(process_and_update, region): region
			for region in region_names
		}
		for future in as_completed(futures):
			region, pred_df = future.result()
			st.markdown(f'### Processed Region: {region.upper()}')
			if pred_df is not None:
				prediction_dfs[f'{region.lower()}_prediction_df'] = pred_df
				st.success(f'✅ Successfully processed {region}')
			else:
				st.error(f'❌ Failed to process {region}')
			completed += 1
			progress_bar.progress(completed / total)
			st.markdown('---')

	progress_bar.empty()
	return (
		{},
		{},
		{},
		prediction_dfs,
	)  # Return empty dicts for features, forecasts, predictions


def main() -> None:
	"""
	Main Streamlit app entry point.

	Returns:
		None. Runs the Streamlit dashboard.
	"""
	st.set_page_config(
		page_title='Electricity Demand Prediction App', page_icon='📈', layout='wide'
	)

	st.title('📈 Electricity Demand Prediction Dashboard')
	st.markdown('---')

	# Clean up any saved models at startup
	cleanup_saved_models()

	# Load or initialise models (will always initialise fresh now)
	try:
		predictors, feature_creators = load_or_initialise_models()
		region_names = config.region_names

		st.success(
			f'✅ Prediction models available for {len(region_names)} regions: {", ".join(region_names)}'
		)

		# Plot EIA regions map
		plot_eia_regions_map()
		st.markdown("""
		This interactive dashboard visualises electricity demand predictions across U.S. Energy Information Administration's (EIA) regions.

		🔍 It compares real-time demand data, EIA forecasts, and predictions from a custom-trained machine learning model.

		📡 Data sources include:
		- **Actual demand and EIA forecasts**: pulled via the EIA's API
		- **Weather data**: pulled via the openmeteo's API
		- **Predictions**: generated by region-specific ML models
		""")


		# Sidebar for controls
		st.sidebar.header('Controls')

		# Button to calculate predictions
		if st.sidebar.button('🚀 Calculate Predictions', type='primary'):
			with st.spinner('Generating predictions...'):
				features, forecasts, predictions, prediction_dfs = (
					create_features_and_predictions(
						predictors, feature_creators, region_names
					)
				)

			st.success('✅ Predictions calculated successfully!')

			# Store results in session state
			st.session_state.prediction_results = {
				'features': features,
				'forecasts': forecasts,
				'predictions': predictions,
				'prediction_dfs': prediction_dfs,
			}

		# Region selection and visualisation
		if 'prediction_results' in st.session_state:
			st.sidebar.markdown('---')
			st.sidebar.header('Visualisation')

			# Add '---' as the default option
			region_options = ['---'] + region_names
			selected_region = st.sidebar.selectbox(
				'Select Region for Visualisation:',
				options=region_options,
				format_func=lambda x: x.upper() if x != '---' else x,
				index=0,
			)

			# Only show plot if a region is selected
			if selected_region != '---':
				try:
					prediction_dfs = st.session_state.prediction_results[
						'prediction_dfs'
					]
					st.markdown('---')
					st.header('Predictions and Demand Forecasts')
					st.markdown("""
					This chart shows a side-by-side comparison of:

					- 🔴 **Model Prediction** – the machine learning model’s estimated electricity demand  
					- 🔵 **Current Demand** – the actual recorded consumption  
					- ⚫ **EIA Forecast** – the U.S. Energy Information Administration's official forecast

					🕒 The timeline represents the most recent 5 days (120 hours) in the selected region's local time.
					""")

					plot_region_predictions(selected_region, prediction_dfs)
				except Exception as e:
					st.error(f'Error displaying predictions: {e}')
					import traceback

					st.text('Full error traceback:')
					st.text(traceback.format_exc())
				
				# Create a new subsection for feature analysis
				st.markdown('---')
				st.header('Feature Analysis')
				st.markdown("""
				This section explores which features influence the model's predictions:

				- 📈 **Feature Importance** – ranks predictors using mutual information
				- 🌡️ **Hourly Demand vs Temperature** – visualises how average demand varies with temperature throughout the day
				- 📅 **Weekday vs Weekend Demand** – compares hourly patterns between weekdays and weekends
				""")

				# # Print prediction_dfs values for debugging
				# st.dataframe(prediction_dfs[f'{selected_region.lower()}_prediction_df'])

				# # Print prediction_dfs values for debugging
				# st.dataframe(format_feature_df(selected_region, prediction_dfs, prediction_plot=False)[0])

				important_features = calculate_feature_importance(
					selected_region, prediction_dfs
				)
				plot_feature_importance(important_features, selected_region)
				
				plot_hourly_demand_temprature(
					selected_region, prediction_dfs
				)
				plot_weekday_weekend_comparison(selected_region, prediction_dfs)

				# Show accuracy
				st.subheader(f'Prediction Accuracy – {selected_region.upper()}')
				st.markdown("""
				This table compares how accurately the machine learning model and the EIA forecast match actual demand.

				📐 Metrics used:
				- **MAE / RMSE** – average error magnitude (lower is better)
				- **MAPE** – error as a percentage of actual values
				- **R²** – how well predictions explain actual variance (closer to 1 is better)

				✅ **Conclusion:** Based on these metrics, the model outperforms the EIA forecast across all evaluated dimensions.
				""")

				pred_df, _ = format_feature_df(selected_region, prediction_dfs, prediction_plot=True)
				metrics_df = calculate_model_accuracy(pred_df)

				st.dataframe(metrics_df.style.format(precision=2), use_container_width=True)



		# Footer
		st.markdown('---')
		st.markdown('🔄 Prediction models are initialised on every app restart')

	except Exception as e:
		st.error(f'❌ Error initialising application: {e}')
		import traceback

		st.text('Full error traceback:')
		st.text(traceback.format_exc())


if __name__ == '__main__':
	main()