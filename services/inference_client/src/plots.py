from typing import Dict

import altair as alt
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

from utils import (
	format_feature_df,
	extract_time_features,
	)


def plot_region_predictions(
	selected_region: str, prediction_dfs: Dict[str, pd.DataFrame]
) -> None:
	"""
	Plot predictions, demand, and forecast for a selected region using Altair.

	Args:
		selected_region (str): The region to plot.
		prediction_dfs (dict): Dictionary of region DataFrames.

	Returns:
		None. The function renders an Altair chart in the Streamlit app.
	"""
	pred_df, _ = format_feature_df(selected_region, prediction_dfs, prediction_plot=True)
	# Strip timezone info (make it naive, but now it's local time)
	pred_df['timestamp'] = pred_df['timestamp'].dt.tz_localize(None)
	# Filter to last 120 hours for plotting
	pred_df = pred_df.iloc[-120:].copy().reset_index(drop=True)

	# Map internal column names to display names for legend
	legend_labels = {
		'prediction': 'Predicted Demand',
		'demand': 'Current Demand',
		'demand_forecast': "EIA's Forecast",
	}

	# Only include columns that exist in the DataFrame
	plot_columns = [
		col
		for col in ['prediction', 'demand', 'demand_forecast']
		if col in pred_df.columns
	]

	# Melt DataFrame for Altair plotting
	plot_df = pred_df.melt(
		id_vars=['timestamp'],
		value_vars=plot_columns,
		var_name='Series',
		value_name='Value',
	)
	plot_df['Series'] = plot_df['Series'].map(legend_labels)

	# Calculate x-axis and y-axis limits efficiently
	y_min = min(pred_df[col].min() for col in plot_columns) - 1000
	y_max = max(pred_df[col].max() for col in plot_columns) + 1000

	# Get the latest predicted value for highlighting
	latest_pred = (
		plot_df[plot_df['Series'] == 'Predicted Demand']
		.sort_values('timestamp')
		.iloc[-1]
	)

	# Altair color and dash settings
	color_scale = alt.Scale(
		domain=list(legend_labels.values()), range=['red', 'blue', 'black']
	)
	dash_scale = alt.Scale(domain=list(legend_labels.values()), range=[[], [], [5, 5]])

	base = alt.Chart(plot_df)

	# Plot lines for Predicted Demand and Current Demand
	lines = (
		base.transform_filter(
			alt.FieldOneOfPredicate(
				field='Series', oneOf=['Predicted Demand', 'Current Demand']
			)
		)
		.mark_line()
		.encode(
			x=alt.X('timestamp:T', title='Date', axis=alt.Axis(format='%d/%m %H:%M')),
			y=alt.Y(
				'Value:Q',
				title='Consumption in kWh',
				scale=alt.Scale(domain=[y_min, y_max]),
			),
			color=alt.Color(
				'Series:N', scale=color_scale, legend=alt.Legend(title='Series')
			),
			strokeDash=alt.StrokeDash('Series:N', scale=dash_scale, legend=None),
			size=alt.Size(
				'Series:N',
				scale=alt.Scale(
					domain=['Predicted Demand', 'Current Demand'], range=[3, 1.5]
				),
				legend=None,
			),
		)
	)

	# Plot points for Predicted Demand and Current Demand
	points = (
		base.transform_filter(
			alt.FieldOneOfPredicate(
				field='Series', oneOf=['Predicted Demand', 'Current Demand']
			)
		)
		.mark_point(size=10)
		.encode(
			x=alt.X('timestamp:T', title='Date', axis=alt.Axis(format='%d/%m %H:%M')),
			y=alt.Y(
				'Value:Q',
				title='Consumption in kWh',
				scale=alt.Scale(domain=[y_min, y_max]),
			),
			color=alt.Color('Series:N', scale=color_scale, legend=None),
			tooltip=[
				alt.Tooltip('timestamp:T', title='Date', format='%d/%m %H:%M'),
				alt.Tooltip('Value:Q', title='Consumption in kWh', format=','),
				alt.Tooltip('Series:N', title='Series'),
			],
		)
	)

	# Plot line for EIA's Forecast (no points)
	line_no_points = (
		base.transform_filter(
			alt.FieldEqualPredicate(field='Series', equal="EIA's Forecast")
		)
		.mark_line(point=False)
		.encode(
			x=alt.X('timestamp:T', title='Date', axis=alt.Axis(format='%d/%m %H:%M')),
			y=alt.Y('Value:Q', title='Consumption in kWh'),
			color=alt.Color('Series:N', scale=color_scale, legend=None),
			strokeDash=alt.StrokeDash('Series:N', scale=dash_scale, legend=None),
		)
	)

	# Highlight the latest predicted value
	highlight_df = pd.DataFrame([latest_pred])
	highlight = (
		alt.Chart(highlight_df)
		.mark_point(filled=True, size=200, color='gold', stroke='red', strokeWidth=3)
		.encode(
			x=alt.X('timestamp:T'),
			y=alt.Y('Value:Q'),
			tooltip=[
				alt.Tooltip('timestamp:T', title='Date', format='%d/%m %H:%M'),
				alt.Tooltip('Value:Q', title='Consumption in kWh', format=','),
				alt.Tooltip('Series:N', title='Series'),
			],
		)
	)

	# Annotation for the highlighted point
	annotation = (
		alt.Chart(highlight_df)
		.mark_text(
			align='left',
			baseline='middle',
			dx=10,
			dy=-10,
			fontSize=16,
			fontWeight='bold',
			color='gold',
		)
		.encode(
			x=alt.X('timestamp:T'),
			y=alt.Y('Value:Q'),
			text=alt.value("Next hour's prediction"),
		)
	)

	# Combine all chart elements
	chart = (lines + points + line_no_points + highlight + annotation).properties(
		width=900,
		height=400,
		title=f"Demand, Predicted Demand and EIA's Forecast for {selected_region.upper()} (Local Time)",
	)

	st.altair_chart(chart, use_container_width=True)

