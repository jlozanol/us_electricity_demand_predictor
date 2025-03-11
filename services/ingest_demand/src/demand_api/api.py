import requests
from config import config


def connect_api(
	start_day: str,
	end_day: str,
	region_name: str,
	demand_type: str,
) -> list:
	"""
	Fetch raw electricity demand data from the EIA API for the specified date.

	Parameters:
		start_day (str): Start date in the format 'YYYY-MM-DDT00'.
		end_day (str): End date in the format 'YYYY-MM-DDT00'.
		region_name (str): The name of the region to fetch data for.
		demand_type (str): The type of demand data to fetch ('D' for actual demand, 'DF' for day-ahead forecast).

	Returns:
		list: A list of dictionaries containing the raw electricity demand data for the specified hour.
	"""
	# API URL and parameters
	url = 'https://api.eia.gov/v2/electricity/rto/region-data/data/'
	params = {
		'frequency': 'hourly',
		'data[0]': 'value',
		'facets[respondent][0]': region_name,
		'facets[type][0]': demand_type,
		'sort[0][column]': 'period',
		'sort[0][direction]': 'desc',
		'offset': 0,
		'length': 5000,
		'start': start_day,
		'end': end_day,
		'api_key': config.eia_api_key,
	}
	# Make GET request
	response = requests.get(url, params=params)
	response.raise_for_status()  # Raise HTTPError for bad responses

	# Parse JSON response
	data = response.json()
	data = data['response']['data']

	return data
