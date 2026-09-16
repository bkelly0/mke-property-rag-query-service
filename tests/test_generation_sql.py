import os
from types import SimpleNamespace

os.environ.setdefault("PROJECT_ID", "test-project")

from app import generation_sql
from app.models import AggregateSpec, FilterSpec, PropertyQueryPlan


def test_neighborhood_count_uses_selected_property_context(monkeypatch) -> None:
    captured_request = {}
    plan = PropertyQueryPlan(
        filters=[
            FilterSpec(
                field="neighborhood",
                operator="=",
                value="Avenues West",
            )
        ],
        aggregates=[
            AggregateSpec(
                function="count",
                field=None,
                alias="property_count",
            )
        ],
    )

    class Models:
        def generate_content(self, **kwargs):
            captured_request.update(kwargs)
            return SimpleNamespace(parsed=plan, usage_metadata=None)

    monkeypatch.setattr(
        generation_sql,
        "get_genai_client",
        lambda: SimpleNamespace(models=Models()),
    )

    sql, parameters = generation_sql.generate_property_query(
        "how many properties are in the same neighborhood as this property?",
        [{"taxkey": "123", "neighborhood": "Avenues West"}],
    )

    assert "Avenues West" in captured_request["contents"]
    assert "must use a count aggregate" in captured_request["contents"]
    assert "COUNT(*) AS property_count" in sql
    assert "LIMIT" not in sql
    assert parameters == {"filter_0": "Avenues West"}