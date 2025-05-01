from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
	model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
	kafka_broker_address: str
	kafka_topic: str = None
	last_n_days: int = None
	live_or_historical: Literal['live', 'historical']


config = Config()
