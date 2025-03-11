from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
	model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
	kafka_broker_address: str
	kafka_topic: Optional[str] = None
	region_name: Optional[str] = None
	last_n_days: Optional[int] = None
	live_or_historical: Literal['live', 'historical']
	eia_api_key: str


config = Config()
