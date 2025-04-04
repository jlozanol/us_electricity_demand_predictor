from typing import List, Literal

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
	kafka_broker_address: str
	kafka_topic: str = None
	region_names: List[str] = None
	last_n_days: int = None
	live_or_historical: Literal['live', 'historical']

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


class APICredentials(BaseSettings):
	model_config = SettingsConfigDict(
		env_file='credentials.env', env_file_encoding='utf-8'
	)
	eia_api_key: str


config = Config()
api_credentials = APICredentials()
