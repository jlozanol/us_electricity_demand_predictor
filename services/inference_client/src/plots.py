from typing import Dict

import altair as alt
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st


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
	region_key = f'{selected_region.lower()}_prediction_df'
	if region_key not in prediction_dfs:
		st.error(f'No prediction data found for region: {selected_region}')
		st.write('Available regions:', list(prediction_dfs.keys()))
		return

	pred_df = prediction_dfs[region_key]

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

	# Calculate y-axis limits efficiently
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
		title=f"Demand, Predicted Demand and EIA's Forecast for {selected_region.upper()}",
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
