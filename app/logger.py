import logging

from google.cloud.logging_v2.handlers import StructuredLogHandler

from app.config import get_settings


def build_logger() -> logging.Logger:
    logger = logging.getLogger("mke-rag-query-service")
    logger.setLevel(get_settings().logging_level)
    logger.propagate = False

    if not logger.handlers:
        # Structured JSON to stdout; Cloud Run/GCP ingests this automatically.
        handler = StructuredLogHandler()
        logger.addHandler(handler)

    return logger


logger = build_logger()
