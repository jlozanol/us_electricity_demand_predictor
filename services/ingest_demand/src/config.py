from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
	model_config = SettingsConfigDict(env_file='dev.env', env_file_encoding='utf-8')
	kafka_broker_address: str
	kafka_topic_name: str
	region_name: Optional[str] = None
	last_n_days: Optional[int] = None
	eia_api_key: str


config = Config()
