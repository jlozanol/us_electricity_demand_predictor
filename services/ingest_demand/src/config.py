from typing import Literal, Optional, List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


VALID_REGIONS = {"CAL", "CAR", "CENT", "FLA", "MIDA", "MIDW", "NE", "NW", "NY", "SE", "SW", "TEX"}


class Config(BaseSettings):
	model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
	kafka_broker_address: str
	kafka_topic: Optional[str] = None
	region_names: List[str]
	last_n_days: Optional[int] = None
	live_or_historical: Literal['live', 'historical']
	eia_api_key: str

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


config = Config()