def plot_feature_importance(feature_importance_df: pd.DataFrame, region: str) -> None:
	"""
	Plot feature importance using mutual information for a given region.

	Args:
		feature_importance_df (pd.DataFrame): DataFrame with 'feature' and 'importance' columns.
		region (str): Region name (for title context).
	"""
	if feature_importance_df.empty:
		st.warning(f"No feature importance data available for {region}.")
		return

	chart = (
		alt.Chart(feature_importance_df)
		.mark_bar()
		.encode(
			x=alt.X("importance:Q", title="Mutual Information Score"),
			y=alt.Y("feature:N", sort='-x', title="Feature"),
			tooltip=["feature", "importance"]
		)
		.properties(
			title=f"Feature Importance for {region}",
			width=600,
			height=400
		)
	)

	st.altair_chart(chart, use_container_width=True)

def plot_hourly_demand_temprature(
	selected_region: str, prediction_dfs: Dict[str, pd.DataFrame]
) -> None:
	"""
	Plot hourly demand and temperature for a selected region using Altair.

	Args:
		selected_region (str): The region to plot.
		prediction_dfs (dict): Dictionary of region DataFrames.

	Returns:
		None. The function renders a static Altair chart in the Streamlit app.
	"""
	# Get feature DataFrame and add time-based features
	feature_df, _ = format_feature_df(selected_region, prediction_dfs, prediction_plot=False)
	feature_df = extract_time_features(feature_df, timestamp_col='timestamp')

	# Average temperature and demand by hour of day
	hourly_temp = feature_df.groupby('hour')['weather_temperature'].mean()
	hourly_demand = feature_df.groupby('hour')['demand'].mean()

	# Prepare DataFrame for plotting
	hourly_df = pd.DataFrame({
		'hour': hourly_demand.index,
		'Demand (kWh)': hourly_demand.values,
		'Temperature (°C)': hourly_temp.values
	})

	# --- Calculate fixed y-axis limits ---
	demand_min = hourly_df['Demand (kWh)'].min()
	demand_max = hourly_df['Demand (kWh)'].max()
	temp_min = hourly_df['Temperature (°C)'].min()
	temp_max = hourly_df['Temperature (°C)'].max()

	demand_range = [demand_min - 1000, demand_max + 1000]
	temp_range = [temp_min - 2, temp_max + 2]

	# Common x-axis with horizontal tick labels
	x_axis = alt.X(
		'hour:O',
		title='Hour of Day (Local Time)',
		axis=alt.Axis(
			values=list(range(24)),
			labelAngle=0
		)
	)

	# Demand line chart (red, left y-axis)
	demand_line = alt.Chart(hourly_df).mark_line(
		color='red',
		point=alt.OverlayMarkDef(color='red')
	).encode(
		x=x_axis,
		y=alt.Y(
			'Demand (kWh):Q',
			title='Demand (kWh)',
			scale=alt.Scale(domain=demand_range, clamp=True),  # lock scale
			axis=alt.Axis(
				titleColor='red',
				labelColor='red',
				grid=True
			)
		),
		tooltip=[
			alt.Tooltip('hour:O'),
			alt.Tooltip('Demand (kWh):Q')
		]
	)

	# Temperature line chart (blue, right y-axis)
	temp_line = alt.Chart(hourly_df).mark_line(
		color='blue',
		point=alt.OverlayMarkDef(color='blue')
	).encode(
		x=x_axis,
		y=alt.Y(
			'Temperature (°C):Q',
			title='Temperature (°C)',
			scale=alt.Scale(domain=temp_range, clamp=True),  # lock scale
			axis=alt.Axis(
				titleColor='blue',
				labelColor='blue',
				orient='right',
				grid=False
			)
		),
		tooltip=[
			alt.Tooltip('hour:O'),
			alt.Tooltip('Temperature (°C):Q')
		]
	)

	# Combine both charts with locked axes
	chart = alt.layer(demand_line, temp_line).resolve_scale(
		y='independent'
	).properties(
		title=f'Average Hourly Demand vs Temperature ({selected_region} Region)',
		width=700,
		height=400
	).configure_view(
		stroke=None
	)

	# Render in Streamlit
	st.altair_chart(chart, use_container_width=True)

