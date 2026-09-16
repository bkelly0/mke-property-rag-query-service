import logging
from typing import Any

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


def log_model_usage(
    response: Any,
    operation: str,
    model: str,
) -> None:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        logger.debug("No usage metadata returned for %s", operation)
        return

    def usage_value(name: str) -> int:
        value = getattr(usage, name, 0) or 0
        return int(value)

    input_tokens = usage_value("prompt_token_count")
    output_tokens = usage_value("candidates_token_count")
    thought_tokens = usage_value("thoughts_token_count")
    tool_tokens = usage_value("tool_use_prompt_token_count")
    total_tokens = usage_value("total_token_count")

    logger.info(
        "model_usage",
        extra={
            "operation": operation,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "thought_tokens": thought_tokens,
            "tool_use_prompt_tokens": tool_tokens,
            "total_tokens": total_tokens,
        },
    )