from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
	model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
	kafka_broker_address: str
	kafka_input_topic: Optional[str] = None
	kafka_consumer_group: Optional[str] = None
	feature_group_name: Optional[str] = None
	feature_group_version: Optional[str] = None
	feature_group_primary_keys: Optional[str] = None
	feature_group_event_time: Optional[str] = None
	live_or_historical: Literal['live', 'historical']


class HopsworksCredentials(BaseSettings):
	model_config = SettingsConfigDict(
		env_file='credentials.env', env_file_encoding='utf-8'
	)
	hopsworks_api_key: str
	hopsworks_project_name: str


config = Config()
hopsworks_credentials = HopsworksCredentials()
