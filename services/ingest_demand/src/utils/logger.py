import sys
from datetime import datetime

from loguru import logger


def setup_logger() -> str:
	"""
	Configure loguru logger with both console and file handlers.
	Console output includes colors, while file output is plain text.
	Logs are rotated at 100MB and kept for 30 days.

	Returns:
	    str: Path to the created log file
	"""
	# Generate filename with timestamp
	log_filename = f'logs/demand_ingest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

	# Configure logger to write to both console and file
	logger.remove()  # Remove default handler
	logger.add(
		sys.stderr,
		format='<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
	)
	logger.add(
		log_filename,
		format='{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}',
		rotation='100 MB',  # Create new file when current one reaches 100MB
		retention='30 days',  # Keep logs for 30 days
	)

	logger.info(f'Starting new logging session. Logs will be saved to: {log_filename}')
	return log_filename
