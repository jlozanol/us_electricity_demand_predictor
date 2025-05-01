from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
	model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
	kafka_broker_address: str
	kafka_input_topic: Optional[str] = None
	kafka_output_topic: Optional[str] = None
	kafka_consumer_group: Optional[str] = None
	live_or_historical: Literal['live', 'historical']


config = Config()
