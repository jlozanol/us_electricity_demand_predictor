from typing import ClassVar, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VALID_REGIONS = {
	'CAL',
	'CAR',
	'CENT',
	'FLA',
	'MIDA',
	'MIDW',
	'NE',
	'NW',
	'NY',
	'SE',
	'SW',
	'TEN',
	'TEX',
}


class Config(BaseSettings):
	model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
	region_names: Optional[List[str]] = None
	model_status: Optional[str] = None
	hours_back: int

	eia_locations: ClassVar[dict] = {
		'CAL': [
			('Los Angeles', 34.05, -118.25),
			('San Francisco', 37.77, -122.42),
			('Sacramento', 38.58, -121.49),
			('San Diego', 32.72, -117.16),
			('Fresno', 36.74, -119.78),
		],
		'CAR': [
			('Charlotte', 35.23, -80.84),
			('Columbia', 34.00, -81.03),
			('Raleigh', 35.78, -78.64),
			('Charleston', 32.78, -79.93),
			('Greensboro', 36.07, -79.79),
		],
		'CENT': [
			('Little Rock', 34.74, -92.33),
			('Baton Rouge', 30.45, -91.15),
			('Des Moines', 41.60, -93.61),
			('St. Louis', 38.63, -90.20),
			('Omaha', 41.26, -95.94),
		],
		'FLA': [
			('Miami', 25.76, -80.19),
			('Orlando', 28.54, -81.38),
			('Tallahassee', 30.44, -84.28),
			('Tampa', 27.95, -82.46),
			('Jacksonville', 30.33, -81.65),
		],
		'MIDW': [
			('Chicago', 41.88, -87.63),
			('Indianapolis', 39.77, -86.16),
			('Minneapolis', 44.98, -93.27),
			('Kansas City', 39.10, -94.58),
			('Columbus', 39.96, -83.00),
			('Milwaukee', 43.04, -87.91),
			('Detroit', 42.33, -83.05),
		],
		'NW': [
			('Seattle', 47.61, -122.33),
			('Portland', 45.52, -122.68),
			('Boise', 43.62, -116.20),
			('Spokane', 47.66, -117.43),
			('Missoula', 46.87, -113.99),
		],
		'NY': [
			('New York City', 40.71, -74.01),
			('Albany', 42.65, -73.75),
			('Buffalo', 42.89, -78.87),
			('Rochester', 43.16, -77.61),
			('Syracuse', 43.04, -76.14),
		],
		'SW': [
			('Las Vegas', 36.17, -115.14),
			('Phoenix', 33.45, -112.07),
			('Denver', 39.74, -104.99),
			('Salt Lake City', 40.76, -111.89),
			('Albuquerque', 35.08, -106.65),
		],
	}

	@field_validator('region_names')
	@classmethod
	def validate_region_names(cls, v: List[str]) -> List[str]:
		invalid_regions = set(v) - VALID_REGIONS
		if invalid_regions:
			raise ValueError(
				f'Invalid region(s): {invalid_regions}. '
				f'Valid regions are: {sorted(VALID_REGIONS)}'
			)
		return v


class ServicesCredentials(BaseSettings):
	model_config = SettingsConfigDict(
		env_file='credentials.env', env_file_encoding='utf-8'
	)
	comet_api_key: str
	comet_project_name: str
	comet_workspace: str
	eia_api_key: str


config = Config()
services_credentials = ServicesCredentials()
