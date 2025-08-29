import logging
import sys
from typing import Any, Dict

import structlog


def configure_logging(app_env: str = "dev") -> None:
	shared_processors = [
		structlog.processors.add_log_level,
		structlog.processors.TimeStamper(fmt="iso", utc=True),
	]

	if app_env == "dev":
		processors = shared_processors + [
			structlog.processors.CallsiteParameterAdder(
				parameters=[
					structlog.processors.CallsiteParameter.PATHNAME,
					structlog.processors.CallsiteParameter.LINENO,
				]
			),
			structlog.dev.ConsoleRenderer(),
		]
	else:
		processors = shared_processors + [
			structlog.processors.dict_tracebacks,
			structlog.processors.JSONRenderer(),
		]

	structlog.configure(
		processors=processors,
		wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
		logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
		cache_logger_on_first_use=True,
	)

	# Also set standard logging to INFO
	logging.basicConfig(level=logging.INFO)


def get_logger(module_name: str):
	return structlog.get_logger(module_name)