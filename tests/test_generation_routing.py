import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("PROJECT_ID", "test-project")

from app import generation_routing
from app.models import RetrievalPlan


def test_generate_retrieval_plan_returns_composable_plan(monkeypatch) -> None:
    captured_request = {}
    plan = RetrievalPlan(
        use_provided_data=True,
        structured_query=True,
        vector_search=True,
        use_hyde=True,
        reasoning="Use property data, structured records, and municipal documents.",
    )

    class Models:
        def generate_content(self, **kwargs):
            captured_request.update(kwargs)
            return SimpleNamespace(parsed=plan)

    monkeypatch.setattr(
        generation_routing,
        "get_genai_client",
        lambda: SimpleNamespace(models=Models()),
    )

    result = generation_routing.generate_retrieval_plan(
        "What zoning requirements apply to this property?",
        [{"taxkey": "123", "zoning": "RS6"}],
    )

    assert result == plan
    assert "What zoning requirements apply to this property?" in captured_request["contents"]
    assert "RS6" in captured_request["contents"]
    assert captured_request["config"].response_schema is RetrievalPlan


def test_generate_retrieval_plan_rejects_empty_response(monkeypatch) -> None:
    class Models:
        def generate_content(self, **kwargs):
            return SimpleNamespace(parsed=None)

    monkeypatch.setattr(
        generation_routing,
        "get_genai_client",
        lambda: SimpleNamespace(models=Models()),
    )

    with pytest.raises(RuntimeError, match="generation failed"):
        generation_routing.generate_retrieval_plan("Hello")
