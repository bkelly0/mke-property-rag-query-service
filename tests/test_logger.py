import io
import json
import os
from types import SimpleNamespace

from google.cloud.logging_v2.handlers import StructuredLogHandler

os.environ.setdefault("PROJECT_ID", "test-project")

from app.logger import log_model_usage, logger


def test_log_model_usage_emits_structured_fields(monkeypatch) -> None:
    stream = io.StringIO()
    monkeypatch.setattr(logger, "handlers", [StructuredLogHandler(stream=stream)])
    response = SimpleNamespace(
        usage_metadata=SimpleNamespace(
            prompt_token_count=11,
            candidates_token_count=7,
            thoughts_token_count=3,
            tool_use_prompt_token_count=2,
            total_token_count=23,
        )
    )

    log_model_usage(response, "routing", "gemini-test")

    payload = next(
        json.loads(line)
        for line in stream.getvalue().splitlines()
        if '"message": "model_usage"' in line
    )
    assert payload == payload | {
        "operation": "routing",
        "model": "gemini-test",
        "input_tokens": 11,
        "output_tokens": 7,
        "thought_tokens": 3,
        "tool_use_prompt_tokens": 2,
        "total_tokens": 23,
    }