def plot_weekday_weekend_comparison(
	selected_region: str, prediction_dfs: Dict[str, pd.DataFrame]
) -> None:
	"""
	Plot average hourly demand, comparing weekdays vs weekends.

	Args:
		selected_region (str): The region to plot.
		prediction_dfs (dict): Dictionary of region DataFrames.

	Returns:
		None. Renders a chart in the Streamlit app.
	"""
	# Format and extract features
	feature_df, _ = format_feature_df(selected_region, prediction_dfs, prediction_plot=False)
	feature_df = extract_time_features(feature_df, timestamp_col='timestamp')

	# Group by hour and is_weekend flag
	grouped = (
		feature_df.groupby(['hour', 'is_weekend'])['demand']
		.mean()
		.reset_index()
		.rename(columns={'demand': 'Average Demand (kWh)'})
	)

	# Replace 0/1 with labels
	grouped['Day Type'] = grouped['is_weekend'].map({0: 'Weekday', 1: 'Weekend'})

	# Determine y-axis range
	y_min = grouped['Average Demand (kWh)'].min()
	y_max = grouped['Average Demand (kWh)'].max()
	demand_range = [y_min - 1000, y_max + 1000]

	# Plot styling
	color_scale = alt.Scale(domain=['Weekday', 'Weekend'], range=['red', 'blue'])

	# Create Altair plot
	chart = (
		alt.Chart(grouped)
		.mark_line(point=alt.OverlayMarkDef(filled=True))
		.encode(
			x=alt.X(
				'hour:O',
				title='Hour of Day (Local Time)',
				axis=alt.Axis(values=list(range(24)), labelAngle=0)
			),
			y=alt.Y(
				'Average Demand (kWh):Q',
				title='Average Demand (kWh)',
				scale=alt.Scale(domain=demand_range, clamp=True),
				axis=alt.Axis(titleColor='red', labelColor='red')
			),
			color=alt.Color('Day Type:N', scale=color_scale, legend=alt.Legend(title='Day Type')),
			tooltip=['hour', 'Day Type', alt.Tooltip('Average Demand (kWh):Q', format=',')]
		)
		.properties(
			title=f'Weekday vs Weekend Hourly Demand Pattern – {selected_region.upper()}',
			width=700,
			height=400
		)
		.configure_view(stroke=None)
	)

	st.altair_chart(chart, use_container_width=True)

