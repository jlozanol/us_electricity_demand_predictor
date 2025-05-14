from typing import ClassVar, List, Optional, Literal

from pydantic import field_validator, Field
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
	feature_view_name: str
	feature_view_version: int
	demand_feat_group_name: Optional[str] = None
	demand_feat_group_version: Optional[str] = None
	weather_feat_group_name: Optional[str] = None
	weather_feat_group_version: Optional[str] = None
	hyperparameter_tuning: bool = None
	region_names: List[str] = None
	days_back: Optional[int] = None
	hyperparameter_tuning_search_trials: Optional[int] = Field(
		default=0,
		description='The number of trials to perform for hyperparameter tuning',
	)
	hyperparameter_tuning_n_splits: Optional[int] = Field(
		default=4,
		description='The number of splits to perform for hyperparameter tuning',
	)

	# model registry
	model_status: Literal['Development', 'Staging', 'Production'] = Field(
		default='Development',
		description='The status of the model in the model registry',
	)


	region_timezones: ClassVar[dict] = {
		'CAL': 'America/Los_Angeles',  # California
		'CAR': 'America/New_York',  # Carolinas
		'CENT': 'America/Chicago',  # Central
		'FLA': 'America/New_York',  # Florida
		'MIDW': 'America/Chicago',  # Midwest
		'NW': 'America/Los_Angeles',  # Northwest
		'NY': 'America/New_York',  # New York
		'SW': 'America/Phoenix',  # Southwest
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
	hopsworks_api_key: str
	hopsworks_project_name: str
	comet_api_key: str
	comet_project_name: str


config = Config()
services_credentials = ServicesCredentials()
