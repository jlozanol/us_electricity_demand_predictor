import hopsworks
import pandas as pd
from quixstreams.sinks.base import BatchingSink, SinkBackpressureError, SinkBatch


class HopsworksFeatureStoreSink(BatchingSink):
	"""
	A custom sink implementation for writing streaming data to Hopsworks Feature Store.

	This sink extends the QuixStreams BatchingSink to provide seamless integration
	between Kafka streaming data and Hopsworks Feature Store. It handles:

	1. Connection to Hopsworks Feature Store
	2. Feature group creation/retrieval
	3. Batch data insertion with error handling
	4. Backpressure management for reliability

	The sink automatically converts incoming Kafka messages to a pandas DataFrame
	before inserting them into the specified feature group.
	"""

	def __init__(
		self,
		api_key: str,
		project_name: str,
		feature_group_name: str,
		feature_group_version: int,
		feature_group_primary_keys: str,
		feature_group_event_time: str,
	):
		"""
		Initialize the Hopsworks Feature Store sink with connection parameters.

		Args:
		    api_key (str): Hopsworks API key for authentication
		    project_name (str): Name of the Hopsworks project
		    feature_group_name (str): Name of the feature group to write to
		    feature_group_version (int): Version of the feature group
		    feature_group_primary_keys (str): Comma-separated list of primary key column names
		    feature_group_event_time (str): Name of the column to use as event time
		"""
		self.feature_group_name = feature_group_name
		self.feature_group_version = feature_group_version

		# Convert comma-separated string to list if needed
		if isinstance(feature_group_primary_keys, str):
			primary_keys = [
				key.strip() for key in feature_group_primary_keys.split(',')
			]
		else:
			primary_keys = feature_group_primary_keys

		# Establish a connection to the Hopsworks Feature Store
		# This authenticates with the provided API key and project name
		project = hopsworks.login(project=project_name, api_key_value=api_key)
		self._fs = project.get_feature_store()

		# Get or create the feature group in Hopsworks
		# If the feature group doesn't exist, it will be created with the specified parameters
		# If it exists, the existing feature group will be used
		self._feature_group = self._fs.get_or_create_feature_group(
			name=feature_group_name,
			version=feature_group_version,
			primary_key=primary_keys,  # Use the processed list of primary keys
			event_time=feature_group_event_time,
			online_enabled=False,  # Only enable offline storage for now
		)

		# Initialize the base BatchingSink class
		# This sets up the internal batching mechanism for efficient writes
		super().__init__()

	def write(self, batch: SinkBatch):
		"""
		Write a batch of messages to the Hopsworks Feature Store.

		This method is called by the QuixStreams framework when a batch of messages
		is ready to be written to the sink. It:
		1. Converts the batch of messages to a pandas DataFrame
		2. Inserts the DataFrame into the Hopsworks Feature Group
		3. Handles timeout errors with appropriate backpressure

		Args:
		    batch (SinkBatch): A batch of messages from the Kafka topic

		Raises:
		    SinkBackpressureError: If a timeout occurs, signaling the framework
		        to retry the operation after a delay
		"""
		# Extract message values from the batch and convert to a pandas DataFrame
		# Each message value is expected to be a dictionary that can be converted to a DataFrame row
		data = [item.value for item in batch]
		data = pd.DataFrame(data)

		try:
			# Insert the DataFrame into the Hopsworks Feature Group
			# This will automatically handle schema validation and data type conversion
			self._feature_group.insert(data)
		except TimeoutError:
			# If a timeout occurs, signal the framework to apply backpressure
			# This tells QuixStreams to wait and retry the operation later
			# The retry_after parameter specifies the delay in seconds
			raise SinkBackpressureError(
				retry_after=30.0,  # Wait 30 seconds before retrying
				topic=batch.topic,
				partition=batch.partition,
			)