def plot_eia_regions_map() -> None:
	"""
	Plot EIA regions on a USA map using pydeck.

	Args:
		None

	Returns:
		None. The function renders a Pydeck map in the Streamlit app.
	"""
	states_geojson_url = (
		'https://eric.clst.org/assets/wiki/uploads/Stuff/gz_2010_us_040_00_500k.json'
	)
	eia_regions = {
		'CAL': ['California'],
		'CAR': ['North Carolina', 'South Carolina'],
		'CENT': ['Arkansas', 'Louisiana', 'Missouri', 'Iowa'],
		'FLA': ['Florida'],
		'MIDW': [
			'Illinois',
			'Indiana',
			'Kansas',
			'Michigan',
			'Minnesota',
			'Nebraska',
			'North Dakota',
			'Ohio',
			'South Dakota',
			'Wisconsin',
		],
		'NW': ['Idaho', 'Montana', 'Oregon', 'Washington', 'Wyoming'],
		'NY': ['New York'],
		'SW': ['Nevada', 'Arizona', 'New Mexico', 'Colorado', 'Utah'],
	}
	state_to_region = {
		state: region for region, states in eia_regions.items() for state in states
	}

	try:
		resp = requests.get(states_geojson_url)
		resp.raise_for_status()
		us_states_geojson = resp.json()
		region_features = []
		for feature in us_states_geojson['features']:
			state_name = feature['properties']['NAME']
			region = state_to_region.get(state_name)
			if region:
				# Copy and flatten properties for tooltip access
				new_feature = {
					'type': feature['type'],
					'geometry': feature['geometry'],
					'properties': feature['properties'].copy(),
					'NAME': state_name,
					'region': region,
				}
				new_feature['properties']['region'] = region
				region_features.append(new_feature)
		if not region_features:
			st.error('Could not find any EIA region states in the US states GeoJSON.')
			region_geojson = None
		else:
			region_geojson = {'type': 'FeatureCollection', 'features': region_features}
	except Exception as e:
		st.error(f'Failed to load EIA regions GeoJSON: {e}')
		region_geojson = None

	if region_geojson:
		# Use a JS accessor for region color assignment
		get_fill_color_expr = (
			"properties.region === 'CAL' ? [200,30,0,160] : "
			"properties.region === 'CAR' ? [0,60,200,160] : "
			"properties.region === 'CENT' ? [255,165,0,160] : "
			"properties.region === 'FLA' ? [0,200,100,160] : "
			"properties.region === 'MIDW' ? [128,0,128,160] : "
			"properties.region === 'NW' ? [0,200,200,160] : "
			"properties.region === 'NY' ? [255,0,255,160] : "
			"properties.region === 'SW' ? [255,215,0,160] : "
			'[150,150,150,80]'
		)
		region_layer = pdk.Layer(
			'GeoJsonLayer',
			data=region_geojson,
			get_fill_color=get_fill_color_expr,
			get_line_color='[80, 80, 80, 255]',
			pickable=True,
			auto_highlight=True,
		)

		view_state = pdk.ViewState(
			longitude=-98.5795, latitude=39.8283, zoom=2.8, pitch=0
		)

		st.pydeck_chart(
			pdk.Deck(
				layers=[region_layer],
				initial_view_state=view_state,
				tooltip={
					'html': '<b>STATE:</b> {NAME}<br/><b>REGION:</b> {region}',
					'style': {'backgroundColor': '#090909', 'color': 'white'},
				},
				map_style='mapbox://styles/mapbox/light-v9',
			)
		)